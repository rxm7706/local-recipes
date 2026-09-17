---
title: 'Kedro pipeline surfacing (Story 15.3, CAP-4)'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
difficulty: ''
baseline_revision: '3c10b87a3b0a01839ae69b86484f02c18b11e445'
final_revision: 'd8a84c5a1a7735c73f45b87e3299ecba803f4e80'
---

<intent-contract>

## Intent

**Problem:** Stories 15.1/15.2 shipped `ArtifactoryAqlAdapter.fetch_download_rows()` and
`join_identity()` as standalone, pure capabilities in `artifactory/` — deliberately NOT wired
into a Kedro pipeline, catalog entry, or dataset. Atlas has no registered pipeline that surfaces
Artifactory download intelligence, and no path for those rows to reach the existing PURL-export
surface.

**Approach:** Add a new `pipelines/artifactory_downloads/` Kedro pipeline (3 pure nodes: fetch →
join → export) that wires 15.1's adapter and 15.2's join into the catalog, lands the joined rows
in a new Parquet-backed catalog dataset, and contributes exactly one new partition
(`artifactory_downloads.tsv`) to the already-declared-but-unproduced `derived_purl_exports`
`PartitionedDataset` (`conf/base/catalog.yml:797`) — in the exact TSV shape
`export_purls.py::mapped_tsv_lines` already produces for the conda→pypi direction, mirrored for
the pypi→conda direction. By default (`params:artifactory.virtual_repos: []`), the fetch node
constructs no adapter/transport and contacts nothing — matching the epic's binding "no live
instance named, selected, or contacted" constraint.

## Boundaries & Constraints

**Always:**
- Reuse `ArtifactoryAqlAdapter`/`DownloadRow` (`artifactory/aql_adapter.py`) and
  `join_identity`/`JoinedDownloadRow` (`artifactory/identity_join.py`) exactly as they are — zero
  edits to either module in this diff.
- The fetch node short-circuits to an empty, correctly-columned DataFrame with **zero**
  `ArtifactoryAqlAdapter`/transport construction when `params:artifactory.virtual_repos` is empty
  (the committed default) — no live instance is named, selected, or contacted anywhere in the
  default run path, in tests, or in this diff.
- `pipelines/artifactory_downloads/nodes.py` stays pure (pandas/stdlib only) — no `dagster` /
  `kedro_mcp` imports (AD-1); no direct HTTP/DB/subprocess imports.
- The export node includes ONLY rows with a resolved `conda_name`; `is_internal=True` /
  unmatched rows are excluded — mirrors `export_purls.py::mapped_tsv_lines`'s own "skip rows
  missing the join partner" rule, applied to the reversed pypi→conda direction.
- The exported partition's shape (header `conda_purl\tpypi_purl\tmatch_source\tmatch_confidence`,
  `pkg:conda/<name>?channel=conda-forge`, `pkg:pypi/<g98-folded-name>`, tab-separated, blank
  `match_confidence` — this data source has no confidence column, same as the legacy fallback)
  byte-for-byte matches `export_purls.py`'s `MAPPED_TSV_HEADER`/`mapped_tsv_lines`/`g98_pypi_name`
  convention, reimplemented locally (no cross-package import — matches the established
  `_is_missing`/`_normalize_pypi_name` convention from Stories 13.2/15.2).
- New catalog entries (`artifactory_downloads_raw`, `artifactory_downloads_joined`) are plain
  `pandas.ParquetDataset`, no `ttls:` entry — mirrors the existing non-TTL
  `trending_candidates_classified`-style derived-output precedent (no live fetch cadence exists
  yet to gate on).
- The pipeline contributes exactly one NEW partition key to `derived_purl_exports` — it must not
  read, rewrite, or remove any other partition of that shared dataset.

**Block If:** None identified — the adapter/join reuse, export shape, and no-live-instance
default are all fully determined by the Spec plus the `export_purls.py` /
`derived_artifacts/__init__.py` precedents found during investigation.

**Never:**
- Never add a live `base_url` default, credential entry, or `endpoint_bases`/`extra_overrides`
  catalog entry — that structure is a closed, pinned 19+1 enumeration unrelated to this epic; real
  config/credential resolution stays out of scope (per Story 15.1 Design Notes).
- Never introduce a second/parallel export format or catalog dataset for the mapped-PURL shape —
  the only export path is the new partition inside the existing `derived_purl_exports` entry.
- Never wire an MCP trigger tool for this pipeline (out of CAP-4's stated scope).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default (no repos configured) | `params:artifactory.virtual_repos = []` | Fetch node returns an empty DataFrame (`name`, `version`, `download_count` columns); no adapter/transport constructed | No error |
| Configured repos, injected transport (test-only) | `virtual_repos=["repo-a"]` + a test-supplied mock transport | Fetch node returns `DownloadRow`-shaped rows aggregated across repos, matching Story 15.1's own aggregation | No error |
| Mixed joined rows | Joined DataFrame with one `conda_name`-resolved row and one `is_internal=True` row | Export partition content includes only the resolved row, in exact TSV shape | No error |
| Empty joined DataFrame | Zero rows | Export node returns `{"artifactory_downloads.tsv": "<header only>"}` | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/artifactory_downloads/__init__.py` -- new; re-exports `create_pipeline` (auto-discovered by `find_pipelines()`).
- `.../pipelines/artifactory_downloads/pipeline.py` -- new; 3-node `Pipeline([...])`: fetch → join → export, wired by catalog-name string edges (AD-3).
- `.../pipelines/artifactory_downloads/nodes.py` -- new; `fetch_artifactory_downloads(artifactory_params: dict) -> pd.DataFrame`, `join_artifactory_identity(artifactory_downloads_raw, pypi_conda_mapping, pypi_universe) -> pd.DataFrame`, `format_artifactory_purl_export(artifactory_downloads_joined: pd.DataFrame) -> dict[str, str]`; local `CHANNEL_QUALIFIER`/`g98_pypi_name` reimplementations (no cross-import).
- `.../pyforge/atlas/artifactory/aql_adapter.py`, `identity_join.py`, `__init__.py` -- read-only reference; the Story 15.1/15.2 capabilities this story wires together.
- `.claude/skills/conda-forge-expert/scripts/export_purls.py` (lines ~69-76, ~150-165) -- read-only reference: `MAPPED_TSV_HEADER`, `mapped_tsv_lines`, `g98_pypi_name`, `CHANNEL_QUALIFIER` — the exact shape this story's export node replicates for the reversed direction.
- `.../pipelines/derived_artifacts/__init__.py` -- read-only reference; its docstring names `derived_purl_exports` as "out of B7's ACs and owned by a later story" — this story is that later story, for one partition.
- `conf/base/catalog.yml` -- add `artifactory_downloads_raw` (layer `raw`) and `artifactory_downloads_joined` (layer `derived`) plain `pandas.ParquetDataset` entries; `derived_purl_exports` (line ~797) is read-only reference — already declared, gains a new partition, no YAML edit there.
- `conf/base/parameters.yml` -- add `artifactory: {virtual_repos: []}` — the one new, empty-by-default override point.
- `tests/pipelines/upstream_discovery/test_nodes.py` -- read-only reference for this codebase's pure-node unit-test convention (hand-built `pd.DataFrame` fixtures, no catalog).
- `tests/pipelines/artifactory_downloads/__init__.py` -- new test package marker.
- `tests/pipelines/artifactory_downloads/test_nodes.py` -- new tests, one per I/O Matrix row.

## Tasks & Acceptance

**Execution:**
- [x] `conf/base/parameters.yml` -- add `artifactory: {virtual_repos: []}` -- the one new override point, empty/inert by default.
- [x] `conf/base/catalog.yml` -- add `artifactory_downloads_raw` (raw, `pandas.ParquetDataset`) and `artifactory_downloads_joined` (derived, `pandas.ParquetDataset`) entries -- no TTL.
- [x] `pipelines/artifactory_downloads/nodes.py` -- create the three pure node functions per Code Map; `fetch_artifactory_downloads` must check `virtual_repos` emptiness BEFORE constructing `ArtifactoryConfig`/`ArtifactoryAqlAdapter`; `format_artifactory_purl_export` filters to `conda_name`-resolved rows only and matches `export_purls.py`'s exact TSV shape.
- [x] `pipelines/artifactory_downloads/pipeline.py` -- wire the 3 nodes via `Pipeline([node(...), ...])`, `outputs="derived_purl_exports"` on the export node.
- [x] `pipelines/artifactory_downloads/__init__.py` -- `create_pipeline` re-export.
- [x] `tests/pipelines/artifactory_downloads/test_nodes.py` -- one test per I/O Matrix row, plus a test proving the TSV row/header content matches `export_purls.py::mapped_tsv_lines`'s shape exactly for a resolved row.

**Acceptance Criteria:**
- Given the committed default `parameters.yml` (`artifactory.virtual_repos: []`), when `fetch_artifactory_downloads` runs, then it returns an empty DataFrame and constructs no adapter or transport — no live instance is contacted.
- Given a joined DataFrame with a `conda_name`-resolved row and an `is_internal=True` row, when `format_artifactory_purl_export` runs, then only the resolved row appears in the returned partition content, in `export_purls.py`'s exact mapped-TSV shape.
- Given `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check`, when run after this story's changes, then both pass -- the new pipeline auto-registers via `find_pipelines()`, and the AD-1 no-inline-IO scan covers the new module with zero denylisted imports.

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 1, low 4)
- defer: 1: (high 0, medium 0, low 1)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` `join_artifactory_identity`'s docstring claimed "never raises," but only guarded against missing columns, not malformed cell values -- a `NaN`/`None` `download_count` crashed `int(nan)` with an unhandled `ValueError`, and a `NaN`/`None` `name`/`version` would have silently produced a garbage `"nan"`/`"None"` identity-join key via `str()`. Fixed: row-level `_is_missing()`/`int()`-conversion guard skips malformed rows instead of raising or corrupting; added `test_join_artifactory_identity_skips_rows_with_nan_download_count` and `test_join_artifactory_identity_skips_rows_with_missing_name_or_version`.
  - `[low]` `[patch]` `fetch_artifactory_downloads` used `params.get("virtual_repos") or []` (or-coalesce, handles an explicit `null`) for one param but `params.get("base_url", "")` (default-only-if-absent, does NOT handle an explicit `null`) for the other -- an explicit `base_url: null` would have passed `None` through to `ArtifactoryConfig`. Fixed to the same `or ""` pattern; added `test_explicit_null_base_url_does_not_pass_none_through`.
  - `[low]` `[patch]` `virtual_repos` had no type guard -- a misconfigured bare string (truthy, iterable) would silently iterate per-character, issuing bogus per-character AQL calls instead of a clear error. Added an `isinstance(virtual_repos, (list, tuple))` guard raising `ValueError`; added `test_non_list_virtual_repos_raises_clear_error`.
  - `[low]` `[patch]` The three new ops (`fetch_artifactory_downloads`, `join_artifactory_identity`, `format_artifactory_purl_export`) were absent from `orchestration/definitions.py::NODE_TIMEOUTS`, silently falling back to the generic `DEFAULT_TIMEOUT`, contradicting that module's own documented invariant ("every migrated node appears here explicitly"). Added explicit entries (600s fetch / 120s join / 120s export, sized against comparable existing ops); verified via `tests/orchestration/test_definitions_dryrun.py` (all 76 tests still pass).
  - `[low]` `[patch]` The `derived_purl_exports` catalog comment ("The 6 purl/mapping artifacts as ONE partitioned dataset") was now stale -- this story adds a 7th, unrelated partition. Updated the comment to note it.
  - `[low]` `[defer]` `tests/catalog/conftest.py::PREFIX_TO_PIPELINE` attributes `derived_purl_exports` to the `derived_artifacts` pipeline by naming-prefix convention, but this story adds its first-ever real producer node in the unrelated `artifactory_downloads` pipeline -- a pre-existing prefix-bucketing quirk (the entry was already "declared but unproduced" and mis-bucketed before this diff), not caused by this story. Deferred as `DW-FU-15-3`.
  - `[reject x5]` The MCP-trigger exemption's spec citation was challenged as unverifiable ("no Story 15.3 spec file present") -- verified false; `_bmad-output/implementation-artifacts/spec-15-3-kedro-pipeline-surfacing.md` (this file) exists on disk, just gitignored per the repo's Tier-3 convention, outside the reviewing subagent's search scope. The weekly `bootstrap_data` job silently including the 3 new ops was challenged as contradicting the catalog's "no live fetch cadence" comment -- verified this is the pre-existing, correct default categorization for any pipeline without a special cadence (`bootstrap_ops = node_ops - PHASE_P_OPS`), not a story-introduced defect, and the catalog comment is about TTL-gating (absent `ttls:` param), not Dagster scheduling. `MockArtifactory` test-fixture duplication (vs. `tests/artifactory/test_aql_adapter.py`'s own copy) -- test-fixture independence across modules is an established, defensible pattern in this codebase, not a defect. `_is_missing` triplicated across modules -- explicitly the established, deliberate no-cross-package-`nodes.py`-import convention (already litigated and rejected on this exact point in Story 15.2's own review). Hand-incremented `EXPECTED_TOTAL`/`EXPECTED_PIPELINE_COUNTS` integers in `tests/catalog/conftest.py` -- the same pattern every prior story in this file uses, not a new defect.

### 2026-08-15 — Verify-gate repair pass (deterministic, not a subagent review)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` bmad-loop's deterministic verify command `python scripts/spec_surface_reconcile.py` returned rc=1 (5 findings) against foreign, unrelated `pyforge-marshal` specs -- zero surface overlap with this story's own diff (confined to `src/shared/packages/pyforge-atlas/**`). Traced each finding: `spec-fleet-status-supervisor-fallback` and `spec-landing-evidence-grammar` both incidentally govern `core/status.py`/`cli/status.py`/`core/promotion.py`, which moved under an unrelated, already-shipped fix (`spec-marshal-land-cross-project-story-key-collision`, commits `d7fd62707b` + review-pass `ec5a4e3da2`) without that spec's own capability being touched (verified via targeted `git diff`/`git show` against the exact commits); `spec-marshal-land-cross-project-story-key-collision` itself had no baseline entry (`[no-baseline]`, empty `surface:`, first stamp, zero risk). Documented the incidental overlap in both foreign memlogs (matching each spec's own established reconcile-note convention) and scoped-stamped all three via `python scripts/spec_surface_check.py --write-baseline --spec <name>` (never a bare `--write-baseline`); verified the resulting baseline diff was exactly 1 added / 2 changed / 0 removed with no other spec's key touched. Re-ran this story's own verify commands (`kedro-test`: 1179 passed; `kedro-catalog-check`: 48 passed) to confirm no regression. Committed as `d8a84c5a1a`.

## Design Notes

`derived_purl_exports` (`conf/base/catalog.yml:797`) is a `partitions.PartitionedDataset` over
`text.TextDataset`, recorded as "the 6 purl/mapping artifacts as ONE partitioned dataset,"
currently declared but unproduced (`derived_artifacts/__init__.py`'s own docstring: "out of B7's
ACs and is owned by a later story"). Kedro's `PartitionedDataset.save()` writes only the
partition keys given in the returned dict — it never deletes or touches partitions absent from
that dict — so this story's node can contribute its own `artifactory_downloads.tsv` partition
without needing (or being blocked by) the other 5 legacy artifacts' producers, which remain
future work.

`export_purls.py::mapped_tsv_lines` filters on "has a non-empty `pypi_name`" because that legacy
artifact is keyed conda-first (conda packages that also map to PyPI). This story's data is
keyed pypi-first (Artifactory downloads that may or may not map to conda) — the mirror-image
filter is "has a resolved `conda_name`," which is exactly the boolean this story's `is_internal`
flag already inverts (a `conda_name`-resolved row is never `is_internal=True` — see Story 15.2's
Boundaries). `match_confidence` is left blank (not a fabricated token): the Phase C/C.5
`pypi_conda_mapping` this join reuses never carried a confidence column, so blank is the literal
truth, matching the legacy code's own `p['match_confidence'] or ''` fallback rather than
inventing a new value.

Config/credential resolution for a REAL Artifactory instance is explicitly out of scope here too
(same as Story 15.1) — `params:artifactory.virtual_repos` defaulting to `[]` is what keeps the
committed pipeline structurally wired but functionally inert; a later, attended bring-up sets
real values and injects a real transport, exactly as Epic 16's `LaSuiteClient`/`WikiSyncer`
pattern defers its real `Opener` construction outside package code.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` -- expected: full suite passes, including the new `tests/pipelines/artifactory_downloads/test_nodes.py`.
- `pixi run -e pyforge-atlas kedro-catalog-check` -- expected: passes with the two new catalog entries and zero denylisted imports in the new pipeline package.

## Auto Run Result

Status: `done`

**Summary:** New `pipelines/artifactory_downloads/` Kedro pipeline (fetch → join → export, 3 pure
nodes) wires Story 15.1's `ArtifactoryAqlAdapter` and Story 15.2's `join_identity` into the
catalog and contributes exactly one new partition (`artifactory_downloads.tsv`) to the existing
`derived_purl_exports` `PartitionedDataset`, in `export_purls.py`'s exact mapped-TSV shape
mirrored for the pypi→conda direction. Default `params:artifactory.virtual_repos: []` keeps the
fetch node fully inert -- no adapter/transport constructed, no live instance contacted.

**Files changed:**
- `conf/base/parameters.yml` -- `artifactory: {virtual_repos: []}` override point.
- `conf/base/catalog.yml` -- `artifactory_downloads_raw`/`artifactory_downloads_joined` entries.
- `pipelines/artifactory_downloads/{__init__,nodes,pipeline}.py` -- new pipeline package.
- `orchestration/definitions.py` -- `NODE_TIMEOUTS` entries for the 3 new ops (review pass 1).
- `tests/pipelines/artifactory_downloads/test_nodes.py` -- one test per I/O Matrix row + TSV-shape parity test + review-pass edge-case tests.
- `tests/catalog/conftest.py` -- updated `derived_purl_exports` comment (review pass 1).

**Review findings breakdown:** Review pass 1 (2026-08-15): 5 patch (0 high, 1 medium, 4 low), 1 defer (`DW-FU-15-3`), 5 reject. Verify-gate repair pass (2026-08-15): 1 patch (medium) -- see Review Triage Log above; not a code defect in this story's own diff, a repo-level `spec_surface_reconcile.py` gate tripped by unrelated, already-shipped `pyforge-marshal` drift.

**Verification performed:** `pixi run -e pyforge-atlas kedro-test` (1179 passed, 19 skipped), `pixi run -e pyforge-atlas kedro-catalog-check` (48 passed), `python scripts/spec_surface_reconcile.py` (rc=0, all three of bmad-loop's deterministic verify commands green).

**Residual risks:** None new from this story's own diff. Pre-existing, deferred: `DW-FU-15-3` (`tests/catalog/conftest.py::PREFIX_TO_PIPELINE` mis-buckets `derived_purl_exports` to `derived_artifacts` by naming convention, unrelated to this story).

