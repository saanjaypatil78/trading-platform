# Sequential execution order

Tasks are executed strictly in dependency order. A task cannot be marked complete until its acceptance criteria, automated tests (where applicable), and verification evidence are recorded.

| Order | Task | Scope | Exit gate |
|---:|---|---|---|
| 1 | TASK-001 | Product requirements and qualification policy | Product/engineering sign-off |
| 2 | TASK-002 | Shared Markdown execution and collaboration model | Versioning, concurrency, permissions tested |
| 3 | TASK-003 | Database foundation and immutable ledger | Migrations, constraints, authorization tests |
| 4 | TASK-004 | Cache and performance layer | Cache invalidation and idempotency tested |
| 5 | TASK-005 | Market-data ingestion and normalization | Provenance, stale-feed, replay tests |
| 6 | TASK-006 | Versioned indicator engine | Golden-data and determinism tests |
| 7 | TASK-007 | Deep Research Tutor and lesson workflow | Source grounding and failure/retry tests |
| 8 | TASK-008 | Simulated challenge lifecycle | State-machine and authorization tests |
| 9 | TASK-009 | Monthly qualification calculator | Decimal precision and boundary tests |
| 10 | TASK-010 | Twelve-month streak tracker and audit | Consecutive-month/reset tests |
| 11 | TASK-011 | Reward/legal separation controls | Negative tests prove all payouts disabled |
| 12 | TASK-012 | Production readiness | Security, observability, backup/restore, release review |

## Execution protocol

1. Confirm dependencies and current task state.
2. Write or update the task specification and acceptance criteria.
3. Implement only the current task.
4. Add automated tests for normal, boundary, failure, and authorization cases.
5. Run tests and inspect the resulting evidence.
6. Update the task status and record commit/PR references.
7. Proceed to the next task only when the current task's exit gate is met.

A failed verification blocks progression. A policy ambiguity is recorded as a decision request; it is never filled with an invented assumption.
