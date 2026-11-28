# Reporte de skills externas

Generado por `scripts/external_scan.py` (solo lectura, sin timestamps). Regenerar con `python scripts/hub.py external-scan`.

> La clasificación es automatizada por reglas deterministas; no es una auditoría de seguridad completa y el contenido aprobado no ha sido revisado manualmente línea por línea.

## Repositorios

| Repo | Commit | Licencia | Redistribucion | Skills | Agentes | Hooks | MCP | Scripts | Manifiestos deps | Configs |
|---|---|---|---|---|---|---|---|---|---|---|
| Anthropic-Cybersecurity-Skills | 54a798831d22 | Apache-2.0 | allowed | 818 | 0 | 0 | 0 | 1105 | 0 | 2 |
| ECC | 4adeee6732a1 | MIT | allowed | 1089 | 311 | 244 | 43 | 1463 | 36 | 63 |
| OpenViking | 600babf130a8 | AGPL-3.0 | excluded-by-policy | 96 | 1 | 43 | 11 | 4411 | 29 | 27 |
| agentmemory | 5c9e2e698bda | Apache-2.0 | allowed | 17 | 0 | 35 | 8 | 771 | 7 | 12 |
| awesome-harness-engineering | 0b14b85ab0fe | none | forbidden | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| diagram-design | 795eec47fd37 | MIT | allowed | 1 | 0 | 0 | 0 | 124 | 2 | 7 |
| rea | 8ff311b4ca0c | MIT | allowed | 6 | 0 | 0 | 4 | 8430 | 7 | 5 |
| scientific-agent-skills | c21d13b3cc28 | MIT | allowed | 177 | 0 | 0 | 0 | 776 | 5 | 1 |

## Totales encontrados

Skills: 2204; agentes: 312; hooks: 322; mcp: 66; scripts: 17080; manifiestos de dependencias: 86; configs: 117; manifiestos de plugin: 36.

Hooks, MCP, plugins, settings y dependencias son siempre `inventory-only` (nunca se activan).

## Decisiones

- skills: approved=998, rejected=1025, requires-review=181
- agents: approved=45, rejected=267

### Por motivo

| Motivo | Items |
|---|---|
| duplicate-of | 1 |
| duplicate-of-own | 32 |
| invalid-name | 2 |
| license-not-allowed | 112 |
| model-missing-or-inherit | 34 |
| model-opus-not-allowed | 20 |
| non-canonical-copy | 1046 |
| offensive-security | 36 |
| out-of-scope-domain | 565 |
| requires-script-review | 218 |
| requires-service | 19 |
| requires-toolchain | 6 |
| unsafe-pattern | 38 |

## Skills activas aprobadas

| Id | Dominios | Descripcion |
|---|---|---|
| Anthropic-Cybersecurity-Skills--analyzing-kubernetes-audit-logs | security-defensive, sre-devops, web | Parses Kubernetes API server audit logs (JSON lines) to detect exec-into-pod, secret access, RBAC modifications, privile |
| Anthropic-Cybersecurity-Skills--implementing-aws-macie-for-data-classification | data-science, security-defensive, sre-devops | Enable and configure Amazon Macie via AWS CLI/Terraform to discover, classify, and protect sensitive data (PII, financia |
| Anthropic-Cybersecurity-Skills--implementing-just-in-time-access-provisioning | automation, security-defensive | Implements Just-In-Time (JIT) access provisioning to eliminate standing privileges by granting temporary, time-bound acc |
| Anthropic-Cybersecurity-Skills--implementing-pod-security-admission-controller | general, security-defensive, sre-devops | Configures and operates the Kubernetes Pod Security Admission (PSA) controller that enforces Pod Security Standards: nam |
| Anthropic-Cybersecurity-Skills--performing-docker-bench-security-assessment | security-defensive, sre-devops | Runs Docker Bench for Security, the open-source CIS Docker Benchmark audit script, across host configuration, daemon set |
| Anthropic-Cybersecurity-Skills--securing-helm-chart-deployments | security-defensive, sre-devops | Secures Helm chart deployments by verifying chart signatures and provenance, rendering and linting templates for misconf |
| ECC--backend-patterns | data-science, general, web | Backend architecture patterns, API design, database optimization, and server-side best practices for Node.js, Express, a |
| ECC--context-budget | security-defensive | Routes live context checks to the native Codex or Claude Code meter without scanning files, and performs a bounded stati |
| ECC--django-tdd | general, web | Django testing strategies with pytest-django, TDD methodology, factory_boy, mocking, coverage, and testing Django REST F |
| ECC--godot-patterns | games, web | Idiomatic Godot 4 GDScript patterns - static typing, scene and node design, signals, resources, autoloads, input, and li |
| ECC--godot-testing | games, general | Testing Godot 4 GDScript projects - a zero-dependency headless check scene, gdUnit4 and GUT suites, scene-runner tests,  |
| ECC--kotlin-testing | general | Kotlin testing patterns with Kotest, MockK, coroutine testing, property-based testing, and Kover coverage. Follows TDD m |
| ECC--rust-testing | automation, general | Rust testing patterns including unit tests, integration tests, async testing, property-based testing, mocking, and cover |
| ECC--strategic-compact | general | Suggests manual context compaction at logical intervals to preserve context through task phases rather than arbitrary au |
| scientific-agent-skills--benchling-integration | automation, data-science, general, web | Benchling Python SDK and REST API integration for registry entities, inventory, ELN entries, workflows, Benchling Apps,  |
| scientific-agent-skills--datalad | data-science, general | Retrieves, versions, and publishes scientific datasets with DataLad and git-annex, and captures computational provenance |

## Skills catalogo por dominio (total 982)

| Dominio | Skills |
|---|---|
| general | 254 |
| data-science | 138 |
| games | 0 |
| web | 147 |
| sre-devops | 253 |
| security-defensive | 760 |
| automation | 102 |

## Agentes aprobados (45)

| Id | Modelo | Dominios |
|---|---|---|
| ECC--a11y-architect | sonnet | security-defensive |
| ECC--bengali-reviewer | sonnet | general |
| ECC--build-error-resolver | sonnet | general |
| ECC--chief-of-staff | sonnet | automation |
| ECC--code-architect | sonnet | data-science, general |
| ECC--code-explorer | sonnet | general |
| ECC--commit-reviewer | sonnet | general |
| ECC--csharp-reviewer | sonnet | general, security-defensive |
| ECC--database-reviewer | sonnet | general, security-defensive |
| ECC--django-build-resolver | sonnet | general, web |
| ECC--django-reviewer | sonnet | security-defensive, web |
| ECC--doc-updater | haiku | general |
| ECC--docs-lookup | haiku | general, web |
| ECC--e2e-runner | sonnet | general |
| ECC--enrichment-agent | sonnet | data-science |
| ECC--fastapi-reviewer | sonnet | general, security-defensive, web |
| ECC--flutter-reviewer | sonnet | general |
| ECC--gdscript-reviewer | sonnet | games, web |
| ECC--harmonyos-app-resolver | sonnet | general, security-defensive, web |
| ECC--java-build-resolver | sonnet | general |
| ECC--java-reviewer | sonnet | general, security-defensive |
| ECC--kotlin-build-resolver | sonnet | general |
| ECC--kotlin-reviewer | sonnet | general |
| ECC--marketing-agent | sonnet | general |
| ECC--mle-reviewer | sonnet | data-science, sre-devops |
| ECC--network-architect | sonnet | automation, general |
| ECC--network-config-reviewer | sonnet | general, security-defensive |
| ECC--network-troubleshooter | sonnet | automation |
| ECC--opensource-forker | haiku | general |
| ECC--outreach-drafter | sonnet | data-science |
| ECC--php-reviewer | sonnet | security-defensive |
| ECC--pr-test-analyzer | sonnet | general |
| ECC--python-reviewer | sonnet | general, security-defensive |
| ECC--rag-pipeline-reviewer | sonnet | automation, general |
| ECC--react-build-resolver | sonnet | web |
| ECC--react-reviewer | sonnet | security-defensive, web |
| ECC--refactor-cleaner | sonnet | general |
| ECC--ruby-reviewer | sonnet | security-defensive, web |
| ECC--rust-build-resolver | sonnet | general |
| ECC--rust-reviewer | sonnet | general |
| ECC--seo-specialist | sonnet | data-science, general, security-defensive |
| ECC--silent-failure-hunter | sonnet | general |
| ECC--tdd-guide | sonnet | general |
| ECC--typescript-reviewer | sonnet | general, security-defensive, web |
| ECC--vue-reviewer | sonnet | general, security-defensive, web |
