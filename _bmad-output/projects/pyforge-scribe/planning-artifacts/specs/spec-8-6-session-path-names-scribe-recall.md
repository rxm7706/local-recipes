---
title: 'Session path names scribe recall'
type: 'docs'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

Durable session instruction: `scribe recall` for decisions; default omits `code:`; `codegraph` owns navigation.

## Boundaries & Constraints

**Always:** write outside the `bmad:context` replace-block in `AGENTS.md`.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — `AGENTS.md` § *Scribe recall (session path)*
  sits after `<!-- /bmad:context -->`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `8-6-session-path-names-scribe-recall: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `8-6-session-path-names-scribe-recall: done`).
- `## Auto Run Result` reconstructed from git (none survived).
