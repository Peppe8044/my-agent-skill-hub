---
name: ecc-search-first
description: Use for a bounded research-first comparison of existing packages and solutions; do not launch subagents automatically.
---

# ECC pilot: Research-first, token-limited
Consult `experiments/ecc/upstream/search-first/SKILL.md` only for new dependencies, integrations or substantial new features.
Start with quick mode: check repository and existing skills first; next research only channels that materially influence the decision. Record candidate, license, maturity, security and maintenance.
**Pilot override:** do not automatically launch the ECC researcher agent, parallel agents, external package installers, network scanners or MCP tools. Delegate only with an explicit user request and a bounded token/time budget. Never install packages or modify workspaces during the research phase.
Follow `AGENTS.md` and `token-budget`. Present Adopt / Extend / Build with evidence and any unknowns.

## Attribution
Adapted wrapper for affaan-m/ECC at 4adeee6732a12d1540f49a4d50a38ce8c97f9a53; original skill remains unmodified in `experiments/ecc/upstream/search-first/SKILL.md`. Upstream license: MIT; see `experiments/ecc/UPSTREAM_LICENSE`.
