---
name: api-design
description: Use when designing APIs, schemas and external or internal service contracts.
---

# api-design

## Procedure
1. Identify consumers, authorization boundaries and compatibility requirements.
2. Define routes/events, schemas, error formats, pagination, idempotency, versions, retries and rate limits as relevant.
3. Model negative and permission cases; prefer stable typed contracts and examples without secrets.
4. Validate contract with consumer and provider, then write tests and a concise API specification.
5. Document migration strategy when changing existing contracts.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
