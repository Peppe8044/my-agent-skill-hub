# My Agent Skill Hub

Biblioteca **reutilizable** de agentes, skills, perfiles de stack y controles de calidad para proyectos de software, datos, IA, automatización y SRE.

> **Regla de oro:** primero entender el problema, luego elegir stack y equipo. Un agente por defecto; delegar solo si aporta valor. Documentación, pruebas y seguridad son obligatorias por defecto.

## Inicio

1. Lee [AGENTS.md](AGENTS.md) (Claude Code también lee [CLAUDE.md](CLAUDE.md)).
2. Usa `python scripts/hub.py doctor` para comprobar la biblioteca.
3. Usa `python scripts/hub.py new --name mi-idea --kind web` para generar un paquete de planificación en `workspaces/mi-idea/`.
4. Completa `PROJECT_BRIEF.md` con el problema, criterios de éxito y restricciones.
5. Usa `stack-selection` para investigar y documentar al menos dos alternativas antes de aprobar el stack.
6. Selecciona agentes/skills según la tarea, implementa con pruebas y documenta cada cambio en `docs/WORK_LOG.md` (o bitácora del proyecto).
7. Antes de entregar, ejecuta `python scripts/hub.py validate` y `python -m unittest discover -s tests -v`.

## Componentes

- `agents/`: perfiles conceptuales independientes del proveedor.
- `.claude/agents/`: definiciones ejecutables de subagentes en Claude Code.
- `.claude/skills/` y `.agents/skills/`: skills portables de Claude y Codex.
- `stacks/`: catálogo de alternativas, **no** stacks obligatorios.
- `templates/`: documentos de intake, decisión técnica, pruebas, seguridad y entrega.
- `scripts/hub.py`: CLI de diagnóstico, validación e inicialización (sin dependencias externas).
- `docs/`: políticas, decisiones, registro de trabajo y fuentes.

## Límites de esta versión

Las skills y los agentes son instrucciones compatibles con entornos que soporten esos formatos. **No** constituyen por sí solos un motor autónomo que ejecute múltiples modelos ni un sistema de mensajería en tiempo real. Claude Code Agent Teams puede ofrecer colaboración multi-sesión cuando se habilita explícitamente; es experimental y consume más tokens. La selección del stack requiere aprobación técnica humana.

La biblioteca no ejecuta despliegues ni operaciones sobre producción automáticamente. Nunca guardar secretos, PHI/PII ni datos de clientes en este repositorio público.

## Fuentes oficiales

- [Agent Skills](https://agentskills.io/specification)
- [Claude Code: subagentes](https://code.claude.com/docs/en/sub-agents)
- [Claude Code: skills](https://code.claude.com/docs/en/skills)
- [Codex: skills](https://developers.openai.com/api/reference/cli)
- [GitHub Actions: seguridad](https://docs.github.com/en/actions/reference/security/secure-use)

Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/GOVERNANCE.md](docs/GOVERNANCE.md) y [docs/OPERATING_GUIDE.md](docs/OPERATING_GUIDE.md).
