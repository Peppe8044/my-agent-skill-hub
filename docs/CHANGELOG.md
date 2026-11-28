# Changelog del hub

## Unreleased — fase 4.1 (2026-11-28)
- Presupuesto real y persistente de ejecutores en `model_guard`: 50.000 tokens ponderados por fase y por sesión, con reserva de 10.000 por ejecutor activo. Mide input, output, cache creation y 0,1 × cache read; el libro `.agent-hub/budget/state.json` sobrevive a las sesiones nuevas. Bloquea si no puede medir, salvo recuperación autorizada (`hub.py budget authorize-recovery`). Sustituye a `max_executor_tokens_per_session`.
- Concurrencia: 1 ejecutor por defecto, 2 como máximo y 1 reintento; el hook aplica el tope de 2 aunque la política local indique otro valor.
- Skills obligatorias efectivas: `mandatory_agent_skills` en `MODEL_POLICY.json`. `model_guard` deniega los agentes que no precargan `token-budget` o cuyo archivo de skill falta, así como los built-ins y `fork`; `catalog.py enable` inyecta las skills obligatorias en los agentes externos.
- Herencia automática: nuevo `hub.py update` (actualización segura que conserva los valores ajustables del proyecto y restablece las claves centrales); `launch` actualiza antes de abrir la sesión y admite `--phase`. `usage_tracker` es obligatorio en todos los perfiles y se registra en Stop y SubagentStop, también en proyectos existentes.
- Orquestador con effort `medium`. Se eliminan la delegación de operaciones deterministas, la reinvocación de skills precargadas y las revisiones redundantes (ahora proporcionales al riesgo); sesión nueva por fase usando `LATEST_REPORT.md` como traspaso.
- ECC: se activan `strategic-compact` y `context-budget`; `cost-tracking` queda pendiente de su servicio.
- Rol del orquestador: solo coordina, planifica, decide y acepta. Ejecuta comandos deterministas cortos; la implementación es de Sonnet. Los informes muestran el consumo del orquestador y el de los ejecutores por separado.
- Informes de subfase (`PHASE_04_1_REPORT.md`) y requisito permanente documentado en `docs/GOVERNANCE.md`, con pruebas de herencia (`tests/test_inheritance.py`).

## Unreleased — fase 4 (2026-11-28)
- Gestor de hooks (`hub.py hooks registry|list|enable|disable|verify`):
  - `registry/HOOK_REGISTRY.json` contiene 110 hooks con procedencia, sha256, riesgo y estado.
  - `bootstrap` instala los aprobados: `model_guard`, `command_guard`, `file_guard`, `usage_tracker` y `config-protection` de ECC.
  - Activar o desactivar un hook crea una copia de seguridad que se deshace con `rollback`.
- Presupuesto real de tokens de ejecutores por sesión (`max_executor_tokens_per_session`), aplicado por `model_guard`.
- Informes consolidados por fase (`hub.py report render|latest|check`, 19 secciones, filtro de privacidad), heredados por los proyectos.
- Hashes de contenido independientes del salto de línea.
- OpenViking pasa a `excluded-by-policy`: AGPL permite redistribuir bajo condiciones.

## Unreleased — fase 3 (2026-11-28)
- Capacidades externas:
  - `hub.py external-scan` genera de forma determinista el inventario de los 8 submódulos, el registro central `registry/external_capabilities.json` y los informes de compatibilidad y licencias.
  - Resultado: 995 skills aprobadas (14 activas y 981 en el catálogo), 181 pendientes de revisión de scripts y 1 028 rechazadas; 45 agentes aprobados al catálogo y 267 rechazados.
- `install`, `new` y `bootstrap` (perfil `full`) instalan automáticamente las capacidades aprobadas:
  - Las skills activas van a `.claude/skills` y `.agents/skills`.
  - El catálogo bajo demanda va a `.agent-hub/catalog`, con `skill-catalog` y `.agent-hub/bin/catalog.py`.
  - Las licencias se copian junto al contenido.
  - El manifiesto guarda la procedencia (commit fijado y sha256), y hay copias de seguridad y `hub.py rollback`.
- Control de tokens:
  - Esfuerzo `medium` para los ejecutores y `high` para el orquestador; `launch` pasa `--effort`.
  - `model_guard` bloquea `xhigh`/`max`.
  - El orquestador solo precarga las 2 skills obligatorias.
  - Nuevas reglas de tokens en `AGENTS.md` y en `token-budget`.
- `doctor` informa del estado del catálogo externo; `validate` comprueba el registro externo.

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
