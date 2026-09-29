---
title: Dispatch cites the same numbers the poster already shows
type: dream
owner: scribe
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-scribe]]** on 2026-09-17 (one-chain-per-station scribe fold).

# Dispatch cites the same numbers the poster already shows

## The Dream

Herald already derives `presentations/<slug>/facts.yaml`. Scribe already
compiles each ledger as a `doc:` node. An unscoped `scribe recall` can hit
those citations. Marshal planning-graph retrieve cannot: `--scope <slug>`
admits only `_bmad-output/projects/<slug>/`, so the fact ledger sits
outside the candidate list.

The Dream is **identity visibility**. When retrieve asks for
`pyforge-scribe`, that project's own `presentations/pyforge-scribe/facts.yaml`
is a legal citation — not every deck, not the export tree, not a second
`--facts` flag that Marshal would have to learn.

> A number the poster already shows should be recallable under the same
> slug the loop is scoped to.

## What it looks like when real

- `scribe recall "…" --scope pyforge-scribe` can cite
  `presentations/pyforge-scribe/facts.yaml`.
- `--scope pyforge-scribe` still excludes `presentations/pyforge-warden/facts.yaml`
  and every path that is not that project's planning tree or that one ledger.
- Marshal `context retrieve` keeps passing `--scope` only. No new argv.

## Constraints / Non-goals

- Identity slug only. No alias table (`pyforge-unifying-strategy` /
  `pyforge-genesis` stay unscoped-only until a later mapping CAP).
- Do not widen `--scope` to `presentations/` or the export tree.
- Do not change compile. Do not replace Herald as the ledger owner.

## Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[deck-family-currency]] · [[marshal-token-economy]]

## Realization log

- **2026-09-13** — Hoisted parked CAP-10 from
  `spec-scribe-knowledge-layers/later-caps.md`. Spec
  `spec-scribe-marshal-fact-visibility`; Epic 9 Story 9.1.
- **2026-09-13** — CAP-1 realized in Story 9.1: identity citation rule in
  `recall.py`.
