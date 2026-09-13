---
title: 'Named docs join the compile'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

Compile `docs/how-to/*.md` (except README) as ordinary `doc` nodes and
`docs/reference/library-llms-full.md` as a `##` heading extract. Never
`docs/**`.

## Boundaries & Constraints

**Always:** named paths only.

**Never:** how-to README; tutorials; explanation; wholesale catalog body.

</intent-contract>

## Spec Change Log

- **2026-09-13:** minted for Story 14.1 / `spec-scribe-named-docs` CAP-1.
- **2026-09-13:** implemented — how-tos as `doc` bodies; catalog as `##` extract.
