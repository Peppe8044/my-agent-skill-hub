---
name: skill-factory
description: Use when authoring or improving portable SKILL.md workflows and their supporting scripts or references.
---

# skill-factory

## Procedure
1. Define an observable trigger and exclusions, goal, preconditions, input/output and success criteria; check whether a similar skill exists.
2. Use concise frontmatter with name and description; short numbered procedure in SKILL.md. Push large references into separate files, loaded on demand.
3. Put canonical skill in skills/<name>/SKILL.md; run python scripts/hub.py sync to copy to .claude/skills and .agents/skills.
4. Add representative positive/negative triggering examples or validation tests, and check no secrets/untrusted instructions are embedded.
5. Document change and measured benefit (when available) in WORK_LOG/CHANGELOG. Maintain compatibility with Agent Skills specification.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
