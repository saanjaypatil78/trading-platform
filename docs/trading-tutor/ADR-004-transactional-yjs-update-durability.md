# ADR-004 — Transactional Yjs update durability with Hocuspocus

**Status:** Proposed integration-spike design; not implemented or approved for production  
**Date:** 2026-10-31  
**Scope:** TASK-002 only. This ADR does not authorize TASK-003, production deployment, or live collaboration.

## Context

The existing collaboration schema already has append-only `document_updates`, append-only `collaboration_audit_events`, one-time document credentials, membership versions, and a Python helper that locks an active session while leaving the SQLAlchemy transaction open. Hocuspocus v4 exposes:

- `onAuthenticate` for provider token authentication;
- `beforeHandleMessage`, which runs before an inbound message is applied and may reject it;
- `afterHandleMessage`, which runs after the inbound message has been handled/applied;
- `onStoreDocument`, which is debounced persistence;
- ordered inbound message processing per connection.

The official provider API passes its `token` to server authentication. The official hook documentation describes `beforeHandleMessage` as the pre-apply interception point and `afterHandleMessage` as post-apply. Hocuspocus v4 release notes document ordered per-connection message processing. These facts make a pre-apply durable update journal a plausible design, but do not prove end-to-end acknowledgement semantics. See:

- https://tiptap.dev/docs/hocuspocus/server/hooks
- https://www.npmjs.com/package/@hocuspocus/provider
- https://tiptap.dev/docs/hocuspocus/guides/persistence
- https://github.com/ueberdosis/hocuspocus/blob/main/RELEASE_NOTES_V4.md

## Proposed update pipeline

For each inbound document update:

1. Hocuspocus authenticates the provider's token through `onAuthenticate`. The token is the existing 60-second one-time credential; do not place it in a URL, query parameter, or application log.
2. Authentication consumes the credential exactly once and binds immutable server context: session ID, user ID, workspace ID, document ID, role, and membership version. The client must not choose or override these fields.
3. In `beforeHandleMessage`, classify the inbound message. Only a decoded Yjs document update enters the durable-update path; sync negotiation and awareness messages must not be recorded as document edits.
4. Open a PostgreSQL transaction. Lock in the established global order: active workspace membership row first, collaboration session row second, document row third. Revalidate that the session is consumed, unrevoked, open, scoped to this document, and that membership is still active with the same membership version and a role allowed to edit.
5. Derive a deterministic update idempotency key from the authenticated session ID, document ID, and exact update bytes. Use a collision-resistant digest and encode it into the schema's UUID field with UUID version/variant bits set. This makes a byte-identical retry from the same session idempotent; it does not trust a client-supplied update ID.
6. Under the document row lock, allocate the next monotonic content revision. Insert the exact binary update bytes into `document_updates` and the corresponding audit event with the same idempotency key in the same transaction. Enforce unique update/audit keys. A duplicate insert must not allocate a new revision or duplicate the audit event.
7. Commit PostgreSQL successfully before returning from `beforeHandleMessage`. If authorization, validation, insert, or commit fails, throw/reject so Hocuspocus does not apply or broadcast that update.
8. Only after the pre-apply hook returns successfully may Hocuspocus apply and broadcast the update. The server's normal protocol response is not to be described as a durable acknowledgement until the exact v4 message path is proven by tests.
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
2. Verify the exact `beforeHandleMessage` callback ordering relative to apply, broadcast, and server responses for every supported inbound update message type.
3. Prove PostgreSQL commit occurs before any peer receives the update.
4. Inject database connection loss, constraint errors, deadlocks, and transaction timeouts; verify no apply/broadcast on pre-apply failure.
5. Crash the process after commit and before apply; restart and prove the update is recovered exactly once.
6. Force apply/broadcast failure after commit; prove all affected connections are closed and the document is reloaded before another update is accepted.
7. Replay identical bytes and verify one update row, one audit row, and no duplicate revision.
8. Send two different updates concurrently from two users and verify monotonic revisions and converged Yjs state.
9. Race member revocation against a document update and prove there is no post-revocation committed update.
10. Verify VIEWER can read but cannot write, including attempts through raw WebSocket frames.
11. Verify binary snapshot + update replay reconstructs the same Yjs state as two connected clients.
12. Verify payload/message/connection limits, rate limiting, graceful shutdown, and recovery under process restart.

## Decision boundary

This design is a testable hypothesis, not a guarantee supplied by Hocuspocus. In particular, the team must inspect the pinned v4 implementation and capture actual wire behavior. If the provider sends a success response or broadcasts before the pre-apply hook's durable transaction completes, or if apply failure cannot force a safe document reload, reject this integration approach and implement a custom transport/protocol adapter or evaluate another provider.

No production provider decision is made by this ADR. TASK-002 remains incomplete until all mandatory tests pass, code review is complete, and the full frontend/backend acceptance suite succeeds.
