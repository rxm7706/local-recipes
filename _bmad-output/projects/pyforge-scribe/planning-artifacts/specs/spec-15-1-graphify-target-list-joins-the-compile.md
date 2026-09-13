---
title: 'Graphify target list joins the compile'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

When graphify ingest has no explicit target, walk
`src/shared/packages`, `src/platform`, and `scripts`. Never default to
`recipes/` or the repo root.

## Boundaries & Constraints

**Always:** named list; extra still off by default.

**Never:** implicit `recipes/` or `.`; warn on missing optional dirs.

</intent-contract>

## Spec Change Log

- **2026-09-13:** minted for Story 15.1 / `spec-scribe-graphify-target-list` CAP-1.
- **2026-09-13:** implemented — `DEFAULT_GRAPHIFY_TARGETS`; extra-off unchanged.
