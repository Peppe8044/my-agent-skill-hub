# Changelog del hub

## 0.3.1 - 2026-11-27
- Solo el orquestador usa `opus`; supervisor, solution-architect y security-reviewer pasan a `sonnet`. Escalar a opus requiere aprobación explícita del usuario.
- Las skills requeridas deben invocarse con la herramienta Skill; leerlas desde archivo no cuenta como aplicada.
- Un revisor distinto (por ejemplo ECC) no reemplaza a qa-engineer antes de aceptar un cambio.

## 0.3.0 — 2026-11-26
- Cada agente de `.claude/agents/` precarga sus skills obligatorias con el campo `skills` del encabezado (Claude Code las inyecta al iniciar el subagente): `token-budget` y `documentation-ledger` en todos, más las de su rol (por ejemplo `web-ui`, `test-and-verify` y `secure-development` en frontend-engineer).
- Contrato `### Run report` obligatorio al final de cada entrega: agente, modelo exacto, skills aplicadas, inicio/fin, estado y comandos ejecutados.
- `orchestrator`: reglas de delegación obligatorias (modelo explícito, skills por encargo, rechazo de entregas sin Run report, revisión de security-reviewer y qa-engineer antes de aceptar cambios materiales) y registro de ejecuciones con duración/tokens del runtime.
- Nueva plantilla `templates/project/AGENT_RUNS.md`; `hub.py validate` falla si un agente no precarga skills existentes, omite las obligatorias o no exige el Run report.

## 0.2.0 — 2026-11-26
- Nuevo agente `orchestrator`: sesión principal (`claude --agent orchestrator`) en el modelo más capaz, que toma decisiones y delega ejecución con ruteo explícito de modelos.
- Modelo por rol en `.claude/agents/`: `opus` para roles de decisión (supervisor, solution-architect, security-reviewer), `sonnet` para ejecutores y revisores.

## 0.1.0 — 2026-11-08
- Configuración inicial del hub con agentes Claude Code y skills portables.
- Documentos de gobierno, protocolo de tareas, plantillas de proyecto y guía de stack dinámico.
- CLI de diagnóstico/inicialización, validaciones y workflow de CI.
- Registro obligatorio de trabajo y criterios de aceptación.

No se ha habilitado un runtime autónomo que ejecute agentes sin intervención.