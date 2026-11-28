# My Agent Skill Hub

Biblioteca **reutilizable** de agentes, skills, perfiles de stack y controles de calidad para proyectos de software, datos, IA, automatización y SRE.

> **Regla de oro:** primero entender el problema, luego elegir stack y equipo. Un agente por defecto; delegar solo si aporta valor. Documentación, pruebas y seguridad son obligatorias por defecto.

## Inicio

1. Lee [AGENTS.md](AGENTS.md) (Claude Code también lee [CLAUDE.md](CLAUDE.md)).
2. Usa `python scripts/hub.py doctor` para comprobar la biblioteca y el entorno (validate + Python, Git/submodulos, CLI de Claude Code, `gh`, Docker, Ollama por HTTP, Godot, variables prohibidas, ruta OneDrive; admite `--json`, sale con 1 solo ante FAIL).
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

## Instalación por proyecto

`python scripts/hub.py install --target /ruta/proyecto` (perfil `full` por defecto) copia agentes, skills, `MODEL_POLICY.json` y el hook `model_guard`; fusiona `.claude/settings.json` conservando las claves y hooks del proyecto (añade `env.CLAUDE_CODE_SUBAGENT_MODEL: sonnet` si falta; un valor del proyecto fuera de sonnet/haiku es un conflicto de política); por defecto descarga los ocho submódulos y cataloga skills externas sin activarlas. `--no-fetch` usa el checkout actual. `new` instala automáticamente el contenido propio y cataloga los submódulos ya descargados, sin red.

- **Archivos del proyecto nunca se sobrescriben:** la versión del hub se deja en `.agent-hub/incoming/<ruta>`, se lista en `conflicts` y `bootstrap` informa `ready: false` hasta reconciliar. Los conflictos de política (settings con modelo no opus o variables prohibidas) detienen la instalación antes de escribir.
- **Hooks:** el único hook que se instala es el propio `model_guard` del hub. El código upstream de `external/` (hooks, instaladores, MCP) nunca se activa ni se ejecuta.
- **MCP:** se declaran los servidores HTTP de GitHub y ClickUp en `.mcp.json` del proyecto **solo si no existe uno equivalente** (mismo nombre normalizado o URL) en el `.mcp.json` del proyecto, en el ámbito usuario/local (`~/.claude.json`) o en la lista de runtime de `claude mcp list` (incluye conectores de claude.ai). Los duplicados omitidos se listan en el informe de instalación y los servidores existentes nunca se eliminan ni reescriben. `--no-runtime-mcp-scan` omite `claude mcp list`. Declarar un servidor no lo autentica: Claude Code pide aprobación antes de usar servidores MCP del proyecto y las credenciales siguen siendo locales.

Iniciar con `claude --agent orchestrator --model opus` (o `python scripts/hub.py launch`). Ver ADR 0004.

### External integrations
Default full installation declares GitHub and ClickUp project MCP servers (only when no equivalent exists in project, user/local or runtime scope) and copies reviewed external skills from the central approval registry. Run `python scripts/hub.py integrations --target PATH` to inspect prerequisites. See docs/INTEGRATION_BOOTSTRAP.md for services requiring local setup and real verification.

### One-command bootstrap
`python scripts/hub.py bootstrap --target PATH` installs project-local files, verifies their hashes and model declarations, checks prerequisites and probes the local Agent Memory health endpoint. It writes `.agent-hub/bootstrap-report.json`. `python scripts/hub.py launch --target PATH` verifies managed files, refuses to start if forbidden model environment variables are set (`CLAUDE_CODE_SUBAGENT_MODEL` other than sonnet/haiku, `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_*_MODEL`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) and starts Claude Code with Opus. External runtime setup and credentials remain local prerequisites; see docs/LOCAL_COMPLETION.md.
