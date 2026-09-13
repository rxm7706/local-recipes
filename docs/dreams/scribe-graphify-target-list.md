---
title: The code map covers the host and factory scripts, not the recipe warehouse
type: dream
owner: scribe
status: specified
---

# The code map covers the host and factory scripts, not the recipe warehouse

## The Dream

Nightly extra-on compile already keeps `code:` nodes for
`src/shared/packages/`. Agents asking about the Django host or a pixi
helper still miss, because those trees were never on the list. Widening
the default to the repo root — or to `recipes/` — recreates the cost
bound Story 3.3 / 8.2 exist to hold.

The Dream is an **explicit target list**: station packages, the platform
host, and `scripts/`. Missing optional dirs are silent. `recipes/` and
`.` stay off the list.

## What it looks like when real

- Extra-on compile ingest walks `src/shared/packages/`, `src/platform/`,
  and `scripts/` when those directories exist.
- A fixture with `recipes/` present still produces no `code:` citation
  under `recipes/`.
- `scribe index build` with no `--target` uses the same list.
- An explicit `--target` stays one path.
- Extra-off compile is unchanged (zero `code:` nodes).

## Constraints / Non-goals

- Do not add `recipes/` or the repo root to the default list.
- Do not turn the extra on by default.
- Do not decide CAP-14 (graphify `code:` vs `codegraph.db`).

## Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[scribe-graphify-nightly-currency]]

## Realization log

- **2026-09-13** — Hoisted parked CAP-8. Spec
  `spec-scribe-graphify-target-list`; Epic 15 Story 15.1.
