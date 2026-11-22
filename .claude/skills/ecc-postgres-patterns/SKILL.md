---
name: ecc-postgres-patterns
description: Use when reviewing PostgreSQL schema, SQL performance or indexes with ECC reference; read only and load reference on demand.
---

# ECC pilot: PostgreSQL review
Read `experiments/ecc/upstream/postgres-patterns/SKILL.md` only when PostgreSQL schema, performance, indexing or query behavior is central to the task.
Use the upstream material as a reference, not as an execution plan. PostgreSQL guidance may be version-specific or assume Supabase. Confirm server version, schema, workload and actual EXPLAIN evidence first.
Default to a single agent and read-only sandbox/QA analysis. Never execute ALTER SYSTEM, CREATE INDEX, CREATE EXTENSION, REVOKE, migrations, or production SQL without specific authorization. Never expose patient records, secrets or production logs.
Respect `AGENTS.md`, `token-budget`, `test-and-verify`, and `documentation-ledger`. Provide findings, reversible recommendations and what was actually measured.

## Attribution
Adapted wrapper for affaan-m/ECC at 4adeee6732a12d1540f49a4d50a38ce8c97f9a53; original skill remains unmodified in `experiments/ecc/upstream/postgres-patterns/SKILL.md`. Upstream license: MIT; see `experiments/ecc/UPSTREAM_LICENSE`.
