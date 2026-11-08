---
name: incident-analysis
description: Use for operational incidents, outages, unexpected errors or postmortem drafting.
---

# incident-analysis

## Procedure
1. Establish impact, scope, detection time, symptoms and current state from authorized evidence.
2. Collect minimal redacted logs and metrics, form hypotheses and falsify them; avoid restarting systems as a diagnostic default.
3. Separate immediate mitigation from root cause and long-term prevention; note evidence gaps.
4. Define timelines, contributing factors, user-visible impact, recovery criteria and owners.
5. Document actual commands, permission scope, safe rollback, prevention actions and validation in an incident report. No production writes without explicit approval.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
