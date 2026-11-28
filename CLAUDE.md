# Claude Code entry point

Follow [AGENTS.md](AGENTS.md) for mandatory rules. Do not repeat its content in your prompt.

Use project-local Claude agents in `.claude/agents/` when their specialized context adds value. Use skills in `.claude/skills/` on demand. Start with `claude --agent orchestrator --model opus`; delegate to one executor by default (max 3 in parallel, max 2 retries), always with explicit `model: sonnet` or `haiku` (never Opus, `fork` or `inherit`; the `model_guard` hook denies it); do not activate experimental Agent Teams automatically. Never claim agent-to-agent messaging or automated execution exists without confirming the runtime.

For tasks requiring code changes: evidence in the relevant `WORK_LOG.md` and tests/security checks are required by default. For new projects: choose the stack **after** analyzing requirements and documenting alternatives.