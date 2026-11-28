---
name: token-budget
description: Use for all agent work to minimize needless context, model calls, retries and total token cost.
---

# token-budget

## Procedure
1. Identify the exact question and minimal relevant paths; list top sources before reading full files.
2. Prefer filtered searches, line ranges, concise tool outputs and deterministic scripts over copying massive logs into prompts.
3. Model routing: Opus only for the main-session orchestrator; Sonnet for specialized execution (implementation, architecture, security, QA, review); Haiku for simple bounded tasks (research, documentation, validation, lookups). Pass `model` explicitly on every delegation; never escalate an executor to Opus. Default to 1 executor; at most 3 in parallel, only for independent tasks with non-overlapping files.
4. When delegating pass objective, limited context paths, acceptance criteria, output format and stop conditions. Handoff only summary + artifact references.
5. At most 2 retries (`max_retries: 2`); then change strategy or report the task as blocked rather than blindly retrying.
6. Record durations and tokens only from harness evidence (task-notification `duration_ms`/`subagent_tokens`/`tool_uses`, or stream-json `modelUsage`) and the effective model from runtime evidence (`message.model`), never from estimates or agent names. If unavailable write **not measured**; never invent savings.
7. Optimize **cost per correctly verified outcome**, not raw answer length. Never drop security, QA or documentation to save tokens.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
