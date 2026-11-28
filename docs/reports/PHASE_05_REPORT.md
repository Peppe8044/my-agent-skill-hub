# Reporte de fase 05: Agent Memory local y aislado por proyecto

Documento sintético generado de forma determinista. No incluye registros completos.

## 1. Número de fase y objetivo

Fase 5: Agent Memory local y aislado por proyecto

Objetivo: Instalar, integrar y validar Agent Memory (external/agentmemory, commit fijado 5c9e2e6) como componente reutilizable del hub: almacenamiento local, sin APIs de pago, aislado por proyecto e integrado mediante MCP en bootstrap y update.

## 2. Resumen ejecutivo

- Nuevo scripts/memory.py con configure, start, stop, status y recover; se expone como python scripts/hub.py memory <acción> --target <dir>.
- Aislamiento por proyecto:
-   - Datos y HOME del servicio en <proyecto>/.agent-hub/memory/ (ignorado por git).
-   - Puerto estable por proyecto.
-   - Servicio ligado a 127.0.0.1.
- Sin cambios globales y sin ~/.agentmemory.
- bootstrap y update añaden la entrada MCP en .mcp.json de forma idempotente y conservan los demás servidores. No arrancan el servicio.
- No se instalan hooks de captura ni se importan conversaciones. No hay skills compatibles que registrar. Los embeddings locales quedan desactivados: requieren descargar un modelo y no hay un beneficio medido.
- Pruebas 1 a 7 superadas, incluida la recuperación desde Claude Code mediante MCP (Haiku).
- Desviación de presupuesto: el ejecutor consumió 827.116 tokens ponderados según su transcripción, frente a los 50.000 de la fase, y el libro de presupuesto registró 0. El orquestador superó también el objetivo de 15.000. La revisión de seguridad queda pendiente (EXCEPTIONS).

## 3. Estado inicial y estado final

**Estado inicial:**
- external/agentmemory estaba clonado en el commit fijado, sin compilar ni integrar.
- bootstrap solo sondeaba 127.0.0.1:3111 con un puerto fijo y sin aislamiento.

**Estado final:**
- Servicio por proyecto gestionado por el hub, con configuración MCP automática en install, bootstrap y update.
- probe_memory usa el puerto configurado del proyecto.
- 13 pruebas unitarias nuevas; suite completa: 167 OK.

## 4. Componentes implementados

- scripts/memory.py: configuración, puertos, ciclo de vida del servicio y parada segura limitada a los PID del proyecto.
- scripts/hub.py: subcomando memory.
- scripts/bootstrap.py: integración en bootstrap y update, y probe_memory por proyecto.
- docs/decisions/0006-agent-memory.md: ADR.

## 5. Archivos creados y modificados

Creados:
- scripts/memory.py
- tests/test_memory.py
- docs/decisions/0006-agent-memory.md
- docs/reports/data/PHASE_05.json
- docs/reports/PHASE_05_REPORT.md

Modificados:
- scripts/hub.py
- scripts/bootstrap.py
- docs/WORK_LOG.md
- docs/CHANGELOG.md
- docs/EXCEPTIONS.md
- docs/reports/LATEST_REPORT.md

## 6. Versiones y dependencias

- agentmemory en el commit fijado 5c9e2e6
- Node 24
- Claude Code (claude-haiku-5-5 para la prueba MCP)
- Python 3

## 7. Comandos relevantes ejecutados

- `cd external/agentmemory && npm install --ignore-scripts && npm run build`: 311 paquetes; build OK (lo ejecutó el ejecutor)
- `python scripts/hub.py memory start|stop|status --target <proyecto temporal>`: healthy true en 127.0.0.1:3430; tras stop, healthy false y ningún puerto en LISTENING
- `claude -p ... --model haiku --strict-mcp-config --mcp-config .mcp.json --allowedTools mcp__agentmemory`: recuperó la decisión sintética KIWIOBSIDIAN
- `python -m unittest tests.test_memory`: Ran 13 tests, OK
- `python -m unittest discover -s tests`: Ran 167 tests, OK
- `python scripts/hub.py validate`: PASS

## 8. Resultados reales de pruebas

| Prueba | Estado | Evidencia |
|---|---|---|
| 1. Servicio operativo | ✅ pasó | livez OK en 127.0.0.1:3430 y 127.0.0.1:3530 |
| 2. Guardar una decisión técnica | ✅ pasó | POST /remember devolvió 201 (marcador sintético KIWIOBSIDIAN) |
| 3. Recuperarla mediante una consulta | ✅ pasó | POST /smart-search devolvió 200 con el marcador |
| 4. Persistencia tras reiniciar | ✅ pasó | el marcador se encontró después de stop y start |
| 5. Aislamiento entre dos proyectos | ✅ pasó | el proyecto p2 no ve el marcador de p1 |
| 6. Recuperación mediante Claude Code y su MCP | ✅ pasó | claude -p (claude-haiku-5-5) respondió 'Decision KIWIOBSIDIAN: use SQLite WAL for the billing ledger store' |
| 7. Instalación repetida sin duplicados | ✅ pasó | dos bootstrap: una sola entrada agentmemory, una línea en .gitignore y la segunda ejecución sin cambios |

## 9. Evidencia de funcionamiento

- Consulta pequeña con memoria: 4 turnos, 29.737 tokens ponderados, USD 0,0051.
- La misma consulta sin memoria: 2 turnos, 21.448 tokens ponderados, USD 0,0038, sin respuesta útil.
- Recuperar la memoria cuesta unos 8.300 tokens ponderados más (+39 %) y aporta la respuesta correcta.

## 10. Riesgos y hallazgos de seguridad

- El libro de presupuesto no registró el consumo del ejecutor (0 frente a 827.116 ponderados según la transcripción), así que el presupuesto de fase no protegió esta ejecución.
- Revisión de seguridad pendiente (excepción abierta).
- npm run build modificó archivos rastreados en external/agentmemory/plugin/scripts. Al ejecutor se le denegó el checkout y queda pendiente que el owner restaure el submódulo.
- La entrada MCP contiene rutas absolutas de la máquina; un proyecto movido requiere ejecutar update.
- El primer arranque de cada proyecto descarga el motor iii (unos 6 MB) en su HOME local.

## 11. Decisiones técnicas y justificación

- Una instancia de servicio y un directorio de datos por proyecto: Aislamiento verificable sin depender de espacios de nombres compartidos.
- Solo MCP, sin hooks de captura de agentmemory: Evita capturar conversaciones y duplicar hooks del hub.
- Embeddings locales desactivados: Requieren descargar un modelo y no hay un beneficio medido.
- HOME y USERPROFILE redirigidos al proyecto: El CLI escribiría en ~/.agentmemory (configuración global).
- stop solo mata los PID que escuchan en los puertos del proyecto: Un memory.pid obsoleto podría nombrar un PID reutilizado.

## 12. Consumo de tokens por agente y modelo

| Agente | Modelo | Tokens | Llamadas a herramientas | Duración (s) | Fuente |
|---|---|---|---|---|---|
| orchestrator (Opus, sesión principal; incluye la corrección previa del lanzador, PR #5) | claude-opus-5-5 | 262101 | 0 | 0.0 | usage_tracker (transcripción): input 46, output 14.667, cache creation 90.870, cache read 1.565.178 x0,1; medición parcial, anterior a los últimos pasos |
| P5-T1 backend-engineer | claude-sonnet-5-5 (observado en la transcripción) | 827116 | 63 | 1932.0 | usage_tracker (transcripción): input 126, output 42.277, cache creation 200.350, cache read 5.843.634 x0,1; el harness informó 126.243 sin ponderar |
| Prueba MCP con claude -p (2 ejecuciones) | claude-haiku-5-5 | 51185 | 0 | 0.0 | usage de --output-format json, ponderado (cache read x0,1) |
| **Total** |  | 1140402 | 63 | 1932.0 |  |

## 13. Costos medidos

- Prueba MCP con y sin memoria (Haiku): USD 0.01 (fuente: total_cost_usd)

## 14. Duración de la fase

Ejecutor: 1.932 s. Fase completa: unos 45 minutos (de 13:51 a 14:35 aprox.).

## 15. Problemas encontrados y soluciones

- El CLI se demoniza, así que el PID lanzado no sirve: Se registran los PID que escuchan en los puertos REST, del visor y del motor.
- Matar el proceso dejaba vivo el demonio Worker Compose: stop ejecuta primero el agentmemory stop oficial.
- Riesgo de matar un PID reutilizado: stop filtra por los PID que escuchan en los puertos del proyecto; prueba de regresión añadida.

## 16. Componentes pendientes

- Revisión de seguridad (security-reviewer, sonnet) antes de fusionar, con presupuesto autorizado.
- Restaurar external/agentmemory: git -C external/agentmemory checkout -- .
- Corregir la medición del libro de presupuesto para subagentes.
- Fusionar primero el PR #5 (esta rama parte de él).

## 17. Decisiones que requieren autorización

- El owner autorizó la fase 5 con un presupuesto de ejecutores de 50.000 tokens ponderados; ese presupuesto se superó (ver los riesgos).

## 18. Commits, Pull Requests y enlaces

**Commits:**
- feat(memory): integración de Agent Memory local y aislada por proyecto

**Pull Requests:**
- feat/agent-memory-integration (sin fusionar; depende del PR #5)

**Enlaces:**
- https://github.com/Peppe8044/my-agent-skill-hub/pull/5

## 19. Recomendación para la siguiente fase

Resolver los pendientes (revisión de seguridad, submódulo y medición del presupuesto) antes de fusionar, y después iniciar la siguiente fase con: python scripts/hub.py launch --target . --phase <id>.
