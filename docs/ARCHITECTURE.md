# Arquitectura objetivo

```mermaid
flowchart TD
    USER[Idea / requisitos] --> INTAKE[project-intake]
    INTAKE --> STACK[stack-selection: comparar alternativas]
    STACK --> APPROVE{Aprobacion humana de stack y riesgos}
    APPROVE -->|Ajustar| INTAKE
    APPROVE -->|OK| SUP[Supervisor: plan y delegacion]
    SUP --> ONE[Un agente por defecto]
    SUP --> TEAM[Especialistas solo si compensa]
    ONE --> BUILD[Implementacion]
    TEAM --> BUILD
    BUILD --> GATES[Pruebas + seguridad + review]
    GATES -->|Falla| BUILD
    GATES --> DOC[documentation-ledger + evidencia]
    DOC --> HANDOFF[Handoff y decision de despliegue]
```

## Componentes
- `AGENTS.md`: política duradera mínima y rutas de skills.
- `agents/`: responsabilidades conceptuales; `.claude/agents/`: adaptadores nativos Claude Code.
- `skills/`: fuente canónica de procedimientos portables (Agent Skills); `.claude/skills/` y `.agents/skills/` son copias generadas por `hub.py sync`.
- `stacks/catalog.json`: alternativas y factores de idoneidad; **no** es un mandato tecnológico.
- `templates/project/`: evidencia de evaluación, decisiones, implementación y control.
- `scripts/hub.py`: utilidades deterministas sin modelos LLM (`validate`, `doctor` con chequeos de entorno, `install`, `bootstrap`, `launch`).
- `MODEL_POLICY.json` y `.claude/hooks/model_guard.py`: política de modelos (Opus solo orquestador; ejecutores sonnet/haiku) y su guardia de runtime; ver ADR 0003.
- `.github/workflows/quality.yml`: puertas técnicas reproducibles; el owner aún debe habilitar protecciones de rama.

## Coordinacion y alcance real
1. Proyecto inicia con un solo agente y documentos breves.
2. Si hay tareas separables, el supervisor asigna dueño de archivos, entrada, salida, dependencias y presupuesto por trabajo.
3. El traspaso entre agentes se hace mediante contratos versionados, ruta del artefacto, decisiones y resumen compacto.
4. Nunca editar simultáneamente el mismo archivo entre agentes sin coordinación y revisión de merge.
5. Documentación y evidencias persistentes en el repositorio del **proyecto**, no en conversaciones privadas.
6. La biblioteca **no** ejecuta por sí misma agentes remotos ni implementa bus de mensajes: Claude Code / Codex son runtimes externos. Agent Teams de Claude es experimental y opt-in.

## Enrutamiento de modelos
Opus solo en el orquestador de la sesión principal; Sonnet para ejecución especializada; Haiku para tareas simples y acotadas. Capas de cumplimiento: `hub.py validate` (estático), hook PreToolUse `model_guard` con matcher `Agent|Task` (runtime) y comprobaciones de entorno en `hub.py launch`. El supervisor es un subagente Sonnet de planificación que no crea subagentes. Ver `docs/decisions/0003-model-routing-policy.md`.

## Instalación
Perfil `full` por defecto; no sobrescribe archivos del proyecto (los deja en `.agent-hub/incoming/`), fusiona settings y declara MCP solo sin duplicados. Ver `docs/decisions/0004-installer-mcp-dedup-and-preservation.md`.

## Controles
- Requisitos y stack aprobados antes de cambios amplios.
- Calidad + seguridad + documentación antes de handoff.
- Secretos y acceso a producción requieren controles externos, no solo prompts.
- Optimizar costo por tarea correcta, no por mensaje más corto.

## Decisiones arquitectónicas
Ver `docs/decisions/`. Los cambios de arquitectura deben generar una ADR (Contexto, opciones, decisión, consecuencias y evidencia).