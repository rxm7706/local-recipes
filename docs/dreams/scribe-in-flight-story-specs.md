---
title: The story you are on is in the graph; the ones you finished are not
type: dream
owner: scribe
status: specified
---

# The story you are on is in the graph; the ones you finished are not

## The Dream

Folder `SPEC.md` files already compile when they are `ready` or
`in-progress`. Per-story specs — the atomic SM→dev handoff — do not.
An agent mid-story asking “what does 10.1 actually bind?” gets silence,
or would get every historical `spec-2-1-…` if we globbed the folder.

The Dream is **in-flight only**. A story spec joins the compile as `doc`
when that project's tracked sprint ledger says the story is
`ready-for-dev`, `in-progress`, or `review`. Frontmatter on those files
is stale (`ready-for-dev` on stories that have been `done` for months).
The ledger is the filter. Done and backlog stay out.

## What it looks like when real

- A ledger row `10-1-…: in-progress` plus
  `planning-artifacts/specs/spec-10-1-….md` becomes one `doc:` node.
- The same file with ledger `done` produces no node, even if frontmatter
  still says `ready-for-dev`.
- A project with no ledger, or every story `done`, compiles zero
  story-spec nodes and no warning.

## Constraints / Non-goals

- Do not ingest the historical corpus. Do not use frontmatter as the
  in-flight oracle.
- Do not compile folder `SPEC.md` here (already CAP-3).
- Do not compile `prd.md` / `epics.md` bodies (CAP-7, parked).

## Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]]

## Realization log

- **2026-09-13** — Hoisted parked CAP-6. Spec
  `spec-scribe-in-flight-story-specs`; Epic 10 Story 10.1.
- **2026-09-13** — CAP-1 realized in Story 10.1: ledger-filtered compile.
