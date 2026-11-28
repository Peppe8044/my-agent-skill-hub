# Changelog del hub

## Unreleased — 2026-11-27
- Add 15 game specialists and 24 portable skills; external integration registry.
- 2026-11-28 (HUB-009): política de modelos aplicada en runtime.
  - `model_guard`, un hook PreToolUse propio, bloquea subagentes que no usen `sonnet`/`haiku`: Opus explícito, `fork` o built-ins sin modelo.
  - `MODEL_POLICY.json` añade `default_parallel_agents: 1`, y `validate` comprueba el esquema completo.
  - `launch` rechaza las variables de entorno que alteran el modelo.
  - Sustituye la regla de la 0.3.1 ("escalar a opus requiere aprobación explícita") y la asignación de la 0.2.0 (opus para supervisor, solution-architect y security-reviewer). Ningún ejecutor usa Opus. Ambas entradas se conservan como historial.
- `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` se mantiene como respaldo: con Claude Code 2.1.332 se verificó que no anula el modelo de cada agente (docs/MODEL_ROUTING_REPORT.md).
- Instalador `full` (sigue siendo el predeterminado):
  - No declara servidores MCP de GitHub o ClickUp si ya existen en el proyecto, en el ámbito usuario/local o como conector de claude.ai.
  - Fusiona `.claude/settings.json` sin perder la configuración del proyecto.
  - Nunca sobrescribe archivos modificados por el proyecto: los deja en `.agent-hub/incoming/`.
- `doctor` comprueba el entorno real: Git y submódulos, Claude Code, gh, Docker, Ollama por HTTP, Godot, variables de modelo, `core.longpaths` y OneDrive. Admite `--json`.
- `validate` comprueba que los commits fijados de los submódulos coincidan con la documentación y el registro.

## 0.3.1 - 2026-11-27
- Solo el orquestador usa `opus`; supervisor, solution-architect y security-reviewer pasan a `sonnet`. Escalar a opus requiere aprobación explícita del usuario.
- Las skills requeridas deben invocarse con la herramienta Skill; leerlas desde archivo no cuenta como aplicada.
- Un revisor distinto (por ejemplo ECC) no reemplaza a qa-engineer antes de aceptar un cambio.

## 0.3.0 — 2026-11-26
- Cada agente de `.claude/agents/` precarga sus skills obligatorias con el campo `skills` del encabezado (Claude Code las inyecta al iniciar el subagente): `token-budget` y `documentation-ledger` en todos, más las de su rol (por ejemplo `web-ui`, `test-and-verify` y `secure-development` en frontend-engineer).
- Contrato `### Run report` obligatorio al final de cada entrega: agente, modelo exacto, skills aplicadas, inicio/fin, estado y comandos ejecutados.
- `orchestrator`: reglas de delegación obligatorias (modelo explícito, skills por encargo, rechazo de entregas sin Run report, revisión de security-reviewer y qa-engineer antes de aceptar cambios materiales) y registro de ejecuciones con duración/tokens del runtime.
- Nueva plantilla `templates/project/AGENT_RUNS.md`; `hub.py validate` falla si un agente no precarga skills existentes, omite las obligatorias o no exige el Run report.

## 0.2.0 — 2026-11-26
- Nuevo agente `orchestrator`: sesión principal (`claude --agent orchestrator`) en el modelo más capaz, que toma decisiones y delega ejecución con ruteo explícito de modelos.
- Modelo por rol en `.claude/agents/`: `opus` para roles de decisión (supervisor, solution-architect, security-reviewer), `sonnet` para ejecutores y revisores.

## 0.1.0 — 2026-11-08
- Configuración inicial del hub con agentes Claude Code y skills portables.
- Documentos de gobierno, protocolo de tareas, plantillas de proyecto y guía de stack dinámico.
- CLI de diagnóstico/inicialización, validaciones y workflow de CI.
- Registro obligatorio de trabajo y criterios de aceptación.

No se ha habilitado un runtime autónomo que ejecute agentes sin intervención.
- HUB-005: eight upstream Git submodules, pinned to explicit commits; no automatic activation.

- HUB-006: default project installer, automatic bootstrap for new, external skill catalog and conflict checks.

- HUB-007: project MCP defaults, approved external skill installation and diagnostics.

- HUB-008: one-command bootstrap, local diagnostics and verified launcher.
