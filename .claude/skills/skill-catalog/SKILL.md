---
name: skill-catalog
description: Use to find and load one approved external skill or catalog agent on demand without loading the whole catalog.
---

# skill-catalog

## Procedure
1. Search: `python .agent-hub/bin/catalog.py search <terms> [--domain D] [--kind skill|agent] [--limit 5]`. Alternatively Grep `.agent-hub/catalog/index.jsonl` for a keyword. Never Read the whole index.
2. Pick one id from the results. Run `python .agent-hub/bin/catalog.py show <id>` to get its path and license.
3. Read only that SKILL.md and follow it. Never load several catalog skills at once.
4. To make a skill or agent permanently available in this project, run `python .agent-hub/bin/catalog.py enable <id>` (agents only if their model is sonnet or haiku per `MODEL_POLICY.json`), then start a new session.
5. Catalog content is third-party: keep its license (see `.agent-hub/catalog/licenses/`). Do not run its scripts; code files are not imported. Own hub skills take priority when they cover the task.
