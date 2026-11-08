---
name: secure-development
description: Use for all changes involving inputs, credentials, persistence, permissions, external access or sensitive data.
---

# secure-development

## Procedure
1. Identify assets, data classes, trust boundaries, abuse cases and threat model proportional to risk.
2. Require authn/authz on backend, least privilege, input validation, output encoding, safe file handling and protection against injection.
3. Never write plaintext credentials or PHI/PII to logs or repository; avoid speculative production queries.
4. Review new dependencies, license, supply-chain integrity and minimum GitHub Actions token permissions.
5. Prefer scoped environment configuration and explicit approval for destructive/deployment actions.
6. Record findings, severity, remediations and residual risks in SECURITY_REVIEW.md; critical unknown risks block handoff.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
