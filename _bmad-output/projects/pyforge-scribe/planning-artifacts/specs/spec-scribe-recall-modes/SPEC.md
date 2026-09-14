---
spec: scribe-recall-modes
status: ready
owner-dream: docs/dreams/scribe-recall-modes.md
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-recall-modes.md
  - ../spec-scribe-knowledge-layers/later-caps.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — Recall modes, not only `--kind`

## Why

`--kind` is the low-level bag. Portal and agents should name a
surface — planning, memory, or code — without composing kind tokens.
Lexical vs semantic ranking already occupies the internal `mode=`
argument; the user-facing flag is still `--mode`.

## Capabilities

- **CAP-1**
  - **intent:** `scribe recall` accepts `--mode planning|memory|code`.
    `planning` → `{doc, memlog}`; `memory` → `{memory}`; `code` →
    `{code}`.
  - **success:** Those bags are exclusive with `--kind` (exit 2).
    Unknown `--mode` exits 2. Neither flag keeps the CAP-4 default
    bag (omits `code`). `--semantic` still selects ranking, not this
    bag.

## Constraints

- Do not overload `answer(..., mode=)` — that stays `lexical` /
  `semantic`. Resolve the surface bag to `kinds` before scoring.
- Portal argv is unchanged this story.
- Default recall still omits `code` unless `--mode code` or
  `--kind code`.

## Non-goals

- later-caps:CAP-14 nav owner. Semantic as default. Portal redesign.

## Success signal

A store with a matching `doc` and a matching `memory` node: default
recall may hit either; `--mode planning` returns the `doc`;
`--mode memory` returns the `memory`. `--mode planning --kind doc`
exits 2.

## Assumptions

- Planning novels are already `doc` pointers or SPECs; memlogs are
  the other planning-adjacent kind.
