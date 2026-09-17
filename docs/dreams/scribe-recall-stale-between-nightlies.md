---
title: Yesterday's graph withholds today's commit
type: dream
owner: scribe
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-scribe]]** on 2026-09-17 (one-chain-per-station scribe fold).

# Yesterday's graph withholds today's commit

## The Dream

A full rebuild flags stale only when the source commit is newer than
that compile's clock. After 02:30 the stored `stale` bit stays false.
Someone lands a decision at noon. Recall still serves last night's
node as current until the next nightly.

The Dream is **recall-time stale**. The store remembers `compiled_at`.
Recall withholds a current node whose source file has a git commit
authored after that stamp. The next nightly rewrite resets the stamp.

## What it looks like when real

- `graph.json` carries `compiled_at`.
- After a post-compile commit to a cited file, `scribe recall` does
  not return that node until the graph is compiled again.
- Commit and transcript nodes stay exempt (no git-trackable file).
- A store without `compiled_at` (older file, PG/plane) keeps today's
  compile-time bit only.

## Constraints / Non-goals

- Do not re-run a full compile on every recall.
- Do not git-log every node up front — check candidates at selection.
- Do not change compile-time CAP-1.

## Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]]

## Realization log

- **2026-09-13** — Hoisted parked CAP-9. Spec
  `spec-scribe-recall-stale-between-nightlies`; Epic 11 Story 11.1.
- **2026-09-13** — CAP-1 realized in Story 11.1.
