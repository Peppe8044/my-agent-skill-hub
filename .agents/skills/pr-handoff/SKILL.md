---
name: pr-handoff
description: Use at the end of a feature, PR or deliverable to prepare trustworthy handoff and review.
---

# pr-handoff

## Procedure
1. Confirm work completed relative to acceptance criteria, implementation paths and open blockers.
2. Check WORK_LOG, quality report, changelog, security review and ADRs as applicable; demand missing evidence.
3. Summarize what changed, why, how to test, commands actually run, limits, rollback and next steps.
4. Do not imply merges/deploys executed if not done. Provide commit/PR references only if verified.
5. For skipped controls, ensure explicit dated EXCEPTIONS entry authorized by owner.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
