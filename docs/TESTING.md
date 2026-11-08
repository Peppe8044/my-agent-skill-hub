# Testing guide

```bash
python3 scripts/hub.py doctor
python3 scripts/hub.py validate
python3 -m unittest discover -s tests -v
python3 scripts/hub.py new --name demo --kind web
python3 scripts/hub.py recommend --input workspaces/demo/project.json
```

Run the final two demonstration commands in a clone (workspaces is gitignored), and delete the local folder afterward. New projects default to planning documents, not live integrations.

On PR, GitHub Actions checks registry, frontmatter, skill sync, tests and whether `docs/WORK_LOG.md` and `docs/CHANGELOG.md` were updated (or an authorized exception with a ledger entry). Human reviewers still assess quality, risk and completeness. The workflow cannot force code review unless branch protections are separately configured in GitHub.

Code review should cite actual checks: report **not run** when no execution evidence exists.
