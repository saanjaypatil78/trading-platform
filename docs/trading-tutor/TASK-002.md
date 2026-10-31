# TASK-002 — Shared Markdown execution and collaboration

**Status:** In progress — PostgreSQL collaboration schema, workspace RBAC, and initial authenticated workspace/document APIs implemented; CRDT collaboration remains pending  
**Priority:** P0  
**Depends on:** TASK-001  
**Branch:** codex/trading-tutor-task-002-markdown-collaboration

## Repository fit

The existing repository is a mixed application with FastAPI/Python backend services and a Next.js 14 + TypeScript frontend. Keep this task inside the existing stack; do not introduce a second frontend framework or replace the current backend.

## Objective

Create a shared workspace in which users and authorised coaches can collaboratively author Markdown learning notes, task specifications, research briefs, and execution checklists. A task must progress through an explicit, auditable sequential workflow. Concurrent editing must not silently overwrite another user's changes.

## Architecture decision

Use a CRDT-backed collaborative text model for concurrent Markdown editing. Preferred implementation is Yjs with a compatible WebSocket collaboration provider, subject to dependency and deployment verification against the current repository. Persist durable document snapshots and update history in the existing database layer. Do not treat the browser's local state as authoritative.

The task execution engine is separate from the editor:
- Editing a task document never executes the task.
- Execution starts only after an explicit authorised action.
- A task may enter RUNNING only when all dependencies are COMPLETE.
- A failed acceptance gate blocks downstream tasks.
- Each execution transition is an append-only audit event.

If the final deployment environment cannot host a compatible Yjs provider, stop and record the infrastructure blocker rather than silently substituting last-write-wins editing.

## Document model

Each Markdown document has:
- immutable document ID
- workspace ID
- document type: lesson, research, task, decision, runbook, or trade_execution
- title and Markdown body
- schema version
- content revision / CRDT state version
- owner and access-control metadata
- created_at and updated_at timestamps in UTC
- archived flag
- optional linked trade_id for trade_execution documents; the trade ledger remains authoritative for financial facts

Task Markdown uses YAML frontmatter with validated fields:
- id
- title
- status: BACKLOG, READY, RUNNING, BLOCKED, REVIEW, COMPLETE
- priority: P0, P1, P2, P3
- depends_on: list of task IDs
- acceptance_criteria: list
- owner_id
- created_at
- updated_at

The Markdown body contains context, implementation notes, test evidence, decisions, and a completion summary. Frontmatter is parsed as data and must never be executed as code.

### Trade execution document behavior

A trade_execution document is linked to exactly one simulated trade ID. It contains the human-readable thesis and structured entry, management, and exit conditions, but it is not the source of truth for orders, fills, fees, timestamps, or P&L.

- The initial entry snapshot is captured before or at entry. If captured later, it is visibly marked LATE_CAPTURE.
- The document remains editable while the linked trade is OPEN, subject to server-side ownership and coach permissions.
- Every accepted edit produces an immutable revision/audit event with actor, server UTC timestamp, effective time, reason, and references to the prior/current versions.
- Structured condition bases include PRICE_ACTION, INDICATOR, LIQUIDITY, MARKET_CONTEXT, RISK_RULE, TIME_EVENT, DISCRETIONARY, and HYBRID. HYBRID requires explicit ALL/ANY grouping.
- A CLOSED trade makes the main journal read-only. Post-close clarifications are append-only addenda.
- CRDT collaboration may merge concurrent Markdown text changes, but it must not overwrite structured ledger facts or audit history.

## Sequential execution state machine

BACKLOG -> READY -> RUNNING -> REVIEW -> COMPLETE

Additional transitions:
- READY -> BLOCKED when a dependency fails or is incomplete.
- RUNNING -> BLOCKED when implementation cannot safely proceed.
- REVIEW -> RUNNING when review requests changes.
- RUNNING -> REVIEW when implementation is ready for acceptance.
- REVIEW -> COMPLETE only when all acceptance criteria have evidence and an authorised reviewer approves.
- COMPLETE is immutable for that execution revision. Reopening creates a new revision and audit event.

No task may skip states. No dependent task may enter RUNNING until all dependencies are COMPLETE. Cycles in the dependency graph are rejected.

## Collaboration and concurrency requirements

- Presence indicators show active collaborators but do not grant edit permissions.
- CRDT updates merge concurrent text edits without last-write-wins data loss.
- Persist updates in bounded batches and periodically create durable snapshots.
- Reconnect must synchronise from the latest durable state plus retained updates.
- Duplicate updates must be idempotent.
- Document-level access checks run server-side for every join, update, snapshot, and export.
- Role changes and revocations must take effect on active collaboration sessions.
- Audit metadata records actor, workspace, document, event type, server timestamp, and revision; do not log secrets or private tokens.
- Markdown export must produce a stable UTF-8 file and preserve frontmatter.

## Security requirements

- Workspace membership and document permissions are checked on the server.
- Users cannot edit another workspace's documents by changing IDs.
- Only authorised roles can change task status or approve acceptance criteria.
- Frontmatter fields that control workflow state are validated server-side; editor text alone cannot mark a task COMPLETE.
- WebSocket connections require authenticated, short-lived session credentials.
- Rate-limit document updates and connection creation.
- Never expose service-role database keys in the browser.

## Acceptance criteria

1. Two authenticated users can edit the same Markdown document concurrently without silent overwrite.
2. Concurrent inserts/deletes converge to the same document state on both clients.
3. Reconnect restores the latest durable document state.
4. Duplicate update delivery does not duplicate content or audit transitions.
5. A user outside a workspace cannot read or edit its documents.
6. A revoked user loses access to an active session.
7. Task frontmatter rejects invalid status, priority, IDs, and malformed dependency lists.
8. Dependency cycles are rejected.
9. A task with incomplete dependencies cannot transition to RUNNING.
10. A task cannot transition directly from RUNNING to COMPLETE.
11. COMPLETE requires acceptance evidence and authorised reviewer approval.
12. Reopening a completed task creates a new revision and preserves prior audit history.
13. Markdown export is stable and round-trips UTF-8 content and frontmatter.
14. Automated tests cover concurrency, reconnect, permissions, invalid transitions, and idempotency.
15. A trade_execution document can only link to an authorised simulated trade and is editable only while that trade is OPEN.
16. Every accepted trade-journal amendment preserves the prior revision and records actor, server timestamp, effective time, reason, and evidence references.
17. Closing a trade freezes its journal; post-close corrections are append-only addenda and cannot mutate ledger facts.
18. HYBRID conditions require explicit ALL/ANY semantics, and indicator conditions retain exact settings/timeframe/version metadata.

## Implementation sequence

1. Inspect the existing database/authentication abstractions and frontend component conventions.
2. Add validated document and task domain models. The task frontmatter and pure transition/dependency validators are now implemented; durable persistence and audit events remain pending.
3. Add workspace/document persistence and server-side access checks.
4. Add collaboration transport and CRDT persistence/snapshot strategy.
5. Add the Markdown editor and presence/reconnect states.
6. Add task state transition service and append-only audit events.
7. Add export/import and integration tests.
8. Run backend and frontend test/build workflows.

## Exit gate

TASK-002 remains IN_PROGRESS until the implementation, automated tests, and acceptance evidence are committed and reviewed. TASK-003 must not begin before TASK-002 is COMPLETE.


## Repository assessment (2026-10-31)

- Frontend: Next.js 14, React 18, TypeScript, Supabase JS client.
- Backend: Python 3.11-era FastAPI services, SQLAlchemy, PostgreSQL driver, Redis client, and WebSocket support.
- Existing shared database module: SQLAlchemy engine/session factory in backend/shared/database.py.
- Existing WebSocket service: backend/services/websocket/main.py is for market-data streaming and currently contains a TODO for JWT validation while accepting anonymous connections. It is NOT approved for collaborative document traffic until authentication, workspace authorization, and session revocation are implemented and tested.
- Existing backend auth security module provides request size and rate-limit helpers but does not itself establish identity. A new HTTP identity dependency now validates Supabase bearer tokens through Supabase Auth and returns only the verified user ID/email. It does not grant workspace membership or roles.
- Added pure Pydantic task-frontmatter validation, sequential transition rules, dependency existence checks, and cycle detection. These validators do not yet persist state or write audit events.
- The existing market-data WebSocket protocol is not a Yjs sync protocol. Do not send Yjs messages to it as though it were compatible.
- Keep collaboration transport isolated from market-data subscriptions. Select a Yjs-compatible provider only after deployment topology, authentication handshake, persistence adapter, and dependency compatibility are verified.

## Engineering decisions recorded (2026-10-31)

- Alembic is selected as the single backend schema migration mechanism. Configuration and revisions will live under `backend/alembic.ini` and `backend/migrations/`; application startup must not run `create_all()`. The detailed workspace authorization, role matrix, schema boundaries, and collaboration session protocol are recorded in [ADR-002](ADR-002-workspace-authorization-and-migrations.md).
- Initial workspace roles are OWNER, ADMIN, COACH, EDITOR, and VIEWER. Membership is stored in the backend database and is independent of Supabase identity verification. Document access is inherited from active workspace membership for the first release.
- Collaboration credentials will be one-time, short-lived, document-scoped credentials sent in the first WebSocket authentication frame over TLS, never in URL query strings. Active sessions must re-check current membership and role on every write.
- Removed hard-coded Upstox API key/secret defaults from `backend/shared/config.py`; the settings now default to unset optional environment variables. This does not erase the values from Git history. Treat them as exposed and revoke/rotate them with the broker provider. No secret values should be committed again.
- TASK-002 remains IN_PROGRESS. The ADR is a design decision, not evidence that migrations, authorization APIs, persistence, CRDT transport, or frontend collaboration have been implemented.

## Implemented milestones and verification (2026-10-31)

### Database and migration foundation
- Added Alembic configuration, migration environment, an initial PostgreSQL revision, and collaboration ORM models on the existing shared SQLAlchemy Base metadata.
- Added the workspace/document/session/audit schema, foreign-key and uniqueness constraints, an exactly-one-active-OWNER database invariant, and append-only database triggers for document updates, snapshots, and collaboration audit events.
- PostgreSQL 16 CI verifies migration upgrade/downgrade, owner creation within the workspace transaction, rejection of an ownerless workspace, last-owner protection, and append-only mutation rejection.
- Migration execution remains an explicit deployment/release step. Application startup does not call create_all() or apply migrations implicitly.

### Workspace authorization and initial HTTP API
- Implemented the server-side role/permission policy for OWNER, ADMIN, COACH, EDITOR, and VIEWER. A verified Supabase identity is not treated as workspace permission.
- Each authorization check loads the persisted active membership for the requested workspace. Missing/revoked membership or insufficient permission returns 403; authorization database failure returns 503 (fail closed).
- Added authenticated endpoints:
  - POST /api/v1/collaboration/workspaces
  - GET /api/v1/collaboration/workspaces
  - POST /api/v1/collaboration/workspaces/{workspace_id}/documents
  - GET /api/v1/collaboration/workspaces/{workspace_id}/documents
  - GET /api/v1/collaboration/workspaces/{workspace_id}/documents/{document_id}
- Workspace creation records its creator as OWNER and writes the workspace audit event in the same transaction. Document creation and reads require server-side workspace permissions.
- No HTTP Markdown-body update endpoint is exposed. Live editing remains unavailable until the CRDT update path exists; this avoids last-write-wins replacement of concurrent edits.
- Membership invitations, role changes, and owner-transfer APIs are not implemented.

### CI evidence
- PostgreSQL migration and metadata gate: GitHub Actions runs #21 and #22 passed.
- RBAC gate: runs #23 and #24 passed; 63 tests passed.
- Workspace/document API gate: runs #31 and #32 passed on commit c0171759d332ee00da088dbeb639d999a647180f; 68 tests passed, 3 warnings, 0 failures in each run.
- These are focused backend CI tests. They do not prove full frontend build, production deployment, or concurrent browser editing.

## Remaining blockers / exit-gate work

1. Implement one-time, document-scoped WebSocket credentials with a 60-second establishment window. Generate cryptographically random raw credentials, deliver them only in the first TLS WebSocket authentication frame, and persist only a cryptographic hash.
2. Implement atomic one-time credential consumption. Expired, replayed, wrong-document, revoked, and stale-membership-version credentials must fail closed.
3. Re-check active membership and membership version for every collaboration message; prove an already-connected session cannot continue writing after revocation.
4. Select and pin a Yjs-compatible collaboration server/provider and persistence adapter only after verifying deployment topology and long-lived WebSocket support. Keep collaboration transport separate from the anonymous market-data WebSocket.
5. Implement durable CRDT update storage, bounded batching, snapshots, reconnect/replay, idempotency, payload/concurrency limits, and acknowledgements only after database commit.
6. Implement the Markdown editor, presence, reconnect states, stable UTF-8 export/import, and backend/frontend build plus integration tests.
7. Implement task-state persistence and append-only transition/evidence audit. Existing task validators are pure domain logic only.

Until these gates pass, shared live editing must remain disabled or read-only. No anonymous collaboration endpoint may be exposed. TASK-003 remains blocked until the full TASK-002 exit gate is reviewed and accepted.
