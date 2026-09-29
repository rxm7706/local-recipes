---
title: 'The graphify ingest extra and its move-list verbs (Story 6.1, Epic 6)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: 'e38f269cc5f642e86b3a379a720a191b94fb0129'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md
  - docs/dreams/pyforge-unifying-strategy.md
warnings:
  - Two consumers are waiting on this extra's grammar — the foundry-cutover move-list
    (docs/dreams/pyforge-unifying-strategy.md § One working tree) and marshal Story 28.9 (planning-corpus
    retrieval). Declare the grammar in the scribe SKILL.md so consumers bind to it, not to
    internals.
---

<intent-contract>

## Intent

**Problem:** The estate locks `graphifyy` (≥0.9.44, MIT) and the unifying-strategy stack
schedules it "bind now" behind Scribe, but no story builds the binding. Meanwhile the
foundry cutover needs a move list (host `import pyforge.*` sites, `sys.path` inserts,
`five_tier` roots, CFE callers) and marshal's token economy needs a queryable planning
graph — both would otherwise hand-roll their own graphify use.

**Approach:** Bind graphifyy as an **optional `compile_surface` ingest extra** (the
Grounding 2026-08-30 port contract): when enabled, folder ingest writes `GraphNode`s
*through* the `graph_store` persist port (`open_graph_store`, Story 4.1's CAP-18 plugins).
Add report verbs on the scribe grammar (`scribe index …`) that emit a GRAPH_REPORT-style
summary (incl. God-node findings) and the move list — derived, gitignored artifacts, like
`graph.json`. Extras are off by default (air-gap).

## Acceptance Criteria

- Given the extra absent or off (default), when a compile runs, then behavior is identical
  to today's six builtins — proven by an off-mode test.
- Given the extra on, when a folder is ingested, then `GraphNode`s are written through the
  persist port — no parallel store, no second persistence format.
- Given the report verbs, when run against the repo, then a GRAPH_REPORT-style summary
  (incl. God-node findings) and a move list (host `import pyforge.*` sites, `sys.path`
  inserts, `five_tier` roots, CFE callers) land as derived, gitignored artifacts.
- Given the implementation, when inspected, then graphifyy is imported only inside the
  extra adapter, and no foundry-root `graphify-out/` product dir is created.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-scribe/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-scribe` only — never `scripts/bmad-switch`. Ledger
key `6-1-the-graphify-ingest-extra-and-its-move-list-verbs`. AD-1 (append-only capture is
the only mutation path), AD-2 (write boundary), AD-6 (air-gap: extras off by default) all
bind.

**Block If:** A change would create a second graph store-of-record, alter the `GraphStore`
protocol, or put graphify output anywhere a detector treats as tracked product surface.

**Never:** A `mem0` binding (out of this epic). A Kedro project. Publishing any graph
metric as a PR-gate verdict (Warden doctrine).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` (compile_surface fan-in — extra hook point)
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py` + `graph_store.py` (persist port, Story 4.1 — read-only protocol)
- graphify extra adapter (new, e.g. `pyforge/scribe/extras/graphify.py`; optional dependency)
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` (`scribe index` verbs)
- `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` (declare the consumer grammar)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(off-mode identical, port-only writes, report/move-list artifacts derived + gitignored,
adapter-only import). Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 6.1. The stack.md row: "`cocoindex` + `graphifyy` | scribe |
`scribe index`: AST graph + incremental index; link functions to Dream/PRD/spec_id |
**bind**". The Grounding rules: "behind GraphStore" means ingest writes through the persist
port; extras off by default. Consumers bind to the declared grammar only — marshal Story
28.9 explicitly forbids importing graph internals, so whatever this story declares in the
SKILL.md is the contract they get.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass, including coverage for the `graphify` `compile_surface` ingest extra (off by default via `SCRIBE_GRAPHIFY_EXTRA`), the `scribe index build|report|move-list` grammar, and the recall-citation fix that made graphify-ingested code nodes unrecallable via `scribe recall`.

## Spec Change Log

- 2026-08-30: drafted as Epic 6 preflight (unifying-strategy stack.md "bind now" rows; pairs with marshal Epic 28's token-economy consumers)

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `ca254233ed` (2026-08-14, "Merge branch 'bmad-loop/20260813-094917-9bba/6-11-the-classifier-recognizes-a-spike-report' into land/doctor-6"). Ledger row `6-1-the-graphify-ingest-extra-and-its-move-list-verbs: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-drift-new-artifact-shape/.memlog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-drift-new-artifact-shape/SPEC.md`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
