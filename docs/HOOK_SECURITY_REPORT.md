# Informe de seguridad de hooks

Generado por `python scripts/hooks_manager.py registry` desde `registry/hook_decisions.json`. No editar a mano.

## Totales

| Estado | Cantidad |
|---|---|
| approved | 5 |
| inventory-only | 96 |
| rejected | 9 |

| Origen | Cantidad |
|---|---|
| ECC | 28 |
| OpenViking | 43 |
| agentmemory | 35 |
| own | 4 |

## Hooks aprobados

| id | evento / matcher | runtime | riesgo | archivos (sha256) | hechos revisados |
|---|---|---|---|---|---|
| own:command-guard | PreToolUse / Bash|PowerShell | python | low | `.claude/hooks/command_guard.py` 3a41bb70804d | Own deterministic replacement for ECC pre:bash:dispatcher and gateguard: denies destructive, remote-execution, global-config and guard-tampering commands; asks for force push, hard reset, clean -fdx and global package installs. |
| own:file-guard | PreToolUse / Edit|Write|MultiEdit|NotebookEdit | python | low | `.claude/hooks/file_guard.py` 7ed7ec11c86f | Denies edits to model_guard.py, MODEL_POLICY.json and hook scripts, and content with credential patterns; asks for .claude/settings.json edits and paths outside the project. |
| own:model-guard (obligatorio) | PreToolUse / Agent|Task | python | low | `.claude/hooks/model_guard.py` f71c9418fa67 | Denies subagents outside sonnet/haiku, fork, built-ins, agents without the mandatory skills (token-budget), xhigh/max effort and delegations over the persistent phase/session budget or that cannot be measured. Cannot be disabled. |
| own:usage-tracker (obligatorio) | Stop / *; SubagentStop / * | python | low | `.claude/hooks/usage_tracker.py` afedc8868c54 | Own replacement for ECC stop:cost-tracker: stores only token counts per model and subagent in .agent-hub/usage/ (project-local, no content) on Stop and SubagentStop. Never blocks. Mandatory (measurement) in every profile. |
| pre:config-protection | PreToolUse / Write|Edit|MultiEdit | node | low | `scripts/hooks/config-protection.js` 9cfbc2b1fb09<br>`scripts/lib/hooks/recovery-hints.js` 30b7c874e104 | Reviewed: reads stdin (1 MB cap) and lstat of the target only; no writes, network, child processes or credentials. Blocks edits that weaken existing linter/formatter configs. Requires node; fails open if node is missing. |

## Hooks rechazados

| id | motivo |
|---|---|
| post:skill:track | Skill-health telemetry stored outside the project. |
| pre:compact | Persists session state (memory) outside the project; conflicts with Agent Memory. |
| pre:edit-write:gateguard-fact-force | Denies the first edit of every file with questions: extra turns and tokens; very high complexity. |
| pre:governance-capture | Captures governance events including secrets; privacy risk. |
| pre:observe:continuous-learning | Captures tool-use observations (conversation capture); conflicts with future Agent Memory/OpenViking. |
| session:start | Loads previous session context (memory); conflicts with Agent Memory/OpenViking. |
| stop:cost-tracker | Writes to ~/.claude/metrics and the OS temp dir (outside the project); replaced by own:usage-tracker. |
| stop:evaluate-session | Extracts patterns from sessions (continuous learning, conversation capture). |
| stop:session-end | Persists session state (memory) after each response. |

## Solo inventario

Total: 96.

| Repo | Cantidad |
|---|---|
| ECC | 18 |
| OpenViking | 43 |
| agentmemory | 35 |

Hooks de ECC en solo inventario:

| id | motivo |
|---|---|
| post:dispatcher:async | Runs ECC-internal background PostToolUse hooks; too broad. |
| post:dispatcher:sync | Runs ECC-internal PostToolUse hooks (formatting, telemetry); too broad. |
| post:mcp-health-check | MCP reconnection logic; no new MCP in scope. |
| pre:bash:dispatcher | Broad dispatcher (quality, tmux, push, GateGuard) with many dependencies; replaced by own:command-guard. |
| pre:edit-write:suggest-compact | State kept through shared libraries outside the hook; Claude Code already auto-compacts; benefit not demonstrated. |
| pre:hookify-runtime | Generic rule engine with no project rules defined; evaluate later. |
| pre:mcp-health-check | Manages MCP health state and reconnection; no new MCP in scope. |
| pre:powershell:gateguard-fact-force | 2,848 lines plus 5 libraries and on-disk state; replaced by own:command-guard. |
| pre:write:doc-file-warning | Conflicts with the hub documentation workflow (WORK_LOG, reports). |
| prompt:hookify-runtime | Generic rule engine with no project rules defined; evaluate later. |
| session-start:plan-canvas-sessions | Depends on ECC Plan Canvas browser UI. |
| session:end:marker | Lifecycle marker without useful effect. |
| stop:check-console-log | JS/TS specific. |
| stop:desktop-notify | Desktop notifications; no value for the hub. |
| stop:format-typecheck | JS/TS specific (Biome/Prettier/tsc through npx); not a default for Godot projects. |
| stop:hookify-runtime | Generic rule engine with no project rules defined; evaluate later. |
| stop:plan-canvas-pending | Depends on ECC Plan Canvas browser UI. |
| user-prompt:context-gate | Opt-in stop-and-restart at 90% context reading the transcript; benefit not demonstrated. |

## Comportamientos prohibidos y como se evitan

| Prohibido | Control |
|---|---|
| Exfiltracion de datos | Solo se aprueban hooks revisados sin red ni procesos hijos; `command_guard` bloquea ejecucion remota (curl/wget a shell). |
| Captura global de conversaciones | Rechazados los hooks de observacion, sesion y aprendizaje; `usage_tracker` guarda solo conteos de tokens en el proyecto. |
| Scripts remotos sin revisar | El instalador copia solo archivos cuyo sha256 y commit coinciden con el registro; si no coinciden se omiten. |
| Acceso a credenciales | `file_guard` bloquea contenido con patrones de credenciales; ningun hook aprobado lee credenciales. |
| Comandos destructivos automaticos | `command_guard` deniega o pide confirmacion; ningun hook ejecuta comandos. |
| Escritura fuera del proyecto | Rutas de instalacion relativas al proyecto; `file_guard` pregunta por rutas externas; rechazados los hooks que escriben en `~/.claude` o temp. |
| Desactivar model_guard | `own:model-guard` es obligatorio: `hooks disable` lo rechaza, el instalador lo registra siempre y `validate` lo exige. |
| Cambiar el modelo | `model_guard` deniega modelos fuera de sonnet/haiku; `file_guard` protege `MODEL_POLICY.json` y los scripts de hooks. |
