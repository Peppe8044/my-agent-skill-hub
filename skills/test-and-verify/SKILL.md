---
name: test-and-verify
description: Use whenever code, configs, data pipelines or system behavior changes; enforce meaningful, reproducible quality checks.
---

# test-and-verify

## Procedure
1. Derive tests from acceptance criteria including success, invalid input, failure, permission and regression cases.
2. Choose environment-appropriate unit/integration/e2e checks; use mocks for unauthorized systems.
3. Execute formatting, lint, type check and security scans where tools exist; report exact commands and exit codes.
4. If a check cannot run, write NOT RUN with reason and risk. Never claim passing based on code inspection alone.
5. Store focused evidence in QUALITY_REPORT, update WORK_LOG and block delivery for unresolved critical failures.
6. For production-affecting changes, verify rollback and migration safety without executing unapproved operations.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
