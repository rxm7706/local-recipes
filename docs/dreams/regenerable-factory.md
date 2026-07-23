---
title: Regenerable factory — every line of code under a spec it can be rebuilt from
type: dream
owner: marshal
status: seeded
---

# Regenerable factory — every line of code under a spec it can be rebuilt from

## The Dream

No orphan code. Every realized surface in the repo — even the ones that
shipped before the Dream-first model existed — gets its chain **backfilled**:
Dream → PRD (where product-scope) → spec → code, so the factory can *generate
and change any code* through idea → spec → BMAD, never by hand-editing outside
the contract. The spec stops being a build record and becomes the **living
change-surface**: to alter behavior you alter the spec and re-derive.

The proof of the dream is the **regeneration drill**: pick a governed module,
delete it, and rebuild it from its spec alone — the result passes the same
gates the original did.

And because every file maps to a contract, **drift checks run on all code**:
an out-of-band edit to any governed surface is detected, named, and reconciled
— the two-layer loop (cheap deterministic detector + BMAD skills as
reconciler) that already keeps the factory's own artifacts honest, generalized
repo-wide.

## What is real (the prototype already runs)

- **The sync loop** — `bmad-drift-check` (pins, counts, coverage
  completeness: *every project file must be classified*, baseline-vs-live
  surface change) + reconciler skills (`bmad-document-project`,
  `bmad-generate-project-context`, `bmad-correct-course`) + re-stamped
  baselines. This Dream is that loop, applied to everything.
- **The transformer** — `bmad-spec` distills brownfield code + docs into the
  five-field kernel with stable CAP-IDs and an append-only memlog; re-derives
  on update instead of hand-patching. Piloted on [[design-code-bridge]].
- **The map** — 24 Dreams, no-straggler policy: every shipped surface already
  traces to a Dream; what's missing is the spec layer beneath the realized
  ones ([[packaging-factory]], [[enterprise-airgap]], [[modernist-identity]],
  [[fleet-stewardship]], [[factory-console]] have no BMAD spec;
  [[pyforge-marshal]] and [[fleet-stewardship]] lean on legacy Tier-1 specs).

## The frontier

- **Backfill waves** — brownfield-`bmad-spec` each realized Dream, smallest
  first as the dogfood pilot ([[factory-console]]), PRD-scope only where the
  surface is a product (the CFE skill under [[packaging-factory]]).
- **The surface map** — each backfilled spec declares the code paths it
  governs; a repo-wide checker enforces (a) coverage: every tracked source
  file belongs to some spec's surface, (b) drift: a governed file changed
  without its spec/memlog moving → finding, reconcile or re-derive.
- **The CI gate** — surface check joins `llms-full-check` / `bmad-drift-check`
  as a red-on-drift detector.
- **The drill** — one successful regeneration from spec alone, as the
  program's success signal.
- Decks stay a communication decision ([[pyforge-herald]]'s backlog —
  [[packaging-factory]] first); they proclaim the chain, they don't gate it.

## Kinships

[[pyforge-genesis]] (the operating model this completes — brownfield adoption
implies backfill) · [[pyforge-marshal]] (BMAD executes every change) ·
[[pyforge-warden]] (drift gate temperament: never false-green) ·
[[agent-portability]] (the spec kernel is what makes regeneration
framework-neutral) · [[ecosystem-crew]].

## Realization log

- **2026-07-23** — doctrine decided (user call, inverting the
  "no retroactive ceremony" default): backfill PRDs/specs for realized work
  so any code is changeable through the pipeline; Dream seeded.
