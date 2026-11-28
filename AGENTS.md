# Working agreement — My Agent Skill Hub

This file is intentionally short to conserve context. Detailed procedures live in skills and docs. Applies to all human and AI contributors.

## Non-negotiable defaults (unless the user **explicitly** approves a documented project-scoped exception)
1. **Understand before coding.** Identify goal, users, acceptance criteria, limits, risk and evidence. For nontrivial or new projects create/update `PROJECT_BRIEF.md` and `TASK_PLAN.md`.
2. **Choose stack per project.** Never impose a default framework without considering requirements, existing code, maintainability, team skills, data/privacy, operations and cost. Record options, rationale, trade-offs and approval in `STACK_DECISION.md`. Prefer the simplest viable solution.
3. **Documentation is a deliverable.** For EVERY meaningful task record intent, files changed, rationale, decisions, tests/evidence, outcome and next steps in `WORK_LOG.md` (hub: `docs/WORK_LOG.md`). Maintain `CHANGELOG.md` for user-visible changes; ADR for consequential architecture changes. Never claim a test ran if it did not.
4. **Quality gates.** Run relevant formatting, lint/static analysis, tests, security checks and review. Record actual commands/results. Report skipped/failed checks and risks. Avoid unrelated changes.
5. **Security/privacy.** No secrets, credentials, customer data, PHI, raw production logs or identifying personal data in code, examples, prompts or output. Never read/write production, deploy, delete or migrate destructively without explicit scoped approval. Apply least privilege and threat modeling proportional to risk.
6. **Token discipline.** Read only relevant files and bounded log output; use one executor by default under Opus orchestration; delegate execution to Sonnet or Haiku. Share short summaries and artifact paths rather than repeating entire histories. Track usage when the runtime exposes it; never invent savings.
7. **Audit exceptions.** User-approved exceptions must be recorded in `EXCEPTIONS.md` with exact rule, reason, approver, scope, date, expiry, risks and compensating controls. No exception may override access controls, secret protection or the requirement for honest evidence.
8. **Before handoff**: provide what changed, where, test evidence, unresolved limitations, docs written and how to verify/rollback.
9. **Phase reports.** At the end of every implementation phase produce `docs/reports/PHASE_NN_REPORT.md` (19-section template: `templates/PHASE_REPORT.md`) with `python scripts/hub.py report render --data docs/reports/data/PHASE_NN.json` (projects: `.agent-hub/bin/phase_report.py`), then `report latest`. Generate deterministically first; Haiku drafting only when needed. Never paste full logs or secrets; distinguish done, pending and not measured.

## Mandatory skill routing
- All work: consult `token-budget` policy and `documentation-ledger` before finishing.
- New idea: `project-intake`; stack choice/change: `stack-selection`.
- Code changes: `test-and-verify` and `secure-development`; major design: `architecture-review`.
- Delivery: `pr-handoff`; incident response: `incident-analysis`.

Agents are optional specialists, not a permanent swarm. Model policy (MODEL_POLICY.json, mandatory): Opus only for the main-session orchestrator; Sonnet for specialized execution; Haiku for simple bounded tasks. Every delegation targets a project agent from `.claude/agents` that preloads the mandatory skills (`MODEL_POLICY.json` `mandatory_agent_skills`, always `token-budget`) and passes `model` explicitly (`sonnet`/`haiku`; built-ins such as `general-purpose`/`Plan`/Explore, `fork` and `inherit` are denied), and no executor is ever escalated to Opus. Default 1 executor, max 2 at the same time (independent tasks, non-overlapping files), max 1 retry, then report blocked. Enforced by `hub.py validate` (static), the `.claude/hooks/model_guard.py` PreToolUse hook (runtime, matcher `Agent|Task`) and `hub.py launch` (refuses forbidden model env vars). `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` in project settings is only the fallback for model-less subagents. Take the effective model from runtime evidence, never from names. In Claude Code use .claude/agents; skills load from .claude/skills. Codex uses .agents/skills. Master skill source: skills/. Run `python scripts/hub.py sync` if changing master skills; `python scripts/hub.py validate` before commit.

## Token rules (reusable config)
- Permanent: these rules live in the reusable core (`MODEL_POLICY.json` is the single source of truth) and reach every project through `install`, `new`, `bootstrap`, `update` and `launch`; see "Herencia obligatoria" in `docs/GOVERNANCE.md`. No skill, agent, plugin or MCP may override them.
- Opus only coordinates, plans, decides and accepts results. It may run existing short deterministic commands (validators, tests, generators, git/gh) and trivial edits of a few lines, but never takes on extensive implementation (new modules, multi-file or long changes) and never replaces Sonnet to stay under the executor budget: Sonnet implements, Haiku does simple bounded tasks; when the budget blocks, stop and report.
- Executors use `effort: medium` by default, `low`/`high` per task, never `xhigh` or `max`.
- One executor by default; at most 2 at the same time only with a stated justification.
- Never repeat an audit already done; reuse its report.
- Never read whole repositories into context; use Python or deterministic tools to inventory files and print counts.
- Haiku for simple tasks; Sonnet only when complexity justifies it.
- Skills load on demand: do not preload or read many skills at once; external skills are reached through `skill-catalog`.
- Report the orchestrator (main session) and the executors separately (`usage_tracker` records `main` and `subagents`; phase reports show them by role). Apply `token-budget` always and `strategic-compact`/`context-budget` at logical breakpoints or when context grows.
- Record real consumption (task-notification `subagent_tokens`/`duration_ms`, stream-json `modelUsage`) or write "not measured".
- Hard budget: `model_guard` blocks new delegations when this phase's or this session's executor usage plus a reserve per active executor would exceed `MODEL_POLICY.json` (`executor_budget_per_phase` and `executor_budget_per_session`: 50000; weighted input + output + cache creation + 0.1 x cache read). Usage is persisted per phase in `.agent-hub/budget/state.json`, so a new session does not reset it. If usage cannot be measured, delegation is blocked until the user authorizes recovery (`python scripts/hub.py budget authorize-recovery`). It cannot stop an executor that is already running: an active executor can exceed the budget.
- Start a new session per phase (`python scripts/hub.py launch --target . --phase <id>`) with `docs/reports/LATEST_REPORT.md` as handoff; do not carry long sessions across phases.
- Preloaded skills are already in context: do not invoke them again. Do not delegate deterministic operations (scripts, validators, inventories, single bounded commands). Reviews are proportional to risk. Limit each task to the files it needs and ask for bounded reports.

Read `docs/GOVERNANCE.md` only for exceptions/gates, `docs/ARCHITECTURE.md` for system changes, and relevant project files for project work.