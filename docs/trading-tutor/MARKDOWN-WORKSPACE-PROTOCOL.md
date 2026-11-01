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


## Trade execution journal protocol

- A trade_execution Markdown document must reference one canonical simulated trade_id; the ledger is authoritative for financial and execution facts.
- Capture the entry thesis before or at entry. Later capture must be marked LATE_CAPTURE and include a reason.
- While the trade is OPEN, authorised users may amend the thesis, management rules, and exit conditions. The service must append a new version and audit event rather than replacing the previous version.
- Each amendment records actor, server-generated UTC timestamp, effective time, reason, previous/current revision, and optional evidence reference. Effective time cannot be backdated before the last accepted version.
- Conditions use explicit typed bases (price action, indicator, liquidity, market context, risk rule, time/event, discretionary, or hybrid). Hybrid logic must explicitly declare ALL or ANY semantics.
- The actual exit event records the condition/version that triggered it, or a documented discretionary/risk-forced reason.
- Once the linked trade is CLOSED, the journal becomes read-only. Corrections are append-only addenda.
- Journal editing must never mutate ledger orders, fills, costs, position quantities, balances, or realised P&L.
- CRDT merge behavior applies to collaborative prose only; structured execution events and audit records are server-authoritative and append-only.
