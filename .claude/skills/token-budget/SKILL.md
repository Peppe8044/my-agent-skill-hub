---
name: token-budget
description: Use for all agent work to minimize needless context, model calls, retries and total token cost.
---

# token-budget

## Procedure
1. Identify the exact question and minimal relevant paths; list top sources before reading full files.
2. Prefer filtered searches, line ranges, concise tool outputs and deterministic scripts over copying massive logs into prompts.
3. Default to one agent. Delegate only if subtasks can work independently or need context isolation; record cost/coordination reasons.
4. When delegating pass objective, limited context paths, acceptance criteria, output format and stop conditions. Handoff only summary + artifact references.
5. After 2 ineffective attempts, change strategy or report a blocker rather than blindly retrying.
6. If the runtime exposes prompt/completion tokens and costs, log them in the project report. If unavailable write **not measured**; never invent savings.
7. Optimize **cost per correctly verified outcome**, not raw answer length. Never drop security, QA or documentation to save tokens.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
