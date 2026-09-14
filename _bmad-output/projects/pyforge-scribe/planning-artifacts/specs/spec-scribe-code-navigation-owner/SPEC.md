---
spec: scribe-code-navigation-owner
status: ready
owner-dream: docs/dreams/scribe-code-navigation-owner.md
surface:
  - AGENTS.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_navigation_owner.py
  - .cursor/rules/scribe-recall.mdc
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-code-navigation-owner.md
  - ../spec-scribe-knowledge-layers/later-caps.md
open_questions: []
updated: "2026-09-13"
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — One navigation owner

## Why

Parked later-caps:CAP-14 left graphify `code:` and Marshal
`codegraph.db` as peer answers to “where is this symbol?”. Agents
re-read files. A foundry move would copy the split.

## Capabilities

- **CAP-1**
  - **intent:** Session instructions and the graphify extra state that
    Marshal codegraph owns symbol navigation; Scribe `--mode code` is
    an AST/report surface, not nav.
  - **success:** `AGENTS.md` outside `bmad:context` names codegraph as
    the nav owner and forbids using `scribe recall --mode code` for
    symbols. The graphify module docstring says it is not the nav
    API. A unit test fails if those AGENTS sentences are removed.

## Constraints

- Do not delete graphify.
- Default recall still omits `code:`.
- Do not run `codegraph install --target claude`.
- Do not nightly-graphify `recipes/` or the repo root.

## Non-goals

- Unifying Strategy canopy:CAP-14 (pgvector / semantic recall) — steward 49.7.
- Flipping Epic 44 `blocked` rows.

## Success signal

An agent following `AGENTS.md` uses codegraph for symbols and Scribe
recall for decisions.

## Assumptions

- Loop-home index is `codegraph.db`; the recipe is `recipes/codegraph/`.
