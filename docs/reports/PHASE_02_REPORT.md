# Reporte de fase 02: Política de modelos verificada, instalador seguro y doctor real

Documento sintético generado de forma determinista. No incluye registros completos.

## 1. Número de fase y objetivo

Fase 2: Política de modelos verificada, instalador seguro y doctor real

Objetivo: Autenticar GitHub CLI, resolver los conflictos del PR #2 sin perder mejoras, corregir los hallazgos de política de modelos con pruebas reales de delegación, hacer seguro el instalador (perfil full) y validar Docker, WSL y OneDrive.

## 2. Resumen ejecutivo

- gh autenticado como Peppe8044; indie-game-studio confirmado PRIVATE y el hub PUBLIC.
- Conflictos del PR #2 resueltos con merge (sin push forzado); CI en verde.
- Las pruebas reales refutaron que CLAUDE_CODE_SUBAGENT_MODEL anule el modelo de cada agente: se conservó como respaldo.
- Nuevo hook model_guard: bloquea ejecutores Opus, fork y built-ins sin modelo en runtime.
- Instalador full con detección de MCP duplicados y preservación de archivos; doctor comprueba el entorno real.

## 3. Estado inicial y estado final

**Estado inicial:**
- PR #2 en draft con conflictos.
- gh sin autenticar.
- Docker detenido.

**Estado final:**
- PR #2 MERGEABLE/CLEAN con CI success.
- Docker operativo.
- Política verificada en runtime.

## 4. Componentes implementados

- scripts/model_policy.py
- .claude/hooks/model_guard.py
- Detección de MCP y merge de settings en el instalador
- Conflictos preservados en .agent-hub/incoming/
- scripts/doctor.py
- ADR 0003 y 0004

## 5. Archivos creados y modificados

Creados:
- scripts/model_policy.py
- scripts/doctor.py
- .claude/hooks/model_guard.py
- docs/MODEL_ROUTING_REPORT.md
- docs/QUALITY_REPORT.md
- docs/decisions/0003-model-routing-policy.md
- docs/decisions/0004-installer-mcp-dedup-and-preservation.md

Modificados:
- scripts/hub.py
- scripts/bootstrap.py
- scripts/project_install.py
- .claude/settings.json
- MODEL_POLICY.json
- AGENTS.md
- CLAUDE.md
- README.md
- docs/*
- tests/*

## 6. Versiones y dependencias

- Claude Code 2.1.332
- Docker Desktop 4.87.0 / Engine 29.7.2 / Compose v5.4.0
- WSL 2.7.11.0

## 7. Comandos relevantes ejecutados

- `python scripts/hub.py validate`: PASS
- `python scripts/hub.py doctor`: exit 0 (11 OK, 2 WARN: core.longpaths, ruta OneDrive)
- `python -m unittest discover -s tests -v`: 57 tests OK
- `claude -p --agent orchestrator --model opus (antes, control y después)`: modelos observados en las transcripciones

## 8. Resultados reales de pruebas

| Prueba | Estado | Evidencia |
|---|---|---|
| unittest | ✅ pasó | 57 OK; cada commit verificado en worktree limpio |
| Delegación real antes del cambio | ✅ pasó | researcher y memory-curator → claude-haiku-5-5; code-reviewer → claude-sonnet-5-5 |
| Control general-purpose sin modelo | ✅ pasó | claude-sonnet-5-5 (no heredó Opus) |
| model_guard en runtime | ✅ pasó | bloqueó opus explícito, general-purpose y Explore sin modelo |
| GitHub Actions | ✅ pasó | run 46100671177 success |
| Docker hello-world | ✅ pasó | Hello from Docker! |
| Sincronización de OneDrive | ➖ no medido | proceso OneDrive no activo; estado desconocido |

## 9. Evidencia de funcionamiento

- Precedencia observada: model explícito > frontmatter > CLAUDE_CODE_SUBAGENT_MODEL > heredado.
- Evidencia por subagente tomada de message.model en las transcripciones.

## 10. Riesgos y hallazgos de seguridad

- Un model: opus explícito tendría prioridad sobre el respaldo: lo cubre model_guard.
- Los hooks pueden desactivarse en la configuración del usuario.
- Repositorios bajo una ruta de OneDrive.

## 11. Decisiones técnicas y justificación

- Conservar CLAUDE_CODE_SUBAGENT_MODEL=sonnet: La evidencia mostró que no contradice la asignación individual; evita heredar Opus.
- Hook PreToolUse model_guard: Única defensa en runtime contra la escalada a Opus.
- Merge en lugar de rebase: Sin push forzado.
- full por defecto con detección de MCP duplicados: Decisión del owner; evita duplicar el conector claude.ai ClickUp.

## 12. Consumo de tokens por agente y modelo

| Agente | Modelo | Tokens | Llamadas a herramientas | Duración (s) | Fuente |
|---|---|---|---|---|---|
| Docker/WSL/OneDrive (incompleto) | claude-haiku-5-5 | 52287 | 3 | 382.1 | task-notification |
| Documentación de política | claude-sonnet-5-5 | 94244 | 16 | 277.9 | task-notification |
| Docker/WSL/OneDrive (repetición) | claude-haiku-5-5 | 59628 | 6 | 254.8 | task-notification |
| Código de política, instalador y doctor | claude-sonnet-5-5 | 129165 | 31 | 669.1 | task-notification |
| **Total** |  | 335324 | 56 | 1583.9 |  |

## 13. Costos medidos

- Pruebas reales claude -p (antes, control y después): USD 1.05 (fuente: total_cost_usd)

## 14. Duración de la fase

No medida con precisión; ejecutores entre 02:31 y 02:54 UTC del 2026-11-28.

## 15. Problemas encontrados y soluciones

- Caducó el primer código de dispositivo de GitHub: Se generó uno nuevo.
- Docker devolvió HTTP 500 durante más de 5 min: Arranque lento; operativo al reintentar.
- El primer ejecutor de Docker se detuvo por una instrucción ambigua: Repetición con secciones independientes (52.287 tokens desperdiciados).
- El hallazgo de la fase 1 sobre la variable era incorrecto: Refutado con prueba de control y documentado.

## 16. Componentes pendientes

- Instalar la política en indie-game-studio.
- Evaluar el riesgo de OneDrive.
- Esfuerzo global xhigh de Opus.

## 17. Decisiones que requieren autorización

- Fusionar el PR #2

## 18. Commits, Pull Requests y enlaces

**Commits:**
- da57564 merge de main
- f6c37f8 política, guard, MCP y doctor
- aef24f4 documentación
- 1e1ea41 informes
- c0bd078 (indie-game-studio) estado del proyecto

**Pull Requests:**
- #2 actualizado (fusionado al inicio de la fase 3 como 97aedfa)

**Enlaces:**
- https://github.com/Peppe8044/my-agent-skill-hub/pull/2
- https://github.com/Peppe8044/my-agent-skill-hub/actions/runs/46100671177

## 19. Recomendación para la siguiente fase

Integrar las capacidades externas por reglas, con carga bajo demanda e instalación automática.
