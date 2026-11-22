---
name: ecc-strategic-compact
description: Use for optional manual context compaction at phase boundaries; no automatic hooks or savings claims.
---

# ECC pilot: Manual context control
Consult `experiments/ecc/upstream/strategic-compact/SKILL.md` only for long sessions or transitions between distinct phases.
In this pilot, do not enable the upstream `suggest-compact.js` hook, plugin, global settings or any automatic context agent. The upstream hook thresholds and promotional savings figures are not validated for this environment.
At a natural transition, write a concise state checkpoint (goal, changed files, decisions, next step, verification status) to a project-safe file, excluding secrets/PHI, then *suggest* manual `/compact` when justified. Do not compact in the middle of unresolved changes.
Follow `AGENTS.md` and `token-budget`; measure actual use when the runtime exposes it.

## Attribution
Adapted wrapper for affaan-m/ECC at 4adeee6732a12d1540f49a4d50a38ce8c97f9a53; original skill remains unmodified in `experiments/ecc/upstream/strategic-compact/SKILL.md`. Upstream license: MIT; see `experiments/ecc/UPSTREAM_LICENSE`.
