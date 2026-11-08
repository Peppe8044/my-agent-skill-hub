# Skills catalog (18)

Canonical sources: `skills/*/SKILL.md`. Runtime copies: `.claude/skills/*/SKILL.md` and `.agents/skills/*/SKILL.md`. Run `python scripts/hub.py sync` after editing canonical skills; `python scripts/hub.py validate` checks byte-for-byte sync.

- **token-budget** — Use for all agent work to minimize needless context, model calls, retries and total token cost.
- **documentation-ledger** — Use on every meaningful project task to record decisions, code changes, tests, quality evidence and handoff.
- **project-intake** — Use when a project starts or its requirements change to define scope, risks and acceptance criteria before coding.
- **stack-selection** — Use before a new project's technology selection or architectural migration; justify stack based on actual requirements.
- **architecture-review** — Use for system design or changes affecting contracts, storage, security boundaries or production reliability.
- **test-and-verify** — Use whenever code, configs, data pipelines or system behavior changes; enforce meaningful, reproducible quality checks.
- **secure-development** — Use for all changes involving inputs, credentials, persistence, permissions, external access or sensitive data.
- **code-review** — Use before merging changes to check correctness, maintainability, tests, security and adherence to project conventions.
- **pr-handoff** — Use at the end of a feature, PR or deliverable to prepare trustworthy handoff and review.
- **incident-analysis** — Use for operational incidents, outages, unexpected errors or postmortem drafting.
- **agent-factory** — Use when creating, revising or retiring a reusable specialist agent within the hub.
- **skill-factory** — Use when authoring or improving portable SKILL.md workflows and their supporting scripts or references.
- **api-design** — Use when designing APIs, schemas and external or internal service contracts.
- **data-science** — Use for statistical analysis, experiments, ML model development and reproducible research.
- **data-pipelines** — Use for ETL, ingestion, transformations, analytics engineering and data quality.
- **sre-operations** — Use for infra changes, reliability plans, monitoring, backup, deployment and incident prevention.
- **integration-contracts** — Use when integrating APIs, webhooks, HL7, databases or external systems.
- **web-ui** — Use when building frontend experiences, forms, data fetching and accessible component systems.

**Mandatory transversal policies:** `documentation-ledger`, `token-budget`, and risk-relevant quality/security controls. They are workflow obligations; a separate agent process is not always needed.
