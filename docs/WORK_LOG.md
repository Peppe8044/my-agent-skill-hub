# Bitácora de trabajo del hub

| Fecha (UTC) | Tarea | Cambios y justificación | Validación / evidencia | Riesgos / siguiente paso |
|---|---|---|---|---|
| 2026-11-08 | HUB-001 | Creación de biblioteca de agentes y skills portables, selección de stack por proyecto, documentación obligatoria y CI | Configuración inicial y validación por CLI/CI prevista; verificar ejecución de workflow tras publicar | Aún no hay motor autónomo multiagente ni protecciones de rama activadas |
| 2026-11-26 | HUB-002 | Agrega agente `orchestrator` (sesión principal, `model: opus`) que decide y delega; asigna modelo por rol: opus a supervisor/solution-architect/security-reviewer, sonnet a ejecutores y revisores (antes todos `inherit`) | `python scripts/hub.py validate` y `python -m unittest discover -s tests -v` (ver commit) | Validar en un proyecto real que `claude --agent orchestrator` delega con el ruteo esperado |
| 2026-11-26 | HUB-003 | Skills obligatorias por agente vía campo `skills` (preload documentado de Claude Code), contrato `### Run report` (modelo, skills, tiempos, comandos), reglas de delegación del orquestador y plantilla `AGENT_RUNS.md`. Origen: en un proyecto real los subagentes no aplicaron skills porque las definiciones solo decían "consult relevant skills" y el orquestador no las nombró en los encargos | `python scripts/hub.py validate` -> PASS; `python -m unittest discover -s tests` -> 9 OK (incluye 2 pruebas nuevas del validador) | Verificar en la próxima ejecución real que cada entrega trae el Run report; la duración/tokens solo existen si el runtime los expone |
| 2026-11-27 | HUB-004 | Ruteo de modelos: solo orchestrator en opus, resto en sonnet; skills deben invocarse con Skill; qa-engineer no reemplazable por otro revisor. Pedido del usuario tras detectar solution-architect en opus en Support Hub/Arcana | `python scripts/hub.py validate` PASS; `python -m unittest` OK | Sincronizar agentes en Support Hub y en `~/.claude/agents` |


## Plantilla para nuevos registros
```md
### YYYY-MM-DD — ID — Título
- Objetivo:
- Decisión y por qué:
- Archivos afectados:
- Comandos/pruebas realmente ejecutados y resultado:
- Revisión de seguridad y documentación:
- Bloqueos, riesgos y próximas acciones:
- Responsable/aprobación:
```

## 2026-11-27 — HUB-004
Added 15 game specialists and 24 original portable skills. Runtime tests pending; external packages not installed. Review CI before merge.

## 2026-11-27 — HUB-005
Added eight upstream repositories as pinned Git submodules under external/. No upstream hooks, packages or MCP servers activated. Git checkout and runtime verification pending.

## 2026-11-27 — HUB-006
Project installer and automatic new-project bootstrap; external discovery only, no automatic activation. Tests added; runtime/CI results pending.

## 2026-11-27 — HUB-007
Added central external skill approval/copy mechanism, default remote MCP definitions, integration status command and local service setup guidance. No upstream skills approved or services executed yet. Tests added; execution pending.

## 2026-11-27 — HUB-008
Added bootstrap, local report, managed-file verification, explicit Opus launcher and tests. Previous CI run 46030114336 completed successfully. New CI and actual runtime checks pending.

## 2026-11-27 — Nota de fusión (HUB-004 duplicado)
El identificador HUB-004 se asignó en paralelo en `main` (ruteo de modelos, fila de la tabla superior) y en esta rama (especialistas de juego, sección anterior). Ambos registros se conservan sin cambios; las referencias posteriores usan `HUB-004/main` y `HUB-004/feat`.

### 2026-11-28 — HUB-009 — Fase 2: conflictos del PR #2, política de modelos verificada en runtime, instalador y doctor
- Objetivo: resolver los conflictos del PR #2 con `main` sin perder mejoras; corregir todos los hallazgos de la auditoría de fase 1 (política de modelos, instalador, doctor); verificar el ruteo con delegaciones reales.
- Decisión y por qué:
  - Merge (no rebase) de `origin/main` para no forzar el push.
  - Política final del owner: Opus solo orquestador, Sonnet ejecución especializada, Haiku tareas simples, sin escalada (ADR 0003).
  - `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` se **conserva**. La prueba real en Claude Code 2.1.332 mostró que solo actúa como respaldo de subagentes sin modelo y no anula el frontmatter. El hallazgo alto de la fase 1 era incorrecto para este runtime.
  - Se añade el hook propio `model_guard`, que es la única defensa ante un `model: opus` explícito.
  - El instalador mantiene `full` por defecto, con detección de MCP duplicados y preservación de archivos del proyecto (ADR 0004).
- Archivos afectados:
  - Merge `da57564`: orchestrator.md, CHANGELOG.md y WORK_LOG.md.
  - `f6c37f8`: scripts/{model_policy,doctor}.py (nuevos), hub.py, bootstrap.py, project_install.py, .claude/hooks/model_guard.py, .claude/settings.json, MODEL_POLICY.json y tests/.
  - `aef24f4`: AGENTS.md, CLAUDE.md, README.md, agents/, .claude/agents/{orchestrator,supervisor}.md, skill token-budget (3 copias), templates/project/AGENT_RUNS.md, docs/ y ADR 0003/0004.
  - Este registro: docs/MODEL_ROUTING_REPORT.md, docs/QUALITY_REPORT.md, CHANGELOG.md, endurecimiento y mensaje del hook.
- Comandos/pruebas realmente ejecutados y resultado:
  - `python scripts/hub.py validate`: PASS.
  - `python scripts/hub.py doctor`: exit 0, con 11 OK y 2 WARN (`core.longpaths`, repositorio dentro de OneDrive).
  - `python -m unittest discover -s tests -v`: 57 tests OK (170,5 s).
  - `git submodule status`: 8 submódulos en los commits fijados.
  - Commits verificados por separado en worktrees limpios: `f6c37f8` y `aef24f4`, ambos con validate PASS y 57 tests OK.
  - Pruebas reales de delegación `claude -p --agent orchestrator --model opus` antes, de control y después: ver docs/MODEL_ROUTING_REPORT.md. Costo total 1,0461 USD.
- Revisión de seguridad y documentación:
  - Revisado por el orquestador:
    - El hook falla de forma cerrada y no puede ampliarse a Opus desde MODEL_POLICY.json.
    - Ningún `subprocess` usa `shell=True`.
    - El instalador no imprime secretos de `~/.claude.json` (solo nombres y URLs normalizadas).
    - `doctor` nunca invoca el CLI de Ollama, que arranca la app de escritorio.
  - Documentación alineada en el commit `aef24f4`.
- Bloqueos, riesgos y próximas acciones:
  - Resultado del CI tras el push: ver el PR #2.
  - Hallazgo de la fase 1 pendiente: indie-game-studio aún no tiene la política instalada. Depende de fusionar el PR y de instalar MCP (restricción vigente).
  - Repositorios bajo una ruta de OneDrive: el proceso no está activo, pero hay riesgo si se reanuda la sincronización.
  - `core.longpaths` no está activado.
  - Repetir MODEL_ROUTING_REPORT al actualizar Claude Code.
- Responsable/aprobación: owner (Peppe8044) aprobó la fase 2 y la política; ejecución delegada por el orquestador Opus a ejecutores Sonnet/Haiku; merge del PR pendiente de autorización.

### 2026-11-28 — HUB-010 — Fase 3: integración de capacidades externas y control de tokens
- **Objetivo:**
  - Inventariar y clasificar de forma determinista los 8 submódulos.
  - Incorporar de forma automática las capacidades aprobadas, con carga bajo demanda, procedencia y rollback.
  - Incorporar las reglas de control de tokens a la configuración reutilizable.
- **Decisión y por qué (ADR 0005):**
  - Aprobación por reglas: licencia permitida; solo la copia canónica; las capacidades propias ganan en los duplicados; sin código y con revisión si la skill depende de scripts; solo seguridad defensiva; sin patrones inseguros; agentes solo Sonnet o Haiku.
  - Dos niveles:
    - 14 skills activas detectadas de forma nativa.
    - Catálogo bajo demanda con 981 skills y 45 agentes, accesible mediante `skill-catalog` y `.agent-hub/bin/catalog.py`.
    - Motivo: instalar cientos de skills activas añadiría sus descripciones al contexto de cada sesión.
  - Ajustes del orquestador sobre el escáner:
    - R6b: un nombre con intención defensiva anula los falsos positivos (10 recuperadas).
    - R9b: dominio por defecto según el repositorio.
    - Exclusión del nivel activo de las herramientas de ECC y de otros harnesses de orquestación.
  - `launch` pasa `--effort` porque la configuración global `xhigh` prevalecía sobre el frontmatter (evidencia en TOKEN_USAGE_REPORT).
- **Archivos afectados:**
  - Código y pruebas: `scripts/external_scan.py` (nuevo), `scripts/smoke_bootstrap.py` (nuevo), `templates/agent-hub/catalog.py` (nuevo), project_install, integrations, hub, bootstrap, doctor, model_policy, `model_guard`, `MODEL_POLICY.json` y tests (3 archivos nuevos).
  - Agentes y skills: `.claude/agents/*` (effort), skill `skill-catalog` y `token-budget`.
  - Registros: `registry/` (inventario, capacidades aprobadas y skills).
  - Documentación: `docs/` (3 informes generados, ADR 0005, TOKEN_USAGE_REPORT, QUALITY_REPORT), README, AGENTS.md y CLAUDE.md.
- **Comandos/pruebas realmente ejecutados y resultado:**
  - `python -m unittest discover -s tests`: 93 OK.
  - `python scripts/external_scan.py --check`: OK.
  - `python scripts/smoke_bootstrap.py <temp>`: `ok: true`.
  - Prueba real `claude -p` en el proyecto temporal: detección de 57 skills, carga bajo demanda, Opus y `xhigh` bloqueados.
  - `--effort high` verificado en la transcripción.
  - Proyecto temporal eliminado al terminar.
- **Revisión de seguridad y documentación:**
  - Sin ejecución de código externo; hooks, MCP y servicios solo en el inventario.
  - Validación de rutas en el instalador y en `catalog.py`.
  - Licencias copiadas; AGPL y repositorios sin licencia no se redistribuyen.
  - Ver QUALITY_REPORT.
- **Bloqueos, riesgos y próximas acciones:**
  - Revisión humana pendiente de 181 skills con scripts y de los 45 agentes del catálogo.
  - Sigue la configuración global `effortLevel=xhigh` (decisión del owner).
  - Agent Memory, OpenViking y los hooks de ECC siguen sin instalar (restricción vigente).
  - La instalación completa tarda alrededor de 1 minuto por los hashes y el `git status` de cada repositorio.
- **Responsable/aprobación:**
  - El owner (Peppe8044) autorizó la fase 3 y la fusión del PR #2.
  - Ejecutores: S1 Sonnet, S2 Sonnet y S3 Haiku, todos con `effort: medium`.
  - La fusión del nuevo PR está pendiente.

### 2026-11-28 — HUB-011 — Fase 4: ECC selectivo, gestor de hooks, presupuesto de tokens e informes por fase
- **Objetivo:**
  - Cerrar la fase 3.
  - Integrar los hooks de ECC de forma selectiva con un gestor reutilizable.
  - Aplicar un control efectivo de tokens.
  - Implantar informes consolidados heredables.
- **Decisión y por qué:**
  - Se aprueba solo `pre:config-protection` de ECC, tras revisar su código.
  - Se usan guardas propias deterministas (`command_guard`, `file_guard`, `usage_tracker`) en lugar de hooks complejos o globales de ECC.
  - Los hooks de memoria, sesión y telemetría quedan solo en el inventario.
  - Presupuesto de tokens en `model_guard`, autorizado por el owner.
  - Hashes de contenido con LF normalizado.
  - Ver `docs/reports/PHASE_04_REPORT.md`.
- **Archivos afectados:**
  - Scripts: `hooks_manager.py` y `phase_report.py`.
  - Hooks propios en `.claude/hooks`.
  - Registros: `HOOK_REGISTRY.json` y `hook_decisions.json`.
  - Instalador, hub, doctor y `model_policy`.
  - Documentación: `docs/reports`, ECC_INTEGRATION_REPORT y HOOK_SECURITY_REPORT.
  - Reglas: AGENTS, CLAUDE, `documentation-ledger` y `documentation-keeper`.
- **Comandos/pruebas realmente ejecutados y resultado:**
  - Suite completa sin submódulos: 137 OK.
  - Prueba de humo end-to-end y comprobaciones de hooks en un proyecto temporal: todo correcto, rollback incluido.
  - Prueba real `claude -p`: 4 bloqueos de hooks y 1 delegación Haiku.
  - Proyecto temporal eliminado.
- **Revisión de seguridad y documentación:**
  - Ver HOOK_SECURITY_REPORT.
  - Sin cambios globales: el hash de la configuración de usuario no varió.
- **Bloqueos, riesgos y próximas acciones:**
  - CI final del PR #4.
  - La próxima fase debe iniciarse con `hub.py launch` en una sesión nueva.
  - Consumo de la fase: 239 699 tokens de ejecutores, por encima del objetivo.
- **Responsable/aprobación:**
  - El owner autorizó la fase 4 y el presupuesto de tokens.
  - Ejecutores: E1 Sonnet y E2 Haiku, con `effort: medium`.
