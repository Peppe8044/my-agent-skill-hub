# Changelog del hub

## 0.2.0 — 2026-11-26
- Nuevo agente `orchestrator`: sesión principal (`claude --agent orchestrator`) en el modelo más capaz, que toma decisiones y delega ejecución con ruteo explícito de modelos.
- Modelo por rol en `.claude/agents/`: `opus` para roles de decisión (supervisor, solution-architect, security-reviewer), `sonnet` para ejecutores y revisores.

## 0.1.0 — 2026-11-08
- Configuración inicial del hub con agentes Claude Code y skills portables.
- Documentos de gobierno, protocolo de tareas, plantillas de proyecto y guía de stack dinámico.
- CLI de diagnóstico/inicialización, validaciones y workflow de CI.
- Registro obligatorio de trabajo y criterios de aceptación.

No se ha habilitado un runtime autónomo que ejecute agentes sin intervención.