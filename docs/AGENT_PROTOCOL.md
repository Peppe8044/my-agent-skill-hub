# Contrato de delegación / handoff de agentes

Cada delegación debe contener:
- `task_id`, objetivo y criterios de aceptación.
- Contexto mínimo: rutas/contratos/decisiones aplicables, no toda la conversación.
- Archivos bajo responsabilidad y límites (read-only, sin deploy, sin producción).
- Pruebas esperadas, presupuesto/costo si hay medición real, criterio de detención.
- Salida: resumen breve, artefactos y rutas, decisiones, comandos realmente ejecutados, estado (hecho/bloqueado), riesgos y siguientes pasos.

Ejemplo:
```json
{"task_id":"API-004","owner":"backend-engineer",
 "goal":"Implement endpoint /tickets with validation",
 "inputs":["docs/API_CONTRACT.md"],"files_owned":["src/api/tickets.py"],
 "constraints":["no production","no credentials"],"acceptance":["test 201/400","auth checked"],
 "report":{"status":"done","artifacts":["src/api/tickets.py"],"tests":["python -m unittest ..."],"risks":[]}}
```

## Modelo y skills (obligatorio)
- El orquestador delega solo en agentes del proyecto (`.claude/agents`) que precargan las skills obligatorias (`token-budget` siempre) y pasa siempre el `model` explícito (`sonnet` o `haiku`), según la tabla de ruteo de `agents/orchestrator.md`. Los agentes integrados (`general-purpose`, `Plan`, Explore) no pueden precargar skills y se deniegan. Prohibidos `fork`, `model: inherit`, Opus/Fable o IDs completos en ejecutores; ningún ejecutor se escala a Opus. El hook `.claude/hooks/model_guard.py` (matcher `Agent|Task`) deniega estas llamadas en runtime.
- Cada agente declara sus skills obligatorias en el campo `skills` de su encabezado (`.claude/agents/*.md`); Claude Code las inyecta al iniciar el subagente. La delegación agrega las skills específicas de la tarea.
- Toda entrega empieza con el bloque `### Run report`: agente, modelo exacto, skills aplicadas, inicio/fin (ISO), estado y comandos ejecutados con su resultado.
- El orquestador registra cada delegación en `AGENT_RUNS.md` del proyecto (plantilla `templates/project/AGENT_RUNS.md`) con el modelo solicitado, el modelo observado (evidencia de runtime: stream-json `message.model`, transcripciones, `modelUsage`), duración, tokens y herramientas tal como los reporta el runtime; si no hay dato, **no medido**.
- Una entrega sin `### Run report` o sin las skills obligatorias se devuelve una vez; si se repite, se registra la desviación.

## Concurrencia
Por defecto 1 ejecutor (`default_parallel_agents: 1`); máximo 2 simultáneos (`max_parallel_agents: 2`) y solo por módulos/archivos no solapados; `max_retries: 1` y luego se reporta bloqueado; establecer contratos primero; integrar secuencialmente con QA. Sincronización mediante Git y artefactos versionados, no memoria conversacional como única fuente.

## Token budget
Al delegar incluir límite orientativo y prioridades; los límites son estimaciones hasta que el runtime permita cuotas duras. Reportar costo real únicamente si se recibe de API/herramienta.