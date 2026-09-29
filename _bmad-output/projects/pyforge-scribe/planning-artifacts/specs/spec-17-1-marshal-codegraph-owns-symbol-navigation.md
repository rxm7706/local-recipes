---
title: 'Marshal codegraph owns symbol navigation'
type: 'docs'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

One navigation owner: Marshal `codegraph.db` for symbols. Graphify
`code:` stays an AST/report extra, not the nav API.

## Boundaries & Constraints

**Always:** write session sentences outside the `bmad:context` block;
unit test fails if they leave `AGENTS.md`; Cursor rule stays consistent
(force-add).

**Never:** delete graphify; default-recall `code:`; `codegraph install
--target claude`; nightly-graphify `recipes/` or repo root; flip Epic 44.

</intent-contract>

## Spec Change Log

- **2026-09-13:** minted and implemented for Story 17.1 /
  `spec-scribe-code-navigation-owner` CAP-1.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `17-1-marshal-codegraph-owns-symbol-navigation: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
