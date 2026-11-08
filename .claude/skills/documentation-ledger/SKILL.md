---
name: documentation-ledger
description: Use on every meaningful project task to record decisions, code changes, tests, quality evidence and handoff.
---

# documentation-ledger

## Procedure
1. At start identify project WORK_LOG, PROJECT_BRIEF and TASK_PLAN; if absent create from templates proportionately.
2. On architecture or stack decisions capture options, why chosen, dated approval and consequences in STACK_DECISION or an ADR.
3. During work keep a concise running record of intent, files touched, decisions and blockers. Do not paste secrets, PHI, or full unredacted logs.
4. On completion append a dated WORK_LOG entry stating objective, changed paths, actual commands/results, security review, risks, next actions and responsible party.
5. Update CHANGELOG for user-visible changes and runbooks/API docs for changed interfaces. Generate QUALITY_REPORT and HANDOFF for deliveries.
6. Check every claim against actual evidence: distinguish passed, failed, skipped and not-run. If any mandatory record missing flag the task incomplete.
7. If the user explicitly waives a process step, register exact scope/approver/date/risk/expiry and compensation in EXCEPTIONS. Never silently omit controls.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
