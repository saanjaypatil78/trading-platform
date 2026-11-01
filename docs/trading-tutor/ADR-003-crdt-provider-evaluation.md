# ADR-003 — CRDT collaboration provider evaluation

**Status:** Conditional candidate selected for a time-boxed integration spike; production provider decision remains open  
**Date:** 2026-10-31  
**Scope:** TASK-002 only. This ADR does not enable live collaboration, authorize TASK-003, or approve production deployment.

## Decision summary

Evaluate **Hocuspocus v4** first as the leading candidate for the TASK-002 CRDT spike. Do not yet pin or ship it as the production provider.

The repository already uses a TypeScript/Next.js frontend and PostgreSQL-backed Python services. Hocuspocus is a TypeScript Yjs WebSocket backend with authentication hooks, document lifecycle hooks, configurable WebSocket limits, and a generic persistence extension point. Its current major version requires Node.js 22+. A separate collaboration process/container is therefore the likely integration boundary; do not embed it in the existing anonymous market-data WebSocket service.

**Y-Sweet remains the alternative** if the project chooses an S3-compatible binary-document store and its deployment/token model proves easier to operate. It is MIT-licensed and supports horizontal scaling and document-scoped client tokens, but its documented persistence target is S3-compatible storage rather than the existing PostgreSQL append-only update/audit model.

## Evidence reviewed

### Hocuspocus

- Official repository identifies Hocuspocus as a Yjs collaboration backend and publishes it under the MIT license: https://github.com/ueberdosis/hocuspocus
- Current package documentation identifies Node.js 22+ and the built-in WebSocket server: https://www.npmjs.com/package/@hocuspocus/server
- Authentication is performed through `onAuthenticate`; the provider supplies a token and the server may reject the connection. The provider configuration exposes a token option: https://tiptap.dev/docs/hocuspocus/guides/authentication and https://tiptap.dev/docs/hocuspocus/provider/configuration
- `beforeHandleMessage` runs before an inbound message is applied and can reject it. `afterHandleMessage` runs after it has been handled. These hooks are promising for revalidation, but do not by themselves prove an atomic PostgreSQL commit-before-client-ack guarantee: https://tiptap.dev/docs/hocuspocus/server/hooks
- `onLoadDocument` and `onStoreDocument` support persistence. The documented store hook is debounced; Yjs binary state must be persisted as binary rather than converting to JSON and reconstructing a Y.Doc: https://tiptap.dev/docs/hocuspocus/guides/persistence
- The Redis extension synchronizes changes/awareness between instances but explicitly does not persist documents: https://tiptap.dev/docs/hocuspocus/server/extensions/redis
- v4 adds ordered per-connection message processing and requires Node.js 22+: https://tiptap.dev/blog/release-notes/hocuspocus-4-stable-release
- The server exposes limits for unauthenticated queued bytes/messages, pending documents, timeout, and WebSocket payload size: https://tiptap.dev/docs/hocuspocus/server/configuration

### Y-Sweet

- Y-Sweet is a Yjs document store with S3-compatible persistence, horizontal scaling, document-level client tokens, and an MIT license: https://github.com/jamsocket/y-sweet
- Self-hosting supports local disk or S3-compatible storage and provides a Docker image: https://github.com/jamsocket/y-sweet/blob/main/docs/running.md

## Why Hocuspocus is the first spike candidate

1. Its TypeScript server and provider align with the existing Next.js/TypeScript frontend.
2. Its hooks allow server-side authentication and pre-message checks.
3. Its generic persistence hooks can be adapted to the existing PostgreSQL schema without introducing an object-store dependency for the first release.
4. It can run as a separately isolated collaboration service, keeping the Python API responsible for identity, membership, one-time credential issuance, and revocation.
5. The MIT license is compatible with the repository's open-source preference.

This is an engineering candidate, not a claim that the provider already meets the project's durability or security requirements.

## Non-negotiable integration constraints

- The Python API remains the authority for Supabase identity, workspace membership, role, document scope, and credential issuance.
- The existing 60-second, one-time credential primitive must be exposed only through an authenticated HTTPS endpoint after the collaboration handshake path is ready.
- The collaboration service must consume the credential exactly once and bind the resulting context to user, workspace, document, and membership version.
- The raw credential must never be placed in a WebSocket URL, browser logs, analytics, or persistent storage. Confirm the exact Hocuspocus provider wire protocol in an integration test before adopting its token option.
- Every accepted update must be associated with a verified actor and an idempotency key. PostgreSQL update history and audit events remain append-only.
- Active membership revocation must prevent subsequent writes, including on already-established sockets.
- The update must not be acknowledged as durable until the update and its audit record have committed. A debounced document snapshot is not a substitute for per-update durable history.
- If the provider applies an update in memory and the PostgreSQL transaction subsequently fails, the server must not continue broadcasting or serving a divergent in-memory state. Recovery behavior must be proven, not assumed.
- Redis may be considered for cross-instance synchronization only after durable persistence and revocation semantics are correct. Redis pub/sub is not the source of truth.
- Keep market-data WebSocket traffic and collaboration traffic isolated.

## Required proof-of-concept gates

The spike must implement and test the following before provider selection is finalized:

1. **Handshake protocol:** capture the actual WebSocket frames and prove the one-time credential is sent in the first authentication message, not in the URL or an upgrade header that leaks into logs.
2. **Credential lifecycle:** prove expired, replayed, wrong-document, revoked, stale-membership-version, and concurrent-consumption cases fail closed.
3. **Per-update authorization:** prove every document update revalidates the active session and current membership; revocation races are serialized with update persistence.
4. **Durable ordering:** inject PostgreSQL latency, constraint failures, disconnects, and process crashes. Demonstrate that no client receives a durable acknowledgement before the update and audit commit.
5. **In-memory rollback/recovery:** force a database failure after the provider has received an update. Prove the server cannot continue from an uncommitted divergent state; verify restart/reload recovery.
6. **Idempotency:** replay the same update and prove the document and audit history are not duplicated.
7. **Reconnect:** restart the provider and reconnect two clients from PostgreSQL binary state plus retained updates; both clients must converge.
8. **Concurrency:** two authenticated users concurrently insert/delete text and converge to identical Yjs state.
9. **Limits:** verify payload size, message rate, connection rate, unauthenticated buffering, document fan-out, and handshake timeout.
10. **Frontend integration:** prove the chosen provider works with the existing React/Next.js version and the selected Markdown editor without changing approved indicator settings or trading behavior.
11. **Deployment:** build a dedicated Node.js 22+ collaboration image and prove the target host supports long-lived WebSockets, health checks, graceful shutdown, and persistent PostgreSQL connectivity.
12. **License/dependency review:** pin exact tested versions, inspect transitive licenses and advisories, and record an upgrade policy.

## Provider decision matrix

| Requirement | Hocuspocus v4 | Y-Sweet |
|---|---|---|
| Yjs CRDT sync | Documented | Documented |
| License | MIT | MIT |
| Frontend fit | TypeScript provider | TypeScript SDK/client/React packages |
| Server runtime | Node.js 22+ or supported alternative runtimes | Native Rust server |
| Authentication | Server hook and provider token option | Document-scoped client tokens |
| Persistence model | Custom hooks/database extension; binary Yjs state | S3-compatible object storage |
| Horizontal sync | Redis extension; Redis is not persistence | Session backend model |
| Fit with existing PostgreSQL append-only update/audit schema | Promising, but transaction/ack semantics unproven | Requires a separate PostgreSQL audit/update integration |
| Current decision | First spike candidate only | Retain as alternative |

## Exit criteria and status

No provider is approved for production until every proof-of-concept gate passes and the resulting implementation, tests, and evidence are reviewed as part of TASK-002.

Until then:
- live shared editing remains disabled/read-only;
- no anonymous collaboration endpoint is permitted;
- no TASK-003 implementation may begin;
- no claim of production-ready collaboration is valid.
