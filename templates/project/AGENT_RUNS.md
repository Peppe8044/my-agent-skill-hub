# Registro de ejecuciones de agentes

Lo mantiene el orquestador (o el agente principal) por cada delegación. Duración, tokens y herramientas se copian de lo que reporta el runtime (en Claude Code, la notificación de tarea: `duration_ms`, `subagent_tokens`, `tool_uses`). Si el runtime no entrega un dato, escribir **no medido**; nunca estimar.

| Fecha | Tarea | Agente | Modelo solicitado | Modelo reportado por el agente | Skills aplicadas | Duración | Tokens | Herramientas | Estado | Observaciones |
|---|---|---|---|---|---|---|---|---|---|---|
| AAAA-MM-DD | ID | nombre | sonnet/opus/haiku | ID exacto | lista | mm:ss | n | n | hecho/bloqueado/devuelto | desviaciones, excepciones |

Reglas:
- Una fila por ejecución (si una entrega se devuelve y se repite, son dos filas).
- `orchestrator (self)` cuando el orquestador hace una tarea él mismo.
- Una entrega sin bloque `### Run report` o sin las skills obligatorias se marca `devuelto`.
