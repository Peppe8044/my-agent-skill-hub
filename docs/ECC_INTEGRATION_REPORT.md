# ECC_INTEGRATION_REPORT — integración selectiva de ECC (fase 4)

- **Fuente:** `external/ECC`, submódulo en el commit fijado `4adeee6732a1` (MIT). No se volvió a descargar.
- **Método:**
  - Consultas deterministas sobre `hooks/hooks.json`, `hooks/hooks.metadata.json` y el registro de capacidades de la fase 3.
  - Revisión de código por el orquestador solo para los hooks candidatos.
  - Esto **no es una auditoría completa** de ECC.

## 1. Mecanismos de instalación de ECC

- ECC ofrece `install.ps1`, `install.sh`, un manifiesto de plugin (`.claude-plugin/plugin.json`) y un paquete npm (`ecc-universal@2.2.3`).
- Sus 28 hooks se ejecutan con arranques `node -e` que localizan el plugin mediante `CLAUDE_PLUGIN_ROOT` o `~/.claude`. Están diseñados para una **instalación global** como plugin.
- **No se usaron.** Instalarían en el ámbito de usuario y contradicen la restricción de no modificar configuraciones globales.
- El hub copia por proyecto solo los archivos revisados, con verificación del commit y sha256, y los ejecuta directamente con `node "$CLAUDE_PROJECT_DIR/.claude/hooks/ecc/..."`.

## 2. Hooks de ECC (28)

| Estado | Número | Hooks |
|---|---|---|
| Aprobado | 1 | `pre:config-protection` |
| Rechazado | 9 | `pre:observe:continuous-learning`, `pre:governance-capture`, `pre:edit-write:gateguard-fact-force`, `pre:compact`, `session:start`, `post:skill:track`, `stop:session-end`, `stop:evaluate-session`, `stop:cost-tracker` |
| Solo inventario | 18 | dispatchers, gateguard de PowerShell, doc-file-warning, suggest-compact, mcp-health, hookify, context-gate, plan-canvas, format-typecheck, check-console-log, desktop-notify, session-end marker |

Motivos de los rechazos:
- Captura de conversaciones u observaciones.
- Memoria de sesión, en conflicto con Agent Memory y OpenViking.
- Escrituras fuera del proyecto: `~/.claude/metrics` y el directorio temporal del sistema.
- Captura de secretos.
- Fricción que multiplica los turnos y tokens (gateguard en Edit/Write).

Los detalles por hook están en `registry/HOOK_REGISTRY.json` y `docs/HOOK_SECURITY_REPORT.md`.

**Sustituciones por controles propios deterministas** (Python, sin dependencias, con menos complejidad):

| Hook de ECC | Sustituto propio |
|---|---|
| `pre:bash:dispatcher` y gateguard (2 848 líneas y 5 bibliotecas) | `command_guard` |
| `stop:cost-tracker` | `usage_tracker` (solo cifras, dentro del proyecto) |
| — (necesidad propia) | `file_guard`, que protege la política y los hooks y detecta credenciales |

## 3. Otras capacidades de ECC, por área

Ya estaban clasificadas en la fase 3. El mapeo es por palabras clave sobre nombre y descripción, así que es orientativo y no exclusivo.

| Área | Skills aprobadas (14 activas en total en el hub, 6 de ECC) | Agentes en catálogo |
|---|---|---|
| Calidad de código | 94 | 12 |
| Seguridad defensiva | 25 | 12 |
| Verificación de pruebas | 48 | 5 |
| Documentación automática | 12 | 3 |
| Control de contexto | 8 | 2 |
| Reducción de tokens | 14 (p. ej. `context-budget`, `cost-aware-llm-pipeline`) | 0 |
| Validación de herramientas | 34 | 3 |
| Revisión de cambios | 58 | 26 |
| Control de dependencias | 25 | 8 |
| Gestión de sesiones | 9 | 0 |
| Recuperación ante errores | 16 | 12 |

- ECC aporta 233 skills aprobadas: 6 activas y 227 en el catálogo bajo demanda.
- Aporta también 45 agentes en catálogo, todos con `sonnet` o `haiku` y ninguno activado automáticamente.
- Sus 99 comandos y 122 reglas quedan fuera del alcance: no se instalan.
- No se habilitó ningún orquestador externo. ECC no reemplaza al orquestador, no modifica `MODEL_POLICY.json` ni introduce ejecutores Opus.

## 4. Compatibilidad con la política

Se mantienen:
- Opus solo como orquestador y `model_guard` como control obligatorio, que no se puede desactivar.
- Un ejecutor por defecto y como máximo 3 en paralelo.
- Esfuerzo `medium` para los ejecutores.
- Carga bajo demanda.
- `full` como perfil predeterminado.

Novedad de esta fase: un **presupuesto real de tokens** de ejecutores por sesión (100 000), aplicado por `model_guard` a partir de las transcripciones.
