---
name: token-budget
description: Use for all agent work to minimize needless context, model calls, retries and total token cost.
---

# token-budget

## Procedure
1. Identify the exact question and minimal relevant paths; list top sources before reading full files.
2. Prefer filtered searches, line ranges, concise tool outputs and deterministic scripts over copying massive logs into prompts. Never read whole repositories: use Python or deterministic tools to inventory files and print counts. Never repeat an audit already done; reuse its report.
3. Model routing: Opus only coordinates and decides (main-session orchestrator). Executors use moderate effort: `effort: medium` by default, `low` or `high` per task, never `xhigh` or `max`. Haiku for simple bounded tasks (research, documentation, validation, lookups); Sonnet only when complexity justifies it (implementation, architecture, security, QA, review). Pass `model` explicitly on every delegation; never escalate an executor to Opus. Default to 1 executor; at most 2 at the same time, only for independent tasks with non-overlapping files and a stated justification.
4. Skills load on demand: do not preload or read many skills at once. External skills are reached through `skill-catalog` (search, then read only the one chosen SKILL.md).
5. When delegating pass objective, limited context paths, acceptance criteria, output format and stop conditions. Handoff only summary + artifact references.
6. At most 1 retry (`max_retries: 1`); then change strategy or report the task as blocked rather than blindly retrying.
7. Record real consumption from harness evidence: task-notification `subagent_tokens`/`duration_ms`/`tool_uses`, or stream-json `modelUsage`; the effective model from `message.model`. Never from estimates or agent names. If unavailable write **not measured**; never invent savings.
8. Optimize **cost per correctly verified outcome**, not raw answer length. Never drop security, QA or documentation to save tokens.

9. Budget and sessions: `model_guard` enforces the executor budget per phase and per session (`MODEL_POLICY.json`, persisted in `.agent-hub/budget/state.json`, not reset by new sessions) and blocks delegation when usage cannot be measured; an executor that is already running can exceed it. Start a new session per phase with `docs/reports/LATEST_REPORT.md` as handoff. Preloaded skills are not invoked again; deterministic operations are not delegated; reviews are proportional to risk.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
