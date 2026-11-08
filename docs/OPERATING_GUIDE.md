# Guía de uso de la plantilla

## Uso inicial
```bash
python scripts/hub.py doctor
python scripts/hub.py new --name mi-proyecto --kind data-science
python scripts/hub.py recommend --input workspaces/mi-proyecto/project.json
python scripts/hub.py validate
python -m unittest discover -s tests -v
```

`new` crea archivos de **planificación** en `workspaces/` (ignorado por Git), no crea un repositorio Git ni realiza deploy. Tras aprobación, copia las plantillas y políticas al repositorio independiente de tu proyecto; registra su propia bitácora.

## Flujo obligatorio
1. Usuario describe problema; analista redacta brief y criterios verificables.
2. Arquitecto compara al menos dos diseños y un baseline simple. Documenta stack decidido y riesgos.
3. Usuario/owner confirma alcance, costos y riesgos antes de cambios irreversibles.
4. Supervisor elige modo: uno, subagente puntual, equipo paralelo (tareas independientes y presupuesto suficiente).
5. Cada agente recibe tarea, input delimitado, salida y responsable de archivos.
6. Implementación en cambios pequeños con pruebas, seguridad, revisión.
7. Documentador actualiza registro de trabajo, ADR si procede, changelog, evidencias y handoff.
8. CI y revisión humana; no afirmar despliegue automático.

## Uso con Claude Code / Codex
- Claude: abre el proyecto, revisa `CLAUDE.md`, `AGENTS.md`; usa `.claude/agents/` y `.claude/skills/`. Invoca una skill con `/nombre` si corresponde.
- Codex: utiliza `AGENTS.md` y `.agents/skills/`. Invoca skill `$nombre` cuando corresponda.
- El repositorio de biblioteca **no inyecta** automáticamente estas instrucciones en repositorios externos. Copia/adapta los archivos y registra la versión. La opción de empaquetado automatizado es futura.

## Riesgos de sobreingeniería
- No crear frontend, ORM, Postgres, Kubernetes o un enjambre solo por estar en el catálogo.
- No activar Agent Teams sin evaluación de costo. Sus sesiones son experimentales.
- No duplicar instrucciones extensas en archivos always-on. Las skills son on-demand.
- Nunca usar tokens como proxy de calidad: contar costo total por tarea verificada.