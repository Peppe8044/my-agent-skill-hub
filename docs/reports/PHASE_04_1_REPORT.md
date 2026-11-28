# Reporte de fase 04.1: Corrección urgente del consumo de tokens y herencia obligatoria

Documento sintético generado de forma determinista. No incluye registros completos.

## 1. Número de fase y objetivo

Fase 4.1: Corrección urgente del consumo de tokens y herencia obligatoria

Objetivo: Corregir sin nueva auditoría los hallazgos de consumo confirmados e incorporar las optimizaciones al núcleo reutilizable para que todos los proyectos, nuevos y existentes, las hereden y las cumplan de verdad.

## 2. Resumen ejecutivo

- El presupuesto de ejecutores ahora es técnico y persistente: model_guard bloquea antes de delegar con 50.000 tokens ponderados por fase y por sesión, una reserva de 10.000 por ejecutor activo y un libro que sobrevive a las sesiones nuevas.
- Mide input, output, cache creation y cache read por separado (cache read con peso 0,1). Si no puede medir, bloquea salvo recuperación autorizada.
- token-budget es obligatoria de forma efectiva: model_guard deniega los agentes que no la precargan, los built-ins y fork; catalog.py la inyecta en los agentes externos al activarlos.
- install, new, bootstrap, update (nuevo) y launch aplican la política, los hooks de protección y medición, el effort por modelo, las skills ECC compatibles y los informes. update conserva solo los valores ajustables del proyecto.
- Prueba real en Claude Code superada: delegación a Haiku con token-budget cargada, bloqueo por presupuesto de sesión, bloqueo de general-purpose y bloqueo de la fase en una sesión nueva.
- Esta fase no lanzó ejecutores en el hub (0 tokens). La prueba real consumió 23.876 tokens de Haiku y USD 0,52 en total.
- Desviación corregida: el orquestador asumió la implementación (unos 2,2 M tokens ponderados). Las reglas reutilizables limitan ahora a Opus a coordinar, planificar, decidir y aceptar resultados, y a ejecutar comandos deterministas cortos; la implementación corresponde a Sonnet. Los informes muestran el consumo del orquestador y el de los ejecutores por separado.

## 3. Estado inicial y estado final

**Estado inicial:**
- token-budget era solo texto; model_guard comprobaba un tope por sesión que se reiniciaba y excluía cache read.
- Si no podía medir, model_guard permitía delegar; usage_tracker solo se ejecutaba en Stop.
- orchestrator.md obligaba a delegar incluso las tareas sencillas y exigía reinvocar las skills precargadas; bootstrap lanzaba Opus con effort high.
- Los proyectos existentes no tenían una vía de actualización que conservara sus valores ni que garantizara la herencia.

**Estado final:**
- MODEL_POLICY.json es la fuente única: presupuestos, pesos, reserva, concurrencia 1/2, 1 reintento y mandatory_agent_skills.
- model_guard aplica el modelo, las skills obligatorias, la concurrencia (tope 2), el presupuesto de fase y sesión y el bloqueo sin medición, con valores centrales de respaldo para proyectos desactualizados.
- hub.py update y launch con actualización previa; usage_tracker obligatorio en Stop y SubagentStop en todos los perfiles.
- Requisito permanente documentado en docs/GOVERNANCE.md y verificado por tests/test_inheritance.py en proyectos temporales aislados.

## 4. Componentes implementados

- .claude/hooks/model_guard.py (presupuesto persistente, skills obligatorias, valores de respaldo y CLI --budget)
- scripts/project_install.py (fusión segura de MODEL_POLICY.json con claves ajustables y overrides en el manifiesto)
- scripts/bootstrap.py (update y launch con actualización previa, effort medium y --phase)
- scripts/hub.py (comandos update y budget; skills obligatorias tomadas de la política)
- templates/agent-hub/catalog.py (inyección de skills obligatorias en los agentes externos)
- scripts/hooks_manager.py (registro por evento; usage_tracker obligatorio)
- scripts/phase_report.py (informes de subfase PHASE_04_1)
- scripts/external_scan.py (activación de ECC strategic-compact y context-budget)
- Reglas: AGENTS.md, CLAUDE.md, GOVERNANCE.md, orchestrator.md y token-budget

## 5. Archivos creados y modificados

Creados:
- tests/test_inheritance.py
- docs/reports/data/PHASE_04_1.json
- docs/reports/PHASE_04_1_REPORT.md

Modificados:
- .claude/hooks/model_guard.py
- .claude/settings.json
- .claude/agents/orchestrator.md
- .claude/agents/supervisor.md
- MODEL_POLICY.json
- AGENTS.md
- CLAUDE.md
- docs/GOVERNANCE.md
- docs/AGENT_PROTOCOL.md
- docs/OPERATING_GUIDE.md
- skills/token-budget/SKILL.md (y sus copias de runtime)
- agents/README.md, agents/orchestrator.md y agents/supervisor.md
- scripts/bootstrap.py, hub.py, model_policy.py, project_install.py, hooks_manager.py, phase_report.py y external_scan.py
- templates/agent-hub/catalog.py y templates/project/TOKEN_METRICS.md
- registry/hook_decisions.json y registros regenerados
- tests de model_guard, hooks_manager, bootstrap, external_scan y phase_report
- docs/WORK_LOG.md, docs/CHANGELOG.md y docs/reports/LATEST_REPORT.md

## 6. Versiones y dependencias

- Claude Code 2.1.332
- ECC en el commit fijado 4adeee6732a1 (solo se consultó el inventario existente)
- Python 3 de la biblioteca estándar en los hooks

## 7. Comandos relevantes ejecutados

- `python -m unittest discover -s tests`: 150 tests OK con submódulos
- `python scripts/hub.py validate`: PASS
- `python scripts/hub.py update --target <proyecto temporal>`: sin errores ni conflictos; presupuestos propios conservados; usage_tracker en SubagentStop
- `claude -p --agent orchestrator --model opus --effort medium (2 sesiones)`: permitido, bloqueado por sesión, bloqueado por built-in y bloqueado por fase
- `python scripts/hub.py hooks registry --check`: sin desviaciones

## 8. Resultados reales de pruebas

| Prueba | Estado | Evidencia |
|---|---|---|
| Suite completa con submódulos | ✅ pasó | 150 tests OK |
| Herencia en proyectos new de los 10 tipos | ✅ pasó | tests/test_inheritance.py ejecuta el hook instalado en cada proyecto |
| Proyecto de juego (install) y fase que sobrevive a una sesión nueva | ✅ pasó | bloqueo con el mensaje de fase |
| Actualización de un proyecto existente | ✅ pasó | conserva executor_budget_per_phase; restablece executors y max_parallel_agents; un agente desactualizado sin token-budget queda denegado hasta update |
| Agentes externos al activarse | ✅ pasó | skills obligatorias inyectadas en las formas sin lista, en bloque y en línea |
| La política local no amplía los límites centrales | ✅ pasó | opus denegado, concurrencia limitada a 2, presupuesto por defecto y token-budget siempre exigida |
| launch actualiza antes de abrir la sesión | ✅ pasó | mandatory_agent_skills restaurado y --effort pasado |
| Presupuesto en model_guard | ✅ pasó | ponderación, reserva, fase persistente, paralelismo, bloqueo sin medición y recuperación, start-phase y valores por defecto |
| Prueba real de presupuesto en Claude Code | ✅ pasó | 4 comprobaciones superadas en 2 sesiones reales |

## 9. Evidencia de funcionamiento

- Sesión real 1: researcher (Haiku) permitido; respondió el título del paso 9 de token-budget («Budget and sessions»), lo que demuestra que la skill se cargó. La segunda delegación se denegó con «23876 used + 10000 reserved > 20000 (executor_budget_per_session)» y general-purpose con «not a project agent».
- Sesión real 2 (sesión nueva, misma fase): denegada con «executor token budget for phase 4.1-real exhausted: 23876 used + 10000 reserved > 20000».
- Lo medido por el libro (23.876) coincide con modelUsage de Claude Code para Haiku: input 2, output 220 y cache creation 23.654.
- usage_tracker registró ambas sesiones, con el subagente researcher, solo con conteos y sin contenido.

## 10. Riesgos y hallazgos de seguridad

- Un ejecutor que ya está en marcha puede superar el presupuesto: el hook solo actúa antes de cada delegación y Claude Code no ofrece un tope de tokens por subagente.
- --max-budget-usd solo existe en modo -p; no hay --max-turns en la ayuda de la CLI. La cancelación de tareas en segundo plano se hace con TaskStop.
- Los agentes integrados quedan denegados; las búsquedas de solo lectura usan researcher (Haiku).
- El consumo del orquestador no se limita técnicamente: solo se reduce con sesiones nuevas por fase y effort medium.

## 11. Decisiones técnicas y justificación

- Presupuesto técnico y persistente en model_guard: La skill es texto y no limitaba el consumo; el hook se ejecuta siempre antes de delegar.
- Denegar los built-ins y los agentes sin token-budget: Es la única forma de que la skill sea obligatoria de verdad para cada ejecutor.
- update conserva solo las claves ajustables: Preserva la configuración del proyecto sin permitir ampliar modelos, concurrencia ni skills obligatorias.
- usage_tracker obligatorio en Stop y SubagentStop: La medición debe existir en todos los perfiles y por ejecutor.
- Reutilizar solo strategic-compact y context-budget de ECC: Aportan control de contexto sin hooks nuevos; cost-tracking requiere su propio servicio.
- Rol del orquestador limitado a coordinar: Absorber la implementación en Opus evade el presupuesto de ejecutores y es más caro; Sonnet implementa y Haiku hace las tareas simples.

## 12. Consumo de tokens por agente y modelo

| Agente | Modelo | Tokens | Llamadas a herramientas | Duración (s) | Fuente |
|---|---|---|---|---|---|
| Ejecutores en el hub | ninguno (trabajo determinista hecho por el orquestador) | 0 | 0 | 0.0 | sin delegaciones |
| Prueba real: researcher | claude-haiku-5-5 (effort medium) | 23876 | 0 | 0.0 | modelUsage de claude -p y libro de presupuesto |
| Orquestador de esta sesión (fase 4.1) | claude-opus-5-5 | 2219632 | 0 | 0.0 | transcripción: input 134, output 120.203, cache creation 238.468 y cache read 18.608.274 (ponderado con cache read 0,1) |
| Orquestador: ajuste mínimo de gobernanza y cierre | claude-opus-5-5 | 61331 | 0 | 0.0 | transcripción: output 6.179, cache creation 7.714 y cache read 474.339 (ponderado); sin delegación posible porque el presupuesto de la sesión está agotado |
| **Total** |  | 2304839 | 0 | 0.0 |  |

## 13. Costos medidos

- Prueba real de presupuesto en Claude Code (2 sesiones): USD 0.52 (fuente: total_cost_usd)

## 14. Duración de la fase

No medida con precisión; la prueba real duró dos ejecuciones cortas de claude -p.

## 15. Problemas encontrados y soluciones

- La primera prueba real chocó con el límite de 5 horas de la cuenta: Se repitió después del reinicio del límite y fue correcta.
- Las sesiones anteriores no reflejaban el gasto posterior a su última delegación: El libro guarda la transcripción de cada sesión y la recalcula en cada comprobación.
- Los proyectos existentes no recibían SubagentStop porque el registro comparaba solo el comando: Los hooks se registran por par evento-comando.
- Los proyectos con política propia quedaban sin presupuesto: Fusión segura en update y valores centrales de respaldo en el hook.
- Opus implementó directamente la fase (unos 2,2 M tokens ponderados del orquestador), sustituyendo a Sonnet: AGENTS.md, orchestrator.md y token-budget fijan el límite del rol (solo comandos deterministas cortos y ediciones triviales; la implementación va a Sonnet y nunca se absorbe para ahorrar presupuesto de ejecutores). usage_tracker y el informe separan el orquestador de los ejecutores.

## 16. Componentes pendientes

- Iniciar la fase 5 en una sesión nueva cuando el owner lo indique.
- Agent Memory, OpenViking, Codex y MCP nuevos (restricción vigente).
- Tope por subagente: no existe en Claude Code; vigilar nuevas versiones.

## 17. Decisiones que requieren autorización

- Autorizados por el owner: presupuestos de 50.000 tokens ponderados, bloqueo de agentes integrados y política de herencia.
- Fusión del PR #4 autorizada si todas las validaciones son satisfactorias.

## 18. Commits, Pull Requests y enlaces

**Commits:**
- Fase 4.1: presupuesto persistente, skills obligatorias efectivas y herencia (ver el PR #4)

**Pull Requests:**
- #4 feat/ecc-hooks-integration (actualizado, sin fusionar)

**Enlaces:**
- https://github.com/Peppe8044/my-agent-skill-hub/pull/4

## 19. Recomendación para la siguiente fase

En una sesión nueva, desde la raíz de my-agent-skill-hub: python scripts/hub.py launch --target . --phase 5 (usa LATEST_REPORT.md como traspaso; el libro de presupuesto abre la fase 5).
