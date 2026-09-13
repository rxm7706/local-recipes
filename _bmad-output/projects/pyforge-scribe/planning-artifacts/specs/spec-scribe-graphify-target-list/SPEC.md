---
spec: scribe-graphify-target-list
status: ready
owner-dream: docs/dreams/scribe-graphify-target-list.md
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-graphify-target-list.md
  - ../spec-scribe-knowledge-layers/later-caps.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — Named graphify targets, never recipes or repo root

## Why

Story 8.2 kept the graphify extra on the nightly rebuild. The ingest
target is still one folder. Host code and factory scripts are the
named gap. A bigger default (`.` or `recipes/`) blows the cost bound
that extra was gated for.

## Capabilities

- **CAP-1**
  - **intent:** When `ingest_repo()` is called with no `target`, walk
    this list and ingest each directory that exists:
    `src/shared/packages`, `src/platform`, `scripts`.
  - **success:** Extra-on compile (and `scribe index build` with no
    `--target`) writes `code:` nodes from those trees. A present
    `recipes/` directory is not ingested. Missing optional list
    entries produce no warning. Zero list entries (or a missing
    explicit `--target`) warn once and return no nodes. Extra-off
    compile is unchanged.

## Constraints

- The default list is the contract — do not derive it from a glob of
  `src/` or the repo root.
- `DEFAULT_GRAPHIFY_TARGET` remains `src/shared/packages` for
  single-path APIs (`index report`, explicit `--target` default help).
- Import graphifyy only after at least one target exists.
- Still off by default (`SCRIBE_GRAPHIFY_EXTRA`).

## Non-goals

- `recipes/`, repo-root ingest, cocoindex-in-compile.
- CAP-14 (one navigation owner).
- Turning the extra on for interactive compile.

## Success signal

A fixture with packages, platform, scripts, and recipes present, extra
on, writes `code:` citations under the first three paths and none
under `recipes/`.

## Assumptions

- `src/platform/` is the Django host; `scripts/` is the factory CLI
  tree. Both may be absent in a tmp fixture.
