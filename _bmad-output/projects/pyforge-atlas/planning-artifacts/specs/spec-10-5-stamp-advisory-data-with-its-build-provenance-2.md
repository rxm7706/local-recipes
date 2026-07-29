---
title: 'Stamp advisory data with its build provenance (AD-17)'
type: 'feature'
created: '2026-07-28'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: true  # pass 3 (fresh follow-up): 0 bad_spec, 7 patches auto-fixed (2 medium: a reproduced datetime/ns fetched_at ValueError crash + missing failure isolation in the provenance seam) — new defensive logic in provenance.py warrants one independent look; gates green (800/19, 47/47)
context: []
warnings: ['oversized']
baseline_revision: 'fd2fd0b260a1f59164afc9314de268e2cd7abedc'
final_revision: '6696543a68ef790571d7ad4adc0e7247ad0a0f82'
---

<intent-contract>

## Intent

**Problem:** `read_dataset` and 7 of 8 dashboard pages carry no freshness marker
(AUD-ATLAS-043/044). A first attempt (2026-07-28, reverted) stamped `read_dataset`
with wall-clock-now at call time — this was CRITICALLY escalated and rejected: a
read-time stamp can never distinguish fresh data from stale (a month-old dataset
reports "now"), violating AD-13 and the canonical AD-17 definition (a payload
carries **the data's own build timestamp**, not a read receipt). The escalation was
resolved: `epics.md` Story I4 now carries binding ACs C1-C6 requiring genuine
per-dataset-KIND provenance instead of a fabricated clock read.

**Approach:** Add a new module, `pyforge.atlas.provenance`, that derives a
dataset's real provenance by KIND: `IncrementalParquetDataset` → its own
`fetched_at` column (oldest+newest); `pandas.ParquetDataset` → the materialized
file's mtime; `api.APIDataset` → `now` (the read genuinely IS the fetch); anything
else → `null` + a stated reason. `read_dataset` wraps its return in a
`{schema_version, dataset, provenance_kind, build_stamp, build_stamp_newest,
reason, value}` envelope built from this module. `dashboard/app.py` threads the
same per-page provenance (derived from the actual backing Parquet file, not
render time) into every non-factory-status page's legibility Card.

## Boundaries & Constraints

**Always:**
- Provenance comes from the dataset's own recorded state (a `fetched_at` column
  value, a file's mtime, or a live-fetch instant) — never from the clock standing
  in for data that already existed before the call.
- `read_dataset`'s envelope adds exactly: `schema_version` (str, `"1"`), `dataset`
  (the requested name), `provenance_kind` (one of `row-fetched-at` / `file-mtime`
  / `live-fetch` / `unavailable` — C2), `build_stamp` (ISO-8601 or `null`),
  `build_stamp_newest` (ISO-8601 or `null`; only meaningful for `row-fetched-at`),
  `reason` (str or `null`; populated only when `provenance_kind == "unavailable"`),
  `value` (the existing coerced return, byte-for-byte unchanged).
- For `row-fetched-at`, `build_stamp` is the OLDEST `fetched_at` in the loaded
  frame and `build_stamp_newest` the newest (C3 — any staleness judgment a
  consumer makes must use the worst case). Ignore individual NULL cells in the
  column; if every value is NULL or the frame has 0 rows, fall back to
  `unavailable` with a reason — never crash on an empty/all-null column.
- `null` + a stated `reason` is a REQUIRED, valid, non-error response when no
  genuine provenance exists (C4) — never fabricate a plausible value.
- New provenance-resolution logic (kind dispatch, file stat, DataFrame column
  read) lives in a module OUTSIDE `mcp/` — `mcp/tools.py`'s AD-7 AST gate
  (`tests/mcp/test_no_business_logic_in_tool_bodies.py`) denies importing
  pandas/numpy/duckdb/sqlite3/sqlalchemy/ibis/pyarrow in 5 named files and
  restricts every call inside a `tools.py` function body to a fixed
  `ALLOWED_CALL_ROOTS` set. Route ALL catalog/dataset introspection through the
  new module as a single seam call, mirroring the existing `_session`/`_nl` seam
  pattern, and add the new seam's import alias to `ALLOWED_CALL_ROOTS`.
- Every dashboard page's legibility/stamp Card text states ITS OWN data's
  provenance (not dashboard-render time) and contains the literal substring
  `AD-17` (C6).
- An unknown dataset name still raises whatever `catalog.load` raises — the
  envelope wraps only the success path.

**Block If:** none identified — C1-C6 fully specify the mechanism and this pass's
investigation grounded every piece (catalog dataset-kind inventory, the
`IncrementalParquetDataset.fetched_at` column, kedro's `catalog[name]`/`_describe()`
API, the AD-7 AST gate's exact rules) against the live code; no further human
decision is required.

**Never:**
- Do not compute `build_stamp` as `datetime.now()`/wall-clock-at-call for any
  kind except `live-fetch` (`api.APIDataset`), where "now" is correct because the
  read IS the fetch.
- Do not touch `_factory_page`/`factory-status`'s existing stamp Card or
  `run_pipeline`'s return shape.
- Do not invent a new persistent freshness-tracking mechanism (a run manifest, a
  metadata DB, etc.) — the escalation's resolution confirmed genuine provenance
  already exists (`fetched_at` columns, file mtimes) and needs no inventing.
- Do not add a computed boolean staleness VERDICT (e.g. `is_stale`) to the
  envelope — C1-C6 requires surfacing the timestamp(s) for the consumer to judge,
  not a verdict.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `IncrementalParquetDataset`, rows present | `read_dataset("core_downloads")` | `provenance_kind="row-fetched-at"`; `build_stamp`=oldest `fetched_at` (ISO-8601); `build_stamp_newest`=newest; `reason=null` | No error expected |
| `IncrementalParquetDataset`, 0 rows or all-NULL `fetched_at` | same, empty/degenerate frame | `provenance_kind="unavailable"`; `build_stamp=null`; `reason` states no provenance rows | No error expected |
| `pandas.ParquetDataset` | `read_dataset("core_feedstock_health")` | `provenance_kind="file-mtime"`; `build_stamp`=the file's mtime (ISO-8601); `build_stamp_newest=null` | No error expected |
| `api.APIDataset` | `read_dataset("core_repodata_raw")` | `provenance_kind="live-fetch"`; `build_stamp`≈now; `build_stamp_newest=null` | No error expected |
| Unsupported dataset type (e.g. `json.JSONDataset`) | `read_dataset("sbom_normalized_bom_entry")` | `provenance_kind="unavailable"`; `build_stamp=null`; `reason` names the dataset's type | No error expected |
| Unknown dataset name | `read_dataset("no_such_ds")` | No envelope constructed | Propagates `catalog.load`'s exception unchanged |
| Dashboard grounded/bsl-shell page, backing Parquet present | `build_dashboard(data_root=<dir with a real file>)` | That page's Card text contains the file's mtime (ISO-8601) + `AD-17` | No error expected |
| Dashboard bsl-shell page, composed store not yet materialized (today's default state) | `build_dashboard()` (default `data_root`) | `staleness-report`/`query-atlas`/`detail-cf-atlas` Cards state "unavailable" + `AD-17`; page still renders with an empty grid | No error expected |
| Dashboard no-bsl-shell page | `behind-upstream` / `whodepends` | Card states no data function is registered + `AD-17` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/provenance.py` (NEW) --
  `ProvenanceInfo` frozen dataclass (`kind`, `build_stamp`, `build_stamp_newest`,
  `reason`), `SCHEMA_VERSION = "1"`, `resolve_for_file(path) -> ProvenanceInfo`
  (file-mtime or unavailable-if-missing), `resolve_for_catalog_dataset(catalog,
  name, loaded_value) -> ProvenanceInfo` (isinstance-dispatches on
  `catalog[name]`'s type: `pyforge.atlas.datasets.IncrementalParquetDataset` →
  reads `loaded_value[dataset._describe()["fetched_at_column"]]` oldest/newest;
  `kedro_datasets.pandas.ParquetDataset` → delegates to `resolve_for_file` using
  `dataset._describe()["filepath"]`; `kedro_datasets.api.APIDataset` →
  live-fetch/now; else → unavailable with the type name as reason). Lives
  outside `mcp/` — free to import pandas/kedro_datasets since the AD-7 gate only
  scans `mcp/tools.py` + 4 named siblings, never this file.
  **[review pass 1, bad_spec fix]** Before converting a `fetched_at` value with
  `datetime.fromtimestamp`, normalize millisecond-magnitude values to seconds
  the SAME way `IncrementalParquetDataset` itself already does — reuse or
  mirror its `_MS_EPOCH_THRESHOLD` guard (documented there for exactly this
  case: Phase F/I writers produce ms-source stamps). Skipping this crashes
  `read_dataset` (`ValueError: year ... out of range`) on real persisted data
  instead of returning a stamp.
  **[review pass 1, bad_spec fix]** Add `load_with_provenance(catalog: Any,
  name: str) -> tuple[Any, ProvenanceInfo]`: calls `catalog.load(name)` AND
  `resolve_for_catalog_dataset(catalog, name, value)` in ONE function, so
  `tools.py` never needs to invoke `_session.loaded_catalog(s)` a second time
  just to obtain `.load()` (see the `mcp/tools.py` entry below and Design
  Notes for why the AD-7 gate forces this shape). `resolve_for_catalog_dataset`
  itself stays as-is (still directly unit-testable against an
  already-loaded value).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` --
  `read_dataset` (lines 72-106) rebuilt to return the envelope; add `from
  pyforge.atlas import provenance as _provenance`; update the module/function
  docstrings to describe the envelope shape. **[review pass 1, bad_spec fix]**
  Call `_session.loaded_catalog(s)` exactly ONCE (assign to `catalog`), then
  ONE call `_provenance.load_with_provenance(catalog, name)` — do NOT also
  call `_session.loaded_catalog(s).load(name)` separately; that redundant
  second call was pass 1's bug (each `loaded_catalog(s)` access rebuilds a
  fresh `DataCatalog` from `catalog.yml` — confirmed via Kedro's
  `KedroContext.catalog` being an uncached property — so the old pattern
  parsed the catalog twice per read and risked the provenance dispatch and
  the actual load running against two independently-built catalog instances).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` --
  `read_atlas_dataset` (~lines 65-67) docstring: replace "a thin catalog.load
  passthrough" with a description of the stamped envelope.
- `src/shared/packages/pyforge-atlas/tests/mcp/test_no_business_logic_in_tool_bodies.py`
  -- add `"_provenance"` to `ALLOWED_CALL_ROOTS` (~lines 43-58), with a comment
  in the same style as the existing `_nl` entry.
- `src/shared/packages/pyforge-atlas/tests/mcp/test_read_surface.py` -- unwrap
  the 3 existing DataFrame/Series/ndarray/set-coercion assertions to read
  `result["value"]`; add tests for `schema_version`+`dataset` presence, the
  `unavailable`/`live-fetch` kinds, and — the epic's binding gate requirement —
  a `row-fetched-at` test AND a `file-mtime` test each proving the reported
  `build_stamp` is the dataset's OWN recorded time, not the moment `read_dataset`
  was called (e.g. assert equality against a deliberately-old fixture value, not
  merely "a stamp is present").
- `src/shared/packages/pyforge-atlas/tests/mcp/test_kedro_mcp_absent.py` --
  line 102 unwrap to `["value"]`; add assertions that `schema_version`/`dataset`/
  `provenance_kind` are present (expect `"unavailable"` for the `MemoryDataset`
  fixture there).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` --
  `_legibility_card`/`_data_page`/`_shell_page` gain a `provenance: ProvenanceInfo`
  parameter and render a `"**Data build stamp (AD-17):** ..."` line from it;
  `build_dashboard` computes each grounded/bsl-shell page's `ProvenanceInfo` via
  `_provenance.resolve_for_file(root / _data.<CONST>)` before constructing the
  page list, and a hardcoded `unavailable` info for the 2 no-bsl-shell pages;
  import `from .. import provenance as _provenance`. `_factory_page` is untouched.
- `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py`
  -- add a test proving a grounded page's Card carries a real file's mtime (via
  `os.utime` on a fixture Parquet to a deliberately old value) rather than the
  dashboard's render-time `STAMP`/`NOW` constants, plus a test that shell pages
  honestly state "unavailable" + `AD-17`. Leave
  `test_factory_status_carries_build_timestamp_ad17` unchanged.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/provenance.py` --
  create the module: `ProvenanceInfo` dataclass, `SCHEMA_VERSION`,
  `resolve_for_file`, `resolve_for_catalog_dataset`, and
  `load_with_provenance(catalog, name) -> tuple[Any, ProvenanceInfo]` per the
  Code Map -- gives both MCP and the dashboard one shared, genuinely-derived
  provenance source (C1/C2/C3/C4), with the `.load(name)` call itself living
  here (not in `tools.py`) so the caller only touches the session seam once.
  Normalize ms-magnitude `fetched_at` values before `datetime.fromtimestamp`
  per the Design Notes.
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` --
  rewrite `read_dataset` to call `_session.loaded_catalog(s)` exactly ONCE
  (assign to `catalog`), then `result, info = _provenance.load_with_provenance(catalog, name)`
  (unknown-name errors still propagate before any envelope exists, from inside
  `load_with_provenance`), then return `{"schema_version":
  _provenance.SCHEMA_VERSION, "dataset": name, "provenance_kind": info.kind,
  "build_stamp": info.build_stamp, "build_stamp_newest": info.build_stamp_newest,
  "reason": info.reason, "value": <existing coercion>}` -- closes
  AUD-ATLAS-043/AD-17 for the MCP read surface without fabricating a read-time
  clock value and without a second, redundant catalog construction.
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` --
  update `read_atlas_dataset`'s docstring to describe the envelope -- keeps the
  doc truthful.
- [x] `src/shared/packages/pyforge-atlas/tests/mcp/test_no_business_logic_in_tool_bodies.py`
  -- add `_provenance` to `ALLOWED_CALL_ROOTS` -- the new seam must be callable
  from a tool body under the AD-7 gate.
- [x] `src/shared/packages/pyforge-atlas/tests/mcp/test_read_surface.py` --
  unwrap the 3 existing coercion tests to `["value"]`; add
  `test_read_dataset_envelope_carries_schema_version_and_dataset_name`,
  `test_read_dataset_unknown_kind_reports_unavailable_with_reason`,
  `test_read_dataset_api_dataset_reports_live_fetch`,
  `test_read_dataset_incremental_parquet_reports_fetched_at_not_read_time` (a
  fixture with a deliberately old `fetched_at` value; assert the returned
  `build_stamp` equals it, proving it is NOT wall-clock-now),
  `test_read_dataset_incremental_parquet_normalizes_millisecond_fetched_at`
  (review pass 1: a fixture with a ms-magnitude `fetched_at` value; assert the
  call does NOT raise and `build_stamp` decodes to the correct instant, not a
  `ValueError`),
  `test_read_dataset_pandas_parquet_reports_file_mtime_not_read_time` (a fixture
  Parquet with `os.utime`-set old mtime; assert `build_stamp` equals it) --
  discharges the epic's explicit gate: "a test that only asserts a stamp is
  present does not discharge C1."
- [x] `src/shared/packages/pyforge-atlas/tests/mcp/test_kedro_mcp_absent.py` --
  unwrap line 102 to `["value"]`; add presence assertions for
  `schema_version`/`dataset`/`provenance_kind` (`"unavailable"` expected) --
  keeps this smoke test meaningful under the new shape.
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` --
  add `provenance: ProvenanceInfo` to `_legibility_card`/`_data_page`/
  `_shell_page`; render a `"**Data build stamp (AD-17):** ..."` line stating
  either the derived stamp+kind or `"unavailable — {reason}"`; in
  `build_dashboard`, resolve each grounded/bsl-shell page's info via
  `_provenance.resolve_for_file(root / _data.<CONST>)` and each no-bsl-shell
  page's info as a hardcoded `unavailable` (`reason="no data function
  registered for this page"`) before building `pages` -- closes
  AUD-ATLAS-044/AD-17 for the 7 non-factory pages (C6).
- [x] `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py`
  -- add `test_grounded_page_carries_file_mtime_not_render_time(tmp_path)` (a
  fixture Parquet with `os.utime`-set old mtime under a `data_root=tmp_path`
  dashboard build; assert the page's Card text contains that mtime's ISO-8601
  form and `AD-17`, and does NOT contain the dashboard's own `STAMP`/`NOW`
  constants) and `test_shell_pages_state_unavailable_provenance_honestly
  (dashboard)` (iterate the 5 non-grounded, non-factory pages under the
  default, file-absent `data_root`; assert each Card states "unavailable" +
  `AD-17`) -- proves the AC's "every page carries its OWN data's provenance,
  not render time" for the full page set.

**Acceptance Criteria:**
- Given the MCP `read_dataset` surface, when a dataset backed by
  `IncrementalParquetDataset` is read, then `provenance_kind == "row-fetched-at"`
  and `build_stamp` equals the OLDEST `fetched_at` value actually recorded in
  that dataset's own data — not the time of this read.
- Given a dataset backed by `pandas.ParquetDataset`, when it is read, then
  `provenance_kind == "file-mtime"` and `build_stamp` equals that file's actual
  mtime — not the time of this read.
- Given a dataset backed by `api.APIDataset`, when it is read, then
  `provenance_kind == "live-fetch"` and `build_stamp` is the current call time
  (this is the one kind where "now" is the genuine provenance).
- Given a dataset with no recorded provenance, when it is read, then
  `provenance_kind == "unavailable"`, `build_stamp` is `null`, and `reason` is a
  non-empty string — the call still succeeds.
- Given `read_dataset` is called with an unknown name, when `catalog.load`
  raises, then the exception propagates unchanged (no envelope swallows it),
  and `value` is byte-for-byte identical to what the surface returned before
  this change for every known-good case.
- Given the dashboard is built, when any of the 7 non-factory pages render,
  then its legibility Card's text states that PAGE'S OWN backing data's
  provenance (a real file mtime when the file exists, an honest "unavailable"
  reason when it does not) and contains the literal substring `AD-17` — never
  the dashboard's build/render time standing in for the data's provenance.
- Given the existing `factory-status` page, when the dashboard builds, then its
  stamp Card is byte-for-byte unchanged from before this story.

## Design Notes

**The AD-7 AST-gate trap (non-obvious):** `test_tool_bodies_only_call_the_session_seam_and_trivial_stdlib`
resolves every `ast.Call`'s root identifier by walking `Attribute`/`Call` chains
down to the base `Name` — so `_session.loaded_catalog(s).load(name)` passes
(root `_session`), but assigning `catalog = _session.loaded_catalog(s)` and then
calling `catalog.load(name)` or `catalog.get_type(name)` FAILS (root resolves to
`catalog`, not in `ALLOWED_CALL_ROOTS`). Assign `catalog` for use as a plain
ARGUMENT only (never as a call target inside `tools.py`); do all catalog
navigation (`catalog[name]`, `catalog.load(name)`, `isinstance(...)`,
`._describe()`) inside `provenance.py`, which the gate never inspects.

**[review pass 1 correction]** Pass 1 called `_session.loaded_catalog(s)`
*twice* — once to bind `catalog`, once more inline as `_session.loaded_catalog(s).load(name)`
— because it kept `catalog.load(name)` itself in `tools.py`. That is what
forced the second, redundant `loaded_catalog(s)` call (confirmed each access
rebuilds a fresh `DataCatalog`). The correct shape moves the `.load(name)` call
itself into `provenance.py` too, via `load_with_provenance`, so
`_session.loaded_catalog(s)` runs exactly once per `read_dataset` call:

```python
with _session.bootstrapped_session(project_path, env=env) as s:
    catalog = _session.loaded_catalog(s)                                  # assignment: OK, root _session
    result, info = _provenance.load_with_provenance(catalog, name)        # ONE call, root _provenance: OK
```

`_provenance.load_with_provenance` (inside the ungated module) does
`value = catalog.load(name)` then `return value, resolve_for_catalog_dataset(catalog, name, value)`
— an unknown name still raises there and propagates up unchanged, satisfying
the intent-contract's "envelope wraps only the success path" rule exactly as
before; only the CALL SITE moved.

**Millisecond-magnitude `fetched_at` values (review pass 1 addition):**
`IncrementalParquetDataset.save()` documents that it normalizes ms-magnitude
input via an `_MS_EPOCH_THRESHOLD` guard because upstream Phase F/I writers
sometimes produce ms-source timestamps; `stale_mask()` relies on that
normalization having already happened at write time. `_resolve_row_fetched_at`
reads the SAME column back and must not assume it is always already
seconds-normalized on every code path that could reach it (e.g. a frame
constructed directly in a test, or a future writer that bypasses `save()`) —
apply the identical ms-threshold guard before calling `datetime.fromtimestamp`,
so a ms-magnitude value degrades to a correct (if surprising) stamp instead of
raising `ValueError: year ... out of range`.

**Path resolution for `file-mtime`:** `ParquetDataset._describe()["filepath"]`
returns the RAW (often relative, e.g. `data/primary/.../x.parquet`) path as
declared in `catalog.yml` — confirmed empirically (`kedro_datasets.pandas.ParquetDataset(filepath="data/...")._describe()`
echoes it back as a relative `PurePosixPath`, unresolved). Inside
`read_dataset`'s `with _session.bootstrapped_session(...)` block this already
works today for `catalog.load(name)` itself, so the same relative path resolves
correctly there too; verify this empirically while implementing (a quick
`read_dataset("core_feedstock_health")` call whose `build_stamp` matches the
real file mtime is sufficient proof) and fall back to resolving against
`mcp.session.PROJECT_ROOT` only if it does not. The dashboard side has no such
ambiguity: `build_dashboard` already computes an absolute `root` via
`_data.default_data_root()` before this story, so `root / _data.FEEDSTOCK_HEALTH_PARQUET`
is already a full path.

**Catalog inventory correction:** the epic's ACs cite "~75 catalog entries"
approximately; the live `catalog.yml` has 86 entries (24 `api.APIDataset`, 22
`pandas.ParquetDataset`, 15 `IncrementalParquetDataset`, 25 other types across
12 distinct type names). This does not change the binding rule — dispatch is by
KIND via `isinstance`, not by an enumerated/hardcoded list of names — so the
count discrepancy has no implementation impact; noted here only so a reviewer
does not mistake it for a spec deviation.

**Dashboard page → backing file map** (used by `build_dashboard`, all already
resolvable via existing `dashboard/data.py` constants — no new path logic
needed): `feedstock-health` → `_data.FEEDSTOCK_HEALTH_PARQUET`; `my-feedstocks`
→ `_data.PACKAGE_MAINTAINERS_PARQUET`; `staleness-report` / `query-atlas` /
`detail-cf-atlas` → `_data.PACKAGES_PARQUET` (today typically absent — the
composed store is DW-D2-deferred, so these 3 pages report `unavailable` until
that store lands, which is honest and correct, not a bug); `behind-upstream` /
`whodepends` → no file, always `unavailable`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` -- expected: all tests pass, including
  the new/updated cases across `tests/mcp/test_read_surface.py`,
  `tests/mcp/test_kedro_mcp_absent.py`, `tests/mcp/test_no_business_logic_in_tool_bodies.py`,
  and `tests/dashboard/test_dashboard_dryrun.py` (baseline 788 passing from
  Story I3/10.4; zero regressions).
- `pixi run -e pyforge-atlas kedro-catalog-check` -- expected: unaffected, still
  47/47 green (no catalog.yml changes in this story).

**Manual checks (if no CLI):**
- After implementing, run `read_dataset` once against a real
  `IncrementalParquetDataset` entry (e.g. `core_downloads`) and once against a
  real `pandas.ParquetDataset` entry (e.g. `core_feedstock_health`) through a
  bootstrapped session; confirm `build_stamp` matches the dataset's actual
  recorded time, not the moment of the call (e.g. run it twice a few seconds
  apart and confirm the stamp does NOT change for `pandas.ParquetDataset`/
  `IncrementalParquetDataset`, but DOES for `api.APIDataset`).

## Spec Change Log

### 2026-07-28 — review pass 1 (bad_spec loopback)

**Triggering findings:**
1. `[high]` `[bad_spec]` `provenance.py::_resolve_row_fetched_at` never
   normalized millisecond-magnitude `fetched_at` values before
   `datetime.fromtimestamp`, unlike the sibling
   `IncrementalParquetDataset.save()`/`stale_mask()`'s own documented ms-guard
   for exactly this case — crashes `read_dataset` on real persisted data from
   a ms-source writer instead of returning a stamp.
2. `[medium]` `[bad_spec]` `mcp/tools.py::read_dataset` called
   `_session.loaded_catalog(s)` twice (once bound to `catalog`, once more
   inline for `.load(name)`), each rebuilding a fresh `DataCatalog` from
   `catalog.yml` (confirmed: Kedro's `KedroContext.catalog` is an uncached
   property) — redundant cost and a latent split-catalog-instance risk. Root
   cause: this pass's own Design Notes prescribed exactly that two-call
   pattern as "the fix."

**What was amended:** Code Map for `provenance.py` (added
`load_with_provenance(catalog, name) -> tuple[Any, ProvenanceInfo]` combining
the load and the dispatch in one ungated call, plus an explicit ms-normalization
requirement) and for `mcp/tools.py` (call `_session.loaded_catalog(s)` exactly
once, route the load itself through `load_with_provenance`); Design Notes'
AD-7 AST-gate-trap example snippet corrected to the one-call-per-session-seam
shape; Tasks & Acceptance updated to match, plus one new required test proving
ms-magnitude normalization. The `<intent-contract>` was not touched — both
fixes are "how," not "what": the envelope shape, the four `provenance_kind`
values, and every Acceptance Criterion are unchanged.

**Known-bad state avoided:** re-deriving from the unamended pass-1 Design
Notes would very likely reproduce the identical double-`loaded_catalog(s)`
snippet (it was given verbatim as example code) and the identical missing
ms-guard (never mentioned at all), since neither was an ambiguity a fresh
implementer would necessarily resolve differently on a second attempt.

**KEEP instructions (what worked well and must survive re-derivation):**
- The `provenance.py` module's overall shape — `ProvenanceInfo` dataclass,
  `SCHEMA_VERSION`, `resolve_for_file`, the `isinstance`-based kind dispatch
  in `resolve_for_catalog_dataset` (`IncrementalParquetDataset` →
  row-fetched-at, `pandas.ParquetDataset` → file-mtime via `resolve_for_file`,
  `api.APIDataset` → live-fetch, else → unavailable+reason) — is correct and
  should be preserved; only add `load_with_provenance` and the ms-guard.
- `mcp/tools.py`'s envelope dict shape
  (`schema_version`/`dataset`/`provenance_kind`/`build_stamp`/`build_stamp_newest`/`reason`/`value`)
  and its DataFrame/Series/ndarray/set coercion logic are unchanged and
  correct — keep verbatim, only the catalog-access lines change.
- The `ALLOWED_CALL_ROOTS` addition of `_provenance` in
  `test_no_business_logic_in_tool_bodies.py` is correct and unaffected by this
  amendment.
- `dashboard/app.py`'s design (provenance param threaded through
  `_legibility_card`/`_data_page`/`_shell_page`, `build_dashboard` resolving
  each grounded/bsl-shell page's `ProvenanceInfo` via `resolve_for_file`, a
  hardcoded `unavailable` for the two no-bsl-shell pages) is unaffected by
  this amendment and should be re-derived unchanged.
- The 5 new `test_read_surface.py` tests, the `test_kedro_mcp_absent.py`
  envelope-presence additions, and the 2 new `test_dashboard_dryrun.py` tests
  are all well-designed and should be re-derived following the same pattern
  (equality against a deliberately-old fixture value, not mere presence),
  plus the one new ms-normalization test this amendment adds.

**Findings surfaced but NOT acted on this pass** (moot per the cascading rule
— code is being fully re-derived; these were not the root cause of the
bad_spec loopback and may resurface for the next review pass to triage fresh):
double-catalog test-blindness (a consequence of finding 2, not separate),
`resolve_for_file`'s `exists()`→`stat()` TOCTOU, `my-feedstocks` not
independently tested for the file-mtime property, the shell-page test not
distinguishing its two distinct `unavailable` reasons, the dashboard never
exercising `IncrementalParquetDataset`-kind dispatch (latent — no such
dashboard-backing dataset exists today), `isinstance(..., ParquetDataset)`
not matching a polars dataset (latent — none exist today), and the generic
fallback `reason` only naming the Python class. Also surfaced and explicitly
**not** treated as a defect: the dashboard's per-page provenance being
resolved once at `build_dashboard()` time rather than per-Vizro-render — this
mirrors the SAME already-accepted pattern `factory-status`'s own `build_stamp`
uses (out of scope to change per this spec's Never boundary), and pass 1 of
THIS story's own prior (reverted) attempt already triaged the identical
finding as `[low]` `[defer]` ("pre-existing, extended by this story").

## Review Triage Log

### 2026-07-28 — Review pass 1

- intent_gap: 0
- bad_spec: 2: (high 1, medium 1, low 0)
- patch: 3: (high 0, medium 0, low 3)
- defer: 4: (high 0, medium 0, low 4)
- reject: 2
- addressed_findings:
  - `[high]` `[bad_spec]` `provenance.py::_resolve_row_fetched_at` missing
    millisecond-magnitude `fetched_at` normalization (crashes `read_dataset`
    on real ms-source data) — Code Map + Design Notes amended, new task added
    to require a ms-normalization test.
  - `[medium]` `[bad_spec]` `mcp/tools.py::read_dataset` double
    `_session.loaded_catalog(s)` call (redundant `DataCatalog` construction,
    confirmed via Kedro source) — Code Map + Design Notes amended to route
    the load itself through a new `provenance.load_with_provenance` seam call.

### 2026-07-28 — Review pass 2 (re-derived diff)

- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 4: (high 0, medium 0, low 4)
- reject: 4
- addressed_findings:
  - `[low]` `[patch]` `provenance.py::resolve_for_file` had a TOCTOU race
    between `Path.exists()` and `Path.stat()` (raised independently by both
    reviewers on pass 1 and pass 2) — fixed directly: a single `stat()` call
    wrapped in `try/except OSError`, no separate existence check.

Both pass-1 `bad_spec` findings (ms-normalization, double catalog
construction) were verified fixed in the re-derived diff and did not
resurface. 4 new findings deferred to `deferred-work.md` (dashboard
eager-vs-lazy provenance timing — matches established `factory-status`
precedent and this story's own pass-1 disposition; `_describe()` fragility
with no failure isolation; versioned-`ParquetDataset` base-path risk;
`build_stamp_newest` never rendered by the dashboard — all latent, none
reproducible against the current catalog/dashboard). 4 findings rejected as
noise or already-settled by the binding contract (envelope shape change
flagged as "breaking" — C5 explicitly mandates it with `schema_version` as
the stated mitigation; `SCHEMA_VERSION` naming-collision speculation;
inline-vs-factory `ProvenanceInfo` construction style nitpick; live-fetch
timestamp captured after the fetch completes — not practically improvable,
same disposition as pass 1).

### 2026-07-28 — Review pass 3 (fresh follow-up pass on the done spec)

- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 2, low 5)
- defer: 0
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` `provenance.py::_resolve_row_fetched_at` crashed
    `read_dataset` with `ValueError: year ... out of range` on a
    datetime-typed or raw epoch-µs/ns `fetched_at` column — the reused
    ms-guard divides by 1000 exactly ONCE, so `to_numeric` on
    `datetime64[us/ns]` (the most natural bypass-`save()` writer shape,
    reproduced live by the reviewer) stays orders of magnitude out of
    `fromtimestamp` range. Fixed: datetime-dtype columns now convert via
    unit-aware timedelta arithmetic (yielding the correct genuine stamps),
    and a conversion backstop degrades anything still out of range to
    `unavailable` + a reason. New tests:
    `test_read_dataset_datetime_typed_fetched_at_reports_genuine_stamp`,
    `test_read_dataset_out_of_range_fetched_at_degrades_to_unavailable`.
  - `[medium]` `[patch]` provenance resolution had no failure isolation —
    any exception in the kind dispatch (the crash above, a `_describe()`
    KeyError, an ImportError) aborted a read whose `catalog.load` had
    already succeeded, contradicting C4's provenance-is-advisory contract.
    Fixed: `load_with_provenance` wraps `resolve_for_catalog_dataset` in a
    broad except that degrades to `unavailable` +
    `"provenance resolution failed (...)"`. (This also closes, in code, the
    failure-isolation half of the existing pass-2 deferred-work ledger entry
    on `_describe()` fragility — the ledger entry itself is untouched; the
    orchestrator owns its status.) New test:
    `test_read_dataset_provenance_failure_never_aborts_a_successful_read`.
  - `[low]` `[patch]` a non-local (fsspec-remote) `ParquetDataset` would
    have been stat'd via its protocol-STRIPPED `_describe()["filepath"]` —
    a false "backing file not found" for data that exists remotely, or worse
    an unrelated local file's mtime reported as the data's. Fixed: protocol
    guard in the `ParquetDataset` branch degrades to `unavailable` naming
    the protocol. New test:
    `test_resolve_for_catalog_dataset_non_local_parquet_degrades_honestly`.
  - `[low]` `[patch]` module-level `from kedro_datasets.api import APIDataset`
    made `requests` (an undeclared kedro-datasets extra, present today only
    transitively) an import-time dependency of the whole MCP surface +
    dashboard — the AUD-ATLAS-010 failure class the member manifests
    document. Fixed: lazy import via `_api_dataset_cls()` at dispatch time.
  - `[low]` `[patch]` `resolve_for_file` collapsed every `OSError` into
    "backing file not found" — a `PermissionError` would misdirect operator
    remediation. Fixed: `FileNotFoundError` keeps the not-found reason;
    other `OSError`s report "not readable" + the exception class name.
  - `[low]` `[patch]` two load-bearing docstrings misstated their
    mechanisms: `provenance.py` claimed the AD-7 gate "denies importing
    pandas/kedro_datasets" (the denylist is pandas/numpy/duckdb/sqlite3/
    sqlalchemy/ibis/pyarrow — kedro_datasets is constrained only by the
    call-root allowlist), and `mcp/tools.py`'s header still described shape
    2 as a bare `catalog.load` though the load now lives behind the
    `_provenance` seam. Both corrected.
  - `[low]` `[patch]`
    `test_shell_pages_state_unavailable_provenance_honestly` was
    presence-style ("unavailable" anywhere in the card) and could not
    distinguish the two distinct unavailable states. Strengthened: bsl-shell
    pages must state "backing file not found", no-bsl pages "no data
    function registered".

Rejected (8): dashboard eager-vs-lazy provenance timing, `_describe()`
private-API rename risk, versioned-`ParquetDataset` base-path/directory
mtime, and `build_stamp_newest` never rendered — all four are duplicates of
existing `deferred-work.md` entries from pass 2 (per the orchestrator's
instruction, existing ledger entries were not modified or re-opened; no new
entries were appended this pass). Plus: absolute local paths in `reason`
strings (diagnostic value on a local operator surface, not a leak);
`CachedDataset`/wrapper dispatch speculation (no `cached:` catalog entries
exist; the fallback degrade is honest per C4); `SCHEMA_VERSION`
ownership/unversioned-sibling-receipts design speculation (versioning
framing settled in pass 2); style residue incl. the vacuous
`str(NOW) not in card.text` assertion (cosmetic).


