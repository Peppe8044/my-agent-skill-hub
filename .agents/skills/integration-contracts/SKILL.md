---
name: integration-contracts
description: Use when integrating APIs, webhooks, HL7, databases or external systems.
---

# integration-contracts

## Procedure
1. Specify actors, message schemas, protocol/version, auth, failure semantics and data minimization.
2. Define idempotency, retry/backoff, ordering, timeouts, dead-letter handling and reconciliation where needed.
3. Prefer vendor test environment and recorded synthetic examples; never place live identifiers or credentials in repo.
4. Implement contract/integration tests with negative cases, monitorability and rollback.
5. Document dependent organizations/owners, endpoints by environment without secrets and operational instructions.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
