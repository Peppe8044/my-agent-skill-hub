---
name: data-science
description: Use for statistical analysis, experiments, ML model development and reproducible research.
---

# data-science

## Procedure
1. Define objective/target, baseline and decision supported by the model.
2. Validate grain, coverage, missingness, leakage, representativeness and licensing; keep sensitive data out of repo.
3. Choose train/validation/test splits before model selection, preserve seeds and environment, select metrics appropriate to class balance/costs.
4. Evaluate baseline, confidence intervals and domain shift, not only a single accuracy score.
5. Record code, dataset provenance, parameters, test results, failure modes, ethics and reproducibility instructions.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
