# MODEL_ROUTING_REPORT — ruteo de modelos verificado en runtime

- Fecha: 2026-11-28 (UTC)
- Runtime: Claude Code 2.1.332 en Windows 11, sesión principal `claude --agent orchestrator --model opus`
- Política: `MODEL_POLICY.json` (Opus solo orquestador; ejecutores `sonnet`/`haiku`; `default_parallel_agents: 1`, `max_parallel_agents: 3`, `max_retries: 2`) y ADR 0003
- Regla de evidencia: el modelo efectivo se toma del runtime (`message.model` en las transcripciones de cada subagente, `modelUsage` del resultado), nunca del nombre del agente ni de su frontmatter. Las autodeclaraciones de los subagentes ("PONG <agente> <modelo>") se registran pero son evidencia débil.

## 1. Método

Cada prueba se ejecutó con `claude -p ... --agent orchestrator --model opus --output-format stream-json --verbose --max-budget-usd 3 --disallowedTools Bash Edit Write NotebookEdit` en un worktree aislado del commit indicado, para que las ediciones en curso no contaminaran la prueba. La salida stream-json no incluyó mensajes de subagentes, así que la evidencia por subagente sale de las transcripciones de sesión (`<sesión>/subagents/agent-*.jsonl` y `*.meta.json`).

## 2. Resultados

### 2.1 Antes de los cambios (commit `da57564`, `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`, sin hook)

| Llamada | `model` enviado | Frontmatter | Modelo observado (transcripción) |
|---|---|---|---|
| researcher | `haiku` | haiku | **claude-haiku-5-5** |
| memory-curator | (ausente) | haiku | **claude-haiku-5-5** (meta: `modelNotNamed: true`) |
| code-reviewer | `sonnet` | sonnet | **claude-sonnet-5-5** |
| Sesión principal | `--model opus` | opus | **claude-opus-5-5** |

`modelUsage`:
- claude-opus-5-5: 0,3361 USD.
- claude-haiku-5-5: 44 080 tokens de creación de caché y 498 de salida.
- claude-sonnet-5-5: 26 755 tokens de creación de caché y 94 de salida.

Duración 15,5 s. Costo total 0,4098 USD.

### 2.2 Control: built-in sin modelo con la variable activa (commit `da57564`)

| Llamada | `model` enviado | Modelo observado |
|---|---|---|
| general-purpose | (ausente) | **claude-sonnet-5-5**: no heredó Opus |

Duración 8,6 s. Costo total 0,2546 USD.

**Conclusión 2.1 y 2.2.** En 2.1.332 la precedencia observada es:

`model` explícito > frontmatter del agente > `CLAUDE_CODE_SUBAGENT_MODEL` > modelo heredado de la sesión principal.

El hallazgo alto de la fase 1 suponía que la variable anulaba el frontmatter y que, por tanto, todo Haiku correría en Sonnet. **Era incorrecto para este runtime.** Como no hay contradicción, la variable **se conserva** como respaldo: impide que un subagente sin modelo herede Opus. La autorización del owner para eliminarla estaba condicionada a que contradijera la asignación individual, y esa condición no se cumplió.

### 2.3 Después de los cambios (commit `aef24f4`: variable de respaldo + hook `model_guard`)

| # | Llamada | `model` enviado | Resultado | Evidencia |
|---|---|---|---|---|
| 1 | researcher | `haiku` | permitida | transcripción: claude-haiku-5-5 |
| 2 | memory-curator | (ausente) | permitida | transcripción: claude-haiku-5-5 (meta `model: claude-haiku-5-5`) |
| 3 | code-reviewer | `sonnet` | permitida | transcripción: claude-sonnet-5-5 |
| 4 | general-purpose | (ausente) | **bloqueada por model_guard** | `model_guard: subagent 'general-purpose' would inherit the Opus parent model; pass model: sonnet or haiku explicitly (MODEL_POLICY.json)` |
| 5 | researcher | `opus` | **bloqueada por model_guard** | `model_guard: model 'opus' is not allowed for subagents; MODEL_POLICY.json executors: haiku, sonnet` |
| 6 | Explore | (ausente) | **bloqueada por model_guard** | igual que la 4 |

- `modelUsage` registra Opus solo en la sesión principal: 2 586 tokens de salida y 0,3082 USD.
- claude-haiku-5-5: 44 448 tokens de creación de caché. claude-sonnet-5-5: 26 937 tokens de creación de caché.
- Duración 28,4 s. Costo total 0,3817 USD.
- El hook se ejecutó en Windows con `python "$CLAUDE_PROJECT_DIR/.claude/hooks/model_guard.py"`.
- Tras la prueba, el texto de denegación de los casos 4 y 6 se precisó: indica que el subagente no tiene modelo explícito. La lógica no cambió y las pruebas unitarias del hook lo cubren.

## 3. Delegaciones de la sesión orquestadora (fases 1 y 2)

| Fase | Ejecutor | Solicitado | Observado (`message.model`) | Tokens | Herramientas | Duración |
|---|---|---|---|---|---|---|
| 1 | Auditoría de política de modelos | sonnet | claude-sonnet-5-5 | 71 261 | 10 | 229,5 s |
| 1 | Revisión del PR #2 | sonnet | claude-sonnet-5-5 | 71 404 | 8 | 343,5 s |
| 1 | Hardware y runtime | haiku | claude-haiku-5-5 | 60 477 | 12 | 547,4 s |
| 2 | Docker/WSL/OneDrive (1.º intento, incompleto) | haiku | claude-haiku-5-5 | 52 287 | 3 | 382,1 s |
| 2 | Documentación de política | sonnet | claude-sonnet-5-5 | 94 244 | 16 | 277,9 s |
| 2 | Docker/WSL/OneDrive (2.º intento) | haiku | claude-haiku-5-5 | 59 628 | 6 | 254,8 s |
| 2 | Código: política, instalador, doctor | sonnet | claude-sonnet-5-5 | 129 165 | 31 | 669,1 s |

- Tokens y duraciones salen de las notificaciones del harness (`subagent_tokens`, `tool_uses`, `duration_ms`).
- **El consumo del orquestador Opus de esta sesión no se ha medido**, porque el harness no lo expone.
- Nunca hubo más de 3 ejecutores en paralelo.
- El primer intento de Docker quedó incompleto por una instrucción de parada ambigua del orquestador. Se registra como desperdicio: 52 287 tokens.

## 4. Esfuerzo de razonamiento de Opus

- Configuración de usuario (solo lectura): `modelSettings.claude-opus-5-5.effortLevel = "xhigh"`. No se modificó porque es configuración global.
- En las pruebas `claude -p`, los metadatos de los subagentes muestran `pickedEffortModel: claude-opus-5-5`. No se ha verificado qué nivel de esfuerzo aplicaron los subagentes Haiku y Sonnet.
- En pruebas triviales la sesión Opus consumió entre 291 y 2 586 tokens de salida, más 25–40 mil tokens de contexto inicial. Ese contexto corresponde al system prompt, el agente orquestador y 6 skills precargadas.
- **Recomendación (no aplicada):** usar `high` para fases rutinarias de orquestación y reservar `xhigh` para decisiones de arquitectura. Requiere tu decisión porque es un ajuste global.

## 5. Limitaciones

- Resultados válidos para Claude Code 2.1.332. Hay que repetir esta prueba al actualizar el runtime (ADR 0003, "Revisión").
- No se probaron `ANTHROPIC_DEFAULT_*_MODEL` ni Agent Teams en runtime. `launch` y `doctor` los rechazan de forma estática.
- El hook depende de que el proyecto cargue `.claude/settings.json` y de que `python` esté en el PATH del shell de hooks. Un usuario puede desactivar hooks; en ese caso queda la variable de respaldo, pero un `model: opus` explícito no se bloquearía.
- Costo total de las tres pruebas de runtime: 1,0461 USD, según `total_cost_usd`.
