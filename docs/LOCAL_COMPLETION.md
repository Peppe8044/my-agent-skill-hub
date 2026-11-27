# Local completion checklist

Run bootstrap in a personal test project first. Review its report. Existing divergent AGENTS.md, CLAUDE.md, settings or MCP files cause a safe stop; merge them deliberately before installing. Never delete project-specific rules to resolve a conflict.

In VS Code, use Claude Code on the pinned Agent Hub checkout to audit external skill directories, including supporting scripts and licenses. Record reviewed entries in registry/integrations.json; test at least one positive install and a rejected dirty checkout. Do not bulk-approve all discovered skills. Preserve own names and policy.

For Agent Memory, inspect pinned source and supported Windows/WSL2 installation; choose isolated project storage and no global session import. Verify health, authenticated save/retrieve and restart persistence with synthetic data. For OpenViking, choose a provider and isolated storage, obtain credentials locally, bind to loopback, verify indexing and retrieval. For ECC, review exact version and hooks, run documented dry-run first, ensure project/local scope, reject conflicting agents or model inheritance. No global changes without permission.

Use actual Claude Code MCP listing and authenticated read-only calls for GitHub and ClickUp, and actual runtime traces for Opus/Sonnet/Haiku delegation. Report observed model IDs; don't infer from configuration. Only mark operational after successful checks. Record commands, outcomes and blockers in the work log. Do not merge to main before CI and review.

The bootstrap command does not execute third-party installers or configure credentials. The launch command checks installed files and starts Opus explicitly; this does not prevent all runtime overrides.
