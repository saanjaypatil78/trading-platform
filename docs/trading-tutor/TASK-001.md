# TASK-001 — Product requirements and policy baseline

**Status:** In progress — documentation committed; verification pending  
**Priority:** P0  
**Depends on:** None  
**Owner:** Product/Engineering  
**Branch:** codex/trading-tutor-task-001-prd

## Objective

Establish a single source of truth for the simulation-only Trading Tutor product and the approved 12-month qualification policy before schema or application implementation begins.

## Deliverables

- [x] Product requirements document at docs/trading-tutor/PRD.md
- [x] Approved qualification settings captured without reinterpretation
- [x] Metric formulas and edge-case handling documented
- [x] Safety exclusions and reward lock documented
- [x] Unapproved policy decisions explicitly marked as open
- [ ] Product owner review of open decisions
- [ ] Engineering acceptance review
- [ ] Verification checklist completed

## Acceptance criteria

1. PRD contains the approved target of 10% monthly net return.
2. PRD requires 12 consecutive calendar months.
3. PRD requires profit factor >= 1.00.
4. PRD explicitly prohibits carry-forward.
5. PRD states real-money rewards are disabled pending written Indian legal clearance.
6. Monthly return and profit-factor formulas are deterministic and cost allocation is not double-counted.
7. Undefined profit factor and unapproved sample-size policy cannot silently pass.
8. REVIEW_REQUIRED, FAILED, and QUALIFIED are distinct outcomes.
9. The 12th qualified month triggers final audit, not payment.
10. No cash-prize or loss-pool funding mechanism is specified.

## Verification

- [ ] Cross-check every approved setting against the accepted product baseline.
- [ ] Review formula examples and boundary tests with engineering.
- [ ] Confirm no reward/payment flow is enabled in the initial scope.
- [ ] Resolve or explicitly retain OD-01 through OD-06 before production.

## Exit condition

TASK-001 is complete only after the acceptance checklist is reviewed and the product owner signs off. TASK-002 must not begin implementation until TASK-001 is verified.
