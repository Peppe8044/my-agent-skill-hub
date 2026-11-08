---
name: stack-selection
description: Use before a new project's technology selection or architectural migration; justify stack based on actual requirements.
---

# stack-selection

## Procedure
1. Read PROJECT_BRIEF and existing repository languages/dependencies first. Preserve existing stack unless change has a compelling benefit.
2. Establish simple baseline and at least two viable alternatives; if one dominates, explain why instead of manufacturing choices.
3. Compare functionality, skills, ecosystem, deployment, security, data sensitivity, total ownership cost, maintainability, scale and reversibility. Weights adapt to project; never treat heuristics as objective benchmarks.
4. Check current official docs/compatibility for selected tool versions, and run a small spike when uncertainty is material.
5. Recommend only needed components (no default ORM, database, frontend, queue or swarm). Explain explicitly what was excluded.
6. Complete STACK_DECISION.md with reasons, risks, migration and approver; create ADR for durable decisions. Do not start irreversible implementation before approval.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
