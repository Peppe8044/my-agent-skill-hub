---
name: data-pipelines
description: Use for ETL, ingestion, transformations, analytics engineering and data quality.
---

# data-pipelines

## Procedure
1. Define source contracts, schema, refresh schedules, late data and allowed access scope.
2. Create idempotent transforms, checkpointing and transactional boundaries; avoid destructive loads without backups and approval.
3. Build tests for schema, duplicates, nulls, reconciliation and drift; monitor freshness and errors.
4. Document lineage, runbook, recovery, ownership and performance evidence.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
