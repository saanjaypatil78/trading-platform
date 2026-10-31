# Trading Tutor — Product Requirements Document

**Status:** Approved policy baseline for implementation  
**Version:** 1.0  
**Scope:** Simulated trading education and qualification only  
**Financial rewards:** Disabled; no deposit-, recharge-, loss-pool-, or entry-fee-funded prizes.

## 1. Product objective

Build a trading education platform combining structured learning, market-context visualisation, simulated trading, auditable performance measurement, and a sequential qualification programme. The platform teaches risk management and execution discipline; it must not encourage gambling, loss-chasing, or increased deposits.

## 2. Approved qualification policy

| Rule | Approved value |
|---|---|
| Monthly net return target | At least 10% |
| Required sequence | 12 consecutive calendar months |
| Minimum profit factor | 1.00 |
| Carry-forward | Not permitted |
| Capital mode | Simulated capital only |
| Real-money rewards | Disabled pending written Indian legal clearance |

A month passes only when every required metric and data-integrity gate passes. A failed month resets the consecutive-month streak to zero. Excess return in one month cannot compensate for a later month below target. A month with missing or unreconciled data is REVIEW_REQUIRED, not an automatic pass or fail.

## 3. Metric definitions

### 3.1 Monthly net return

monthly_net_pnl = sum(closed_trade_gross_pnl) - sum(allocated_trading_costs)

monthly_net_return_pct = monthly_net_pnl / opening_eligible_simulated_capital * 100

- Use closed, reconciled trades assigned to the month by their authoritative close timestamp in UTC.
- Trading costs include applicable commissions, exchange/regulatory fees, and simulated slippage when configured.
- Do not subtract a cost twice. Each cost record must reference the trade or ledger event to which it is allocated.
- Opening eligible capital is the approved simulated account equity snapshot at the start of the calendar month.
- Deposits, withdrawals, bonuses, manual balance edits, and transfers are not trading profit and must not inflate the numerator.
- The month boundary, timezone, capital snapshot, and calculation version must be stored with the result.

### 3.2 Profit factor

Profit factor is calculated from per-trade net realized P&L after allocated trading costs:

profit_factor = sum(positive_trade_net_pnl) / abs(sum(negative_trade_net_pnl))

- Zero-P&L trades contribute to neither gross profit nor gross loss.
- If gross loss is zero and gross profit is positive, the approved policy treats the profit-factor criterion as PASSED (zero-gross-loss pass). Do not persist infinity or a fabricated numeric ratio; store the explicit result status NO_GROSS_LOSS_PASS and retain gross profit, gross loss, and the calculation version as evidence. This pass applies only to the profit-factor criterion; all other monthly qualification gates still apply.
- If both gross profit and gross loss are zero, the result is UNDEFINED_NO_ACTIVITY and cannot pass.
- The numeric pass threshold is 1.00 or greater.

### 3.3 Sample sufficiency

There is no fixed minimum closed-trade count. The system must record the monthly count and route sample sufficiency to a manual reviewer. The reviewer makes a case-by-case decision using documented evidence and a written rationale; the decision and reviewer identity are audited. A month cannot automatically pass sample sufficiency solely because it has trades.

## 4. Monthly qualification decision

A month may be marked QUALIFIED only when all of the following are true:

1. Monthly net return is at least 10%.
2. Profit factor is defined and at least 1.00.
3. Sample sufficiency policy is approved and satisfied.
4. All trades, costs, capital snapshots, and account events reconcile.
5. No duplicate, altered, prohibited, or otherwise invalid activity is detected.
6. The calculation version and audit evidence are persisted.

If a verified metric misses its threshold, the month is FAILED. If evidence is incomplete or a policy decision is unresolved, it is REVIEW_REQUIRED. Review outcomes must be explicit and audited; the system must not silently convert a review into a pass.

## 5. Twelve-month progression

- Qualification is based on 12 consecutive calendar months for the same challenge attempt and simulated account.
- Every month must independently pass.
- A failed month resets the streak; no carry-forward or averaging is allowed.
- An incomplete month remains pending until its data is closed and reconciled.
- Completion of month 12 triggers a final audit, not an automatic cash reward.
- Final status is SIMULATED_QUALIFICATION_COMPLETE.
- Reward eligibility remains locked while real-money rewards are disabled.

## 6. Core user journeys

1. User signs in and receives a clearly labelled simulated account.
2. User studies lessons and completes knowledge checks.
3. User views market data and indicators with source, timestamp, and delayed/live status.
4. User places simulated orders; the ledger records fills, costs, and immutable audit events.
5. User reviews daily and monthly performance with metric definitions visible.
6. User progresses through monthly qualification only after reconciliation.
7. User can inspect failed criteria, evidence, and review status without editing historical results.

## 7. Functional requirements

- FR-01 Identity and roles: Authenticate users and enforce user, coach, reviewer, and administrator permissions.
- FR-02 Simulated account: Clearly distinguish simulated balances and orders from brokerage or exchange accounts.
- FR-03 Ledger: Persist orders, fills, closed trades, costs, balance events, and immutable audit events.
- FR-04 Calculation: Calculate monthly net return and profit factor deterministically using decimal-safe arithmetic.
- FR-05 Qualification: Apply the approved monthly rules and maintain a 12-month consecutive streak.
- FR-06 Review: Support review-required states with reviewer identity, reason, evidence, and decision history.
- FR-07 Learning: Provide structured lessons, assessments, progress, and source-linked explanations.
- FR-08 Market data: Display provider, instrument, exchange, event timestamp, ingestion timestamp, and live/delayed/historical status.
- FR-09 Indicators: Calculate indicators from versioned input data and settings; disclose settings and warm-up requirements.
- FR-10 Collaboration: Support shared Markdown task/learning workspaces with explicit ownership, versioning, and conflict-safe updates.
- FR-11 Auditability: Preserve calculation versions, input snapshots, policy versions, and administrative changes.
- FR-12 Reward separation: Keep all reward and payment functions disabled behind a server-side policy gate.
- FR-13 Trade execution journal: Require a structured, trade-linked execution journal covering the entry thesis, execution basis, evidence, invalidation, risk management, and planned exit logic for every simulated trade.
- FR-14 Live journal amendments: Permit authorised edits to the thesis and exit logic while a trade is open, preserving every prior version, server timestamp, effective time, actor, and change reason in an append-only audit history.
- FR-15 Exit attribution: Record which planned or newly amended condition triggered each partial or final exit, and distinguish planned rules from the actual observed execution reason.

## 8. Non-functional requirements

- Financial calculations must use fixed-precision decimal types; binary floating-point must not determine qualification.
- All authoritative timestamps are UTC; display timezone is user-configurable and must not alter month assignment.
- Every qualification result must be reproducible from stored input snapshots and a versioned calculation.
- Idempotency keys must prevent duplicate order, fill, ledger, and qualification events.
- User-facing APIs must enforce tenant/user ownership and role checks server-side.
- Secrets must never be committed to source control.
- Logs must avoid credentials and unnecessary personal data.
- Market-data outages or stale feeds must be visible and must not be represented as live.
- The system must provide automated tests for boundary conditions and state transitions.

## 9. Explicit exclusions and safety controls

- No real-money order routing or brokerage execution in the initial release.
- No cash prizes, withdrawals, deposits, or user-to-user transfers.
- No prize pool funded by losing users, recharge balances, entry fees, or trading losses.
- No leverage escalation, martingale, loss-chasing, or guaranteed-profit claims.
- No automatic qualification based on unverified or manually editable performance data.
- No financial reward activation without a separate written legal review and deliberate product release decision.

## 10. Open decisions — must not be silently assumed

| ID | Decision | Current handling |
|---|---|---|
| OD-01 | Minimum closed trades per month | Resolved: no fixed numeric minimum; manual reviewer assesses sufficiency case by case with an audited rationale |
| OD-02 | Treatment of profitable month with zero gross loss | Resolved: profit-factor criterion passes when gross profit > 0 and gross loss = 0; store NO_GROSS_LOSS_PASS, not infinity |
| OD-03 | Month-end open positions | Must be reconciled; final policy required before production |
| OD-04 | Simulated slippage and fee schedule by instrument | Configurable; no invented defaults |
| OD-05 | Market-data vendors, redistribution rights, and latency SLA | Provider/legal review required |
| OD-06 | Indian legal classification of educational competitions/rewards | Real-money rewards remain disabled pending qualified legal advice |

## 11. Release gates

The initial release is simulation-only. Release requires passing automated tests, security and access-control review, data reconciliation tests, operational monitoring, backup/restore verification, and confirmation that reward/payment endpoints remain disabled.

## 12. Acceptance criteria

- The approved policy values are represented as versioned configuration, not scattered constants.
- A month at 9.99% fails the return criterion; a month at exactly 10.00% meets that criterion.
- Profit factor 0.99 fails; exactly 1.00 passes. If gross profit > 0 and gross loss = 0, the profit-factor criterion passes using NO_GROSS_LOSS_PASS; if both are zero, it does not pass.
- A failed month resets the consecutive streak to zero.
- Profits above target in one month do not offset a later failed month.
- Missing or inconsistent evidence yields REVIEW_REQUIRED.
- Monthly trade sample sufficiency requires a recorded manual review and rationale; no fixed trade-count threshold is hard-coded.
- Duplicate events do not change balances or qualification twice.
- Historical trades and qualification results cannot be silently edited.
- Twelve consecutive qualified months trigger final audit only.
- Reward/payment capability is server-side disabled and has automated negative tests.
- Every simulated trade has an entry execution-journal snapshot linked to its trade ID; missing or late-captured rationale is explicitly flagged and cannot be presented as contemporaneous.
- An open trade's journal can be amended, but each amendment preserves the previous content, actor, server timestamp, effective time, reason, and evidence reference.
- Exit conditions support price-action, indicator, liquidity, market-context, risk-management, time/event, discretionary, and hybrid rule types without hard-coded indicator settings.
- Each partial/final exit records the actual trigger, observed evidence, and the journal version/condition it relates to, where applicable.
- Closed trade journals cannot be overwritten; corrections are append-only addenda.
- Journal edits cannot change ledger fills, fees, timestamps, realised P&L, or qualification results.


## 13. Live trade execution journal — normative behavior

### 13.1 Purpose and source of truth

Every simulated trade must have a structured execution journal linked to its immutable trade/ledger identity. The journal explains why the trade was entered, what was expected to happen, how the position would be managed, and what actually caused each exit.

The journal is an explanatory decision record, not the financial ledger and not an order-routing interface. The ledger remains authoritative for orders, fills, quantities, timestamps, costs, and realised P&L. Editing Markdown must never modify those ledger facts.

### 13.2 Entry snapshot

Before or at simulated entry, capture an initial entry snapshot containing:
- instrument, direction, timeframe(s), and setup name or strategy identifier;
- execution basis: PRICE_ACTION, INDICATOR, LIQUIDITY, MARKET_CONTEXT, RISK_RULE, DISCRETIONARY, or HYBRID;
- the observed entry trigger and why it supports the trade;
- entry price reference, initial stop/invalidation, target or exit plan, and planned risk;
- relevant indicator names, parameters, source timeframe, and calculation/version metadata when indicators are used;
- relevant liquidity reference and level/session context when liquidity is used;
- evidence references such as chart snapshot, market-data snapshot, candle/time range, or annotated note.

A trade imported or journalled after entry must be marked LATE_CAPTURE, with capture time and reason. It must not be represented as a contemporaneous pre-entry plan.

### 13.3 Editable while open

While the simulated position is OPEN, the authorised owner (and an explicitly permitted coach, where workspace policy allows) may update:
- the current trade thesis and market-structure interpretation;
- active entry/continuation/re-entry notes, where relevant;
- stop-loss, breakeven, trailing-stop, partial-booking, and target-management rationale;
- exit conditions and the priority/order in which they should be evaluated;
- the reason for keeping, reducing, or closing the position.

Every amendment creates a new immutable version. Store the actor, server-generated UTC timestamp, user-declared effective time (which cannot be earlier than the last accepted version), change reason, before/after version references, and optional market/chart evidence. Do not permit silent overwrite, deletion, or backdating. The UI must show the current plan and the full version timeline.

### 13.4 Condition model

A condition may use one or more of these bases:
- PRICE_ACTION: candle close/rejection, swing high/low, break of structure, change of character, retest, range break, or other explicitly described price behavior.
- INDICATOR: named indicator, exact settings/version, source timeframe, comparison/operator, threshold or signal state, and observed value.
- LIQUIDITY: reference type and level, such as previous-day/session high or low, equal highs/lows, a defined liquidity pool, sweep/grab, or reclaim; record the source and timestamp.
- MARKET_CONTEXT: session, volatility/regime, volume profile/VWAP reference, or a documented market-context event.
- RISK_RULE: initial/final stop, max risk, breakeven, trailing, partial booking, or invalidation rule.
- TIME_EVENT: a time/session boundary or scheduled event rule, with timezone and source where applicable.
- DISCRETIONARY: a manual decision with a mandatory written explanation and evidence reference.
- HYBRID: a versioned group of two or more conditions using explicit ALL or ANY semantics. Do not infer whether conditions are AND/OR.

Each condition must specify its role (ENTRY, MANAGEMENT, EXIT, or INVALIDATION), timeframe, trigger definition, expected action, and whether it was manually observed or system-evaluated. System-evaluated conditions must record the evaluator/version and data provenance; a human annotation must not be presented as an automatically detected signal.

### 13.5 Exit and trade-close record

An exit plan may contain multiple conditional actions, including MOVE_STOP, MOVE_TO_BREAKEVEN, TRAIL_STOP, PARTIAL_EXIT, and CLOSE_POSITION. For each actual partial/final exit, record the observed trigger, time, price/fill reference, quantity, evidence, and linked condition/version when available. Distinguish:
- PLANNED_EXIT: the exit followed a condition in the currently active plan;
- PLAN_AMENDED_EXIT: the exit followed a condition added or changed after entry;
- DISCRETIONARY_EXIT: the user closed manually and supplied a reason;
- RISK_FORCED_EXIT: the configured risk/stop rule caused the exit;
- OTHER: a reason requiring an explanatory note.

After the trade is CLOSED, the journal becomes read-only. A correction is a separate append-only addendum with actor, timestamp, reason, and references to the record being clarified. It cannot alter the original entry snapshot, amendment history, exit events, or ledger values.

### 13.6 Safety, audit, and analytics

- The feature is simulation-only in the initial release and does not send orders to a broker or exchange.
- Journal edits never rewrite fills, fees, order state, timestamps, balances, realised P&L, or qualification calculations.
- A missing journal, late capture, or unlinked exit reason is visible in review and analytics; it is never silently filled with invented rationale.
- Analytics must be able to compare the original plan, amendments, and actual outcome without hindsight contamination.
- Access control is checked server-side for every read, edit, export, addendum, and version-history request.
