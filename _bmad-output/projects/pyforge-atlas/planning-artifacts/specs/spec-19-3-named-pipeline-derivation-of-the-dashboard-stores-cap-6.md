---
title: 'Story 20.3: Named-pipeline derivation of the dashboard stores (CAP-6)'
type: 'feature'
created: '2026-08-27'
status: 'done'
updated: '2026-08-27'
baseline_revision: '440a9183981350421605dd17b61b8a4fc9d4312d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-2-kedro-writes-the-parquet-cache.md
warnings: []
deferred:
  - summary: >-
      dashboard/app.py's PAGE_INVENTORY notes, dashboard/__init__.py's module docstring, and
      a provenance comment at app.py:243 still describe the packages-backed pages as
      "renders empty until the composed store lands (DW-D2)", now stale relative to
      DW-D2-2's closure by this story.
    evidence: |-
      This story's spec explicitly forbids modifying dashboard/app.py's page set or
      PAGE_INVENTORY ("Never" clause) -- that is reserved for Story 20.5, which is
      explicitly gated on this story. dashboard/__init__.py's docstring carries the same
      "BSL-wired SHELL" framing but is not covered by an explicit Never clause; left
      unchanged here for consistency with the same page-inventory documentation set
      Story 20.5 will touch. Purely comment/docstring text, no functional impact.
    location: >-
      src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py:13-19,68-90,243;
      src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/__init__.py:10-13
    severity: low
  - summary: >-
      README.md's "Status" line ("8 Kedro pipelines live") already omitted the pre-existing
      artifactory_downloads and query_plane_cache pipelines before this story; this story
      adds a 9th/10th pipeline (semantic_packages) without correcting that inventory.
    evidence: |-
      Pre-existing drift, not introduced by this story -- confirmed the README already
      undercounted by 2 before this diff. Worsened by one more omission. No functional
      impact; a documentation-completeness item best fixed as one pass across all
      undercounted pipelines rather than piecemeal per-story.
    location: src/shared/packages/pyforge-atlas/README.md:14-17
    severity: low
  - summary: >-
      test_nodes.py's duplicate-key test (test_duplicate_conda_name_across_joined_inputs_does_not_fan_out_the_population)
      only exercises duplicate keys in core_packages_enumerated/core_latest_status, not in
      core_downloads, core_feedstock_attribution, or vcs_archived_feedstocks.
    evidence: |-
      A thoroughness gap, not a correctness defect: nodes.py already calls
      .drop_duplicates("conda_name") on every one of those three inputs before merging, so
      the fan-out guard exists in code: the gap is only in explicit test coverage proving
      it for the other three inputs.
    location: src/shared/packages/pyforge-atlas/tests/pipelines/semantic_packages/test_nodes.py
    severity: low
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

## Review Triage Log

### 2026-08-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 3: (high 0, medium 0, low 3)
- reject: 9: (high 0, medium 0, low 9)
- addressed_findings:
  - `[low]` `[patch]` The Approach paragraph explicitly asked that the operational
    precondition (`kedro run --pipeline core`, `--pipeline vcs_health`, then `--pipeline
    semantic_packages`) be documented in "the runbook/README for the new pipeline" — no such
    file existed. Fixed: added `pipelines/semantic_packages/README.md` stating the 3-step
    precondition and that it is also what resolves `core_feedstock_health`'s fresh-checkout
    absence.
  - `[low]` `[patch]` `compose_semantic_packages`'s population line
    (`core_packages_enumerated[["conda_name"]].drop_duplicates()`) did not guard against a
    null `conda_name`, which would carry a NaN-keyed row into the composed store. Fixed:
    added `.dropna(subset=["conda_name"])` before dedup, plus a new unit test
    (`test_null_conda_name_in_population_is_dropped_not_carried_as_a_row`).
  - `[low]` `[patch]` The `DW-D2-2` ledger entry's heading still listed `behind-upstream` /
    `whodepends` as covered by this entry, while its own new resolution text says those stay
    open under `DW-D2-1` — a self-contradictory heading. Fixed: reworded the heading to state
    that explicitly.

Reject rationale (representative, not exhaustive): `catalog.yml`'s new `semantic_packages`
entry omitting `compression: zstd` (present on the nearest analogous entry) is a stylistic
nit with no functional effect, not a defect; the empty-input branch's separate hand-rolled
shape construction is a minor maintainability observation, not a bug, and is covered by
`test_empty_population_returns_the_declared_empty_shape`; the two test-location conventions
(`tests/pipelines/semantic_packages/` unit tests + top-level `test_semantic_packages_pipeline.py`
integration test) coexisting with the precedent's single-file convention is a defensible
choice, not a fragmentation problem; the edge-case hunter's `astype("Int64")`
non-castable-value crash risk would only be reachable via malformed sealed-pipeline output
(out of this story's scope) and a loud crash there is the intended fail-loud behavior per the
story's own never-fabricate philosophy, not a bug; the first-row-wins-on-duplicate-key
concern likewise assumes malformed upstream data the sealed pipelines already guarantee
against; `DW-D2-3` (the ledger entry actually holding the 2026-08-26
`core_feedstock_health`-absent finding) was correctly left untouched — the spec's own Code
Map names only `DW-D2-2` as the entry this story closes, and the Approach paragraph
explicitly frames the operational-precondition fix as documentation, "not a second code
path" (i.e., not a second ledger edit); the FRESH_CHECKOUT matrix row's dashboard-loader-surface
coverage was independently re-verified during the Matrix Test Audit as already satisfied by
the pre-existing, unchanged `test_data_loaders_offline_return_empty_typed_frames_not_fabricated`
(confirmed still passing after this diff); the `tests/mcp/test_audit_mapping.py`
`NO_MCP_TRIGGER_PIPELINES` fix for `query_plane_cache` (a pre-existing Story 34.2 gap, found
incidentally) is a correct, low-risk, self-documented drive-by fix of an already-red test, not
scope creep requiring a separate ledger entry; the apparent AC tension (the named pipeline's
`Then` clause names `core_feedstock_health` as an outcome, but this pipeline never touches it)
is pre-resolved by the Approach paragraph's own explicit instruction to treat the combined
materialization as an operational sequence to document, not a second code path — addressed by
the README patch above.

## Auto Run Result

**Summary:** Added the named, downstream-only `semantic_packages` Kedro pipeline (CAP-6,
`query-plane-catalog` ruling) that composes the `semantic_packages` primary store from the
sealed `core` + `vcs_health` pipelines' own catalog outputs, mirroring `pipelines/query_plane_cache/`'s
exact shape. Registered a new `catalog.yml` entry at the path `dashboard/data.py::PACKAGES_PARQUET`
already pointed at, retired the "packages composed store not yet materialized — DW-D2" banner
in `dashboard/data.py`, and closed `DW-D2-2` in the deferred-work ledger citing this story. The
4 `metrics.METRIC_PROVENANCE` deferred-input columns are declared explicit NULL, never
fabricated — the story's Block-If honesty constraint, proven end-to-end through the real BSL
query seam by a dedicated test.

**Files changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/semantic_packages/{__init__.py,pipeline.py,nodes.py}` —
  new pipeline: 3-line `Pipeline([node(...)])` wiring + the pure-pandas composition node.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/semantic_packages/README.md` —
  new; documents the 3-step fresh-checkout operational precondition (patch).
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` — new `semantic_packages` dataset
  entry.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py` — retired the
  DW-D2 "not yet materialized" banner/comments; documents the pipeline that now produces the
  store.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` — `DW-D2-2`
  flipped `open` → `closed` with a resolution citing this story; heading corrected to not
  imply `behind-upstream`/`whodepends` are covered (patch).
- `src/shared/packages/pyforge-atlas/tests/pipelines/semantic_packages/{__init__.py,test_nodes.py}` —
  new; 7 unit tests for the composition node (join correctness, never-fabricate guarantee,
  dedup, empty/degraded-input handling, null-identity guard).
- `src/shared/packages/pyforge-atlas/tests/test_semantic_packages_pipeline.py` — new; 6
  integration tests (registration, catalog declaration, real `kedro run`, `MISSING_UPSTREAM`
  fail-loud, downstream-only input check, end-to-end BSL honesty proof).
- `src/shared/packages/pyforge-atlas/tests/catalog/conftest.py` — registered the new pipeline
  in the catalog-check gate's expected-count fixtures.
- `src/shared/packages/pyforge-atlas/tests/mcp/test_audit_mapping.py` — added `semantic_packages`
  (and, as a drive-by fix of a pre-existing Story 34.2 gap, `query_plane_cache`) to the
  no-MCP-trigger exemption set.

**Review findings breakdown:** 3 patches applied (all low severity — missing runbook/README
for the operational precondition, a null-`conda_name` identity guard, a self-contradictory
ledger heading); 3 items deferred (all low — stale "DW-D2 SHELL" banner language in
`dashboard/app.py`/`__init__.py` reserved for Story 20.5; pre-existing `README.md` pipeline-count
staleness worsened by one; a test-coverage thoroughness gap on 3 of 5 dedup inputs); 9 items
rejected as non-issues (stylistic catalog nit, code-maintainability observation, defensible
test-layout choice, two malformed-upstream-data edge cases out of this story's scope, an
already-correctly-untouched ledger entry, an already-covered matrix row, a correct drive-by
bug fix, and an AC tension pre-resolved by the spec's own Approach paragraph).

**Follow-up review recommendation:** `false`. Patched-finding score: 0 high, 0 medium, 3 low
→ `3×0 + 1×3 = 3` (< 5), and no high-severity patch.

**Verification performed:**
- `pixi run -e pyforge-atlas kedro-catalog-check` → 48 passed (was 47 before this story).
- `pixi run -e pyforge-atlas kedro-test` (full suite, run 3× across the session, including
  after the patch pass) → 1279 passed, 21 skipped consistently; the only failures are 2
  confirmed-pre-existing (`test_factory_status_reads_the_real_sprint_status`,
  `test_context_files_unchanged`) + 2 confirmed-pre-existing errors
  (`test_read_only_live_attach.py`), none touching anything this story changed. One
  additional intermittent full-suite-only flake
  (`test_dashboard_e2e_navigation_and_rendering`) was observed once, reproduced as passing in
  isolation and on a subsequent full-suite re-run — confirmed non-deterministic under
  full-suite resource contention, not a regression (it directly exercises the
  `semantic_packages`-backed `/staleness-report` page and was specifically checked for this
  reason).
- `pixi run -e pyforge-atlas bsl-metric-check` → 16 passed.
- New tests specifically (13/13 after the patch pass): join correctness, never-fabricate
  guarantee across every branch, dedup, empty/degraded-input handling, null-identity guard,
  pipeline registration, catalog declaration, real `kedro run` via `SequentialRunner`,
  `MISSING_UPSTREAM` fail-loud (added during this pass — the I/O matrix's row was originally
  uncovered; now proven via a real `DataCatalog` missing the required input), downstream-only
  input check, and the end-to-end BSL honesty proof.
- Matrix Test Audit: all 4 I/O rows independently re-confirmed — HAPPY_PATH
  (`test_kedro_run_composes_and_writes_the_parquet`), MISSING_UPSTREAM
  (`test_missing_required_upstream_fails_loud_naming_the_dataset`, added this pass),
  DEFERRED_METRIC_INPUT (`test_never_fabricates_deferred_inputs_even_with_full_upstream_data`
  + the end-to-end honesty test), FRESH_CHECKOUT (pre-existing, unchanged
  `test_data_loaders_offline_return_empty_typed_frames_not_fabricated`, re-run and confirmed
  still passing).
- Confirmed zero diff inside `pipelines/core/`, `pipelines/vcs_health/`, or
  `pipelines/query_plane_cache/` (`git diff --stat`).
- Confirmed all new pipeline inputs (`core_packages_enumerated`, `core_latest_status`,
  `core_feedstock_attribution`, `vcs_archived_feedstocks`, `core_downloads`) are pre-existing
  sealed-pipeline catalog entries (grep against `catalog.yml`), never a `_raw` source.
- 4-layer parallel review (blind hunter, edge-case hunter, verification-gap, intent-alignment)
  run against the full diff since baseline `440a918398`; verification-gap reviewer reported no
  gaps.

**Residual risks:** The 3 deferred items are all low-severity, non-functional documentation
gaps (stale banner comments in files this story is explicitly barred from touching until
Story 20.5; a pre-existing pipeline-count omission in `README.md`; a test-coverage
thoroughness gap where the underlying `.drop_duplicates()` guard already exists in code for
all 5 join inputs, just not independently proven by a dedicated test for 3 of them). No
functional or correctness risk identified. The intermittent `test_dashboard_e2e_navigation_and_rendering`
full-suite flake is pre-existing resource-contention behavior, not introduced by this story,
but is worth a future look if it recurs.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
