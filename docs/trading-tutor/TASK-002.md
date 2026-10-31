# TASK-002 — Shared Markdown execution and collaboration

**Status:** In progress — repository fit and technical design established  
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
- document type: lesson, research, task, decision, or runbook
- title and Markdown body
- schema version
- content revision / CRDT state version
- owner and access-control metadata
- created_at and updated_at timestamps in UTC
- archived flag

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

## Implementation sequence

1. Inspect the existing database/authentication abstractions and frontend component conventions.
2. Add validated document and task domain models.
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
- Existing backend auth security module provides request size and rate-limit helpers but does not itself establish a verified identity for collaboration.
- The existing market-data WebSocket protocol is not a Yjs sync protocol. Do not send Yjs messages to it as though it were compatible.
- Keep collaboration transport isolated from market-data subscriptions. Select a Yjs-compatible provider only after deployment topology, authentication handshake, persistence adapter, and dependency compatibility are verified.

## Current blockers / implementation prerequisites

1. Identify the canonical authentication dependency that yields a verified user identity for FastAPI routes and WebSocket handshakes.
2. Confirm the actual database migration strategy and workspace membership model before creating persistent collaboration tables.
3. Select and pin a Yjs-compatible provider and persistence adapter; verify that the hosting platform supports its long-lived WebSocket connections.
4. Add integration tests proving unauthorized and revoked sessions cannot join or continue editing.

These are implementation gates, not reasons to weaken the security requirements. Until resolved, shared editing must remain disabled or read-only; no anonymous collaboration endpoint may be exposed.
