---
title: 'Story 20.5: Port the remaining nineteen Vizro pages (CAP-7)'
type: 'feature'
created: '2026-08-27'
status: 'ready'
updated: '2026-08-27'
baseline_revision: 'cc8b3b2b1c09d6e56a5aebf752e25f507c846571'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `dashboard/app.py::PAGE_INVENTORY` ships only 9 of the 28 target pages today
(`feedstock-health`, `my-feedstocks`, `estate-cache`, `staleness-report`, `query-atlas`,
`detail-cf-atlas`, `behind-upstream`, `whodepends`, `factory-status`) — the live-confirmed core
plus factory-status. The remaining 19 are CIS-two-spine-deferred (DW-D2-1). Separately, DW-D2-3
records that no one has ever visually/structurally verified the rendered dashboard's
semantic-HTML/ARIA properties in a browser — the `dashboard-dryrun` gate only builds the
Dashboard OBJECT offline and asserts structure; a first `dashboard-serve` visual pass on
2026-08-26 confirmed `factory-status` fully live but found `feedstock-health` degrading
honestly ("unavailable — backing file not found:
data/primary/core_feedstock_health/core_feedstock_health.parquet") in a fresh checkout — the
§2.1 semantic-HTML/ARIA navigation check itself remains unbuilt.

**Approach:** this story is explicitly GATED on BOTH Story 20.3 (materialized composed stores)
AND Story 20.4 (the CIS two-spine specs) per `epics.md`. Once both land, port the remaining 19
of 28 CLI pages against the two spine design specs, routed through BSL exactly like the existing
9 pages (`dashboard/data.py`'s `_bsl_query_or_empty` seam), reading either the canonical
per-pipeline datasets directly or the Story 20.3 plane/composed store as the fast path (the
`query-plane-catalog` ruling's per-call choice). Extend the existing
`test_all_expected_pages_present_with_stable_id_and_title` style of gate to all 28 pages. Build
the still-missing DW-D2-3 residual: the §2.1 semantic-HTML/ARIA browser-agent navigation check,
plus a data-present visual pass through `pixi run -e local-recipes dashboard-serve`
(`scripts/dashboard_serve.py`) once the pipelines from Story 20.3 have actually run. Vizro stays
outside the Canopy/Django host — this story must not add a Vizro import to any Django-side
module.

## Acceptance Criteria

Lifted verbatim from `epics.md` (Story 20.5):

> **Given** the two-spine specs (S-20.4 — this story is GATED: the DW-D2-1 CIS gap still blocks
> as of 2026-08-27) and the materialized stores (S-20.3) **When** the remaining 19 of 28 CLI
> pages port against the spines — BSL-routed, reading canonical datasets or the plane per the
> `query-plane-catalog` ruling's per-call choice **Then** all 28 pages render with stable
> ids/titles **And** the DW-D2-3 residual executes: the §2.1 semantic-HTML/ARIA browser-agent
> navigation check plus a data-present visual pass through
> `pixi run -e local-recipes dashboard-serve` (`scripts/dashboard_serve.py`, the DW-D2-3
> serve entrypoint, evidence-update 2026-08-26) **And** Vizro stays outside the Canopy host
> (this file's Canopy obligation 3) and Django imports no Vizro.

## Boundaries & Constraints

**Always:** `BMAD_ACTIVE_PROJECT=pyforge-atlas`; ledger key
`20-5-port-the-remaining-nineteen-vizro-pages`; **this story is GATED on Story 20.3 AND Story
20.4 both landing first — it must NOT be dispatched or implemented before both are done**; every
new page routes through the D1 BSL models via `dashboard/data.py`'s `_bsl_query_or_empty` seam,
exactly like the existing 9 pages — no raw SQL, no re-implemented metric arithmetic
(`semantic/models.py`/`semantic/metrics.py` own the formulas); every page carries a stable `id`
and `title` in `PAGE_INVENTORY`, extending the existing
`test_all_expected_pages_present_with_stable_id_and_title` gate to all 28 entries; Vizro stays
OUTSIDE the Canopy/Django host per the unifying-strategy SPEC's "Lane 3 is Vizro over BSL over
the plane... Do not import Kedro or Vizro into Django views."

**Block If:** Story 20.3 or Story 20.4 has not actually landed (verify via the sprint ledger
before starting, not by assumption) — report and stop; do not partially port pages against an
incomplete spine or an unmaterialized store, since the whole point of the gate is that both
preconditions are real.

**Never:** expand the page set before S-20.3 and S-20.4 both land (this is the DW-D2-1 rule
Story 20.4 itself restates); import `vizro`/`vizro_ai` into any `src/platform/` Django module;
re-implement a BSL metric already declared in `semantic/metrics.py`; modify the sealed-seven
pipelines or the Story 20.3 named pipeline's own node logic (only consume its output dataset).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | S-20.3 + S-20.4 both landed; all 28 pages built | dashboard builds offline with 28 stable id/title pages; `dashboard-dryrun` gate passes | none |
| GATE_NOT_MET | S-20.3 or S-20.4 not yet landed | story does not proceed — reports the missing precondition | never silently ports a partial page set |
| VISUAL_PASS_NO_DATA | `dashboard-serve` run before the Story 20.3 pipelines have executed | a grounded page degrades honestly (matches existing `_bsl_query_or_empty` / DW-D2-3 "backing file not found" behavior) | never fabricated rows |
| ARIA_CHECK_FAILS | the new §2.1 semantic-HTML/ARIA navigation check finds a violation on a ported page | check fails, naming the offending page/element | surfaced as a real gate failure, not swallowed |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` — `PAGE_INVENTORY`
  (lines 63-109, currently 9 `PageDef` entries), `build_dashboard()` (lines 216-303),
  `_data_page`/`_shell_page`/`_legibility_card` helpers (lines 124-165) — the exact pattern every
  new page must follow; `LIVE_CONSUMER_CLIS` (lines 41-49) is the existing live-confirmed-first
  ordering to extend, not replace.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py` — `_bsl_query_or_empty`
  (lines 70-99) is the ONE seam every new page's loader must go through; `default_data_root()`
  (lines 51-67) for resolving new Parquet paths; the 19 new loaders are new functions in this
  module following `load_feedstock_health`/`load_staleness`/etc.'s exact shape.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/models.py` and
  `semantic/metrics.py` — the BSL models/metric formulas the 19 new pages must bind to; new
  models likely need to be added here for CLIs with no existing BSL model yet (`behind-upstream`
  and `whodepends` are already flagged `no-bsl-shell` in `PAGE_INVENTORY` for exactly this
  reason — their BSL models don't exist yet either).
- `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py` —
  `test_all_expected_pages_present_with_stable_id_and_title` (line 63) and
  `test_registered_data_functions_are_callable_and_return_frames` (line 226) are the existing
  gates to extend from 9 to 28 pages; `test_dashboard_only_imports_semantic_seam_never_bsl_directly`
  (line 178) is the existing import-boundary gate this story must keep green.
- `scripts/dashboard_serve.py` — the existing DW-D2-3 serve entrypoint
  (`pixi run -e local-recipes dashboard-serve`); this story's data-present visual pass runs
  through this unmodified script, after the Story 20.3 pipelines have populated `data/`.
- `pixi.toml` `[feature.local-recipes.tasks.dashboard-serve]` (~line 956) and
  `[feature.local-recipes.tasks.dashboard-dryrun]` (~line 961) — the existing task definitions;
  `dashboard-dryrun`'s description explicitly says "Full 28-page inventory is CIS-two-spine
  deferred (DW-D2)" — update this description once the full inventory ships.
- No existing semantic-HTML/ARIA test was found anywhere under
  `src/shared/packages/pyforge-atlas/tests/dashboard/` (confirmed by grep for
  `ARIA`/`aria`/`semantic-HTML` across both existing test files) — the §2.1 navigation check is
  genuinely new test/tooling work, most likely a headless-browser-driven check (mirroring the
  2026-08-26 operator-session headless-Chrome-screenshot precedent DW-D2-3 itself describes)
  rather than an offline structural assertion.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` `DW-D2-1`
  (line 351) and `DW-D2-3` (line 369) — the two entries this story's completion closes out,
  citing this story.
