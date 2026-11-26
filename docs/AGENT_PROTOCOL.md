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
- El orquestador pasa siempre el `model` explícito en cada delegación según la tabla de ruteo de `agents/orchestrator.md`.
- Cada agente declara sus skills obligatorias en el campo `skills` de su encabezado (`.claude/agents/*.md`); Claude Code las inyecta al iniciar el subagente. La delegación agrega las skills específicas de la tarea.
- Toda entrega empieza con el bloque `### Run report`: agente, modelo exacto, skills aplicadas, inicio/fin (ISO), estado y comandos ejecutados con su resultado.
- El orquestador registra cada delegación en `AGENT_RUNS.md` del proyecto (plantilla `templates/project/AGENT_RUNS.md`) con duración, tokens y herramientas tal como los reporta el runtime; si no hay dato, **no medido**.
- Una entrega sin `### Run report` o sin las skills obligatorias se devuelve una vez; si se repite, se registra la desviación.

## Concurrencia
Solo paralelizar por módulos/archivos no solapados; establecer contratos primero; integrar secuencialmente con QA. Sincronización mediante Git y artefactos versionados, no memoria conversacional como única fuente.

## Token budget
Al delegar incluir límite orientativo y prioridades; los límites son estimaciones hasta que el runtime permita cuotas duras. Reportar costo real únicamente si se recibe de API/herramienta.