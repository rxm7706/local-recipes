---
title: 'Planning pointers join the compile'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

Compile named Brief / PRD / Architecture-spine / `epics.md` files as
`kind=doc` **pointer** nodes (title, path, status, FR/AD/heading
extract). Never store the wholesale body.

## Boundaries & Constraints

**Always:** named globs only under `planning-artifacts/`.

**Never:** `_node_from_text_file` on this surface; `epics-*.md`;
architecture novels; addenda; research; `specs/`.

</intent-contract>

## Spec Change Log

- **2026-09-13:** minted for Story 13.1 / `spec-scribe-planning-pointers` CAP-1.
- **2026-09-13:** implemented — named-glob pointer surface; body never stored.
