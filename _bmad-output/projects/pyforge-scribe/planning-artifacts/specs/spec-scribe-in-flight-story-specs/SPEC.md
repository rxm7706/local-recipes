---
spec: scribe-in-flight-story-specs
status: ready
owner-dream: docs/dreams/scribe-in-flight-story-specs.md
surface:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py
companions: []
sources:
  - ../../../../../../docs/dreams/scribe-in-flight-story-specs.md
  - ../spec-scribe-knowledge-layers/later-caps.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# SPEC — In-flight story specs only

## Why

The story an agent is implementing is the SM→dev contract. Folder SPECs
already compile. Per-story files do not. A filename glob would drown
recall in every landed `spec-N-M`. Frontmatter on those files is not
kept current. The tracked sprint ledger is.

## Capabilities

- **CAP-1**
  - **intent:** Compile each in-flight story spec as one `kind=doc` node.
    In-flight means that project's `sprint-status-ledger.yaml` marks the
    matching story `ready-for-dev`, `in-progress`, or `review`.
  - **success:** `spec-<n>-<m>-<rest>.md` compiles iff the ledger key
    `<n>-<m>-<rest>` is one of those three statuses. A `done` or
    `backlog` row, a missing ledger, or a missing file yields no node
    and no warning. Stale `status: ready-for-dev` frontmatter on a
    `done` story does not compile it.

## Constraints

- The ledger is the only in-flight oracle. Do not read story-spec
  frontmatter to decide inclusion.
- Filename stem after `spec-` is the ledger key.
- Folder `SPEC.md` stays on the existing CAP-3 surface.
- Same persist port and `_node_from_text_file` path as other `doc` nodes.

## Non-goals

- Historical corpus, `backlog` rows, `prd.md` / `epics.md` bodies.
- Repairing stale story-spec frontmatter.

## Success signal

A compile against a fixture with one in-progress story spec and one
done story spec (both frontmatter `ready-for-dev`) writes exactly the
in-progress citation.

## Assumptions

- `planning-artifacts/sprint-status-ledger.yaml` is the tracked twin
  `sprint-ledger-sync` writes.
