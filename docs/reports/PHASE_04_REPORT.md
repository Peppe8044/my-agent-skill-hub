# Reporte de fase 04: Integración selectiva de ECC, gestor de hooks, presupuesto de tokens e informes consolidados

Documento sintético generado de forma determinista. No incluye registros completos.

## 1. Número de fase y objetivo

Fase 4: Integración selectiva de ECC, gestor de hooks, presupuesto de tokens e informes consolidados

Objetivo: Cerrar la fase 3, integrar de forma selectiva los hooks de ECC con un gestor de hooks propio y reutilizable, mantener la política de modelos, implantar informes consolidados por fase heredables y reducir de forma efectiva el consumo de tokens.

## 2. Resumen ejecutivo

- PR #3 fusionado (623b3ca) tras corregir la documentación de AGPL (OpenViking queda separado por política del proyecto, no por prohibición de la licencia).
- Gestor de hooks: registro de 110 hooks con procedencia, sha256, riesgo y estado; 5 aprobados (4 propios y config-protection de ECC), 9 rechazados y 96 solo en inventario.
- Hooks verificados dentro de Claude Code real: command_guard, file_guard, config-protection y model_guard bloquearon sus casos; usage_tracker registró el consumo real.
- Límite real de tokens: model_guard bloquea nuevas delegaciones al alcanzar 100.000 tokens de ejecutores por sesión, medidos en las transcripciones.
- Informes consolidados deterministas de 19 secciones; fases 1 a 3 reconstruidas sin repetir pruebas; los proyectos los heredan.
- Los ejecutores consumieron 239.699 tokens, 2,4 veces el objetivo de 100.000.

## 3. Estado inicial y estado final

**Estado inicial:**
- PR #3 abierto.
- Sin gestor de hooks: solo model_guard.
- Sin informes por fase.
- Sin límite de tokens aplicable.

**Estado final:**
- PR #3 fusionado.
- PR #4 con gestor de hooks, 4 hooks propios y 1 de ECC aprobados.
- Presupuesto de tokens aplicado por model_guard.
- docs/reports con las fases 1 a 4 y LATEST_REPORT.

## 4. Componentes implementados

- scripts/hooks_manager.py (registro, list/enable/disable/verify, copias de seguridad de los cambios)
- registry/HOOK_REGISTRY.json y registry/hook_decisions.json
- .claude/hooks/command_guard.py
- .claude/hooks/file_guard.py
- .claude/hooks/usage_tracker.py
- Hook ECC pre:config-protection (node, revisado)
- Presupuesto max_executor_tokens_per_session en MODEL_POLICY.json
- scripts/phase_report.py y templates/PHASE_REPORT.md
- Instalación de hooks e informes en proyectos (bootstrap)

## 5. Archivos creados y modificados

Creados:
- scripts/hooks_manager.py
- scripts/phase_report.py
- .claude/hooks/command_guard.py
- .claude/hooks/file_guard.py
- .claude/hooks/usage_tracker.py
- registry/HOOK_REGISTRY.json
- registry/hook_decisions.json
- templates/PHASE_REPORT.md
- templates/project/PHASE_REPORT.md
- docs/ECC_INTEGRATION_REPORT.md
- docs/HOOK_SECURITY_REPORT.md
- docs/reports/*
- tests/test_hooks_manager.py
- tests/test_own_hooks.py
- tests/test_phase_report.py

Modificados:
- scripts/project_install.py
- scripts/hub.py
- scripts/doctor.py
- scripts/model_policy.py
- scripts/integrations.py
- scripts/external_scan.py
- .claude/hooks/model_guard.py
- .claude/settings.json
- MODEL_POLICY.json
- AGENTS.md
- CLAUDE.md
- README.md
- skills/documentation-ledger (3 copias)
- documentation-keeper (2 archivos)

## 6. Versiones y dependencias

- ECC en el commit fijado 4adeee6732a1 (MIT), sin volver a descargar
- Node.js 24.20.0 para config-protection
- Python 3.13.15
- Claude Code 2.1.332

## 7. Comandos relevantes ejecutados

- `python scripts/hub.py hooks registry --check`: registro determinista sin desviaciones
- `python -m unittest discover -s tests`: 137 tests OK en un worktree limpio sin submódulos (condiciones de CI)
- `python scripts/smoke_bootstrap.py <temporal>`: ok: true; segunda instalación sin cambios
- `python scripts/hub.py hooks verify|disable|enable / rollback --target <temporal>`: verify 5/5; disable correcto; model_guard no se puede desactivar; rollback restaura hook y estado
- `claude -p --agent orchestrator --model opus --effort high (proyecto temporal)`: 4 bloqueos de hooks reales y 1 delegación Haiku permitida

## 8. Resultados reales de pruebas

| Prueba | Estado | Evidencia |
|---|---|---|
| Suite completa (sin submódulos, condiciones de CI) | ✅ pasó | 137 tests OK |
| Suite completa con submódulos (antes de los ajustes finales) | ✅ pasó | 135 tests OK |
| Bootstrap instala los hooks aprobados sin duplicados | ✅ pasó | 5 hooks registrados una sola vez |
| Los hooks se ejecutan en Claude Code | ✅ pasó | command_guard, file_guard, config-protection (node) y model_guard bloquearon; el archivo de prueba no se creó |
| model_guard bloquea Opus como ejecutor | ✅ pasó | researcher con model opus bloqueado |
| Presupuesto de tokens | ✅ pasó | pruebas unitarias: bloquea al agotarse, deduplica por id de mensaje, permite si no puede medir |
| Configuración global sin cambios | ✅ pasó | sha256 de la configuración de usuario igual antes y después |
| Segunda instalación idempotente | ✅ pasó | 0 cambios, 0 conflictos, 0 copias de seguridad |
| Desactivar hooks y rollback | ✅ pasó | disable elimina solo ese hook; rollback lo restaura con su estado |
| Skills y agentes siguen disponibles | ✅ pasó | 57 skills (43 propias y 14 activas), 30 agentes, catálogo 981 y 45 |
| Informes heredados por un proyecto nuevo | ✅ pasó | phase_report.py y la plantilla instalados; informe de 19 secciones generado en el proyecto |
| GitHub Actions del PR #4 | ✅ pasó | la primera ejecución falló por hashes CRLF; tras la corrección, CI success en 6cc520e (validate, pruebas y check-docs) |
| Bloqueo real por presupuesto en una sesión viva | ➖ no medido | solo probado con transcripciones sintéticas |

## 9. Evidencia de funcionamiento

- usage_tracker registró en el proyecto temporal los tokens por modelo (Opus principal y Haiku subagente) sin contenido de conversación.
- Revisión de código de config-protection: lee stdin y hace lstat del destino; sin escrituras, red, procesos ni credenciales.

## 10. Riesgos y hallazgos de seguridad

- La clasificación de hooks inventariados no es una auditoría completa: solo se revisó el código de los aprobados.
- config-protection deja de actuar (sin bloquear) si falta node.
- El presupuesto se mide desde las transcripciones locales; si el runtime cambia su formato, deja de medir y permite (fail-open documentado).
- Un usuario puede desactivar todos los hooks en su configuración.

## 11. Decisiones técnicas y justificación

- Aprobar solo pre:config-protection de ECC: Único hook con valor demostrable, código simple y sin efectos fuera del proyecto.
- Guardas propias deterministas en lugar de gateguard, el dispatcher y cost-tracker de ECC: Mismo beneficio con mucha menos complejidad, sin node ni escrituras globales.
- Presupuesto de tokens en model_guard: La skill token-budget es solo texto y no se cargó en los ejecutores de esta sesión; un hook sí se aplica.
- Datos de las fases 1 a 3 redactados por el orquestador: Ya tenía la evidencia verificada; evita que un ejecutor relea unos 6 documentos.
- Hashes de contenido con LF normalizado: autocrlf produce CRLF en Windows y LF en la CI.

## 12. Consumo de tokens por agente y modelo

| Agente | Modelo | Tokens | Llamadas a herramientas | Duración (s) | Fuente |
|---|---|---|---|---|---|
| E1 gestor de hooks e instalador | claude-sonnet-5-5 (effort medium) | 117606 | 24 | 636.1 | task-notification |
| E2 hooks propios e informes | claude-haiku-5-5 (effort medium) | 122093 | 33 | 398.3 | task-notification |
| **Total** |  | 239699 | 57 | 1034.4 |  |

## 13. Costos medidos

- Prueba real de hooks en Claude Code: USD 0.29 (fuente: total_cost_usd)

## 14. Duración de la fase

No medida con precisión; ejecutores 636 s y 398 s; orquestador no medido.

## 15. Problemas encontrados y soluciones

- Los ejecutores superaron el objetivo de tokens (E2 3 veces su objetivo): No se lanzaron más ejecutores; se implementó el presupuesto real en model_guard (autorizado por el owner).
- La skill token-budget no se aplicaba a los ejecutores: Esta sesión no arrancó dentro del hub; la próxima fase debe lanzarse con hub.py launch.
- La CI falló por sha256 calculados sobre CRLF: Hashes de contenido con LF normalizado y registros regenerados.
- Sin checkout de ECC, el registro aparecía desactualizado: La comparación excluye las entradas de ECC cuando no está presente.
- rollback no deshacía un disable: enable/disable crean copia de seguridad de settings y estado.
- Ediciones con heredoc insertaron saltos de línea reales en literales: Corregido escribiendo los cambios sin pasar por el shell.

## 16. Componentes pendientes

- Probar un bloqueo por presupuesto en una sesión viva.
- Agent Memory y OpenViking (restricción vigente).
- Revisión humana de las 181 skills con scripts y de los 45 agentes de catálogo.

## 17. Decisiones que requieren autorización

- Fusionar el PR #4.
- Mantener o ajustar el presupuesto de 100.000 tokens por sesión.
- Bajar effortLevel global de xhigh a high.
- Iniciar la fase 5 en una sesión nueva lanzada con hub.py launch.

## 18. Commits, Pull Requests y enlaces

**Commits:**
- 4824f88 aclaración AGPL (cierre de la fase 3)
- 623b3ca merge del PR #3
- 6e22294 gestor de hooks, guardas, presupuesto e informes
- 8df4e97 documentación e informes de las fases 1 a 3
- e5be8b6 hashes independientes del salto de línea
- 4631b96 comparación del registro sin ECC
- 6cc520e informes y entregables de la fase 4

**Pull Requests:**
- #3 fusionado
- #4 abierto (no fusionar sin autorización)

**Enlaces:**
- https://github.com/Peppe8044/my-agent-skill-hub/pull/4
- https://github.com/Peppe8044/my-agent-skill-hub/blob/feat/ecc-hooks-integration/docs/reports/PHASE_04_REPORT.md

## 19. Recomendación para la siguiente fase

Abrir una sesión nueva con python scripts/hub.py launch dentro del hub, usando LATEST_REPORT.md como traspaso, para que se apliquen token-budget, los hooks y el presupuesto. Después instalar el hub en indie-game-studio o abrir un piloto aislado de Agent Memory.
