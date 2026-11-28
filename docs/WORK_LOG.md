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
