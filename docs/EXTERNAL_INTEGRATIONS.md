# External integration candidates

Audit exact commit, source, license, permissions, dependencies and hooks before installation. Installation follows the tiered model below: rule-based approval, a small active tier of skills detected natively by Claude Code, and an on-demand catalog (`.agent-hub/catalog/`) reached through `skill-catalog`. Upstream code is never executed; hooks, MCP servers, plugins and services (Agent Memory, OpenViking) are never activated. See docs/decisions/0005-external-capabilities.md.

- rohitg00/agentmemory: isolated memory pilot.
- K-Dense-AI/scientific-agent-skills: selective statistics.
- mukul975/Anthropic-Cybersecurity-Skills: defensive subset.
- volcengine/OpenViking: isolated later evaluation. AGPL-3.0 allows redistribution under copyleft conditions; keeping it out of installed projects is a project policy, not a licence prohibition.
- harness-engineer/awesome-harness-engineering: reference.
- cathrynlavery/diagram-design: selective diagram skill.
- affaan-m/ECC: selective hooks and skills after conflict audit.
- morluto/rea: authorized isolated lab.

Local skills are original starter procedures, not imported upstream implementations.

## Tiered installation model
- Approval is rule-based: license allow-list, canonical copies only, own skills win duplicates, code files never imported, code-dependent skills need human review, defensive security only, unsafe patterns rejected, external agents only `sonnet` or `haiku`.
- Active tier: a few approved skills installed in the project's `.claude/skills/` and `.agents/skills/`, detected natively by Claude Code.
- Catalog tier: the rest in `.agent-hub/catalog/`, searched with `.agent-hub/bin/catalog.py` (`search`, `show`, `enable`, `disable`) through the `skill-catalog` skill; one catalog skill is loaded at a time.
- Provenance (repository, pinned commit, sha256, license) is recorded in the manifest. Backups go to `.agent-hub/backups/`; `python scripts/hub.py rollback --target PATH` restores them.
- Inventory and reports are regenerated with `python scripts/hub.py external-scan`.

## Upstream checkout
All eight are pinned submodules in `external/`. Run `git submodule update --init` from the hub root to fetch their source. Do not execute upstream installers, hooks or scripts before review. The hub's own model policy remains authoritative (Opus only for the orchestrator; no upstream hook, agent or installer is activated, and the only installed hook is the hub's `model_guard`). Upstream licenses remain separate; verify before redistribution.

- `external/agentmemory`: `5c9e2e698bda138dcb7de50ee4dd3260ee4fb8eb`
- `external/scientific-agent-skills`: `c21d13b3cc2894680229ba9959a53281acb9200e`
- `external/Anthropic-Cybersecurity-Skills`: `54a798831d2266a3ca61ce68a7acb80b81160d57`
- `external/OpenViking`: `600babf130a8dcb1b2ec811e8211c582ca0ae83b`
- `external/awesome-harness-engineering`: `0b14b85ab0fe286ee19dbe3ad36d7ce5b3fc5c55`
- `external/diagram-design`: `795eec47fd376e5dda0b9e056a49520060cd2f13`
- `external/ECC`: `4adeee6732a12d1540f49a4d50a38ce8c97f9a53`
- `external/rea`: `8ff311b4ca0c67bfe45d811aecb6a68483a649af`
