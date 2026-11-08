# Working agreement — My Agent Skill Hub

This file is intentionally short to conserve context. Detailed procedures live in skills and docs. Applies to all human and AI contributors.

## Non-negotiable defaults (unless the user **explicitly** approves a documented project-scoped exception)
1. **Understand before coding.** Identify goal, users, acceptance criteria, limits, risk and evidence. For nontrivial or new projects create/update `PROJECT_BRIEF.md` and `TASK_PLAN.md`.
2. **Choose stack per project.** Never impose a default framework without considering requirements, existing code, maintainability, team skills, data/privacy, operations and cost. Record options, rationale, trade-offs and approval in `STACK_DECISION.md`. Prefer the simplest viable solution.
3. **Documentation is a deliverable.** For EVERY meaningful task record intent, files changed, rationale, decisions, tests/evidence, outcome and next steps in `WORK_LOG.md` (hub: `docs/WORK_LOG.md`). Maintain `CHANGELOG.md` for user-visible changes; ADR for consequential architecture changes. Never claim a test ran if it did not.
4. **Quality gates.** Run relevant formatting, lint/static analysis, tests, security checks and review. Record actual commands/results. Report skipped/failed checks and risks. Avoid unrelated changes.
5. **Security/privacy.** No secrets, credentials, customer data, PHI, raw production logs or identifying personal data in code, examples, prompts or output. Never read/write production, deploy, delete or migrate destructively without explicit scoped approval. Apply least privilege and threat modeling proportional to risk.
6. **Token discipline.** Read only relevant files and bounded log output; use one agent by default. Delegate only for meaningful context isolation or independent work. Share short summaries and artifact paths rather than repeating entire histories. Track usage when the runtime exposes it; never invent savings.
7. **Audit exceptions.** User-approved exceptions must be recorded in `EXCEPTIONS.md` with exact rule, reason, approver, scope, date, expiry, risks and compensating controls. No exception may override access controls, secret protection or the requirement for honest evidence.
8. **Before handoff**: provide what changed, where, test evidence, unresolved limitations, docs written and how to verify/rollback.

## Mandatory skill routing
- All work: consult `token-budget` policy and `documentation-ledger` before finishing.
- New idea: `project-intake`; stack choice/change: `stack-selection`.
- Code changes: `test-and-verify` and `secure-development`; major design: `architecture-review`.
- Delivery: `pr-handoff`; incident response: `incident-analysis`.

Agents are optional specialists, not a permanent swarm. In Claude Code use .claude/agents; skills load from .claude/skills. Codex uses .agents/skills. Master skill source: skills/. Run `python scripts/hub.py sync` if changing master skills; `python scripts/hub.py validate` before commit.

Read `docs/GOVERNANCE.md` only for exceptions/gates, `docs/ARCHITECTURE.md` for system changes, and relevant project files for project work.