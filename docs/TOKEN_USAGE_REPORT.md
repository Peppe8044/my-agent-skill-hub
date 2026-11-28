# TOKEN_USAGE_REPORT — consumo real por fase

- Fuente de los ejecutores: notificaciones del harness (`subagent_tokens`, `tool_uses`, `duration_ms`).
- Fuente de las pruebas `claude -p`: `total_cost_usd` y `modelUsage` del evento `result`.
- **No medido:** el consumo del orquestador Opus de la sesión interactiva, porque el harness no lo expone. No se ha estimado.

## 1. Ejecutores por fase

| Fase | Ejecutor | Modelo solicitado → observado | Esfuerzo | Tokens | Herramientas | Duración |
|---|---|---|---|---|---|---|
| 1 | Auditoría de política de modelos | sonnet → claude-sonnet-5-5 | por defecto | 71 261 | 10 | 229,5 s |
| 1 | Revisión del PR #2 | sonnet → claude-sonnet-5-5 | por defecto | 71 404 | 8 | 343,5 s |
| 1 | Hardware y runtime | haiku → claude-haiku-5-5 | por defecto | 60 477 | 12 | 547,4 s |
| **1** | **Total** | | | **203 142** | 30 | |
| 2 | Docker/WSL/OneDrive (incompleto, desperdicio) | haiku → claude-haiku-5-5 | por defecto | 52 287 | 3 | 382,1 s |
| 2 | Documentación de política | sonnet → claude-sonnet-5-5 | por defecto | 94 244 | 16 | 277,9 s |
| 2 | Docker/WSL/OneDrive (repetición) | haiku → claude-haiku-5-5 | por defecto | 59 628 | 6 | 254,8 s |
| 2 | Código de política, instalador y doctor | sonnet → claude-sonnet-5-5 | por defecto | 129 165 | 31 | 669,1 s |
| **2** | **Total** | | | **335 324** | 56 | |
| 3 | S1 escáner determinista | sonnet | medium | 104 504 | 12 | 447,5 s |
| 3 | S2 instalador, catálogo y rollback | sonnet | medium | 171 926 | 61 | 2 409,5 s |
| 3 | S3 reglas de tokens, effort y documentación | haiku | medium | 85 622 | 19 | 259,5 s |
| **3** | **Total** | | | **362 052** | 92 | |

**Pruebas reales `claude -p`:**
- **Fase 2:** 1,0461 USD.
- **Fase 3:**
  - Detección en el proyecto temporal: 0,4532 USD y 51,4 s. `modelUsage`: Opus 3 449 tokens de salida; Haiku 326 tokens de salida.
  - Verificación de `--effort high`: 0,2756 USD.

## 2. Qué cambió en la fase 3 y por qué no bajó el total

El trabajo de la fase 3 fue mucho mayor: escáner, instalador en dos niveles, catálogo, procedencia, rollback y 36 pruebas nuevas. Aun así, el total de ejecutores (362 052) **no bajó** respecto a la fase 2 (335 324).

Medidas aplicadas:
1. **Clasificación sin LLM.** El inventario y la clasificación de 2 204 skills, 312 agentes, 322 hooks, 66 configuraciones MCP y 17 080 scripts se hicieron con Python determinista. No se gastó ningún token por elemento.
2. **Esfuerzo moderado.** Todos los ejecutores de la fase 3 corrieron con `effort: medium`. Las transcripciones lo confirman para los subagentes: `"effort":"medium"`.
3. **Contexto pequeño por ejecutor.** Tres ejecutores con archivos disjuntos mantienen cada contexto acotado. Un único ejecutor habría releído un contexto creciente en cada turno.
4. **Sin auditorías repetidas.** Se reutilizaron los resultados del pre-inventario y de las fases 1 y 2.
5. **Verificaciones baratas.** El orquestador ejecutó comprobaciones de un solo comando con salidas acotadas en lugar de crear agentes, que cuestan unos 20–30 mil tokens solo en contexto inicial.
6. **Catálogo bajo demanda.** Las 981 skills del catálogo no entran al contexto. La prueba real muestra 0 skills del catálogo en el `init` de Claude Code, y solo 14 externas activas.

**El mayor coste fue S2** (171 926 tokens, 61 herramientas, 40 min). Su alcance era amplio y su suite de pruebas era lenta: cada iteración tardaba entre 1 y 3 minutos.

**Desperdicio de la fase 3:** un `heredoc` bloqueado de S3, detenido por el orquestador, con coste menor.

## 3. Esfuerzo de razonamiento del orquestador (hallazgo)

- La configuración de usuario fija `modelSettings.claude-opus-5-5.effortLevel = "xhigh"`. Con `claude --agent orchestrator --model opus`, la transcripción registró `perTurnEffort: "xhigh"`, a pesar de que el frontmatter declara `effort: high`.
- Con `--effort high` la transcripción registró `perTurnEffort: "high"`. Por eso `hub.py launch` ahora pasa `--effort <effort del orquestador>`.
- La configuración global **no se modificó**. Bajarla a `high` es una decisión del owner.
- Las sesiones interactivas iniciadas sin `hub.py launch` siguen usando `xhigh`.

## 4. Reglas incorporadas a la configuración reutilizable

Están en `AGENTS.md` (sección "Token rules"), en `skills/token-budget/SKILL.md` y en `templates/project/TOKEN_METRICS.md`. Se aplican así:

| Regla | Dónde se aplica |
|---|---|
| Esfuerzo de ejecutores `low`/`medium`/`high` | `MODEL_POLICY.json` (`executor_efforts`, `default_executor_effort`), comprobado por `validate` |
| Bloqueo de `xhigh`/`max` en delegaciones | `model_guard` |
| Esfuerzo del orquestador | `effort: high` en el frontmatter y `--effort high` en `launch` |
| Ejecutores en paralelo | 1 por defecto y máximo 3 (`MODEL_POLICY.json`) |
| Skills precargadas del orquestador | Solo las 2 obligatorias; el resto se cargan bajo demanda |

## 5. Fase 4

| Ejecutor | Modelo | Esfuerzo | Tokens | Herramientas | Duración |
|---|---|---|---|---|---|
| E1 gestor de hooks e instalador | sonnet → claude-sonnet-5-5 | medium | 117 606 | 24 | 636,1 s |
| E2 hooks propios e informes | haiku → claude-haiku-5-5 | medium | 122 093 | 33 | 398,3 s |
| **Total fase 4** | | | **239 699** | 57 | |

- **Objetivo superado.** El total fue 2,4 veces el objetivo orientativo de 100 000. E2 consumió 3 veces su objetivo de 40 000.
- **Medidas tras la medición:**
  - No se lanzaron más ejecutores.
  - El resto lo hizo el orquestador con comandos deterministas.
  - El owner autorizó un **presupuesto real**: `model_guard` bloquea nuevas delegaciones al alcanzar `max_executor_tokens_per_session` (100 000), medido en las transcripciones de los subagentes. Cuenta los tokens de entrada, de salida y de creación de caché; excluye las lecturas de caché.
- **Causa raíz:**
  - La skill `token-budget` es texto y esta sesión no se inició dentro del hub, así que no se cargó en los ejecutores.
  - No existe un tope automático por subagente en el runtime.
  - El contexto acumulado del orquestador, que no se puede medir, es probablemente el mayor consumo.
- **Coste medido:** la prueba real de hooks costó 0,2947 USD.
- **Total acumulado de ejecutores en las fases 1–4:** 1 140 075 tokens.
