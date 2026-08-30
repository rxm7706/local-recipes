---
title: 'Canvas vs Vizro parity gate (Story 22.5, Epic 22, optional follow-on)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/vizro-canvas-parity.md'
---

<intent-contract>

## Intent

**Problem:** The three Cursor Canvas identity writers (`write_canvas` in
`scripts/conda-forge-packaging-inventory-operations_priority.py`, `write_ops_canvas` /
`write_workbook_canvas` in `scripts/openteams_identity_dashboards.py`, invoked from
`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`) and the new Vizro
`identity-catalog` / `identity-ops` / `identity-workbook` pages (Stories 22.2/22.3/22.4) will
run in parallel over the same ranked-identity data with **no automated proof they agree**.
Without a gate, an operator has no evidence-based way to trust Vizro before the Story 22.6
canvas-deprecation switch is ever flipped to `vizro`.

**Approach:** Add ONE new offline pytest module,
`src/shared/packages/pyforge-atlas/tests/dashboard/test_identity_parity.py`, that:
1. Builds a single shared fixture corpus of GIST-schema-shaped identity rows (the same
   `P`/`Rank`/`Score`/`Work`/`Core_Python_Package_Name`/`OpenTeams_Issue_URL`/
   `Local_Build_Status` shape `identity_ranked_export.parquet` carries per Story 22.1's
   `done_checkpoint`).
2. Feeds that corpus through `write_canvas` and `write_ops_canvas` (loaded via the
   `importlib.util.spec_from_file_location` pattern `tests/packaging/test_openteams_handoffs.py`
   already established for these hyphenated-filename scripts) and decodes each canvas's
   embedded `const DATA = <json> as {...}` blob with `json.JSONDecoder().raw_decode` (same
   technique as that file's `_decode_data_blob` helper).
3. Feeds the SAME corpus (written to a fixture Parquet) through the Vizro `identity-catalog`
   and `identity-ops` loaders Stories 22.2/22.3 register in `dashboard/data.py`.
4. Asserts **exact** row-key equality for `identity-catalog` (the `(P, Work,
   Core_Python_Package_Name)` triple per row — vizro-canvas-parity.md's own documented
   tolerance: "exact row keys, approximate layout N/A") and exact pane-total equality for
   `identity-ops` (`priorityCounts`, `workCounts`, `issues.have`/`issues.miss` — the aggregates
   `write_ops_canvas`'s DATA blob already carries).
5. Handles `identity-workbook`/`write_workbook_canvas` **specially, not by row-parity**: per
   Story 22.4's own scope, the Vizro workbook page ships an honest empty shell until enterprise
   JFROG Parquet exists, so this story only asserts BOTH sides degrade honestly on the same
   fixture (canvas writes a valid schema-shaped file; Vizro page renders its documented
   data-gap Card) — never a byte/row comparison.

Placing the new module inside `tests/dashboard/` means the **existing** `dashboard-dryrun`
pixi task (`cmd = "python -m pytest src/shared/packages/pyforge-atlas/tests/dashboard -q"`)
auto-discovers and runs it with **zero changes to `pixi.toml` or any CI workflow** — no
`dashboard-dryrun`-referencing GitHub Actions workflow exists today (it is invoked directly by
operators/other gates), so "extend `dashboard-dryrun` for three parity pages" is satisfied by
file placement alone. Refresh the task's description string (cosmetic only, mirrors Story
21.9's precedent of refreshing `pixi.toml`'s page-count text) to mention identity-parity
coverage.

## Boundaries & Constraints

**Always:**
- Fully offline: no network, no `gh`, no real Cursor canvas path writes (everything under
  `tmp_path`). Mirrors every existing `tests/dashboard/` fixture's discipline (`conftest.py`
  round-trips Parquet through `tmp_path` only).
- Load `priority.py` / `openteams_identity.py` / `openteams_identity_dashboards.py` via
  `importlib.util.spec_from_file_location` (the hyphenated-filename two scripts cannot be
  `import`ed directly) — duplicate the small `_load_module` + `_decode_data_blob` helpers
  locally in the new test module (or its own module-level constants); do **not** import them
  from `tests/packaging/test_openteams_handoffs.py` — that file lives in a different pytest
  root (`tests/packaging/`, repo-root-scoped) from `src/shared/packages/pyforge-atlas/tests/
  dashboard/` (package-scoped), and importing test code from another test file is not this
  repo's pattern. This duplication mirrors the already-accepted `_cf_atlas_db_path()`
  duplication between `vcs_sources.py` and `request_datasets.py` (spec-21-2 Code Map).
- Resolve the repo root for `importlib.util.spec_from_file_location`'s `scripts/` path the
  same way `dashboard/data.py::default_data_root()` already does in THIS package — an
  anchor-based walk-up (`.git` or `_bmad-output` marker), not a hardcoded `parents[N]` index
  (a fixed index is exactly the kind of fragile detail a directory-depth change silently
  breaks).
- `openpyxl` is available wherever this module runs: `dashboard-dryrun`'s own task
  description states it runs "in local-recipes (the env carrying vizro + boring_semantic_layer)",
  and `openpyxl` is a `[feature.local-recipes.dependencies]` entry in the SAME feature block as
  `vizro` (confirmed by direct inspection of `pixi.toml`) — no `pytest.importorskip("openpyxl")`
  guard is needed here (unlike `tests/packaging/test_openteams_handoffs.py`, which guards
  because `pyforge-ci`'s leaner env also collects that directory).
- The shared fixture corpus is authored ONCE in this module and reused for both canvas writers
  and both Vizro loaders — never two independently-hand-typed row sets that could silently
  drift apart.
- `identity_ranked_export.parquet` (Story 22.1) is the Vizro-side ground truth; write it to a
  `tmp_path` Parquet at whatever relpath constant Stories 22.1/22.2/22.3 actually land (see
  Design Notes — a step-03-style resolve-at-implementation-time item, not an open design
  question: the SHAPE is fixed by this spec, only the concrete constant name is TBD until those
  stories exist).
- This is a `recipes/`-external change (`src/shared/packages/pyforge-atlas/**`) — per
  CLAUDE.md's PR-CI-gates rule, the PR must carry the `maintenance` label
  (`gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`).

**Block If:** None — Stories 22.2/22.3 (this story's `depends_on`) are the human/scheduling
gate on when 22.5 actually runs; the row/pane-total comparison targets are fully specified by
`write_canvas`/`write_ops_canvas`'s own already-shipped JSON shapes (verified below), not an
open spec question.

**Never:**
- Do not write to a real Cursor canvas path (`DEFAULT_OPS_CANVAS_PATH` /
  `DEFAULT_WORKBOOK_CANVAS_PATH` / the hardcoded `--canvas` default in `priority.py`) — always
  pass an explicit `tmp_path` override.
- Do not assert row-level or pane-level equality for `identity-workbook` — Story 22.4 explicitly
  defers full workbook parity until enterprise Parquet exists; asserting equality here would
  make this gate red for a reason outside this story's or 22.4's scope.
- Do not modify `write_canvas` / `write_ops_canvas` / `write_workbook_canvas` themselves, or the
  Vizro `identity-catalog` / `identity-ops` / `identity-workbook` pages' own implementation —
  this story only tests them.
- Do not touch `tests/parity/parity_runner.py` (the unrelated Kedro-catalog credentialed parity
  mode from Epic 21) or `pixi.toml`'s `parity-diff` task — different "parity" concept, out of
  scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Shared fixture corpus (~5 rows, distinct P/Work/issue-url combos) | Same corpus round-tripped into priority.py-shape records (for `write_canvas`) and fed directly to `write_ops_canvas` and the Vizro fixture Parquet | `identity-catalog` canvas rows' `(P, Work, Core_Python_Package_Name)` triples == Vizro `identity-catalog` loader's same triples, as sets, exact match | Test fails loudly (`assert ... == ...`) on any mismatch — no fuzzy tolerance |
| Same corpus, `identity-ops` | — | `write_ops_canvas`'s `priorityCounts`/`workCounts`/`issues.have`/`issues.miss` == the equivalent aggregates recomputed from the Vizro `identity-ops` loader's output | Exact dict/int equality |
| Empty corpus (0 rows) | Zero-row fixture | Canvas writers produce their documented empty-but-schema-shaped output (mirrors `test_write_ops_canvas_empty_records_is_valid_and_schema_shaped`); Vizro loaders return an empty typed frame (existing `_bsl_query_or_empty` contract) | Never raise on either side |
| `identity-workbook` / `write_workbook_canvas` | Same corpus + a missing/absent `xlsx` (mirrors the existing `test_write_workbook_canvas_empty_records_is_valid_and_schema_shaped` precedent) | `write_workbook_canvas` still writes a valid schema-shaped file (no crash); the Vizro `identity-workbook` page renders its own honest data-gap Card | No row/byte comparison performed |
| `dashboard-dryrun` full run | `python -m pytest src/shared/packages/pyforge-atlas/tests/dashboard -q` | New module collected and passes alongside the existing 60+ tests in this directory, with zero `pixi.toml`/CI wiring changes | n/a |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_priority.py` -- `write_canvas` (~L250-296),
  `_CANVAS_PREFIX`/`_CANVAS_SUFFIX` (~L312-332, the exact `const DATA = <json> as {` /
  `};`-wrapping literal this story's decoder strips) -- the catalog canvas writer under test.
- `scripts/openteams_identity_dashboards.py` -- `write_ops_canvas` (~L848-943, JSON keys
  `tab`/`n`/`priorityCounts`/`workCounts`/`priorityDefs`/`workDefs`/`issues.have`/`issues.miss`/
  `issues.byP`/`buildByType`/`rows`/`leaders` -- confirmed by direct inspection), `write_workbook_canvas`
  (~L955+, takes `(path, records, xlsx, tab, helpers)`; a missing `xlsx` still produces a valid
  empty-array-shaped file) -- the ops/workbook canvas writers under test.
- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` -- `GIST_SCHEMA`
  (~L84-120, the `P`/`Rank`/`Score`/`Work`/`Core_Python_Package_Name`/`OpenTeams_Issue_URL`/
  `Local_Build_Status` column contract the shared fixture corpus mirrors); no direct call site
  needed here (the writers are exercised directly, not through `write_dashboard_markdown`).
- `tests/packaging/test_openteams_handoffs.py` -- `_load_module` (~L50-67) and `_decode_data_blob`
  (~L378-382) -- the EXACT precedent patterns for loading these hyphenated scripts and decoding
  the embedded DATA blob (`json.JSONDecoder().raw_decode`, tolerant of the trailing
  `` as {...}; `` TypeScript annotation) -- duplicate locally per Boundaries.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` -- `PAGE_INVENTORY`
  (~L82-295), `build_dashboard()` (~L402-644) -- Stories 22.2/22.3/22.4 will append
  `identity-catalog`/`identity-ops`/`identity-workbook` `PageDef` entries here (page ids fixed
  by `vizro-canvas-parity.md`'s own mapping table); this story reads whichever loaders those
  stories register, does not add pages itself.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py` -- `default_data_root()`
  (~L90-97, the anchor-based repo-root walk-up to mirror for `scripts/` resolution),
  `_bsl_query_or_empty` (~L106-141) -- Stories 22.2/22.3 will add
  `load_identity_catalog`/`load_identity_ops` loaders here (naming per this file's existing
  `load_<page_id_with_underscores>` convention) -- this story calls whatever landed.
- `src/shared/packages/pyforge-atlas/tests/dashboard/conftest.py` -- `write_parquet` (~L25-36)
  fixture -- reuse for writing the shared corpus to a fixture ranked-export Parquet.
- `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py` -- `_dm_get`
  (~L38-42), `test_feedstock_health_page_is_bsl_driven` (~L119-135, the direct-loader-call
  comparison-test pattern to mirror) -- style precedent only, not modified by this story.
- `pixi.toml` -- `dashboard-dryrun` task (~L961-963) -- cosmetic description refresh only
  (mirrors Story 21.9's precedent at ~L139-141 of its own Code Map).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-atlas/tests/dashboard/test_identity_parity.py` (new):
  - `_load_module(filename)` + `_decode_data_blob(text, prefix)` module-level helpers, mirroring
    `tests/packaging/test_openteams_handoffs.py` exactly; resolve `scripts/` via an anchor-based
    repo-root walk-up (mirror `dashboard/data.py::default_data_root()`'s `.git` marker), not a
    fixed `parents[N]` index.
  - A shared fixture corpus (module-level constant or a fixture function): ~5 GIST-schema-shaped
    row dicts spanning at least 2 distinct `P` buckets, 2 distinct `Work` values, and both a
    present and an absent `OpenTeams_Issue_URL` -- enough to make the pane-total assertions
    non-trivial (a 1-row or all-identical-value fixture would pass vacuously).
  - A small derivation helper mapping the GIST-shape corpus into `priority.py`'s internal
    `write_canvas` record shape (`name`/`bucket`/`rank`/`score100`/`work` sourced from
    `Core_Python_Package_Name`/`P`/`Rank`/`Score`/`Work`; `src`/`why`/`plat`/`apps`/`ic`/`lob`/
    `dl`/`ver`/`vuln` given fixed, deterministic placeholder values -- these fields are not part
    of the compared triple) plus a `counts` dict (`Counter` over the mapped `bucket` field).
  - `test_identity_catalog_matches_write_canvas_on_shared_fixture` -- write the canvas via
    `write_canvas(tmp_canvas_path, mapped_records, counts, tab)`; decode its DATA blob; extract
    the `(row[1], row[13], row[0])` -> `(P, Work, Core_Python_Package_Name)` triple per
    `data["rows"]` entry (index positions per `write_canvas`'s own `canvas_rows` construction --
    verify against the live function body at implementation time, since an unrelated future
    column reorder would silently break a hardcoded index); write the fixture corpus to a
    fixture Parquet; call the Vizro `identity-catalog` loader (Story 22.2's actual function
    name); assert the sorted triple sets are exactly equal.
  - `test_identity_ops_pane_totals_match_write_ops_canvas_on_shared_fixture` -- call
    `write_ops_canvas(tmp_ops_path, gist_shape_records, tab, helpers=types.SimpleNamespace(
    **vars(identity_module)))`; decode its DATA blob; call the Vizro `identity-ops` loader(s)
    (Story 22.3's actual function/shape) against the same fixture Parquet; recompute the same
    `priorityCounts`/`workCounts`/`issues.have`/`issues.miss` aggregates from whatever concrete
    DataFrame shape 22.3 produced; assert exact equality against the canvas DATA blob's values.
  - `test_identity_workbook_both_sides_degrade_honestly_on_same_fixture` -- call
    `write_workbook_canvas(tmp_workbook_path, gist_shape_records, missing_xlsx, tab, helpers=...)`
    and assert it writes a valid, non-crashing, schema-shaped file (mirror the existing
    `test_write_workbook_canvas_empty_records_is_valid_and_schema_shaped` shape assertions, now
    against a non-empty fixture too); separately assert the Vizro `identity-workbook` page (Story
    22.4) is present in `PAGE_INVENTORY` and its Card states the documented data-gap honestly
    when no enterprise Parquet is present -- no row-level comparison between the two.
  - `test_empty_corpus_degrades_honestly_on_both_sides` -- zero-row fixture through all three
    canvas writers + both Vizro loaders; assert no crash and the documented empty shapes on both
    sides (mirrors the existing empty-records canvas tests + the existing
    `test_data_loaders_offline_return_empty_typed_frames_not_fabricated` pattern).
- `pixi.toml` -- refresh `dashboard-dryrun`'s task description to mention identity
  catalog/ops/workbook parity coverage (Story 22.5) alongside the existing 28-page-inventory
  text (cosmetic only, not gating).

**Acceptance Criteria:**
- Given the shared fixture corpus, when `write_canvas` and the Vizro `identity-catalog` loader
  both run against it, then the sorted set of `(P, Work, Core_Python_Package_Name)` triples from
  each side is exactly equal.
- Given the shared fixture corpus, when `write_ops_canvas` and the Vizro `identity-ops` loader(s)
  both run against it, then `priorityCounts`, `workCounts`, and `issues.have`/`issues.miss` are
  exactly equal between the two sides.
- Given the shared fixture corpus and an absent enterprise-workbook Parquet, when
  `write_workbook_canvas` and the Vizro `identity-workbook` page both run, then neither crashes
  and both honestly represent the data-gap -- no row-level equality is asserted.
- Given `pixi run --frozen -e local-recipes dashboard-dryrun`, when run after this story, then it
  passes, collecting and running the new parity module with no `pixi.toml` task-command change
  and no new CI workflow file.
- Given a zero-row fixture, when all three canvas writers and both Vizro loaders run, then none
  raises and each degrades to its own documented empty/schema-shaped output.

## Spec Change Log

<!-- Empty -- no review loopback has occurred yet. -->

## Design Notes

The exact Vizro `identity-catalog`/`identity-ops` loader function names, their backing Parquet
relpath constant (e.g. `IDENTITY_RANKED_EXPORT_PARQUET`, following `data.py`'s existing
`<NAME>_PARQUET = "primary/<name>/<name>.parquet"` convention), and `identity-ops`'s exact
returned DataFrame shape (a single long-format frame? multiple loaders, one per pane?) are NOT
fixed by this spec -- as of this story's authoring (2026-08-30) Stories 22.1/22.2/22.3 have no
spec files or implementation yet. This mirrors spec-21-9's own Design Notes precedent for the
identical situation: because this story's own `depends_on: ["22.2", "22.3"]` guarantees those
stories are implemented before 22.5 runs, the implementer's task is a step-03-style research
task -- grep the THEN-current `dashboard/data.py`/`dashboard/app.py` for the real loader names
and DataFrame shape, and bind this story's assertions to them. The SHAPE this spec fixes and
does not leave open: (1) one shared fixture corpus feeds both sides, never independently
authored row sets; (2) the compared VALUES are the `(P, Work, Core_Python_Package_Name)` triple
set for catalog and the `priorityCounts`/`workCounts`/`issues.have`/`issues.miss` aggregate
values for ops -- these are fixed by `write_canvas`/`write_ops_canvas`'s own already-shipped JSON
keys (verified directly against the live source in this spec's Code Map), not by whatever 22.2/
22.3 happen to name their internals; (3) `identity-workbook` gets structural-honesty checks only,
never row parity, per Story 22.4's explicit scope.

The `write_canvas`/`write_ops_canvas`/`write_workbook_canvas` DATA-blob encoding is a fixed,
already-shipped literal (`const DATA = <json> as {...};`), confirmed directly against
`priority.py`'s `_CANVAS_PREFIX`/`_CANVAS_SUFFIX` and `openteams_identity_dashboards.py`'s
`_CANVAS_PREFIX`/`_OPS_CANVAS_SUFFIX`/`_WORKBOOK_CANVAS_SUFFIX`, and already has a working
decoder precedent (`tests/packaging/test_openteams_handoffs.py::_decode_data_blob`, using
`json.JSONDecoder().raw_decode` so the trailing TypeScript type annotation is never a parsing
concern) -- not a step-03 research item, a resolved detail.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes dashboard-dryrun` -- expected: pass, including the three
  new parity assertions (catalog row-key equality, ops pane-total equality, workbook honest-
  degrade-on-both-sides) collected automatically from `tests/dashboard/`.
- `python -m pytest src/shared/packages/pyforge-atlas/tests/dashboard/test_identity_parity.py -v`
  -- expected: all new tests pass in isolation.

**Manual checks (if no CLI):**
- Diff the new test module's shared fixture corpus against `GIST_SCHEMA` in
  `conda-forge-packaging-inventory-operations_openteams_identity.py` to confirm every required
  (`req == "yes"`) column the writers/loaders touch is present in the fixture rows.
