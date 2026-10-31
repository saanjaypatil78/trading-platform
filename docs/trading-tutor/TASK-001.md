# TASK-001 — Product requirements and policy baseline

**Status:** Complete — policy approved and engineering specification review passed  
**Priority:** P0  
**Depends on:** None  
**Owner:** Product/Engineering  
**Branch:** codex/trading-tutor-task-001-prd

## Approved policy decisions

- Monthly net return target: at least 10%.
- Qualification sequence: 12 consecutive calendar months.
- Minimum profit factor: 1.00.
- Carry-forward: prohibited.
- Minimum closed trades: no fixed numeric minimum; manual reviewer assesses sample sufficiency case by case and records rationale.
- Zero gross loss: if gross profit is positive and gross loss is zero, the profit-factor criterion passes as NO_GROSS_LOSS_PASS. Do not store infinity. If gross profit and gross loss are both zero, the criterion fails.
- Real-money rewards: disabled pending written Indian legal clearance.

## Deliverables

- [x] Product requirements document at docs/trading-tutor/PRD.md
- [x] Approved qualification settings captured without reinterpretation
- [x] Metric formulas and edge-case handling documented
- [x] Manual sample review policy documented
- [x] Zero-gross-loss pass policy documented
- [x] Safety exclusions and reward lock documented

## Acceptance criteria and verification

- [x] 10% monthly net return, 12 consecutive months, PF >= 1.00, and no carry-forward are explicit.
- [x] Real-money rewards remain disabled.
- [x] Return and PF formulas are deterministic and cost allocation is not double-counted.
- [x] Manual sample sufficiency review is required and audited; no hard-coded minimum trade count exists.
- [x] Positive gross profit with zero gross loss passes only the PF criterion through NO_GROSS_LOSS_PASS; no infinity value is persisted.
- [x] Zero gross profit and zero gross loss cannot pass.
- [x] REVIEW_REQUIRED, FAILED, and QUALIFIED remain distinct outcomes.
- [x] The 12th qualified month triggers final audit, not payment.
- [x] No cash-prize or loss-pool funding mechanism is specified.
- [x] Product owner approval received in the conversation on 2026-10-31.
- [x] Engineering specification review completed: formulas, policy states, edge cases, and release constraints checked for internal consistency.

## Engineering review notes

1. The profit-factor ratio is undefined when gross loss is zero. The approved explicit status avoids division by zero and avoids representing infinity as a financial metric.
2. Manual sample sufficiency must be a separately persisted review decision with reviewer ID, timestamp, rationale, and evidence reference.
3. A NO_GROSS_LOSS_PASS result must never bypass return, reconciliation, integrity, or manual sample-review gates.
4. All financial arithmetic remains fixed-precision decimal; no binary floating-point qualification decisions.
5. Policy changes must be versioned and must not rewrite historical qualification outcomes.

## Exit decision

TASK-001 exit criteria are satisfied for the product-requirements baseline. TASK-002 may begin. Production release remains blocked by the open decisions and release gates in the PRD, including market-data rights, fee/slippage policy, month-end open-position treatment, and legal review.
