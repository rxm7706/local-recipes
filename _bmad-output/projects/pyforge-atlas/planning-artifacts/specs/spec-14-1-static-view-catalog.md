---
title: 'Story 14.1: Static view catalog (CAP-1)'
type: 'feature'
created: '2026-08-14'
status: 'done'
baseline_revision: '64e717d13554938e03ceac5a6a98c2aae407b957'
final_revision: '06c982c837b6dc7666c26ad3ad8846238b5e226f'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `cf_atlas.db` is queryable today only via 11 text-output CLIs
(`staleness-report`, `feedstock-health`, `whodepends`, …) or hand-written SQL — nothing
renders the same data as a linkable page.

**Approach:** Stand up a new `pyforge.atlas.views` package that mirrors the 6 CLIs whose
`query()` runs with zero required arguments (`staleness-report`, `feedstock-health`,
`behind-upstream`, `cve-watcher`, `release-cadence`, `adoption-stage`) as a static,
self-contained Bokeh HTML fragment per view. Each view calls that CLI's own
`query()` function verbatim (dynamic import, mirroring the `_load()` idiom already used in
`.claude/skills/conda-forge-expert/tests/unit/test_mapping_gap.py`) — no new SQL, no second
data layer. The other 5 CLIs (`whodepends`, `version-downloads`, `find-alternative`,
`detail-cf-atlas`, `scan-project`) all require a package-name/path argument, so they don't
fit a parameterless static view; they're deferred to the interactive layer (Story 14.3).

## Boundaries & Constraints

**Always:** query cf_atlas.db by calling the matching CLI script's existing `query(**kwargs)`
verbatim (dynamic import via `importlib.util.spec_from_file_location`, same idiom as
`test_mapping_gap.py::_load`) — never new SQL/ibis against cf_atlas.db. Render via
`bokeh.embed.components()` only (script+div fragment) — never `server_document`/
`autoload_server`/any live-session API. Keep `src/pyforge/atlas/**/*.py` free of any
`sqlite3` import — the pre-existing F1 gate (`tests/singularity/test_duckdb_sole_engine.py`)
must stay green; it AST-scans literal imports in that tree only, so dynamic-loading a script
that itself imports `sqlite3` (living under `.claude/skills/conda-forge-expert/scripts/`,
outside that tree) is the deliberate, documented way this module honors both "query
cf_atlas.db directly" (Epic 14) and "DuckDB/Parquet is the sole engine in the migrated
surface" (Epic 7/F1) at once.

**Block If:** `bokeh>=3.9.2` fails to solve into the `pyforge-atlas` pixi environment
(conda solver conflict) — needs a human pin decision, not a silent downgrade/skip.

**Never:** build the pluggable widget registry (14.2), Bokeh WebSocket interactivity (14.3),
or air-gap CDN asset rewriting (14.4) — separate, dependent stories. Never touch/modify the
existing Vizro `dashboard/` module or its BSL/Parquet data path. Never add a static view for
one of the 5 parameter-requiring CLIs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | fixture cf_atlas.db, `staleness-report` view | script+div fragment; rows == fixture rows in the view's declared column order | No error expected |
| EMPTY_RESULT | fixture query returns 0 rows | fragment renders with declared columns, 0 data rows | No error expected |
| DB_MISSING | `DB_PATH.exists()` is False (the CLI's own `query()` does `sys.exit(1)`) | `cli_bridge` catches the `SystemExit` and raises `CfAtlasDbUnavailableError` | Caller gets a catchable exception, not a killed process |
| UNKNOWN_VIEW | caller requests a view name not in `STATIC_VIEWS` | raises `KeyError` naming the unknown view | No silent `None` / wrong view |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/` -- NEW package this story creates (registry, dynamic-import bridge, renderer)
- `.claude/skills/conda-forge-expert/scripts/{staleness_report,feedstock_health,behind_upstream,cve_watcher,release_cadence,adoption_stage}.py` -- canonical `query(**kwargs) -> list[dict[str, Any]]` this story calls verbatim; read each for its exact argparse defaults (mirror them as the view's default kwargs) and `SELECT` column list (mirror as the view's declared columns)
- `.claude/skills/conda-forge-expert/tests/unit/test_mapping_gap.py:21-33` -- the `_load()` dynamic-import idiom (`importlib.util.spec_from_file_location`) to mirror in `cli_bridge.py`
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py:50-66` -- `default_data_root()`'s `.git`-anchor walk-up pattern to mirror for resolving the skill scripts dir (env override, walk up to `.git`/`_bmad-output`); this is a DIFFERENT, untouched data path (Vizro/BSL/Parquet) — do not reuse its models, only its path-resolution shape
- `src/shared/packages/pyforge-atlas/tests/singularity/test_duckdb_sole_engine.py` -- the pre-existing F1 gate that must stay green after this story lands
- `src/shared/packages/pyforge-atlas/pyproject.toml` / `pixi.toml` `[package.run-dependencies]` -- add `bokeh` here, matching the root `pixi.toml:1188` `bokeh = ">=3.9.2"` floor already used by `local-recipes`
- `src/shared/packages/pyforge-core/src/pyforge/core/errors.py` (`PyforgeError`) -- base class for the new `CfAtlasDbUnavailableError`, mirroring `rag/store.py`'s `VssNotProvisionedError(PyforgeError, RuntimeError)` pattern

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/pyproject.toml` -- add `"bokeh>=3.9.2"` to `[project].dependencies` with a Story 14.1 comment -- shipped `views/render.py` now hard-imports bokeh
- [x] `src/shared/packages/pyforge-atlas/pixi.toml` -- add `bokeh = ">=3.9.2"` to `[package.run-dependencies]`, matching the pyproject floor -- keeps both manifests byte-for-byte (AUD-ATLAS-010 convention)
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/cli_bridge.py` -- dynamic-import a named skill script (env-overridable scripts-dir, `.git`-anchored default), call its `query(**kwargs)`, catch `SystemExit` from a missing `DB_PATH` and raise `CfAtlasDbUnavailableError` instead -- the "no parallel query surface" seam
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/registry.py` -- `View` dataclass (`name`, `title`, `script`, `columns`, `query_kwargs`) + `STATIC_VIEWS` tuple of the 6 zero-arg views, each `query_kwargs` mirroring that CLI's own argparse defaults -- the curated catalog
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/render.py` -- `list[dict] -> bokeh.models.{ColumnDataSource,DataTable,TableColumn} -> bokeh.embed.components()` self-contained fragment, columns taken from `View.columns` (stable even on 0 rows)
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/__init__.py` -- exports `STATIC_VIEWS`, `render_view`, `CfAtlasDbUnavailableError`
- [x] `src/shared/packages/pyforge-atlas/tests/views/{__init__.py,test_cli_bridge.py,test_registry.py,test_render.py}` -- hermetic tests against a temp sqlite fixture db (stdlib `sqlite3`, test-only, monkeypatching the dynamically-loaded module's `DB_PATH`) covering the I/O matrix's 4 rows plus a fragment-content assertion that no `ws://`/`wss://`/`autoload_server`/`session_id` substring appears in any rendered output

**Acceptance Criteria:**
- Given the 6-entry `STATIC_VIEWS` registry, when `pixi run -e pyforge-atlas kedro-test` runs, then all new tests collect and pass with `bokeh` importable in that environment
- Given `tests/singularity/test_duckdb_sole_engine.py`, when it runs after this story's changes, then it still passes unmodified — no `sqlite3` import anywhere under `src/pyforge/atlas/`
- Given any of the 6 registered views rendered against the fixture db, when the fragment is inspected, then it opens zero WebSocket connections (no session/websocket markers in the output)

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 0, medium 6, low 4)
- defer: 0
- reject: 7: (high 0, medium 1, low 6)
- addressed_findings:
  - `[medium]` `[patch]` F1 singularity gate's docstring claimed the parity comparator is "the ONE legitimate SQLite reader" in the codebase — now imprecise since `cli_bridge.py` is a second, indirect (AST-invisible) reader by deliberate design. Added an honest doc note to `tests/singularity/test_duckdb_sole_engine.py` acknowledging the exception; no assertions changed.
  - `[medium]` `[patch]` `call_query` caught any `SystemExit`, not just the documented DB-missing `exit(1)` case, risking mislabeling an unrelated exit as `CfAtlasDbUnavailableError`. Narrowed to `exc.code == 1`; anything else re-raises.
  - `[medium]` `[patch]` `load_cli_module` re-parsed/re-exec'd the target script and re-mutated `sys.path`/`sys.modules` on every call. Added a `(name, scripts_dir)`-keyed module cache.
  - `[medium]` `[patch]` Only 2 of 6 registered views had a real row-count/content assertion; the other 4 were only exercised by the generic no-websocket-marker test. Added row-count + field assertions for `feedstock-health`/`behind-upstream`/`release-cadence`/`adoption-stage` in `test_render.py`.
  - `[medium]` `[patch]` No test proved `View.columns` matches the real CLI's output keys (only input-kwargs parity was tested), so a future CLI SELECT-column rename could silently render a blank column. Added `test_view_columns_are_a_subset_of_the_clis_real_output_keys`, parametrized over all 6 views, in `test_registry.py`.
  - `[medium]` `[patch]` `load_cli_module` built a filesystem path from an unvalidated, publicly-callable `name` argument — a path-traversal-shaped hygiene gap. Added `_valid_script_name` (bare-identifier regex, mirroring `rag/store.py::_valid_identifier`), raising `ValueError` on anything else.
  - `[low]` `[patch]` `default_scripts_dir`'s docstring overstated parity with `dashboard/data.py::default_data_root` (they diverge on the failure branch: raise vs. best-effort fallback). Tightened the docstring.
  - `[low]` `[patch]` `registry.py` misattributed `behind-upstream`'s dropped `_priority` column to mimicking the CLI's `main()`, when it's actually `render_rows`'s own column-whitelist projection. Fixed the comment.
  - `[low]` `[patch]` `load_cli_module` raised a raw, unclear error when the resolved script path didn't exist. Added an explicit `path.is_file()` check raising the existing clear `ImportError` message.
  - `[low]` `[patch]` `View` was `frozen=True` but its `query_kwargs` field was a plain mutable `dict`, undermining immutability/hashability. Wrapped it in `MappingProxyType` via `__post_init__`.
  - Rejected as noise/out-of-scope for this diff (not re-listed individually): defensive guards for CLI return shapes already verified-impossible for the 6 in-scope CLIs (empty-tuple/`None`/non-dict rows); the `sys.modules`/`sys.path` global-mutation collision risk (mirrors pre-existing, spec-directed precedent, no concurrent callers exist yet); the epic-level `SPEC.md`'s "DuckDB" wording for `cf_atlas.db` (a different, already-`status: ready` artifact outside this diff, and this story's own Design Notes already correct the record for its own purposes); the new module coexisting with the existing Vizro `dashboard/` staleness page (explicitly mandated by the Epic 14 Spec's own Non-goals); bokeh's transitive dependency footprint (inherent to the epic-mandated rendering primitive); and two tests reaching into real ambient CLI source for signature/column-parity contract checks (correct test design, not a hermeticity bug).

 (all 11 skill CLIs do
`sqlite3.connect(DB_PATH)`; the F1 gate's own docstring calls it "the legacy hand-rolled
cf_atlas.db (a SQLite store)" pending retirement). The migrated `dashboard/` module reads a
*different*, separately-populated Parquet/BSL catalog that's incomplete for these metrics
today (`dashboard/data.py`'s `PACKAGES_PARQUET` comment: staleness/detail pages are
"BSL-wired shells" returning empty until a composed store lands, DW-D2) — so matching the
live CLI's output requires reading the live legacy store, not the migrated one.

Rejected alternative: DuckDB `ATTACH … (TYPE SQLITE)` (spiked, works, needs offline
`sqlite_scanner` provisioning like `rag/store.py`'s `load_vss_offline`/`provision_vss`) —
rejected because it means re-deriving each CLI's SQL a second time, exactly the "parallel
query surface" the Epic 14 Spec forbids. Chosen instead: dynamic-import + call the existing
`query()` verbatim, so rows are guaranteed to match by construction, and `sqlite3` never
appears inside `pyforge/atlas/`'s tree. One hazard from reading the source: each CLI's
`query()` calls `sys.exit(1)` on a missing `DB_PATH` instead of raising — `cli_bridge.py`
must catch that `SystemExit` and translate it, or a missing db kills the render host.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary.** Implemented a new `pyforge.atlas.views` package (Story 14.1, Epic 14 CAP-1):
a curated, static catalog of 6 conda-forge-expert CLIs — `staleness-report`,
`feedstock-health`, `behind-upstream`, `cve-watcher`, `release-cadence`,
`adoption-stage` — rendered as self-contained `bokeh.embed.components()` HTML fragments
(zero WebSocket/server code). Each view calls the matching CLI script's existing
`query(**kwargs)` verbatim via dynamic import, so rows are guaranteed to match the CLI's
own output by construction and no new SQL/query surface was introduced. The other 5 CLIs
all require a package-name/path argument and were deliberately excluded (deferred to the
interactive layer, Story 14.3).

**Files changed** (commit `06c982c837b6dc7666c26ad3ad8846238b5e226f`):
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/cli_bridge.py` -- dynamic-import bridge; translates the CLIs' `sys.exit(1)`-on-missing-db into `CfAtlasDbUnavailableError`; memoized; validates script names against path traversal
- `.../views/registry.py` -- `View` dataclass (immutable, incl. `query_kwargs`) + the 6-entry `STATIC_VIEWS` catalog
- `.../views/render.py` -- rows → `ColumnDataSource`/`DataTable` → static fragment
- `.../views/__init__.py` -- public exports
- `.../tests/views/{conftest.py,test_cli_bridge.py,test_registry.py,test_render.py}` -- hermetic sqlite-fixture tests covering the I/O matrix, output-column parity, and per-view content checks for all 6 views
- `.../tests/singularity/test_duckdb_sole_engine.py` -- doc-only note acknowledging the new, deliberate indirect SQLite exception
- `pyproject.toml` / `pixi.toml` (member) + root `pixi.lock` -- added `bokeh>=3.9.2` as a run-dependency

**Review findings breakdown:** 17 total findings from 2 independent reviewers (Blind Hunter + Edge Case Hunter, no shared context) after dedup — 10 patch (6 medium, 4 low; all applied), 0 bad_spec, 0 intent_gap, 0 defer, 7 reject (mischaracterized-as-defect design choices already justified by this story's own spec or the epic's Non-goals, or edge cases already foreclosed by the 6 in-scope CLIs' verified return-type contract). Full detail in `## Review Triage Log` above.

**Verification performed:**
- `pixi run -e pyforge-atlas kedro-test` -- 1107 passed, 19 skipped, 0 failed (independently re-run after patches)
- `pixi run -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/singularity -q` -- 3 passed (F1 gate still green)
- `pixi install -e pyforge-atlas` -- bokeh 3.9.2 solved cleanly

**Residual risks:** none blocking. Noted-but-rejected: the `sys.modules`/`sys.path` global-mutation pattern (inherited from an existing repo precedent, no concurrent callers today — worth revisiting if Story 14.3's WebSocket layer adds concurrent view loads); the epic-level `spec-atlas-query-dashboards/SPEC.md` still narratively calls `cf_atlas.db` "DuckDB" even though it's SQLite — this story's own Design Notes correct the record for implementation purposes, but the epic Spec artifact itself is unchanged (out of this diff's scope).
