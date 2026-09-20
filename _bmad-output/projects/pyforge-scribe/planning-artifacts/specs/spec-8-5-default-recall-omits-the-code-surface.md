---
title: 'Default recall omits the code surface'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

Keep `code:` nodes in the store. Default `answer()` / `scribe recall` exclude them. `--kind` is the opt-in.

## Boundaries & Constraints

**Never:** change Marshal `--scope` semantics. Never make semantic/pgvector the default.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — `answer(..., kinds=)` defaults to all kinds
  except `code`; `scribe recall --kind` is explicit. Marshal `--scope` argv
  unchanged.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `8-5-default-recall-omits-the-code-surface: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `8-5-default-recall-omits-the-code-surface: done`).
- `## Auto Run Result` reconstructed from git (none survived).
