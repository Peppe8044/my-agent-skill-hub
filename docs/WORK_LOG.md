# Bitácora de trabajo del hub

| Fecha (UTC) | Tarea | Cambios y justificación | Validación / evidencia | Riesgos / siguiente paso |
|---|---|---|---|---|
| 2026-11-08 | HUB-001 | Creación de biblioteca de agentes y skills portables, selección de stack por proyecto, documentación obligatoria y CI | Configuración inicial y validación por CLI/CI prevista; verificar ejecución de workflow tras publicar | Aún no hay motor autónomo multiagente ni protecciones de rama activadas |
| 2026-11-26 | HUB-002 | Agrega agente `orchestrator` (sesión principal, `model: opus`) que decide y delega; asigna modelo por rol: opus a supervisor/solution-architect/security-reviewer, sonnet a ejecutores y revisores (antes todos `inherit`) | `python scripts/hub.py validate` y `python -m unittest discover -s tests -v` (ver commit) | Validar en un proyecto real que `claude --agent orchestrator` delega con el ruteo esperado |

| 2026-11-26 | HUB-003 | Skills obligatorias por agente vía campo `skills` (preload documentado de Claude Code), contrato `### Run report` (modelo, skills, tiempos, comandos), reglas de delegación del orquestador y plantilla `AGENT_RUNS.md`. Origen: en un proyecto real los subagentes no aplicaron skills porque las definiciones solo decían "consult relevant skills" y el orquestador no las nombró en los encargos | `python scripts/hub.py validate` -> PASS; `python -m unittest discover -s tests` -> 9 OK (incluye 2 pruebas nuevas del validador) | Verificar en la próxima ejecución real que cada entrega trae el Run report; la duración/tokens solo existen si el runtime los expone |


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
