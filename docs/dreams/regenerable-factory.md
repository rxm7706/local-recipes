---
title: Regenerable factory — every line of code under a spec it can be rebuilt from
type: practice
owner: marshal
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `regenerable-factory`).

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
  five-field Spec with stable CAP-IDs and an append-only memlog; re-derives
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
[[agent-portability]] (the Spec is what makes regeneration
framework-neutral) · [[pyforge-charter]].

## Realization log

- **2026-07-23** — doctrine decided (user call, inverting the
  "no retroactive ceremony" default): backfill PRDs/specs for realized work
  so any code is changeable through the pipeline; Dream seeded.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Currency, status unchanged
  (`realized`). The **drift half is live**: `gather_spec_surface` over the tree returns 6 entries, 5
  informational plus *"every tracked file governed or allowlisted; no drift"*. The **drill half has
  no live oracle**: the 2026-07-23 PASS (`spec-factory-console/drill-evidence.md`) was against
  `generate.py`, and `spec-factory-console/SPEC.md:78` now records *"regeneration drill is historical
  — `generate.py` is gone."* So the estate holds no *re-runnable* proof of this Dream's own central
  claim. The successor drill is named in the Unifying Dream (§ *What the Foundry becomes*) as
  foundry's own construction, rebuild-with-the-archive-as-oracle — **no new drill is owed in
  local-recipes**. Batch: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
