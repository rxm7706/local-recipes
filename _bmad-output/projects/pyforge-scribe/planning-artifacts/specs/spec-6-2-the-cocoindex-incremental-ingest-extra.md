---
title: 'The cocoindex incremental ingest extra (Story 6.2, Epic 6)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-6-1-the-graphify-ingest-extra-and-its-move-list-verbs.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md
warnings:
  - Marshal Story 28.8 consumes this extra for epic-context/continuity freshness (by scribe
    grammar only) and the foundry cutover consumes it for move-list refresh when Mason 12.x
    or Atlas 20.x land. Declare the refresh grammar in the scribe SKILL.md.
---

<intent-contract>

## Intent

**Problem:** Story 6.1's derived artifacts (graph, move list) and marshal's derived
planning context go stale as `main` moves; recomputing them wholesale per change is exactly
the waste the token-economy spec measures. `cocoindex` (≥1.0.20, Apache-2.0, active in
pixi) is the estate's incremental-derivation engine and is scheduled "bind now" — with no
story building the binding.

**Approach:** Bind cocoindex as an **optional `compile_surface` extra** that maintains
declared derived artifacts incrementally: delta re-index on each commit / source change,
rewriting only the derived rows whose sources changed. Outputs write through the persist
port or land as derived gitignored artifacts. cocoindex is the freshness *engine* — never a
GraphStore engine, never a store of record (Grounding 2026-08-30). Extras off by default
(air-gap).

## Acceptance Criteria

- Given the extra off (default), when a compile runs, then behavior is unchanged — proven
  by an off-mode test.
- Given the extra on, when two consecutive runs see unchanged sources, then zero recompute
  occurs; when exactly one source changed, then exactly one refresh occurs touching only
  the affected derived rows.
- Given the outputs, when inspected, then they write through the persist port or land as
  derived gitignored artifacts — no cocoindex-owned store of record.
- Given the implementation, when inspected, then no `cocoindex.serve` MCP product exists,
  no `@coco.fn` lineage surface is introduced (OpenLineage rides CAP-8), and cocoindex is
  imported only inside the extra adapter.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-scribe/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-scribe` only — never `scripts/bmad-switch`. Ledger
key `6-2-the-cocoindex-incremental-ingest-extra`. AD-1/AD-2/AD-6 bind (extras off by
default; write boundary; append-only mutation path).

**Block If:** A change would mint a second store-of-record, a long-running daemon scribe
doesn't own, or alter the `GraphStore` protocol.

**Never:** `cocoindex.serve` as an MCP product. `@coco.fn` as the lineage religion. A
mem0 binding (out of this epic). Publishing freshness as a PR-gate verdict.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` (compile_surface fan-in — extra hook point)
- cocoindex extra adapter (new, e.g. `pyforge/scribe/extras/cocoindex_flow.py`; optional dependency, active in pixi)
- Story 6.1's graphify extra artifacts (first incremental consumers: graph + move list)
- `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` (declare the refresh grammar)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(off-mode unchanged, zero-recompute on unchanged sources, exactly-one-refresh on one edit,
no-store-of-record, adapter-only import). Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 6.2. Use cocoindex's flow/dataflow model for change detection rather
than hand-rolled hash checks — that is the point of binding the engine. The declared derived
artifacts start with Story 6.1's (graph, move list); marshal Story 28.8 registers its
epic-context/continuity distills against the same grammar later — this story must not
special-case marshal, only expose the generic "declare sources → derived artifact" surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass, including this story's own new/updated test coverage.

## Spec Change Log

- 2026-08-30: drafted as Epic 6 preflight (unifying-strategy stack.md "bind now" rows; pairs with marshal Epic 28's token-economy consumers)
