---
spec: scribe-recall-stale-between-nightlies
status: ready
owner-dream: docs/dreams/scribe-recall-stale-between-nightlies.md
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-recall-stale-between-nightlies.md
  - ../spec-scribe-knowledge-layers/later-caps.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — Recall-time stale between nightlies

## Why

Compile-time stale is honest at 02:30 and then frozen. A commit after
that compile is still served as current until the next rebuild.

## Capabilities

- **CAP-1**
  - **intent:** The compiled store remembers when it was built. Recall
    withholds a current node whose git-trackable source has a commit
    authored after that stamp.
  - **success:** After compile, a new commit touching a cited file makes
    `answer()` skip that node. Reloading `graph.json` still knows
    `compiled_at`. Commit and transcript nodes stay eligible.

## Constraints

- Persist `compiled_at` on the flat-file artifact. Do not add a
  GraphStore Protocol method this story.
- Missing `compiled_at` degrades to the stored `stale` bit only.
- Check at candidate selection, not a pre-pass over every node.
- Compile-time CAP-1 rule is unchanged.

## Non-goals

- PostgreSQL / plane `compiled_at` columns.
- Recompiling the graph on recall.

## Success signal

A fixture compiled, then committed again, returns `no grounded answer`
for that node's unique tokens until the next compile.

## Assumptions

- Nightly default store is `FlatFileGraphStore`.
