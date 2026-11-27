# External integration candidates

Audit exact commit, source, license, permissions, dependencies and hooks before installation. No upstream code installed by this change.

- rohitg00/agentmemory: isolated memory pilot.
- K-Dense-AI/scientific-agent-skills: selective statistics.
- mukul975/Anthropic-Cybersecurity-Skills: defensive subset.
- volcengine/OpenViking: isolated later evaluation (AGPL).
- harness-engineer/awesome-harness-engineering: reference.
- cathrynlavery/diagram-design: selective diagram skill.
- affaan-m/ECC: selective hooks and skills after conflict audit.
- morluto/rea: authorized isolated lab.

Local skills are original starter procedures, not imported upstream implementations.

## Upstream checkout
All eight are pinned submodules in `external/`. Run `git submodule update --init` from the hub root to fetch their source. Do not execute upstream installers, hooks or scripts before review. The hub's own model policy remains authoritative. Upstream licenses remain separate; verify before redistribution.

- `external/agentmemory`: `5c9e2e698bda138dcb7de50ee4dd3260ee4fb8eb`
- `external/scientific-agent-skills`: `c21d13b3cc2894680229ba9959a53281acb9200e`
- `external/Anthropic-Cybersecurity-Skills`: `54a798831d2266a3ca61ce68a7acb80b81160d57`
- `external/OpenViking`: `600babf130a8dcb1b2ec811e8211c582ca0ae83b`
- `external/awesome-harness-engineering`: `0b14b85ab0fe286ee19dbe3ad36d7ce5b3fc5c55`
- `external/diagram-design`: `795eec47fd376e5dda0b9e056a49520060cd2f13`
- `external/ECC`: `4adeee6732a12d1540f49a4d50a38ce8c97f9a53`
- `external/rea`: `8ff311b4ca0c67bfe45d811aecb6a68483a649af`
