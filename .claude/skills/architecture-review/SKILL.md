---
name: architecture-review
description: Use for system design or changes affecting contracts, storage, security boundaries or production reliability.
---

# architecture-review

## Procedure
1. Draw a component/data-flow diagram and trust boundaries; describe source of truth and interfaces.
2. Analyze single points of failure, data consistency, retries, versioning, rollback, migration, observability and operational ownership.
3. Evaluate smallest solution and alternatives; identify irreversible choices and measurable risks.
4. Record decision as ADR with context, rejected choices, consequences, proof and review date.
5. Run security-review for sensitive inputs or public endpoints. Link architecture to acceptance criteria.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
