---
title: 'Identity join and internal flag (Story 15.2, CAP-2, CAP-3)'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'e01536e7c7ece99a8a733ea5a1c0ba715ff52107'
final_revision: 'f9fc57b8eaae855aad9e2fa2601a3cea3e309a3f'
---

<intent-contract>

## Intent

**Problem:** Story 15.1's `ArtifactoryAqlAdapter` produces raw `DownloadRow`s (`name`,
`version`, `download_count`) with no connection to atlas's identity space and no signal for
whether a package is even publicly known — an Artifactory-observed package can't yet be
resolved to the same `conda_name` every other atlas signal uses, or flagged when it has no
public PyPI counterpart at all.

**Approach:** Add a pure join function that resolves each `DownloadRow` against atlas's
already-materialized Phase C/C.5 identity mapping (`pypi_conda_mapping`) to attach
`conda_name`/`match_source`, and independently checks Phase D's universe enumeration
(`pypi_universe`) to set a boolean `is_internal` flag — true iff the package is absent from
the public universe. Both inputs are existing DataFrames passed in; nothing is re-fetched.

## Boundaries & Constraints

**Always:**
- The identity join reuses ONLY the already-materialized `pypi_conda_mapping` (Phase C/C.5)
  and `pypi_universe` (Phase D) catalog outputs, passed in as plain `pd.DataFrame` arguments
  — no new PyPI-metadata or conda-forge-crossref fetch path anywhere in the diff.
- `is_internal` is derived SOLELY from a `DownloadRow.name`'s absence from `pypi_universe`
  (PEP-503-normalized membership), independent of whether it also matches
  `pypi_conda_mapping`. A public PyPI package with no conda-forge feedstock (present in the
  universe, absent from the mapping) is NOT internal — it has a public counterpart.
- Name matching uses the same PEP 503 normalization (`lowercase; collapse runs of -_. to -`)
  Phase C/C.5/D's own consumers use, so a match here is the identical match those phases would
  produce. Reimplement this normalization locally in the new module rather than importing it
  from `upstream_discovery/nodes.py` — this codebase's established rule is that no pipeline
  package imports another's `nodes.py` (stated explicitly in that module's `_is_missing`
  docstring).
- An unusable `pypi_universe` (empty, missing the `pypi_name` column, or carrying zero
  non-null names — e.g. `PHASE_D_UNIVERSE_DISABLED=1`) must NOT cause every row to be flagged
  `is_internal=True`; that would be a confident false claim from a signal that was never
  searchable. Degrade to `is_internal=False` for all rows in that case (mirrors the
  `universe_usable` guard in `upstream_discovery/nodes.py::classify_trending_candidates`).
  The identity join against `pypi_conda_mapping` still proceeds independently.
- An unusable `pypi_conda_mapping` degrades every row's `conda_name`/`match_source` to `None`
  — never raises.
- The function never raises on empty/malformed input DataFrames.

**Block If:** None identified — CAP-2/CAP-3's join keys, flag semantics, and degradation
policy are fully determined by the Spec plus the established `classify_trending_candidates`
precedent.

**Never:**
- Never wire this into a Kedro pipeline, catalog entry, or dataset (that is Story 15.3 /
  CAP-4).
- Never introduce a second identity-mapping path, cache, or re-fetch of parselmouth/PyPI/
  conda-forge data — enrich only through `pypi_conda_mapping`/`pypi_universe` as given.
- Never import another pipeline package's `nodes.py` module.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Public package, has a feedstock | `DownloadRow(name="requests", ...)`; both tables contain a normalized match | `conda_name`/`match_source` populated from the mapping row; `is_internal=False` | No error expected |
| Mock-only package | `DownloadRow(name="acme-internal-tool", ...)` absent from both tables | `conda_name=None`, `match_source=None`, `is_internal=True` | No error expected |
| Public PyPI package, no feedstock | Name present in `pypi_universe`, absent from `pypi_conda_mapping` | `conda_name=None`, `match_source=None`, `is_internal=False` (has a public counterpart) | No error expected |
| Casing/separator variant | `DownloadRow(name="My_Package")` vs. universe entry `"my-package"` | Matches via PEP 503 fold — same behavior as a raw match, not a false negative | No error expected |
| Empty/malformed `pypi_universe` | Table is empty or missing `pypi_name` | Every row degrades to `is_internal=False`; identity join against `pypi_conda_mapping` still runs normally | No error raised |
| Empty/malformed `pypi_conda_mapping` | Table is empty or missing `pypi_name`/`conda_name` | Every row's `conda_name`/`match_source` is `None`; `is_internal` still resolved independently | No error raised |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/identity_join.py` -- new
  module: `JoinedDownloadRow` dataclass + `join_identity()` function -- the sole new
  capability this story adds.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/aql_adapter.py` -- read-only
  reference; `DownloadRow` is this module's input row shape (`name`, `version`,
  `download_count`).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/__init__.py` -- add
  `JoinedDownloadRow`/`join_identity` to the package's re-export surface (alongside 15.1's
  exports) for Story 15.3 to import.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/nodes.py`
  -- read-only reference (lines ~110-200, ~275-345): `_normalize_pypi_name`,
  `_normalized_pypi_index`, `_is_missing`, and `classify_trending_candidates`'s
  usable/degrade pattern -- the shape this story's join+flag logic follows.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py`
  -- read-only reference, lines ~95-134 (`match_source_urls`) and ~623-674
  (`_MAP_PROVENANCE_RANK`, `export_pypi_conda_map`). **Critical:** the persisted
  `pypi_conda_mapping` catalog dataset is deduplicated only on `subset=["pypi_name",
  "conda_name"]` (line ~134), NOT on `pypi_name` alone -- it can and does legitimately
  carry multiple rows for the same `pypi_name` with different `conda_name`/`match_source`
  values (e.g. a `g10_spelling` row and a weaker `recipe_source_url` candidate). This
  codebase already has the canonical, deterministic, order-independent resolution for
  that ambiguity: `_MAP_PROVENANCE_RANK = {"g10_spelling": 3, "parselmouth": 2,
  "recipe_source_url": 2}` (unlisted/non-string `match_source` -> rank 1), with a
  lexicographic-`conda_name` tie-break on equal rank, proven order-independent by
  `tests/.../test_mapping_export.py::test_equal_tier_collision_is_order_independent_deterministic`
  and `test_g10_spelling_survives_and_is_not_clobbered`. This story's identity join MUST
  replicate that exact rank + tie-break rule (reimplemented locally, not imported --
  same no-cross-package-`nodes.py`-import convention as `_normalize_pypi_name`/
  `_is_missing`) when collapsing `pypi_conda_mapping` to one row per normalized
  `pypi_name` -- a naive first-seen/`setdefault` collapse can pick a lower-provenance
  `conda_name` than Phase C/C.5's own export would, which directly breaks this story's
  own acceptance bar ("the public package resolves to the identical identity row Phase
  C/C.5 would produce"). Found in review pass 1 (2026-08-15): two independent reviewers
  (Blind Hunter, Edge Case Hunter), given no shared context, both surfaced this
  independently.
- `src/shared/packages/pyforge-atlas/tests/pipelines/pypi_intelligence/test_mapping_export.py`
  -- read-only reference; the existing test fixtures proving the rank/tie-break rule's
  order-independence -- model this story's new duplicate-row test on these.
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` -- read-only reference; confirms
  `pypi_universe` (`pypi_name`, `last_serial`) and `pypi_conda_mapping` (`pypi_name`,
  `conda_name`, `match_source`) column shapes this story joins against.
- `src/shared/packages/pyforge-atlas/tests/artifactory/test_identity_join.py` -- new tests.
- `src/shared/packages/pyforge-atlas/tests/artifactory/test_aql_adapter.py` -- read-only
  reference for the test package's existing fixtures/conventions.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/identity_join.py` --
  create the module: `JoinedDownloadRow` (frozen dataclass: `pypi_name: str`, `version: str`,
  `download_count: int`, `conda_name: str | None`, `match_source: str | None`,
  `is_internal: bool`); local `_normalize_pypi_name`/`_is_missing` helpers (reimplemented, not
  imported, per the no-cross-package-nodes-import rule); a local `_MAP_PROVENANCE_RANK`
  constant + rank/tie-break resolution copied from `pypi_intelligence/nodes.py`'s
  `export_pypi_conda_map` (see Code Map -- reimplemented, not imported, same convention);
  `join_identity(rows: list[DownloadRow], pypi_conda_mapping: pd.DataFrame, pypi_universe:
  pd.DataFrame) -> list[JoinedDownloadRow]` -- builds a normalized universe-membership index
  once, and a normalized `{name: (conda_name, match_source)}` mapping index once by collapsing
  `pypi_conda_mapping` per normalized `pypi_name` using the SAME provenance-rank + lexicographic
  tie-break rule as `export_pypi_conda_map` (strictly-higher rank wins; on an equal-rank
  collision with a different `conda_name`, the lexicographically smaller `conda_name` wins --
  never a naive first-seen/`setdefault` collapse), then resolves each row against both indexes
  per the Boundaries' degradation rules.
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/__init__.py` --
  re-export `JoinedDownloadRow`, `join_identity`.
- [x] `src/shared/packages/pyforge-atlas/tests/artifactory/test_identity_join.py` -- one test
  per I/O Matrix row (public-with-feedstock, mock-only, public-no-feedstock, casing/separator
  variant, empty/malformed universe, empty/malformed mapping) plus a duplicate-name-across-rows
  passthrough case, PLUS two new tests proving the provenance-rank collapse: (a) `pypi_conda_mapping`
  carries two rows for the same normalized `pypi_name` with different ranked `match_source`
  values (e.g. `g10_spelling` vs. `recipe_source_url`) in BOTH row orders -- the higher-rank
  row's `conda_name`/`match_source` wins regardless of which row comes first in the DataFrame;
  (b) an equal-rank collision with two different `conda_name` values -- the lexicographically
  smaller `conda_name` wins, deterministically, in both row orders. Model these two on
  `tests/pipelines/pypi_intelligence/test_mapping_export.py`'s
  `test_g10_spelling_survives_and_is_not_clobbered` /
  `test_equal_tier_collision_is_order_independent_deterministic`. Proves the whole CAP-2/CAP-3
  success signal offline against hand-constructed `pd.DataFrame` fixtures (no catalog, no live
  tables).

**Acceptance Criteria:**
- Given a mock-served public package and a mock-only package as `DownloadRow`s plus
  hand-built `pypi_conda_mapping`/`pypi_universe` fixtures, when `join_identity` runs, then
  the public package resolves to the identical `conda_name`/`match_source` the fixture's
  mapping row carries, and exactly the mock-only package carries `is_internal=True`.
- Given the full test suite for this module, when it runs, then no case raises on an empty or
  malformed input DataFrame -- every scenario degrades per the I/O Matrix.
- Given `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas
  kedro-catalog-check`, when run after this story's changes, then both pass unmodified -- the
  new module needs no catalog entry, pipeline registration, or gate exemption (Story 15.3
  owns wiring this into a real pipeline).

## Spec Change Log

### 2026-08-15 — Review pass 1, bad_spec repair
- **Triggering finding:** Two independent reviewers (Blind Hunter, Edge Case Hunter -- no
  shared context) both surfaced that `_normalized_mapping_index`'s `setdefault`-based collapse
  picks whichever `pypi_conda_mapping` row for a given `pypi_name` happens to be first in
  DataFrame order, rather than the codebase's own canonical, tested provenance-rank + tie-break
  rule (`_MAP_PROVENANCE_RANK` in `pypi_intelligence/nodes.py::export_pypi_conda_map`).
  Verified directly against the codebase: `match_source_urls` dedupes `pypi_conda_mapping` only
  on `["pypi_name", "conda_name"]`, so multi-row-per-`pypi_name` is a real, reachable shape, not
  speculative.
- **What was amended:** Code Map (added `pypi_intelligence/nodes.py` lines ~623-674 and
  `tests/pipelines/pypi_intelligence/test_mapping_export.py` as required reading), Tasks &
  Acceptance (the module task now requires replicating `_MAP_PROVENANCE_RANK` locally; the test
  task now requires two additional tests proving the rank + tie-break collapse in both row
  orders), Design Notes (added the "Provenance-rank collapse" rationale). `<intent-contract>`
  (Intent/Boundaries/I-O Matrix) was NOT modified -- the acceptance bar it already states
  ("identical identity row Phase C/C.5 would produce") was always correct; only the
  implementation guidance needed to name the precedent that makes it achievable.
- **Known-bad state avoided:** a `join_identity` call that resolves a real ambiguous-provenance
  package to a non-canonical (possibly lower-quality-match, non-deterministic-by-row-order)
  `conda_name`, silently diverging from what every other atlas signal would report for the same
  package.
- **KEEP instructions (must survive re-derivation):** the overall module shape (`join_identity`
  as a plain function over `pd.DataFrame` args, living in `artifactory/`, not a Kedro node); the
  `is_internal` degradation policy (unusable `pypi_universe` -> `False` for every row, never
  `True`); local reimplementation (not import) of `_normalize_pypi_name`/`_is_missing`, matching
  the established no-cross-package-`nodes.py`-import convention; the `JoinedDownloadRow` field
  shape (`pypi_name`, `version`, `download_count`, `conda_name`, `match_source`, `is_internal`);
  all 7 original I/O-Matrix test scenarios (public-with-feedstock, mock-only,
  public-no-feedstock, casing/separator variant, empty/malformed universe x2, empty/malformed
  mapping x2, duplicate-name-across-rows) -- these were correctly implemented and must be
  preserved, only extended with the two new provenance-rank tests.

## Review Triage Log

### 2026-08-15 — Review pass 1
- intent_gap: 0
- bad_spec: 1: (high 1, medium 0, low 0)
- patch: 3: (high 0, medium 1, low 2)
- defer: 1: (high 0, medium 1, low 0)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[high]` `[bad_spec]` `_normalized_mapping_index` collapsed duplicate-`pypi_name` rows in
    `pypi_conda_mapping` via naive first-seen `setdefault` instead of the codebase's canonical
    `_MAP_PROVENANCE_RANK` rank + lexicographic tie-break rule (`export_pypi_conda_map`),
    risking a non-canonical/non-deterministic `conda_name` resolution and breaking this story's
    own "identical identity row" acceptance bar -- spec amended (Code Map, Tasks, Design Notes)
    and code reverted for re-derivation via `./step-03-implement.md`.

### 2026-08-15 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 1, low 3)
- defer: 0
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` Two `pypi_conda_mapping` rows sharing the same `pypi_name` AND the
    same `conda_name` but different equal-rank `match_source` values (e.g. `parselmouth` vs.
    `recipe_source_url`, both rank 2) resolved to whichever row happened to come first --
    order-dependent, contradicting the module's own "deterministic, order-independent" claim
    (though `conda_name`/`is_internal` were never affected, only the `match_source` label) --
    extended `_normalized_mapping_index`'s tie-break to a third level: same rank + same
    `conda_name` now breaks on the lexicographically smaller `match_source` too; added
    `test_equal_tier_same_conda_name_different_match_source_is_order_independent` (both row
    orders).
  - `[low]` `[patch]` `join_identity(rows=None, ...)` raised `TypeError` at `for row in rows`
    while the two DataFrame args both degrade gracefully on `None` -- added a `if not rows:
    return []` guard; added `test_none_rows_returns_empty_list_without_raising`.
  - `[low]` `[patch]` `_normalized_universe_index`'s docstring pointed at a nonexistent
    "`_MAP_PROVENANCE_RANK` docstring" for the `is_internal` degradation rationale -- corrected
    to point at `join_identity`'s own docstring, where that rationale actually lives.
  - `[low]` `[patch]` Module docstring claimed the collapse "replicates the exact,
    already-tested rule" `export_pypi_conda_map` uses without noting two real differences (this
    module keys by the PEP-503-normalized name, not the raw name; and additionally tracks/
    tie-breaks on `match_source`, which that precedent does not) -- reworded to state the rank
    + tie-break RULE is replicated, and named both differences explicitly so the claim doesn't
    overstate parity.
  - `[reject x5]` Unhashable/list `match_source` cell hardening (speculative malformed input
    beyond any realistic Parquet-sourced shape, matching pass 1's precedent for rejecting
    exotic-malformation hardening); `universe_usable`'s no-minimum-coverage-floor (exactly
    matches `classify_trending_candidates`'s own established `bool(pypi_index)` threshold --
    not a deviation this story introduced); `JoinedDownloadRow.pypi_name` carrying the raw,
    non-normalized name (deliberate -- the row should reflect the actually-observed name, not
    a normalized fold); the triple hand-copy of `_is_missing`/`_normalize_pypi_name` across
    three modules (matches the established, deliberate no-cross-package-`nodes.py`-import
    convention, not a new defect); unguarded `DownloadRow.name=None` (recurring from pass 1 --
    `DownloadRow` is only ever constructed by `fetch_download_rows` with an already-`str`-cast
    name; matches pass 1's rejection of hardening beyond the real construction path).

## Design Notes

`join_identity` is a plain function over `pd.DataFrame` inputs, not a Kedro node -- it lives
in `artifactory/`, a sibling of `pipelines/` that Kedro's `find_pipelines(raise_errors=True)`
never touches, matching Story 15.1's shape (a callable capability Story 15.3 later imports
into an actual pipeline node). Accepting `pd.DataFrame` here (rather than converting to plain
dicts) is deliberate: `pypi_conda_mapping`/`pypi_universe` are exactly the DataFrames Story
15.3's Kedro node will receive from the catalog, so no shape conversion is needed at the
pipeline-wiring boundary.

The `is_internal` degradation policy (unusable universe -> `False` for every row, never `True`)
is this story's one non-obvious design decision, not stated verbatim in the Spec. It mirrors
`classify_trending_candidates`'s `universe_usable` guard: an empty/disabled Phase D table
(`PHASE_D_UNIVERSE_DISABLED=1` is a documented, legitimate opt-out -- AD-13) must not silently
relabel every package "private" just because the public signal used to disprove that claim
wasn't available this run.

**Provenance-rank collapse (added in review pass 1).** `pypi_conda_mapping` is NOT
pre-collapsed to one row per `pypi_name` -- `match_source_urls` only dedupes on
`["pypi_name", "conda_name"]`, so two rows for the same `pypi_name` with different
`conda_name`/`match_source` values are a real, reachable shape of the persisted table, not a
theoretical one. Picking whichever row happens to be first in DataFrame iteration order (a
naive `setdefault`) is both non-deterministic (Parquet row order is not a stable contract) and
can pick a lower-provenance `conda_name` than Phase C/C.5's own canonical export would --
directly breaking this story's "identical identity row" acceptance bar. `export_pypi_conda_map`
(`pypi_intelligence/nodes.py`) already solves this exact ambiguity for exactly this table with
a proven, tested rule: `_MAP_PROVENANCE_RANK` (`g10_spelling` > `parselmouth`/
`recipe_source_url` > unknown), strictly-higher-rank wins, and on an equal-rank collision the
lexicographically smaller `conda_name` wins (a deterministic tie-break, not a preference
signal). This story's `_normalized_mapping_index` must replicate that identical rule (locally
reimplemented, per the same no-cross-import convention already governing
`_normalize_pypi_name`/`_is_missing`) rather than a plain `setdefault`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` -- expected: full suite passes, including the new
  `tests/artifactory/test_identity_join.py`.
- `pixi run -e pyforge-atlas kedro-catalog-check` -- expected: passes unchanged (no-inline-IO /
  AD-1 scan covers the new module automatically; no catalog entries added).

## Auto Run Result

Status: done

**Summary:** Implemented Story 15.2 (CAP-2/CAP-3) -- `join_identity()`, a pure function
resolving Story 15.1's `DownloadRow`s against atlas's identity space: attaches
`conda_name`/`match_source` from the already-materialized `pypi_conda_mapping` (Phase C/C.5),
and independently flags `is_internal` from `pypi_universe` (Phase D) membership. Ships in a new
`artifactory/identity_join.py` module (not a Kedro node -- Story 15.3 owns pipeline wiring). A
review-pass-1 finding (below) required amending the spec and re-deriving the collapse logic to
replicate the codebase's canonical `_MAP_PROVENANCE_RANK` provenance-rank + tie-break rule
(`pypi_intelligence/nodes.py::export_pypi_conda_map`) rather than a naive first-seen collapse,
since `pypi_conda_mapping` can legitimately carry multiple rows per `pypi_name`.

**Files changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/identity_join.py` (new) --
  `JoinedDownloadRow`, `join_identity()`, `_normalized_universe_index()`,
  `_normalized_mapping_index()` (provenance-rank + lexicographic `conda_name`/`match_source`
  tie-break collapse, locally reimplemented from `export_pypi_conda_map`), local
  `_normalize_pypi_name()`/`_is_missing()`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/__init__.py` -- re-exports
  `JoinedDownloadRow`/`join_identity` for Story 15.3.
- `src/shared/packages/pyforge-atlas/tests/artifactory/test_identity_join.py` (new) -- 12 tests:
  the 7 original I/O-Matrix scenarios, the provenance-rank collapse (both row orders, plain and
  same-`conda_name`-different-`match_source` collisions), and a `rows=None`/empty-`rows` case.

**Review findings breakdown (Blind Hunter + Edge Case Hunter, parallel, no shared context,
2 passes):**
- **Pass 1:** 1 bad_spec (high) -- both reviewers independently found the mapping collapse used
  a naive first-seen `setdefault` instead of the codebase's own canonical
  `_MAP_PROVENANCE_RANK` rank + tie-break rule, risking a non-canonical/non-deterministic
  `conda_name` resolution and breaking the story's own "identical identity row" acceptance bar.
  Verified directly against the codebase (`match_source_urls` dedupes only on
  `["pypi_name", "conda_name"]`, so multi-row-per-`pypi_name` is real, not speculative). Spec
  amended (Code Map, Tasks, Design Notes -- `<intent-contract>` untouched), code reverted,
  re-derived via a fresh implementation pass. 3 patch, 1 defer, 5 reject also logged (moot this
  pass per the bad_spec-cascades rule).
- **Pass 2:** 4 patch (1 medium, 3 low), 5 reject -- all auto-fixed: extended the tie-break to a
  third level (`match_source`) for the narrow case of two equal-rank rows sharing the same
  `conda_name` but differing `match_source` (both reviewers converged on this independently); a
  `rows=None` guard (symmetry with the two DataFrame args' existing `None` guards); two
  docstring corrections (a broken cross-reference, an overclaim re: raw-vs-normalized keying
  parity with `export_pypi_conda_map`). Rejects: speculative unhashable/malformed-cell
  hardening, `universe_usable`'s coverage floor (matches established precedent exactly),
  `JoinedDownloadRow.pypi_name` carrying the raw name (deliberate), the triple hand-copy of
  `_is_missing`/`_normalize_pypi_name` (established convention), and `DownloadRow.name=None`
  (recurring from pass 1, still unrealistic given the sole real construction path).

**Follow-up review recommendation:** false -- pass 2's patched findings are localized to one
function's tie-break logic plus a defensive guard and two docstring corrections, low-to-medium
severity, with no API/behavior/security/data-model surface change (no existing caller yet --
Story 15.3 is the first consumer).

**Verification performed:**
- `pixi run -e pyforge-atlas kedro-test` -- 1161 passed, 19 skipped (up from 1147 baseline;
  all 12 new tests in `test_identity_join.py` pass individually too).
- `pixi run -e pyforge-atlas kedro-catalog-check` -- 48 passed, unchanged (no catalog entry,
  no pipeline wiring added; the no-inline-IO/AD-1 scan covers the new module automatically).

**Residual risks:** None blocking. The provenance-rank collapse logic is now a THIRD local copy
of a rule that also exists (in a `conda_name`-only form) in `pypi_intelligence/nodes.py` and (in
a name-normalization-only form) in `upstream_discovery/nodes.py` -- matches this codebase's
established, deliberate no-cross-package-`nodes.py`-import convention, not a new defect, but
noted for awareness. Story 15.3's own spec should account for `join_identity`'s per-call index
rebuild cost if it is ever invoked more than once per full pipeline run.
