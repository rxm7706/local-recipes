---
title: 'Default recall omits the code surface'
type: 'feature'
created: '2026-09-13'
status: 'ready-for-dev'
---

<intent-contract>

## Intent

Keep `code:` nodes in the store. Default `answer()` / `scribe recall` exclude them. `--kind` is the opt-in.

## Boundaries & Constraints

**Never:** change Marshal `--scope` semantics. Never make semantic/pgvector the default.

</intent-contract>
