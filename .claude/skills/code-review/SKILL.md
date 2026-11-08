---
name: code-review
description: Use before merging changes to check correctness, maintainability, tests, security and adherence to project conventions.
---

# code-review

## Procedure
1. Read diff, requirements, API/stack decision and relevant tests only.
2. Prioritize bugs, auth/data/security issues, incorrect edge handling, concurrency, performance and overcomplexity.
3. Reference exact files/lines and specify reproducible fixes; mark uncertain findings explicitly.
4. Verify logs/docs reflect actual changes and that tests were run rather than merely written.
5. Produce severity-ranked review; fixes should be small and scoped. No blanket approvals without evidence.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
