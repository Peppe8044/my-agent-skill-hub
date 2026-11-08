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

## Concurrencia
Solo paralelizar por módulos/archivos no solapados; establecer contratos primero; integrar secuencialmente con QA. Sincronización mediante Git y artefactos versionados, no memoria conversacional como única fuente.

## Token budget
Al delegar incluir límite orientativo y prioridades; los límites son estimaciones hasta que el runtime permita cuotas duras. Reportar costo real únicamente si se recibe de API/herramienta.