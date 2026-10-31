# ADR-002 — Workspace authorization and database migrations

**Status:** Accepted engineering direction; implementation pending
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
- `collaboration_sessions`: opaque session ID, hashed one-time credential, user/workspace/document scope, membership version, expiry, revocation timestamp, creation timestamp. Raw credentials are never persisted or logged.
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

## Consequences

Alembic is selected because it is already a pinned dependency and matches the existing SQLAlchemy data layer. The workspace schema and role policy are now defined, but no migration, ORM persistence, membership API, WebSocket session implementation, or CRDT provider has been implemented by this ADR.

## Required verification before TASK-002 can pass

1. Alembic upgrade/downgrade and migration-head checks against PostgreSQL.
2. Workspace creation atomically creates exactly one OWNER membership.
3. Every role/permission matrix case has API-level tests.
4. Cross-workspace document access is denied.
5. Owner transfer and last-owner protection are tested.
6. Expired, replayed, wrong-document, and revoked collaboration credentials are rejected.
7. An active session cannot continue writing after membership revocation.
8. Audit and document update records are append-only and idempotent.
9. PostgreSQL integration tests cover constraints, concurrent membership changes, and transaction rollback.
10. No browser path can bypass backend authorization.
