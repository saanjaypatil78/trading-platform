# Markdown workspace and task execution protocol

## Principles

1. Markdown is the human-readable source for task context and learning content.
2. Workflow metadata is validated by backend domain services; Markdown text cannot self-authorise workflow transitions.
3. CRDT state is the collaboration source while a document is actively edited; durable snapshots and update records provide recovery.
4. The task state machine is the authority for execution order.
5. Audit events are append-only.

## Task dependency rules

- Every task ID is unique within its workspace.
- Every dependency must reference an existing task in the same workspace.
- Self-dependencies and dependency cycles are invalid.
- READY requires every dependency to be COMPLETE.
- RUNNING requires READY plus an authorised start command.
- REVIEW requires implementation and test evidence.
- COMPLETE requires all acceptance criteria to be evidenced and reviewer approval.
- Reopening creates a new execution revision; it does not erase prior evidence.

## Suggested audit event envelope

- event_id
- workspace_id
- document_id
- task_id (nullable for non-task documents)
- actor_id
- event_type
- previous_state (nullable)
- next_state (nullable)
- document_revision
- idempotency_key
- occurred_at_utc
- evidence_reference (nullable)
- metadata (allow-listed, no credentials)

## Collaboration lifecycle

1. Authenticate user.
2. Authorise workspace/document access.
3. Join the collaboration room using a short-lived credential.
4. Synchronise durable snapshot and subsequent CRDT updates.
5. Broadcast presence separately from document content.
6. Persist updates idempotently.
7. Periodically compact update history into a snapshot.
8. On disconnect, remove presence and expire the session.
9. On permission revocation, terminate the active session.

## Failure handling

- Database unavailable: do not acknowledge durable persistence; clients retain pending local updates and display offline/pending state.
- Collaboration provider unavailable: disable shared editing and offer read-only mode; do not silently switch to last-write-wins.
- Invalid frontmatter: preserve raw content, flag validation errors, and block workflow actions.
- Invalid transition: return a typed conflict response and retain the audit trail.
