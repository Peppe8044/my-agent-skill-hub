# Agent catalog

These are **specialty definitions**. The runnable Claude Code subagent manifests are in `.claude/agents/`. Agent definitions do not automatically run or communicate across providers. Supervisor selects specialists only as needed, in line with docs/AGENT_PROTOCOL.md and token-budget policy.

## All 14 specialists
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
