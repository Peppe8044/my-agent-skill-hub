# Agent catalog

These are **specialty definitions**. The runnable Claude Code subagent manifests are in `.claude/agents/`. Agent definitions do not automatically run or communicate across providers. Supervisor selects specialists only as needed, in line with docs/AGENT_PROTOCOL.md and token-budget policy.

**Effort:** executors declare `effort: medium` in their frontmatter and the orchestrator `effort: high`; the orchestrator preloads only the two mandatory skills (`token-budget`, `documentation-ledger`) and invokes the rest on demand.

## All 15 agents
- **orchestrator**: Main-session lead (`claude --agent orchestrator`, model opus). Makes decisions and delegates execution to the specialists below with explicit model routing.
- **supervisor**: Coordinate complex work, route to specialists and enforce delivery gates.
- **requirements-analyst**: Turn vague ideas into specific requirements and acceptance criteria.
- **solution-architect**: Select architecture and stack independently for each project.
- **researcher**: Perform focused, source-backed technical research.
- **backend-engineer**: Implement tested APIs, services, integrations and persistence.
- **frontend-engineer**: Build accessible, testable user interfaces.
- **data-scientist**: Build robust analytics and machine-learning evaluations.
- **data-engineer**: Design reliable data ingestion and transformation pipelines.
- **sre-engineer**: Engineer reliability, deployment and observability.
- **security-reviewer**: Analyze threats, access controls, dependency and secret risks.
- **qa-engineer**: Verify behavior, regressions and acceptance criteria.
- **code-reviewer**: Review implementation quality, maintainability and correctness.
- **documentation-keeper**: Maintain complete, verifiable project documentation and traceability.
- **integration-engineer**: Build reliable connections to external APIs and systems.

**Always-on policy:** documentation-keeper is a mandatory workflow role for all material tasks (can be fulfilled by primary agent following documentation-ledger; never spawn unnecessarily). QA/security checks are risk-proportionate, but cannot be silently skipped. The user may expressly authorize a scoped process exception with record.

## Skills y reporte de ejecución
Cada manifiesto de `.claude/agents/` lista sus skills obligatorias en el campo `skills` (Claude Code las precarga al iniciar el subagente) y exige terminar con el bloque `### Run report` (agente, modelo exacto, skills aplicadas, inicio/fin, estado, comandos). El orquestador registra cada delegación en `AGENT_RUNS.md` (plantilla en `templates/project/`). `hub.py validate` verifica ambas cosas.

## Model routing
Final policy (ADR 0003, `MODEL_POLICY.json`):
- **Opus only for the main-session orchestrator** (`claude --agent orchestrator --model opus`). Exactly one Opus agent.
- **Sonnet** = specialized execution: implementation, architecture, security, QA and review (including supervisor, solution-architect and security-reviewer).
- **Haiku** = simple, bounded tasks: researcher, documentation-keeper, asset-validator, localization-agent, memory-curator and the built-in Explore lookups.
- Every delegation passes an explicit `model` (`sonnet` or `haiku`). No `model: inherit`, no Opus/Fable/full model IDs on executors, and **no escalation of any executor to Opus under any circumstance**. Built-in `general-purpose` and `Plan` inherit the main model, so they always need an explicit `model`; `fork` is not allowed (it inherits Opus).
- Parallelism: 1 executor by default (`default_parallel_agents: 1`), at most 3 in parallel (`max_parallel_agents: 3`) and only for independent tasks with non-overlapping files; `max_retries: 2`, then report as blocked.
- Enforcement: (1) `python scripts/hub.py validate` (static: `MODEL_POLICY.json` schema, agent frontmatter; project settings must set `env.CLAUDE_CODE_SUBAGENT_MODEL` to sonnet/haiku and must not set the other model variables); (2) PreToolUse hook `.claude/hooks/model_guard.py` with matcher `Agent|Task` (runtime: denies any call whose model would not be sonnet/haiku); (3) `python scripts/hub.py launch` refuses to start if the process environment sets `CLAUDE_CODE_SUBAGENT_MODEL` to anything other than sonnet/haiku, or sets `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` or `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` in `.claude/settings.json` is the Sonnet fallback for any subagent launched without an explicit model; observed precedence (Claude Code 2.1.332, re-verify on upgrades): explicit `model` param > agent frontmatter > `CLAUDE_CODE_SUBAGENT_MODEL` > inherited main model.
- The effective model comes from runtime evidence (stream-json `message.model`, session transcripts, `modelUsage`), never from agent names or frontmatter. See `docs/MODEL_ROUTING_REPORT.md` and `agents/orchestrator.md`.

### Historial
HUB-002 / CHANGELOG 0.2.0 assigned opus to supervisor, solution-architect and security-reviewer, and CHANGELOG 0.3.1 (HUB-004 on main) allowed escalating an executor to opus with explicit approval. Both rules are **superseded** by `docs/decisions/0003-model-routing-policy.md`; earlier log entries are kept.

### Indie studio agents
Besides the 15 agents above, `.claude/agents/` includes the indie studio agents (Godot, art, audio, balance, game QA, localization, Steam, memory, etc.). All are `sonnet` except `asset-validator`, `localization-agent` and `memory-curator` (`haiku`); the frontmatter validated by `hub.py validate` is the source of truth.
