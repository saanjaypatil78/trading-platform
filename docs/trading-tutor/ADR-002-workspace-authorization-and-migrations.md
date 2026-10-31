# ADR-002 — Workspace authorization and database migrations

**Status:** Accepted engineering direction; schema, RBAC, workspace/document API, credential primitives, and member-revocation API implemented; WebSocket transport/CRDT pending
**Date:** 2026-10-31
**Scope:** TASK-002 only. This ADR does not authorize TASK-003 or production collaboration.

## Context

The repository already depends on SQLAlchemy 2.x and Alembic, and exposes a shared SQLAlchemy `Base`/session factory in `backend/shared/database.py`. No Alembic configuration or migration history was found on the TASK-002 branch. Supabase Auth identity verification is implemented, but it does not establish workspace membership or document permissions.

The application must not rely on browser-supplied workspace roles, document ownership, or task status. The collaboration service must fail closed when membership or session state cannot be verified.

## Decisions

### 1. Migration ownership

- Adopt Alembic as the single schema migration mechanism for the backend PostgreSQL database.
- Keep migration configuration and revisions under `backend/migrations/`, with `backend/alembic.ini`.
- Alembic's `env.py` must import the existing shared SQLAlchemy `Base` and all registered ORM model modules before reading `Base.metadata`.
- Use explicit, reviewed migration revisions. Do not call `Base.metadata.create_all()` during application startup or use ad-hoc production SQL as a substitute for migrations.
- Generate migrations against the actual PostgreSQL dialect. SQLite may be used only for tests where its behavior is compatible; PostgreSQL integration tests remain required for UUID, JSONB, constraints, indexes, and transaction semantics.
- Migration execution is a release/deployment step, not an implicit side effect of importing or starting an API process.
- Existing tables are not to be retroactively adopted or rewritten in this TASK-002 migration without a separately reviewed baseline plan.

### 2. Identity and membership boundary

- Supabase Auth remains the identity provider. The backend accepts only the verified UUID returned by the existing Supabase Auth user-validation dependency.
- A verified identity is not a workspace permission.
- Store workspace membership and roles in the backend PostgreSQL database. Never accept a role, owner ID, reviewer flag, or membership state from the browser as authoritative.
- Do not add a foreign key from `workspace_members.user_id` to `auth.users`: the configured `DATABASE_URL` may point to a PostgreSQL database separate from the Supabase Auth project. Validate the UUID identity at the API boundary instead.
- Every document read, write, export, workflow transition, collaboration join, and collaboration update must resolve active membership server-side.
- If membership storage is unavailable, deny access; do not fall back to public or anonymous access.

### 3. Initial workspace roles

Use these fixed roles for the first implementation:

| Role | Read documents | Edit documents | Start/execute tasks | Approve task completion | Manage members |
|---|---:|---:|---:|---:|---:|
| OWNER | Yes | Yes | Yes | Yes | Yes |
| ADMIN | Yes | Yes | Yes | Yes | Yes, except owner transfer/removal |
| COACH | Yes | Yes | Yes | Yes | No |
| EDITOR | Yes | Yes | Yes | No | No |
| VIEWER | Yes | No | No | No | No |

- The workspace creator is inserted as OWNER in the same database transaction that creates the workspace.
- There must be exactly one active OWNER per workspace in the initial implementation. Owner transfer is a dedicated audited operation; deleting or demoting the last owner is prohibited.
- Membership revocation is immediate at the authorization layer. Existing collaboration sessions must stop authorizing further messages after revocation.
- Document access is inherited from active workspace membership in this initial version. Do not add per-document sharing until a separate policy is approved.

### 4. Persistence boundaries

The planned schema is:

- `workspaces`: immutable UUID, name/slug, creator UUID, timestamps, archived state.
- `workspace_members`: workspace UUID, user UUID, role, active/revoked state, membership version, timestamps; unique active membership per workspace/user.
- `markdown_documents`: immutable UUID, workspace UUID, document type, title, UTF-8 Markdown body, schema version, content revision, creator UUID, timestamps, archived state.
- `document_snapshots`: document UUID, CRDT provider/version metadata, opaque snapshot bytes, server timestamp, revision; never treat client state as a trusted snapshot.
- `document_updates`: document UUID, unique update/idempotency ID, actor UUID, opaque update bytes, server receipt timestamp. Updates are append-only and duplicate update IDs are rejected/idempotently acknowledged.
- `collaboration_sessions`: opaque session ID, hashed one-time credential, user/workspace/document scope, membership version, 60-second credential-establishment expiry, consumed/revoked/closed timestamps, and creation timestamp. Raw credentials are never persisted or logged. The expiry limits initial handshake only; closed_at records closure of an established socket.
- `collaboration_audit_events`: append-only event ID, workspace/document/actor IDs, event type, revision, server UTC timestamp, idempotency key, allow-listed metadata. No tokens or secrets.
- Task state transitions and completion evidence must be represented as append-only audit events; Markdown frontmatter is not authoritative state.

All tables must use explicit foreign keys within this schema, database constraints for uniqueness and valid enum values where practical, and indexes for workspace/document/session authorization lookups. Use timezone-aware UTC timestamps.

### 5. Collaboration credential and revocation protocol

- An authenticated HTTPS endpoint issues a cryptographically random, document-scoped, one-time WebSocket credential only after checking current membership and role.
- The credential is short-lived (60 seconds to establish the socket), stored only as a cryptographic hash, and delivered in the first WebSocket authentication frame over TLS; never put long-lived access tokens or collaboration credentials in URL query strings.
- The server validates and consumes the credential before joining a document room.
- The active session is bound to one user, workspace, document, role/membership version, and expiry.
- Every document update and workflow command must re-check session validity and current membership. A stale role or revoked membership fails closed. Session revocation invalidates all matching active sessions.
- Presence is informational and never grants access.
- Keep collaboration transport separate from the existing market-data WebSocket service. Do not reuse its anonymous endpoint or its non-Yjs protocol.

### 6. Security and operational constraints

- Browser clients never receive database credentials, Supabase service-role keys, raw session hashes, or server signing secrets.
- Do not expose collaboration tables to direct browser writes. If the database is Supabase-hosted, apply restrictive RLS as defense in depth; the backend authorization service remains mandatory.
- Apply payload-size, message-rate, connection-rate, and per-document concurrency limits.
- Do not acknowledge an update as durable until the database transaction commits.
- Database/provider failures disable shared editing or return a retryable error; they never trigger last-write-wins fallback.
- All role changes, membership revocations, task approvals, and document exports are auditable.

## Implementation evidence (2026-10-31)

- Added the Alembic environment and initial PostgreSQL migration under backend/alembic.ini and backend/migrations/.
- Collaboration ORM models register on the existing shared SQLAlchemy Base metadata.
- PostgreSQL 16 Actions runs #21 and #22 passed migration upgrade/downgrade and database invariant checks.
- The server-side RBAC service is implemented in backend/services/collaboration/authorization.py. Its full role matrix and fail-closed tests passed CI runs #23 and #24 (63 tests).
- Authenticated workspace/document endpoints are implemented in backend/services/collaboration/router.py and mounted by backend/unified_entrypoint.py.
- Workspace/document API CI runs #31 and #32 passed on commit c0171759d332ee00da088dbeb639d999a647180f (68 tests passed, 3 warnings, 0 failures).
- The API deliberately does not expose a Markdown body overwrite route. It can create and read documents, but shared editing remains unavailable until CRDT transport and persistence are complete.


## Credential and revocation implementation evidence (2026-10-31)

- Credential issuance and consumption primitives are implemented in the collaboration session service. The raw credential is returned only by the internal service; the current HTTP API does not expose it.
- PostgreSQL row locking and one-time consumption bind each credential to the exact user, workspace, document, and membership version. The active-session guard holds membership/session locks through the caller's durable update transaction. Session closure is idempotent and audited.
- The member-revocation service increments membership_version, revokes related sessions, and appends an audit event in one transaction.
- The authenticated member-revocation route is DELETE /api/v1/collaboration/workspaces/{workspace_id}/members/{member_user_id}. OWNER removal is rejected; the actor's MANAGE_MEMBERS permission is resolved from persisted active membership.
- PostgreSQL 16 CI runs #42 and #43 passed on commit 3735a009ed8e427b260f506290ab01ed1819e2d2: 79 tests, 3 warnings, 0 failures in each run.
- No collaboration WebSocket handshake, HTTP credential-issuance endpoint, CRDT provider/persistence integration, frontend editor, or deployment is implemented by these primitives.

## Consequences

Alembic is selected because it is already a pinned dependency and matches the existing SQLAlchemy data layer. The initial collaboration schema, workspace authorization service, read/create HTTP API, one-time credential primitives, active-session lock guard, idempotent session closure, and member-revocation API now exist. This ADR does not implement the credential-issuance HTTP endpoint, WebSocket handshake, per-message CRDT update path, provider synchronization/persistence, presence, reconnect, or frontend editor. It does not authorize TASK-003 or production collaboration.

## Required verification before TASK-002 can pass

1. Alembic upgrade/downgrade and migration-head checks against PostgreSQL.
2. Workspace creation atomically creates exactly one OWNER membership.
3. Every role/permission matrix case has API-level tests; cross-workspace access is denied.
4. Owner transfer and last-owner protection are tested end-to-end.
5. Expired, replayed, wrong-document, revoked, stale-version, and concurrent credential consumption are rejected safely.
6. WebSocket handshake accepts a credential only in the first TLS frame; malformed, late, replayed, and oversized frames are rejected.
7. Active-session update transactions serialize correctly with member revocation; durable update and audit commit before acknowledgement.
8. Session close, CRDT update replay, snapshot/reconnect, and append-only audit are verified against PostgreSQL.
9. Yjs provider compatibility, maintenance, license, hosting topology, and persistence behavior are pinned and verified.
10. PostgreSQL integration tests cover constraints, concurrent membership changes, rollback, and recovery.
11. No browser path can bypass backend authorization or write collaboration tables directly.
12. Full frontend/backend build and two-client concurrent convergence tests pass.
