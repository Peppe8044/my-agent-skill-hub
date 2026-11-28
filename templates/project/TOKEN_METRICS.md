# TOKEN_METRICS — <project>
Track **actual measured** usage from runtime/API (never speculate).
| Date / task | Mode (solo/subagents/team) | Prompt tokens | Completion tokens | Cost and currency | Outcome verified | Tool/runtime |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | solo | not measured | not measured | not measured | pending | example |

Review cost per accepted task, rework and errors; do not optimize at the expense of safety or documentation.

## Token rules checklist
- [ ] Opus only coordinates and decides; executors use `effort: medium` (`low`/`high` per task, never `xhigh`/`max`).
- [ ] One executor by default; at most 3 in parallel, with a stated justification.
- [ ] No audit repeated; the existing report is reused.
- [ ] No whole-repository reads; inventories come from Python or deterministic tools that print counts.
- [ ] Haiku for simple tasks; Sonnet only when complexity justifies it.
- [ ] Skills load on demand; external skills go through `skill-catalog`; no bulk preload.
- [ ] Consumption recorded from harness evidence (`subagent_tokens`, `duration_ms`, `modelUsage`) or "not measured".
