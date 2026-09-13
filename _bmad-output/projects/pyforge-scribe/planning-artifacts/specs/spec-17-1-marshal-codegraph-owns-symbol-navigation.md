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
