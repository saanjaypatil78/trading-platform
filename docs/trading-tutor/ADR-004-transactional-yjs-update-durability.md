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

The official provider API passes its `token` to server authentication. Source inspection of the current Hocuspocus v4 implementation shows that `Connection.processMessages()` awaits `beforeHandleMessage`, then awaits `MessageReceiver.apply()`. For Yjs sync frames, `MessageReceiver.readSyncMessage()` awaits `beforeSync` before dispatching SyncStep2/YjsUpdate to `readSyncStep2()`/`readUpdate()`; the success sync-status response is sent after the apply call. The document's Yjs update listener broadcasts synchronously during apply when `flushDelay: false`. Therefore `beforeSync` is the more precise durability hook: it exposes the sync subtype and decoded payload, allowing only actual Yjs content updates to be journaled before apply. This source-level order supports the design, but does not replace a pinned-version wire/integration test. See:

- https://tiptap.dev/docs/hocuspocus/server/hooks
- https://www.npmjs.com/package/@hocuspocus/provider
- https://tiptap.dev/docs/hocuspocus/guides/persistence
- https://github.com/ueberdosis/hocuspocus/blob/main/RELEASE_NOTES_V4.md

## Proposed update pipeline

For each inbound document update:

1. Hocuspocus authenticates the provider's token through `onAuthenticate`. The token is the existing 60-second one-time credential; do not place it in a URL, query parameter, or application log.
2. Authentication consumes the credential exactly once and binds immutable server context: session ID, user ID, workspace ID, document ID, role, and membership version. The client must not choose or override these fields.
3. Use `beforeSync` as the primary journal hook. It provides `type` and a decoded `payload`. Persist only y-protocols SyncStep2 (type 1) and YjsUpdate (type 2). Do not persist SyncStep1 (type 0), awareness, stateless, or query-awareness messages as document content. Keep `beforeHandleMessage` for message-level limits/validation, not payload extraction.
4. Open a PostgreSQL transaction. Lock in the established global order: active workspace membership row first, collaboration session row second, document row third. Revalidate that the session is consumed, unrevoked, open, scoped to this document, and that membership is still active with the same membership version and a role allowed to edit. Also reject if the Hocuspocus connection is read-only; the provider's read-only check occurs later in sync handling, so this journal hook must not rely on it to protect persistence.
5. Validate the Yjs payload by applying it to an isolated scratch Y.Doc before committing. Reject malformed payloads and enforce message/byte limits before persistence.
6. Derive a deterministic update idempotency key from the authenticated session ID, document ID, and exact update bytes. Use a collision-resistant digest and encode it into the schema's UUID field with UUID version/variant bits set. This makes a byte-identical retry from the same session id idempotent; it does not trust a client-supplied update ID.
7. Under the document row lock, allocate the next monotonic content revision. Insert the exact binary update payload into `document_updates` and the corresponding audit event with the same idempotency key in the same transaction. Enforce unique update/audit keys. A duplicate insert must not allocate a new revision or duplicate the audit event.
8. Commit PostgreSQL successfully before returning from `beforeSync`. If authorization, validation, insert, or commit fails, throw/reject so Hocuspocus does not apply or broadcast that update.
9. After `beforeSync` returns successfully, Hocuspocus applies the update. The Yjs document update listener broadcasts it (synchronously when `flushDelay: false`), then the sync handler sends its success status. The actual wire ordering still requires an integration test.
9. Periodically create binary Yjs snapshots from the document state and persist them with provider/version metadata. Snapshots are a recovery optimization, not the source of truth; replay retained append-only updates after the snapshot revision.
10. On process restart, load the latest valid binary snapshot and replay subsequent committed updates before accepting connections.

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
5. Verify malformed update payloads are rejected before they are journaled.
6. Crash the process after commit and before apply; restart and prove the update is recovered exactly once.
7. Force apply/broadcast failure after commit; prove all affected connections are closed and the document is reloaded before another update is accepted.
8. Replay identical bytes and verify one update row, one audit row, and no duplicate revision.
9. Send two different updates concurrently from two users and verify monotonic revisions and converged Yjs state.
10. Race member revocation against a document update and prove there is no post-revocation committed update.
11. Verify VIEWER can read but cannot write, including attempts through raw WebSocket frames and the preSync hook.
12. Verify binary snapshot + update replay reconstructs the same Yjs state as two connected clients.
13. Verify payload/message/connection limits, rate limiting, graceful shutdown, and recovery under process restart.

## Decision boundary

The current v4 source establishes a promising internal order: `beforeSync` is awaited before `readSyncStep2`/`readUpdate`; Yjs apply triggers the document update listener and broadcast; the sync-success frame is sent after the apply call. However, this source review used the repository's current main branch, not a package version pinned in this project. The team must pin a release and test actual wire behavior. If the provider sends a success response or broadcasts before the pre-apply journal transaction completes, or if apply failure cannot force a safe document reload, reject this integration approach and implement a custom transport/protocol adapter or evaluate another provider.

No production provider decision is made by this ADR. TASK-002 remains incomplete until all mandatory tests pass, code review is complete, and the full frontend/backend acceptance suite succeeds.
