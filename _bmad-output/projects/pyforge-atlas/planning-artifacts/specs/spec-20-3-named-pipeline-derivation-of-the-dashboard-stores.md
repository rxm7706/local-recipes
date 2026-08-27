---
title: 'Story 20.3: Named-pipeline derivation of the dashboard stores (CAP-6)'
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
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-2-kedro-writes-the-parquet-cache.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** two dashboard data gaps are open and both trace to un-materialized stores. (1)
DW-D2-2: `dashboard/data.py`'s `staleness-report`/`query-atlas`/`detail-cf-atlas` pages are
"BSL-wired SHELL pages (packages composed store not yet materialized — DW-D2)" — they bind to
`build_packages_model` over `PACKAGES_PARQUET =
"primary/semantic_packages/semantic_packages.parquet"`, which no pipeline writes today
(confirmed: `semantic_packages` has no entry anywhere in `conf/base/catalog.yml`). (2) The
2026-08-26 first `dashboard-serve` visual pass (DW-D2-3 evidence-update) found even
`core_feedstock_health` — which IS produced by the sealed `core` pipeline
(`catalog.yml:164`, node `compute_feedstock_health`) — absent in a fresh checkout, because its
Parquet only exists in `data/` after `kedro run --pipeline core` has actually executed once.

**Approach:** per the `query-plane-catalog` ruling ("named new pipeline... the closed seven
stay sealed... a downstream pipeline reads their outputs without modifying them"), add ONE new,
named, downstream-only Kedro pipeline — mirroring the existing `pipelines/query_plane_cache/`
package's exact shape (`__init__.py`/`nodes.py`/`pipeline.py`, auto-discovered by
`pipeline_registry.py::register_pipelines` via `find_pipelines`, zero registry edits needed) —
that reads the sealed `core` pipeline's ALREADY-PRODUCED catalog outputs
(`core_packages_enumerated`, `core_latest_status`, `core_downloads`, `core_feedstock_attribution`,
etc.) as its own pipeline's `inputs=`, composes the `semantic_packages` Parquet, and registers it
as a NEW `catalog.yml` entry. Retire `dashboard/data.py`'s "packages composed store not yet
materialized — DW-D2" banner once `semantic_packages` is a real, resolvable dataset, and close
DW-D2-2 citing this story. Running `core` + the new named pipeline together is also how
`core_feedstock_health` stops being absent in a fresh checkout — document that as the
operational precondition (the runbook/README for the new pipeline should say so explicitly), not
a second code path.

## Acceptance Criteria

Lifted verbatim from `epics.md` (Story 20.3):

> **Given** the sealed seven pipelines' canonical outputs **When** the NAMED downstream plane
> pipeline runs (one `kedro run --pipeline <named>`) **Then** the composed semantic stores the
> grounded dashboard pages bind to (DW-D2-2's `semantic_packages` family plus the
> `core_feedstock_health` Parquet the 2026-08-26 first visual pass found absent in a fresh
> checkout) are materialized **And** zero diff lands inside the sealed seven and no silent
> `01_raw` tree appears (`query-plane-catalog` ruling, 2026-08-26) **And** consumers keep the
> per-call choice — canonical datasets direct, or the plane as the fast path — **And**
> `dashboard/data.py`'s "BSL-wired SHELL pages" banner retires, with DW-D2-2 closed citing this
> story.

## Boundaries & Constraints

**Always:** `BMAD_ACTIVE_PROJECT=pyforge-atlas`; ledger key
`20-3-named-pipeline-derivation-of-the-dashboard-stores`; the new pipeline is DOWNSTREAM ONLY of
the sealed seven's outputs — it reads them as `inputs=` by their existing catalog dataset names
(the same convention `pipelines/core/pipeline.py` and `pipelines/query_plane_cache/pipeline.py`
already use — execution order resolves from declared dataset names, FR-2/AD-3, never a
procedural call-order list); zero diff inside any sealed-seven pipeline package
(`pipelines/core/`, `pipelines/vcs_health/`, `pipelines/pypi_intelligence/`,
`pipelines/vulnerability/`, `pipelines/derived_artifacts/`, `pipelines/artifactory_downloads/`,
`pipelines/seed_gaps/`/`pipelines/upstream_discovery/`/`pipelines/universal_sbom/` — whichever
set exactly comprises the sealed seven) or inside `pipelines/query_plane_cache/`; consumers keep
the per-call choice (canonical dataset direct, or the composed store) per the ruling; no silent
`01_raw` tree.

**Block If:** composing `semantic_packages` would require FABRICATING a value for a field
`semantic/metrics.py::METRIC_PROVENANCE` already declares `data_wiring:
"deferred-input-not-in-migrated-store"` (e.g. `latest_conda_upload`) — report and stop; the
honest-empty/never-fabricate convention (`dashboard/data.py::_bsl_query_or_empty`) must hold for
the new store too.

**Never:** modify any sealed-seven pipeline's nodes or pipeline wiring; modify
`dashboard/app.py`'s page set or `PAGE_INVENTORY` (that is Story 20.5, and it is explicitly
gated on this story); produce the CIS two-spine specs (Story 20.4 — unrelated, parallel work).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | sealed-seven outputs already materialized in `data/`, named pipeline runs | `semantic_packages` Parquet materializes at its new declared catalog path | none |
| MISSING_UPSTREAM | a required sealed-seven output not yet materialized | `kedro run` fails loud naming the missing input dataset (Kedro's own catalog-resolution behavior) | no fabricated composed row is ever written |
| DEFERRED_METRIC_INPUT | a `METRIC_PROVENANCE` deferred-input column has no live source yet | column is omitted/null in the composed frame | never fabricated — matches existing `_bsl_query_or_empty` honesty convention |
| FRESH_CHECKOUT | neither `core` nor the new named pipeline has ever run | dashboard pages render honestly empty, exactly as `dashboard/data.py`'s existing degrade path already does today | matches DW-D2-3's documented "unavailable — backing file not found" behavior; unchanged until pipelines actually run |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py` —
  `register_pipelines()` auto-discovers every pipeline package via
  `find_pipelines(raise_errors=True)`; a new `pipelines/<name>/` package needs NO registry edit,
  just the standard 3-file shape below.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/query_plane_cache/{__init__.py,nodes.py,pipeline.py}`
  — the exact PRECEDENT for this kind of story: a new, named, downstream-only pipeline (Story
  34.2, FR-47) reading an already-sealed source dataset without touching the sealed seven. Its
  `pipeline.py` is a 3-line `Pipeline([node(...)])` — mirror this shape for the new pipeline.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/core/pipeline.py` — the sealed
  `core` pipeline whose outputs (`core_packages_enumerated`, `core_feedstock_attribution`,
  `core_latest_status`, `core_downloads` + 3 breakdown outputs, `core_dependencies`,
  `core_feedstock_health`) are the READ-ONLY inputs the new pipeline composes from. Do not edit
  this file or `pipelines/core/nodes.py`.
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml:102-168` — the sealed `core`
  pipeline's existing dataset declarations (for the exact input names to wire) plus where the
  NEW `semantic_packages` primary-layer dataset entry must be added; confirmed by grep that no
  `semantic_packages:` entry exists anywhere in this file today.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py:37-48,126-180` —
  `PACKAGES_PARQUET` constant (line 47) and the "BSL-wired SHELL pages (packages composed store
  not yet materialized — DW-D2)" banner (lines 126-128) to retire once `semantic_packages` is
  real; `load_staleness`/`load_query_atlas`/`load_detail` (lines 131-180) are the three loaders
  that bind to it via `_bsl_query_or_empty`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/models.py` (`build_packages_model`)
  and `semantic/metrics.py` (`METRIC_PROVENANCE`, ~line 193) — the BSL model the composed store
  must satisfy, and the existing honest bookkeeping of which per-package fields are
  `deferred-input-not-in-migrated-store` (must not be fabricated by the new pipeline).
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` `DW-D2-2`
  (line 360) — the entry this story closes, citing this story, per `epics.md`'s own instruction.
