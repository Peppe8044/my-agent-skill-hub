---
name: agent-factory
description: Use when creating, revising or retiring a reusable specialist agent within the hub.
---

# agent-factory

## Procedure
1. Confirm an existing agent+skill cannot solve the problem; avoid unnecessary role proliferation.
2. Define narrow mission, triggers, exclusion cases, inputs, outputs, permissions, model/cost notes and quality gates.
3. Create conceptual profile in agents/<name>.md and Claude subagent in .claude/agents/<name>.md with valid frontmatter.
4. Require documentation-ledger, security and token-budget defaults; avoid broad tool privileges or uncontrolled delegation.
5. Update agents/README.md, registry/agents.json if present, WORK_LOG and CHANGELOG; add a test/validation check.
6. Verify the new agent is discovered by its target runtime; do not claim execution merely because YAML exists.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
