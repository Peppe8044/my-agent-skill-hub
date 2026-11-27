# Integration lifecycle

Default full install downloads pinned repositories, installs hub skills and approved upstream skills (registry/integrations.json), and writes project-local HTTP MCP definitions for GitHub and ClickUp. Authentication is still required in Claude Code. Existing conflicting files are not overwritten.

External skill activation is deny-by-default until a reviewed registry entry supplies name, repository, relative path and exact commit. All tracked files in that skill directory are copied, not just SKILL.md. Use the original skill name; conflicts with hub skills must be resolved before approval. Review licenses, scripts and prompt content before approving. Do not approve unreviewed hooks or offensive capabilities.

## Runtime setup (local only)
- Agent Memory: review the pinned source and npm package version/integrity, then follow its Windows or WSL2 setup guide. Choose keyless or a local embedding provider, isolated data directory and project-only capture. Do not import global session history. Check localhost:3111/agentmemory/health and save/retrieve a synthetic probe across restart.
- OpenViking: select provider, embedding/VLM, dedicated storage and credentials outside Git; use Windows desktop or WSL2/local server per upstream. Bind to loopback and verify isolated indexing and retrieval. Do not run the global curl installer automatically.
- ECC: review package integrity and plugin hooks; official guided CLI supports project/local scope, standard hooks and dry-run. Do not stack manual and plugin installation. Before activation check every agent/model route and hook conflict; do not enable if it bypasses the hub policy.
- REA: isolated authorized analysis only; no default runtime installation.
- Diagram Design, scientific and defensive cybersecurity skills: review pinned skill directories and add exact approvals to registry.
- Harness Engineering: reference catalog, not a server.

Run python scripts/hub.py integrations --target PATH for local prerequisite and checkout status. Runtime is not considered healthy until a real MCP handshake, authenticated tool call and applicable service probe pass. No model execution or service health is asserted by static checks.
