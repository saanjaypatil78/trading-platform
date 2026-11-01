# ADR-004 — Transactional Yjs update durability with Hocuspocus

**Status:** Proposed integration-spike design; not implemented or approved for production  
**Date:** 2026-10-31  
**Scope:** TASK-002 only. This ADR does not authorize TASK-003, production deployment, or live collaboration.

## Context

The existing collaboration schema already has append-only `document_updates`, append-only `collaboration_audit_events`, one-time document credentials, membership versions, and a Python helper that locks an active session while leaving the SQLAlchemy transaction open. Hocuspocus v4 exposes:

- `onAuthenticate` for provider token authentication;
- `beforeHandleMessage`, which runs before an inbound message is applied and may reject it;
- `beforeSync`, which receives the decoded y-protocols sync subtype and its payload before sync processing;
- `afterHandleMessage`, which runs after the inbound message has been handled/applied;
- `onStoreDocument`, which is debounced persistence;
- ordered inbound message processing per connection.

The official provider API sends its `token` in the Hocuspocus authentication protocol message (not as a URL parameter). This ADR now pins its source review to **`@hocuspocus/server` v4.7.0**, signed release tag commit **`6ddc757`** (2026-09-09), rather than the moving `main` branch. In that source, `Connection.processMessages()` awaits `beforeHandleMessage`, then awaits `MessageReceiver.apply()`. For Yjs sync frames, `MessageReceiver.readSyncMessage()` awaits `beforeSync` with `{ type, payload: message.peekVarUint8Array() }` before dispatching SyncStep2/YjsUpdate to `readSyncStep2()`/`readUpdate()`. The payload is the raw varuint8array content after the sync subtype; SyncStep1 (type 0) must not be journaled as document content. `readSyncStep2()`/`readUpdate()` apply synchronously; the document update callback and broadcast run during apply when `flushDelay: false`, and the sync-status success frame is sent after apply. Hocuspocus v4.7.0 also serializes inbound messages per connection and closes/clears the queue when a hook throws. Therefore `beforeSync` is the most precise pre-apply durability hook. This is a pinned source-code finding, not a substitute for a wire-level integration test. See:

- https://tiptap.dev/docs/hocuspocus/server/hooks
- https://www.npmjs.com/package/@hocuspocus/provider
- https://tiptap.dev/docs/hocuspocus/guides/persistence
- https://github.com/ueberdosis/hocuspocus/blob/v4.7.0/packages/server/src/Connection.ts
- https://github.com/ueberdosis/hocuspocus/blob/v4.7.0/packages/server/src/MessageReceiver.ts
- https://github.com/ueberdosis/hocuspocus/blob/v4.7.0/packages/server/src/Document.ts
- https://github.com/ueberdosis/hocuspocus/blob/v4.7.0/packages/server/src/ClientConnection.ts
- https://github.com/ueberdosis/hocuspocus/blob/v4.7.0/packages/provider/src/HocuspocusProvider.ts
- https://github.com/ueberdosis/hocuspocus/blob/v4.7.0/RELEASE_NOTES_V4.md

## Proposed update pipeline

For each inbound document update:

1. Hocuspocus authenticates the provider's token through `onAuthenticate`. The token is the existing 60-second one-time credential; do not place it in a URL, query parameter, or application log.
2. Authentication consumes the credential exactly once and binds immutable server context: session ID, user ID, workspace ID, document ID, role, and membership version. The client must not choose or override these fields.
3. Use `beforeSync` as the primary journal hook. It provides `type` and a decoded `payload`. Persist only y-protocols SyncStep2 (type 1) and YjsUpdate (type 2). Do not persist SyncStep1 (type 0), awareness, stateless, or query-awareness messages as document content. Keep `beforeHandleMessage` for message-level limits/validation, not payload extraction.
4. Open a PostgreSQL transaction. Lock in the established global order: active workspace membership row first, collaboration session row second, document row third. Revalidate that the session is consumed, unrevoked, open, scoped to this document, and that membership is still active with the same membership version and a role allowed to edit. Also reject if the Hocuspocus connection is read-only; the provider's read-only check occurs later in sync handling, so this journal hook must not rely on it to protect persistence.
5. While holding the document row lock, create an isolated scratch Y.Doc initialized from the current in-memory document state (`encodeStateAsUpdate`/`applyUpdate`), attach an update listener, and apply the inbound payload to the scratch document. Reject malformed payloads and enforce message/byte limits before persistence. If the payload produces no new Yjs structs, treat it as a valid no-op and do not allocate a revision or append a journal row. Destroy the scratch document in a `finally` block. This validation must use the same locked document revision that the transaction will journal against.
6. Derive a deterministic update idempotency key from the authenticated session ID, document ID, and exact update bytes. Use a collision-resistant digest and encode it into the schema's UUID field with UUID version/variant bits set. This makes a byte-identical retry from the same session id idempotent; it does not trust a client-supplied update ID.
7. Under the document row lock, allocate the next monotonic content revision. Insert the exact binary update payload into `document_updates` and the corresponding audit event with the same idempotency key in the same transaction. Enforce unique update/audit keys. A duplicate insert must not allocate a new revision or duplicate the audit event.
8. Commit PostgreSQL successfully before returning from `beforeSync`. If authorization, validation, insert, or commit fails, throw/reject so Hocuspocus does not apply or broadcast that update.
9. After `beforeSync` returns successfully, Hocuspocus applies the update. Configure `flushDelay: false` explicitly: the Yjs document update callback and peer broadcast then run synchronously during apply, and the sync handler sends its success status after apply. Do not rely on the default `flushDelay: 0`, which coalesces broadcasts using `setImmediate` and has different timing. The actual wire ordering still requires an integration test.
10. Periodically create binary Yjs snapshots from the document state and persist them with provider/version metadata. Snapshots are a recovery optimization, not the source of truth; replay retained append-only updates after the snapshot revision.
11. On process restart, load the latest valid binary snapshot and replay subsequent committed updates before accepting connections.

## Failure semantics

| Failure point | Required behavior |
|---|---|
| Invalid, expired, replayed, wrong-document, revoked, or stale-version credential | Reject handshake; do not load/edit the document |
| Membership revoked while socket is open | Membership row lock serializes revocation against update transaction; subsequent updates fail |
| PostgreSQL unavailable or transaction fails | Reject before in-memory apply/broadcast; do not acknowledge |
| Client retries an already committed identical update | Idempotency key prevents duplicate journal/audit rows; applying the same Yjs update remains idempotent |
| Process crashes after commit but before in-memory apply | Restart reconstructs state from committed snapshot plus update journal |
| Apply/broadcast fails after journal commit | Close affected document connections and reload from durable state before serving more updates; do not continue with divergent memory |
| Snapshot write fails | Keep append-only update journal authoritative; retry snapshot without losing committed updates |

## Required schema and implementation checks

- Keep `document_updates` and `collaboration_audit_events` append-only.
- Ensure audit `idempotency_key` is unique and maps to the update's deterministic key.
- Confirm document revision allocation is serialized by a PostgreSQL row lock; never rely on process-local counters.
- Confirm every transaction locks membership -> session -> document in that order. Revocation must use a compatible order.
- Verify the existing append-only triggers permit inserts and reject updates/deletes.
- Validate message type and size before persistence; enforce byte, rate, connection, and per-document limits.
- Reject viewer-role updates even though viewers may receive read credentials.
- Do not persist awareness/presence as document content.
- Keep the Python API as identity/credential authority and PostgreSQL as the durable source of truth. The Node service is a constrained transport/CRDT adapter, not an independent authorization authority.

## Mandatory proof tests

1. Capture provider/server frames and verify the token is sent in the Hocuspocus authentication message, never in the URL.
2. Pin the exact Hocuspocus v4 package version and test that `beforeSync` receives subtype 0/1/2 and the expected decoded payload bytes.
3. Prove PostgreSQL commit inside `beforeSync` occurs before Yjs apply, peer broadcast, and the success sync-status frame.
4. Inject database connection loss, constraint errors, deadlocks, and transaction timeouts; verify no apply/broadcast/success status on pre-apply failure.
4a. Overlap updates from two sockets and two server instances; prove document-wide serialization/fencing and committed-state ordering, not merely per-connection ordering.
5. Verify malformed update payloads are rejected before they are journaled.
6. Crash the process after commit and before apply; restart and prove the update is recovered exactly once.
7. Force apply/broadcast failure after commit; prove all affected connections are closed and the document is reloaded before another update is accepted.
8. Replay identical bytes and verify one update row, one audit row, and no duplicate revision.
9. Send two different updates concurrently from two users and verify monotonic revisions and converged Yjs state.
10. Race member revocation against a document update and prove there is no post-revocation committed update.
11. Verify VIEWER can read but cannot write, including attempts through raw WebSocket frames and the beforeSync hook.
12. Verify binary snapshot + update replay reconstructs the same Yjs state as two connected clients.
13. Verify payload/message/connection limits, rate limiting, graceful shutdown, and recovery under process restart.
14. Verify SyncStep2 no-op/retransmission behavior: a valid duplicate that introduces no new Yjs structs must not allocate a revision or duplicate an audit record.

## Decision boundary

The pinned v4.7.0 source establishes the internal order described above. The repository must still add a pinned dependency and executable wire tests for actual frames, broadcast ordering, no-op SyncStep2 behavior, and failure recovery. The source review alone does not prove that a complete client/server session behaves as expected. If the provider sends a success response or broadcasts before the pre-apply journal transaction completes, or if apply failure cannot force a safe document reload, reject this integration approach and implement a custom transport/protocol adapter or evaluate another provider.

No production provider decision is made by this ADR. TASK-002 remains incomplete until all mandatory tests pass, code review is complete, and the full frontend/backend acceptance suite succeeds.


## Critical concurrency invariant — not yet proven

The per-connection inbound queue in Hocuspocus v4.7.0 does **not** establish a global per-document queue across different WebSocket connections or different server processes. A PostgreSQL row lock serializes journal transactions, but it does not serialize mutations to a process-local in-memory `Y.Doc`. Therefore, the scratch-document validation described in step 5 is unsafe if it reads a stale or concurrently-mutating in-memory state.

Before implementing the journal hook, the spike must choose and prove one of these models:

1. **Single-writer document ownership:** a distributed, fenced lease assigns each document to exactly one collaboration process. All inbound updates for that document pass through one per-document serial queue. A process that loses its lease must stop accepting updates immediately. The lease must be fenced so an expired owner cannot continue committing.
2. **Canonical transaction-driven state:** validate against a state reconstructed from the committed snapshot/update log under the document lock, and ensure provider apply/broadcast is serialized with that committed revision. Do not use a potentially stale process-local document as the validation authority.
3. **Reject Hocuspocus for this persistence contract:** if its hooks cannot provide the required cross-connection ordering and fencing, use a custom transport/adapter or another provider.

Required concurrency tests must use at least two clients on the same document and, separately, two server instances. Force overlapping `beforeSync` hooks, delayed commits, process lease expiry, and concurrent updates. Assert that each applied in-memory state is a prefix of the committed revision order, no update is lost, and no client receives a success response for an update that the authoritative state cannot recover.

This is a blocking design issue, not a minor optimization. The current Hocuspocus source audit proves per-connection ordering only; it does not prove document-wide or cluster-wide serialization.
