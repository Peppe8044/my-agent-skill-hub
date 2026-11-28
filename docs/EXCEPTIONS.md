# Excepciones a procesos (aprobación explícita del usuario)

No hay excepciones autorizadas.

Para cada excepción solicitada, registrar:
- Fecha y persona que autoriza expresamente.
- Regla exacta y tarea/proyecto afectados.
- Justificación, alcance, vencimiento.
- Riesgo conocido y controles compensatorios.
- Resultado y fecha de cierre.

Nunca usar este documento para autorizar publicación de secretos, acceso productivo no aprobado o resultados inventados.
## 2026-11-28 — Fase 5 (HUB-014): revisión de seguridad no ejecutada
- **Regla:** paso 5 del orquestador. Un cambio de alto riesgo (código externo, MCP, servicio local) requiere security-reviewer.
- **Justificación:** el ejecutor P5-T1 consumió 827 116 tokens ponderados según su transcripción (126 243 según el harness), por encima del presupuesto de 50 000 ponderados de la fase. Opus no sustituye al revisor.
- **Controles compensatorios:**
  - Servicio solo en 127.0.0.1, claves de proveedores eliminadas del entorno y secreto fuera de `.mcp.json`.
  - Sin hooks de captura y sin cambios globales (HOME redirigido al proyecto).
  - `stop` limitado a los PID del proyecto.
  - 13 pruebas unitarias y pruebas en vivo.
- **Vencimiento:** antes de fusionar el PR de la fase 5, con autorización del owner para el presupuesto de la revisión.
- **Estado:** abierta.
