# TASK-013 — Live trade execution journal and rationale history

**Status:** Backlog — specification created; implementation not started  
**Priority:** P1  
**Depends on:** TASK-003, TASK-005, TASK-006, TASK-008, and TASK-002 trade_execution document support  
**Execution order:** After TASK-008 and before TASK-009  
**Scope:** Simulation-only

## Objective

Provide a mandatory, trade-linked record for every simulated trade that explains the entry decision, live position-management decisions, editable exit logic, and actual exit reason. The user must be able to refine the plan after entry while preserving a complete, tamper-evident history of what was known and when.

## Product rules

1. Every simulated trade has one canonical execution journal linked to its trade ID.
2. Capture a minimum entry snapshot before or at entry. If the record is created after entry, mark it LATE_CAPTURE and require a reason.
3. While the trade is OPEN, the authorised owner and permitted coach may edit the thesis, management rationale, stop/trailing/partial-booking rules, and exit conditions.
4. Every accepted edit creates a new immutable revision. Never overwrite, delete, silently replace, or backdate an earlier revision.
5. When the trade is CLOSED, freeze the journal. Corrections are append-only addenda.
6. The journal is explanatory documentation; the ledger is authoritative for orders, fills, prices, quantities, costs, and P&L.
7. The first release is simulation-only. No broker/exchange order routing is part of this task.

## Entry snapshot fields

- trade_id, account_id, instrument, direction, and strategy/setup identifier;
- entry timestamp and price/fill reference from the ledger;
- execution basis and timeframe(s);
- entry trigger and plain-language rationale;
- initial invalidation/stop, risk amount or risk percentage, and planned exit/target;
- evidence references to chart/market snapshots and relevant candle/time ranges;
- capture status: CONTEMPORANEOUS or LATE_CAPTURE.

## Condition schema

Each entry, management, invalidation, or exit condition must specify:
- condition_id and revision_id;
- role: ENTRY, MANAGEMENT, EXIT, or INVALIDATION;
- basis: PRICE_ACTION, INDICATOR, LIQUIDITY, MARKET_CONTEXT, RISK_RULE, TIME_EVENT, DISCRETIONARY, or HYBRID;
- timeframe and human-readable trigger definition;
- expected action (for example KEEP_POSITION, MOVE_STOP, MOVE_TO_BREAKEVEN, TRAIL_STOP, PARTIAL_EXIT, or CLOSE_POSITION);
- observed/evaluation mode: MANUAL or SYSTEM;
- evidence reference and observation timestamp.

Additional typed metadata:
- INDICATOR: name, exact parameters, source timeframe, version, comparator/threshold, and observed value.
- LIQUIDITY: reference type, level/zone, session/source, event timestamp, and whether the event was a sweep, grab, reclaim, or other explicitly defined behavior.
- PRICE_ACTION: candle/time range, relevant swing/structure level, and observed close/rejection/break/retest behavior.
- HYBRID: explicit condition tree and ALL/ANY semantics; ambiguous grouping is invalid.
- DISCRETIONARY: mandatory free-text reasoning and evidence reference.

## Version and event model

Each amendment must append:
- journal_id, trade_id, revision_number, previous_revision_id;
- actor_id and permission context;
- server_created_at_utc and effective_at_utc;
- change_reason;
- changed fields or content diff/reference;
- optional market/chart evidence references;
- idempotency key.

Suggested event types:
- JOURNAL_CREATED
- ENTRY_SNAPSHOT_CAPTURED
- THESIS_AMENDED
- CONDITION_ADDED / CONDITION_AMENDED / CONDITION_DISABLED
- STOP_OR_TRAIL_RULE_AMENDED
- PARTIAL_EXIT_RECORDED
- EXIT_TRIGGER_RECORDED
- TRADE_CLOSED
- JOURNAL_FROZEN
- POST_CLOSE_ADDENDUM_ADDED

All event records are append-only. A disabled condition remains visible in history with its disabled timestamp and reason.

## Exit attribution

For every partial or final exit, record:
- actual exit timestamp and fill reference from the ledger;
- observed trigger and evidence;
- condition ID and journal revision that applied, where available;
- exit classification: PLANNED_EXIT, PLAN_AMENDED_EXIT, DISCRETIONARY_EXIT, RISK_FORCED_EXIT, or OTHER;
- mandatory rationale when the exit is discretionary or OTHER.

The UI must make clear whether the exit followed the original plan, a post-entry amendment, or an unplanned decision.

## Acceptance criteria

1. Every simulated trade has one journal linked to one canonical trade ID.
2. A trade cannot be represented as having a contemporaneous entry plan if its journal was first captured after entry.
3. The user can edit the thesis and exit conditions while the trade is OPEN, subject to server-side permissions.
4. Every edit preserves the old revision and records actor, UTC server time, effective time, reason, and previous/current version references.
5. Backdated amendments and destructive revision edits are rejected.
6. Conditions cover price action, indicators, liquidity, market context, risk rules, time/events, discretionary decisions, and explicitly grouped hybrid logic.
7. Indicator settings/version/timeframe and liquidity reference/level/source are stored with the exact condition version.
8. Every partial/final exit is linked to an applicable condition/version or an explicit discretionary/risk-forced/other reason.
9. A CLOSED trade journal is read-only; correction uses an append-only addendum.
10. Journal edits cannot change ledger fills, costs, quantities, timestamps, balances, realised P&L, or qualification values.
11. Concurrent edits cannot silently destroy history; CRDT text convergence and server-side event append semantics are tested.
12. Access control is enforced for read, edit, export, history, and addendum operations.
13. Automated tests cover open/closed lifecycle, permission denial, concurrent updates, duplicate idempotency keys, backdating, partial exits, and ledger immutability.
14. No broker/exchange order-routing capability is introduced.

## Implementation sequence

1. Map journal and condition records to the approved database/migration and immutable-ledger design from TASK-003.
2. Integrate with normalized market-data snapshots and provenance from TASK-005.
3. Reference the versioned indicator registry/settings from TASK-006 without hard-coding indicator parameters.
4. Integrate journal creation, open-position editing, exit attribution, and close/freeze behavior with TASK-008.
5. Reuse authenticated/versioned Markdown document support from TASK-002; keep structured journal events server-authoritative.
6. Add UI for entry snapshot, live amendments, active exit conditions, version timeline, and close summary.
7. Add automated unit, integration, authorization, idempotency, and ledger-immutability tests.

## Exit gate

TASK-013 remains IN_PROGRESS until every acceptance criterion is implemented, tested, and supported by reviewable evidence. It must complete before TASK-009 starts because qualification and performance analytics must consume reconciled trade outcomes without relying on mutable journal prose.
