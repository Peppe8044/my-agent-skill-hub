---
name: sre-operations
description: Use for infra changes, reliability plans, monitoring, backup, deployment and incident prevention.
---

# sre-operations

## Procedure
1. Identify target environment and access policy. Begin read-only and avoid production modifications without explicit approval.
2. Define SLO, health signals, backup/RPO/RTO, capacity, alert thresholds and operational runbooks as warranted.
3. Favor reversible, incremental changes; supply rollback commands and clear stop conditions.
4. Validate through controlled QA or authorized staging; document commands, observations and unresolved risks.
5. Update runbooks, incident notes and change record for every material operation.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
