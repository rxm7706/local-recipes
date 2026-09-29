---
title: The nightly graph still knows the code
type: dream
owner: scribe
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-scribe]]** on 2026-09-17 (one-chain-per-station scribe fold).

# The nightly graph still knows the code

## The Dream

The knowledge graph this repo already compiles every night should still contain
the code surface in the morning. Today it does not. `scribe graph compile` is a
full rebuild. The graphify ingest that writes `code:` nodes is an opt-in extra.
The 02:30 trigger runs the lean compile, so every scheduled night throws away
whatever `scribe index build` wrote the day before.

Worse, the extra cannot run against the graphifyy this estate actually
installs. After `collect_files` loads `graphify.extract` the package attribute
is the **submodule**, and `graphify.extract(...)` raises `TypeError`. The
official `scribe index build` verb in the `pyforge-scribe` env exits 2 for
missing `graphifyy`; even when that package is on `PYTHONPATH`, the call dies
on the submodule shadow.

The Dream is one scheduled rebuild that keeps memory, memlogs, git, retros,
transcripts, **and** the station-package AST graph in the same store — without
turning every interactive `scribe graph compile` into a 60-second ingest, and
without a second graph product.

## What it looks like when real

- `scribe index build` against `src/shared/packages/` completes through the
  GraphStore persist port on the real `graphify` package.
- The 02:30 trigger's compile keeps `code:` nodes. A morning `graph.json` is
  not smaller than last night's by thirty thousand nodes.
- An interactive compile with `SCRIBE_GRAPHIFY_EXTRA` unset still skips the
  extra (air-gap default). An operator can still force the extra off on the
  trigger with an explicit `0`.

## Constraints / Non-goals

- No parallel store. Code nodes write through `open_graph_store`, same as
  Story 6.1.
- No foundry-root `graphify-out/`.
- Not a GitHub Actions workflow (Epic 8 HARD boundary).
- Not a new GraphStore engine.

## Kinships

[[pyforge-scribe]] (owner; CAP-2 already names the optional seventh graphify
surface) · [[scribe-mines-raw-session-transcripts]] (the last compile-surface
currency gap) · [[pyforge-unifying-strategy]] (realization gate: built is not
in effect) · [[deck-family-currency]] (Herald owns `facts.yaml` derivation;
Scribe compiles those ledgers as `doc` nodes — never the presentations/ export
tree)

## Realization log

- **2026-09-13** — Dream captured and specified the same morning. Spec
  `spec-scribe-graphify-nightly-currency` (`ready`, CAP-1/CAP-2) lives under
  pyforge-scribe. Decomposed as Epic 8 Story 8.2; durable story spec
  `spec-8-2-the-nightly-compile-keeps-the-graphify-code-surface.md`. Sprint
  tracking regenerated via `sprint_plan.py generate`; ledger key
  `8-2-the-nightly-compile-keeps-the-graphify-code-surface` is `done`.
- **2026-09-13** — Operator: fact ledgers should be added. CAP-3 + Story 8.3
  (`spec-8-3-herald-fact-ledgers-join-the-compile.md`); compile reads
  `presentations/<slug>/facts.yaml` as `doc` nodes. Kinship
  `deck-family-currency`.
