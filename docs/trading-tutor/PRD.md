# Trading Tutor — Product Requirements Document

**Status:** Draft baseline for implementation  
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
- If gross loss is zero and gross profit is positive, store UNDEFINED_NO_LOSS rather than persisting infinity or silently treating it as a numeric pass. Qualification requires review until the policy is explicitly decided.
- If both gross profit and gross loss are zero, the result is UNDEFINED_NO_ACTIVITY and cannot pass.
- The numeric pass threshold is 1.00 or greater.

### 3.3 Sample sufficiency

The minimum number of closed trades per month is a policy parameter, not yet approved. Do not hard-code a minimum sample count. Until a product owner approves a value, record the closed-trade count and route sample sufficiency to REVIEW_REQUIRED rather than granting automatic qualification.

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
| OD-01 | Minimum closed trades per month | Unapproved; qualification requires review |
| OD-02 | Treatment of profitable month with zero gross loss | Unapproved; qualification requires review |
| OD-03 | Month-end open positions | Must be reconciled; final policy required before production |
| OD-04 | Simulated slippage and fee schedule by instrument | Configurable; no invented defaults |
| OD-05 | Market-data vendors, redistribution rights, and latency SLA | Provider/legal review required |
| OD-06 | Indian legal classification of educational competitions/rewards | Real-money rewards remain disabled pending qualified legal advice |

## 11. Release gates

The initial release is simulation-only. Release requires passing automated tests, security and access-control review, data reconciliation tests, operational monitoring, backup/restore verification, and confirmation that reward/payment endpoints remain disabled.

## 12. Acceptance criteria

- The approved policy values are represented as versioned configuration, not scattered constants.
- A month at 9.99% fails the return criterion; a month at exactly 10.00% meets that criterion.
- Profit factor 0.99 fails; exactly 1.00 meets the numeric threshold when defined.
- A failed month resets the consecutive streak to zero.
- Profits above target in one month do not offset a later failed month.
- Missing or inconsistent evidence yields REVIEW_REQUIRED.
- Duplicate events do not change balances or qualification twice.
- Historical trades and qualification results cannot be silently edited.
- Twelve consecutive qualified months trigger final audit only.
- Reward/payment capability is server-side disabled and has automated negative tests.
