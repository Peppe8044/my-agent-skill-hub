---
name: ecc-docker-patterns
description: Use for Docker and Compose diagnosis or review with selected ECC reference sections; no automatic execution.
---

# ECC pilot: Docker review
Read `experiments/ecc/upstream/docker-patterns/SKILL.md` only for Docker/Compose debugging, images, mounts, networks and security reviews.
The upstream file includes ECC-specific installer harness examples that may not apply to the user's infrastructure. Filter to the relevant sections; do not paste entire file into every response.
Begin with bounded, read-only commands and sanitized results; use one agent. Do not execute compose up/down, restart, prune, delete volumes, pull/build, alter host networking, or write to production without scoped approval. Confirm rollback and environment before changing anything.
Follow `AGENTS.md`, `token-budget`, `sre-operations`, and `documentation-ledger`. Never use real credentials or PHI.

## Attribution
Adapted wrapper for affaan-m/ECC at 4adeee6732a12d1540f49a4d50a38ce8c97f9a53; original skill remains unmodified in `experiments/ecc/upstream/docker-patterns/SKILL.md`. Upstream license: MIT; see `experiments/ecc/UPSTREAM_LICENSE`.
