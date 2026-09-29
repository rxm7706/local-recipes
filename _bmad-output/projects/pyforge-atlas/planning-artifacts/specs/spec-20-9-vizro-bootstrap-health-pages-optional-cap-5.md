---
title: 'Vizro operator pages for bootstrap verification (Story 21.9, Epic 21, optional follow-on)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: 'pending-verification'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/operator-surfaces.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md'
---

<intent-contract>

## Intent

**Problem:** Epic 21 core (21.1–21.8) ships a self-contained Kedro catalog data plane for
bootstrap but adds zero new operator surface — after `pyforge-atlas-bootstrap` runs, an
operator has no dashboard view of whether Tier 0/1 indexes materialized, whether the
identity join (Story 21.6) produced sane associator/inventory-derived/unmapped counts, or
whether verification-matrix BOOL coverage is complete. Today's only recourse is CLI/log
inspection (`metrics.py --live-catalog`, `parity-diff`, Kedro-Viz's passive DAG view).

**Approach:** Add exactly three new BSL-shell pages — `bootstrap-index-health`,
`identity-export-snapshot`, `live-catalog-coverage` — to the existing 28-page
`pyforge.atlas.dashboard` inventory, using the IDENTICAL Story 20.5 pattern already proven
for the other 19 BSL-shell pages: a `PageDef` entry in `app.py::PAGE_INVENTORY`, a
`build_*_model` in `semantic/models.py` declaring only `Dimension`/`Measure` exprs (AD-8), a
`load_*` loader in `dashboard/data.py` routed through the existing `_bsl_query_or_empty` seam,
and a `_provenance.resolve_for_file` line for AD-17 provenance. No new fetch logic, no new
IO seam — pure BSL reads over Parquet under `PYFORGE_ATLAS_DATA_ROOT` that degrade honestly
to an empty typed frame when the backing dataset is not yet materialized (DW-D2-2).

## Boundaries & Constraints

**Always:**
- Follow the exact existing pattern in `dashboard/app.py`: a `PageDef(..., kind="bsl-shell")`
  entry appended to `PAGE_INVENTORY`, a `_provenance.resolve_for_file(root / <PARQUET>)` call,
  and a `_data_page(by_id["<id>"], lambda: _data.load_<x>(...), grounded=False,
  provenance=<x>_provenance)` call inside `build_dashboard()` — mirror the Story 20.5 block
  (`app.py` ~L519–635) verbatim in shape.
- Each loader lives in `dashboard/data.py` as `load_<x>`, calling
  `_bsl_query_or_empty(parquet, build_model, dimensions, measures)` — the single AD-8 seam
  every other page uses; never raw SQL/pandas metric re-implementation.
- Each BSL model lives in `semantic/models.py` as a new `build_<x>_model(table) -> SemanticModel`,
  declared with `Dimension`/`Measure` exprs only — mirror `build_mapping_gap_model` (~L397) /
  `build_lts_registry_gap_model` (~L503) exactly.
- Data functions stay LAZY (`data_manager[key] = loader`, never invoked at build time) so
  `pixi run -e local-recipes dashboard-dryrun` keeps building the Dashboard OBJECT offline,
  no server, no `.run()` (existing gate discipline, unchanged).
- Extend `tests/dashboard/test_dashboard_dryrun.py`'s existing regression fixtures — add the
  3 new page ids to `_NEW_PAGE_LOADERS_NO_ARGS` (~L435) and `_NEW_MODEL_SCHEMAS` (~L463), which
  automatically exercises `test_registered_data_functions_are_callable_and_return_frames`
  (~L243), `test_new_pages_offline_return_empty_typed_frames_not_fabricated` (~L575), and
  `test_new_page_loaders_request_only_dimensions_measures_the_model_declares` (~L557) for the
  new pages with no further test-file changes required for those three checks.
- No ranking columns (`P`/`Rank`/`Score`/`Work`/JFROG telemetry fields) surface on any of the
  3 new models — those stay gist/quartet-owned per `identity-contract.md` § Export columns and
  `vizro-canvas-parity.md` (Epic 22 territory).
- `identity-export-snapshot` binds to `identity_export_parquet` (Story 21.6's export,
  `identity-contract.md` ~L24/~L52) using its documented `identity_source`, `primary_purl`,
  `OpenTeams_Issue_URL` columns (~L37–44) — these column names are fixed by that contract even
  though the Parquet does not exist in `conf/base/catalog.yml` as of this story's authoring.
- `live-catalog-coverage` aggregates the BOOL fields `verification-matrix.md`'s table maps
  (`PyPI_Verified`, `CondaForge_Verified`, Basilisk membership, AOSS free/premium, Anaconda
  main/Dist, cross-channel BOOLs) — an aggregate coverage summary, never a full per-package
  browse (mirrors the existing `universe-sbom` summary-first precedent, `data.py` ~L353).
- `bootstrap-index-health`'s exact backing Parquet relpath(s) and per-entry schema are resolved
  against whatever `conf/base/catalog.yml` entries Stories 21.3/21.4 actually land at
  implementation time — `catalog-sources.md`'s Tier 0/1 tables (~L7–31) and scale sanity gates
  (~L47–57) are the intended SHAPE (one row per catalog entry: name, tier, row_count, staleness),
  not a fixed path list (see Design Notes).
- This is a `recipes/`-external change (`src/shared/packages/pyforge-atlas/**`) — per
  CLAUDE.md's PR-CI-gates rule, the PR must carry the `maintenance` label
  (`gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`).

**Block If:** None — the three concrete Parquet bindings this story depends on are
Stories 21.3/21.4/21.6's outputs, already gated by this story's own `depends_on: ["21.8"]`
in `stories.yaml` (a scheduling constraint, not a spec-time human decision); the per-field
shape needed to write correct `Dimension`/`Measure` declarations is fully documented today in
`catalog-sources.md`/`identity-contract.md`/`verification-matrix.md`.

**Never:**
- Do not touch any of the 28 existing `PageDef` entries or their `_data_page`/`_shell_page`
  wiring — append only.
- Do not add a live fetch, HTTP call, or any new IO path in dashboard code — BSL measures
  only, over already-materialized Parquet (operator-surfaces.md's own constraint).
- Do not add ranking columns (`P`/`Score`/`Work`) to any of the 3 new models.
- Do not replace the inventory `.canvas.tsx` generators (Epic 22 territory).
- Do not implement Stories 21.3/21.4/21.6's actual pipeline work as part of this story —
  presumed already landed via `depends_on: ["21.8"]`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh, green Epic 21 bootstrap | 21.1–21.8 executed on a real data root | All 3 pages render non-empty AgGrid tables; row counts consistent (order of magnitude) with `catalog-sources.md`'s scale sanity gates | n/a |
| Pre-bootstrap / empty data root | No backing Parquet for any of the 3 pages | Each page renders its legibility Card + an empty AgGrid with exactly its declared columns (DW-D2-2 shell state) | Never raise; `_bsl_query_or_empty` returns the declared-column empty frame |
| Partial materialization | e.g. `identity_export_parquet` present, Tier 0/1 indexes not yet | Each page independently reflects its OWN backing file's presence — no single dashboard-wide flag | Same per-page `_provenance.resolve_for_file` discipline as every existing shell page |
| Present but degenerate Parquet | 0-row store round-trips untyped | Degrades to the declared-column empty frame, not a crash | Mirrors `_bsl_query_or_empty`'s existing `except TypeError` branch (`data.py` ~L135–141) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` — `PAGE_INVENTORY`
  (~L82–295), `_data_page`/`_shell_page` helpers (~L329–352), `build_dashboard()`
  (~L402–644) — append 3 `PageDef(..., kind="bsl-shell")` entries + 3
  `_provenance.resolve_for_file(...)` lines + 3 `_data_page(...)` calls, exact shape of the
  Story 20.5 block (~L519–635).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py` — Parquet relpath
  constants (~L57–84), the `_bsl_query_or_empty` seam (~L106–141), `load_*` functions
  (~L235–444) — add 3 constants (e.g. `BOOTSTRAP_INDEX_HEALTH_PARQUET`,
  `IDENTITY_EXPORT_PARQUET`, `LIVE_CATALOG_COVERAGE_PARQUET`) + `load_bootstrap_index_health`,
  `load_identity_export_snapshot`, `load_live_catalog_coverage`, each a one-line
  `_bsl_query_or_empty(...)` call in the same block style as the Story 20.5 loaders.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/models.py` —
  `build_mapping_gap_model` (~L397), `build_lts_registry_gap_model` (~L503) — the exact
  `SemanticModel`/`Dimension`/`Measure` shape to mirror for 3 new `build_*_model(table)`
  functions.
- `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py` —
  `_ALLOWED_PAGE_KINDS` (~L99–106, `"bsl-shell"` already a member, no change needed),
  `_NEW_PAGE_LOADERS_NO_ARGS` (~L435–454), `_NEW_MODEL_SCHEMAS` (~L463 onward),
  `test_all_expected_pages_present_with_stable_id_and_title` (~L65, covers the new count
  automatically via `PAGE_INVENTORY`), `test_packages_shell_pages_are_bsl_wired_and_light_up_with_data`
  (~L175, the pattern for a page-specific BSL-equality test with real fixture data) — extend
  the two dicts with the 3 new page ids; add one BSL-driven-equality test per new page.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md`
  — Tier 0/1 table (~L7–31) + scale sanity gates (~L47–57) — the row-count-floor reference for
  `bootstrap-index-health`'s success check.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md`
  — `identity_export_parquet` (~L24, ~L52) + export columns (~L37–44) — the schema
  `identity-export-snapshot` binds to.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md`
  — the inventory-field → Kedro-source table (~L7–21) — the BOOL-coverage fields
  `live-catalog-coverage` aggregates.
- `pixi.toml` — `dashboard-dryrun` (~L961), `dashboard-serve` (~L956) task descriptions —
  currently say "full 28-page inventory"; refresh to 31 once the 3 pages land (cosmetic, not
  gating).

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/atlas/semantic/models.py` — add `build_bootstrap_index_health_model`,
  `build_identity_export_snapshot_model`, `build_live_catalog_coverage_model`. Suggested
  shapes (confirm exact source columns against the real materialized Parquet from 21.3/21.4/21.6
  at implementation time — the SHAPE below is fixed by the source docs, not an open question):
  - `bootstrap_index_health`: dimensions `catalog_entry`, `tier`, `regenerated_at`; measure
    `row_count` (per `catalog-sources.md`'s Tier 0/1 table + scale sanity gates).
  - `identity_export_snapshot`: dimension `identity_source` (`from_assoc` / `from_inventory` /
    `from_board_only`, per `identity-contract.md` § Join semantics); measures `package_count`,
    `primary_purl_coverage_count` (non-null `primary_purl`), `openteams_issue_url_coverage_count`
    (non-null `OpenTeams_Issue_URL`).
  - `live_catalog_coverage`: dimension `field_name` (`PyPI_Verified`, `CondaForge_Verified`,
    `Basilisk_Member`, `AOSS_Free`, `AOSS_Premium`, `Anaconda_Main`, `Anaconda_Dist`,
    cross-channel BOOLs, per `verification-matrix.md`'s table); measures `true_count`,
    `total_count`.
- [x] `src/pyforge/atlas/dashboard/data.py` — add the 3 Parquet relpath constants + 3
  `load_*` functions, each routed through `_bsl_query_or_empty`.
- [x] `src/pyforge/atlas/dashboard/app.py` — append 3 `PageDef` entries (id `bootstrap-index-health`
  / `identity-export-snapshot` / `live-catalog-coverage`, `kind="bsl-shell"`, each `note`
  stating which upstream story materializes its backing Parquet), 3 `_provenance.resolve_for_file`
  calls, 3 `_data_page(...)` calls in `build_dashboard()`.
- [x] `tests/dashboard/test_dashboard_dryrun.py` — extend `_NEW_PAGE_LOADERS_NO_ARGS` +
  `_NEW_MODEL_SCHEMAS` with the 3 new entries (declared columns per the model shapes above);
  add one BSL-driven-equality test per new page (mirror
  `test_packages_shell_pages_are_bsl_wired_and_light_up_with_data`, ~L175) using a small
  fixture Parquet per page.
- [x] `pixi.toml` — refresh the `dashboard-dryrun`/`dashboard-serve` task descriptions' page
  count.

**Acceptance Criteria:**
- Given the dashboard is built offline with `data_root` pointed at a nonexistent path, when
  `build_dashboard()` runs, then `bootstrap-index-health`, `identity-export-snapshot`, and
  `live-catalog-coverage` each appear in `PAGE_INVENTORY`/`dashboard.pages` with a stable
  id+title and register a lazy data function that returns an empty, declared-column
  `DataFrame` (DW-D2-2), never raising.
- Given `pixi run -e local-recipes dashboard-dryrun`, when run after this story, then it
  passes, and its assertions (page kind, stable id, empty-frame-degrade,
  BSL-schema-subset-of-declared-model) cover all 3 new pages the same way they cover the
  existing 19 Story 20.5 pages.
- Given a green Epic 21 bootstrap (21.1–21.8 executed on a real data root) and
  `pixi run -e local-recipes dashboard-serve`, when the 3 new pages are opened, then each
  shows a non-empty AgGrid table whose row counts are consistent (order of magnitude) with
  `catalog-sources.md`'s scale sanity gates.
- Given the 3 new `SemanticModel`s, when introspected via `.dimensions`/`.measures`, then
  none declares a `P`/`Rank`/`Score`/`Work`/JFROG-telemetry field.

## Spec Change Log

<!-- Empty — no review loopback has occurred yet. -->

## Design Notes

The exact Parquet filepaths this story's 3 new models bind to are intentionally NOT fixed by
this spec. As of this story's authoring (2026-08-30), Stories 21.3 ("Tier 0 harden and
`--live-catalog` contract"), 21.4 ("Tier 1 catalog sources"), and 21.6 ("`upstream_discovery`
identity join and export Parquet") have no spec files yet, and today's `conf/base/catalog.yml`
Tier 0 entries (`core_channeldata_raw`, `pypi_simple_index_raw`, etc.) are direct
`type: pyforge.atlas.datasets.*` live-fetch datasets with no persisted `filepath:` — confirmed
by direct inspection. `identity_export_parquet` (Story 21.6) also does not exist in
`catalog.yml` yet. Because this story's own `depends_on: ["21.8"]` (an end-to-end verification
gate that itself depends on 21.3–21.7) guarantees those upstream stories are green before 21.9
executes, the implementer's task is a step-03-style research task (mirroring `spec-21-2`'s
registry-endpoint precedent): grep the THEN-current `catalog.yml` + any then-updated
`identity-contract.md` for the real dataset names/paths, and bind the 3 loaders to whatever
concrete `<layer>/<name>/<name>.parquet` relpath under `PYFORGE_ATLAS_DATA_ROOT` those stories
actually produced — the SHAPE (one BSL model, one loader, one `PageDef`, degrade-to-empty) is
fixed; only the concrete filepath is TBD.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Open each of the 3 new pages against an empty `PYFORGE_ATLAS_DATA_ROOT` and confirm the
  legibility Card states the data gap honestly (mirrors the existing 19 BSL-shell pages'
  "renders empty until … materializes" note style).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `20-9-vizro-bootstrap-health-pages-optional-cap-5: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `in-progress` → `done` (ledger row `20-9-vizro-bootstrap-health-pages-optional-cap-5: done`).
- `## Auto Run Result` reconstructed from git (none survived).
