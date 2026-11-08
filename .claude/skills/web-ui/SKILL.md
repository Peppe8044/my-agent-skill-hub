---
name: web-ui
description: Use when building frontend experiences, forms, data fetching and accessible component systems.
---

# web-ui

## Procedure
1. Start from user journeys and design constraints, not from a fixed library set.
2. Choose UI framework and data fetching only if justified by stack decision; avoid duplicated state management.
3. Implement keyboard navigation, labels, semantic elements, loading/empty/error states, validation and safe rendering.
4. Cover major flows with component/e2e tests and document accessibility gaps.
5. Keep bundle size and dependency count proportional to need.

## Final gate
Follow `AGENTS.md`; update `WORK_LOG.md` with real evidence on all material tasks. Follow `token-budget` to minimize excess calls while preserving quality. If a process rule is waived, record user approval, scope, risk and compensation in `EXCEPTIONS.md`.
