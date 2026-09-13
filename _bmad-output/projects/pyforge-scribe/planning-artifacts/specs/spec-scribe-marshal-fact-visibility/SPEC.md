---
spec: scribe-marshal-fact-visibility
status: ready
owner-dream: docs/dreams/scribe-marshal-fact-visibility.md
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-marshal-fact-visibility.md
  - ../spec-scribe-knowledge-layers/later-caps.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — Scoped recall admits the project's own fact ledger

## Why

Herald fact ledgers already compile as `doc:` nodes. Marshal retrieve scopes
`scribe recall` to `_bmad-output/projects/<slug>/`, so those citations never
enter the candidate list. Dispatch and the poster do not share a number.

## Capabilities

- **CAP-1**
  - **intent:** A scoped recall for project slug `S` can retrieve the Herald
    fact ledger whose path is exactly `presentations/S/facts.yaml`, in
    addition to that project's planning tree.
  - **success:** `answer(..., scope="pyforge-scribe")` may return a current,
    non-stale node whose citation is `presentations/pyforge-scribe/facts.yaml`.
    The same call never returns `presentations/pyforge-warden/facts.yaml` or
    any other `presentations/` path. Unscoped recall is unchanged.

## Constraints

- Identity only: the presentation directory name must equal `--scope`.
- `--scope` still excludes commits, transcripts, code paths, and other
  projects' planning trees.
- No new CLI flag. Marshal keeps passing `--scope` only.
- Compile and Herald ownership stay as Story 8.3 left them.

## Non-goals

- An alias table that maps `pyforge-unifying-strategy` or `pyforge-genesis`
  into every station scope.
- Widening `--scope` to `presentations/` or the deck export tree.
- Changing `compile_graph` or adding `--facts`.

## Success signal

`scribe recall "…" --scope pyforge-scribe` can cite that station's fact
ledger. The same command cannot cite another station's ledger.

## Assumptions

- Station decks live at `presentations/<project-slug>/facts.yaml`.
- Cross-cutting decks remain visible only to unscoped recall until a later
  mapping CAP.
