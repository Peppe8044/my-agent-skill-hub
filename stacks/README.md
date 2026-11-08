# Stack profiles: decisions, not defaults

Read `stacks/catalog.json` to discover relevant alternatives for each project kind. The CLI produces suggestions, **never an approval**.

- Existing stack has priority when safe and fit for purpose.
- Compare at least two viable options and a minimal baseline.
- No mandatory TypeScript/Python, React, database, ORM, Docker or swarm.
- Record final choice and tradeoffs in project-specific `STACK_DECISION.md`.
- Revisit choices when real constraints or evidence change.
- Do not compare costs or model performance without verified measurements.

Run: `python scripts/hub.py recommend --input workspaces/my-project/project.json`.
