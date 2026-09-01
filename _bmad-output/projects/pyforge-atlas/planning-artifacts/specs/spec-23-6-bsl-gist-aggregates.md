---
title: 'BSL gist and dashboard aggregates from complete export (Story 23.6, Epic 23, CAP-8d)'
type: 'feature'
created: '2026-08-30'
status: 'in-progress'
baseline_revision: 'dispatch/pyforge-atlas/23.6'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/vizro-canvas-parity.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-5-identity-complete-export-parquet.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-4-deliverable-a-packaging-candidate-status.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `scripts/openteams_identity_dashboards.py::render()` (1093 lines total; `render()`
alone is ~260 lines, L61-320) hand-computes every aggregate the pinned gist's companion dashboard
file needs — `identity_source` counts, `Local_Build_Status` crosstabs, priority (`P`)/`Work`
counts, packaging-issue gap by `P`, a JFROG-to-PyPI/conda-forge membership map, board gap,
workbook-tab stats — via raw `Counter`/dict aggregation over `xlsx` rows, then string-templates
two markdown files. This is a second, `scripts/`-owned implementation of metric logic that BSL
(`boring_semantic_layer`) already owns as the ONE declared aggregation layer for every other
pyforge-atlas dashboard page (AD-8: "the metric logic lives once in `semantic/metrics.py` +
`semantic/models.py`" — `dashboard/data.py`'s own module docstring). It also reads from an Excel
workbook tab (`CDO-ENT-JFROG`, `read_xlsx_tab`) and the live `recipes/` filesystem
(`load_local_recipe_type`) rather than the Kedro-owned `identity_complete_export.parquet` (Story
23.5) — exactly the dual-maintenance and workbook dependency `complete-export-contract.md` §5
(CAP-8d) exists to retire.

**Approach:** Port the aggregate computations into a new BSL `SemanticModel` binding
`identity_complete_export.parquet` (following the 28 existing `build_*_model` precedents in
`src/pyforge/atlas/semantic/models.py`), plus a new markdown-rendering module in
`pyforge.atlas.dashboard` that formats BSL query results into the same two-document shape as
today's gist (`mgmt-wf-python-modernization-identity.md` row catalog +
`mgmt-wf-python-modernization-dashboards.md` companion). The credentialed `gh gist edit` publish
step stays a thin actuator in `scripts/` — it calls into the new pyforge-atlas rendering function
for markdown bodies, then only handles gist-id resolution and the `gh` subprocess call. No new
fetch: `identity_complete_export.parquet` is already materialized by Story 23.5.

## Boundaries & Constraints

**Always:**
- Every count/crosstab currently computed inline in `openteams_identity_dashboards.py::render()`
  is expressed as a BSL dimension/measure query over `identity_complete_export.parquet` — not
  reimplemented a second time with raw `Counter`/dict code in the new module.
- The gist-publish actuator (`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`'s
  `--gist-only` path) becomes THIN: gist-id resolution (`resolve_gist_id`), `gh` binary discovery
  (`gh_bin`), and the `gh gist edit` subprocess calls (`publish_gist_files`,
  `publish_identity_gist`, `gist_file_names`) are the only logic that remains there — the markdown
  BODY comes from a single call into the new `pyforge.atlas.dashboard` module.
- `pyforge.atlas` is imported from `scripts/` the same way `dashboard-dryrun`/`dashboard-serve`
  already do it — `PYTHONPATH=src/shared/packages/pyforge-atlas/src` (see `pixi.toml` L959,
  L963-964, L968-969: every `[feature.local-recipes.tasks.*]` entry that imports `pyforge.atlas`
  sets this env var; there is no formal `pypi-dependencies` install of `pyforge-atlas` into the
  `local-recipes` environment).
- Pure-formatting helpers that carry NO metric logic (`md_table`, `md_cell`, the YAML-frontmatter
  emission, `PRIORITY_DESC`/`WORK_DESC`/`PRIORITY_HOW` narrative text) may be ported verbatim —
  they are presentation, not aggregation, and porting them is not "dual template logic" in the
  CAP-8d sense.
- `GIST_SCHEMA`'s column-schema table (rendered in the identity-row markdown's "## Column schema"
  section) is sourced from Story 23.5's own column-source table
  (`spec-23-5-identity-complete-export-parquet.md`'s Code Map), not re-typed independently.

**Block If:** Story 23.5 is not `status: done` (this spec's own `depends_on`). See Design Notes.

**Never:**
- Do not re-fetch anything — `identity_complete_export.parquet` is the sole data source; no
  network call, no `xlsx` read, in the new BSL-grounded aggregate path.
- Do not duplicate the markdown-table-building logic in two places (`scripts/` AND
  `pyforge.atlas.dashboard`) — the actuator calls the pyforge-atlas renderer once; it does not
  keep a parallel fallback template.
- Do not port `openteams_identity_dashboards.py`'s `write_ops_canvas`/`write_workbook_canvas`
  (Cursor `.canvas.tsx` DATA-blob writers) — `complete-export-contract.md` §5 marks the canvas row
  "optional; superseded by Epic 22 Vizro"; leave those two functions untouched, still fed by the
  legacy in-script computation, until Story 22.6's canvas-deprecation switch.
- Do not touch `identity_complete_export.parquet`'s schema or Story 23.5's join node — this story
  is a pure downstream consumer.
- Do not silently drop a dashboard section without recording it — see the three sections this
  story cannot port unchanged (recipe-type classification, JFROG workbook-tab source, workbook
  sheet-stats census) in Design Notes; each gets an explicit, cited resolution, not a silent
  omission.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|----------------|----------------------------|-----------------|
| `identity_complete_export.parquet` present, non-empty | Normal post-bootstrap state | Gist markdown (row catalog + dashboards) renders from BSL queries; `gh gist edit` publishes both files | — |
| `identity_complete_export.parquet` absent or empty | Bootstrap not yet run, or a fresh clone | Actuator fails loudly (non-zero exit) with a clear message — same "Skipped gist publish" honesty pattern the script already uses for a missing `gist_id`/`gh` binary, not a silent empty-markdown publish | Never publish a garbage/empty gist body |
| `gh` binary absent | No `gh` on PATH, no `.pixi/envs/local-recipes/bin/gh` | Actuator prints the existing "gh not found" message and exits non-zero — unchanged from today | Unchanged |
| `OPENTEAMS_IDENTITY_GIST_ID` unset | No gist id resolvable | Actuator prints "Skipped gist publish" — unchanged from today | Unchanged |
| Fixture corpus (`tests/fixtures/inventory_identity/`, extended by Story 23.5) | Frozen `identity_complete_export.parquet`-shaped fixture | New BSL-rendered markdown's computed VALUES (every count/crosstab number) match `openteams_identity_dashboards.py::render()`'s legacy output on the same fixture, run offline with `--skip-gist` | A value mismatch fails the story; a section this story deliberately drops (see Design Notes) is documented, not silently absent from the diff |

</intent-contract>

## Code Map

**Legacy surface being replaced (read-only reference for the port, not deleted wholesale):**
- `scripts/openteams_identity_dashboards.py` — `render()` (L61-320, the markdown body this story
  ports to BSL), `PRIORITY_DESC`/`WORK_DESC`/`PRIORITY_HOW`/`EXTERNAL_LIVE` (L16-58, narrative
  text + a hardcoded, dated 2026-08-15 external-source-count table — see Design Notes for the
  `EXTERNAL_LIVE` replacement proposal), `write_ops_canvas`/`write_workbook_canvas` (L848-1093,
  explicitly OUT of this story's scope per Boundaries).
- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` —
  `write_gist_markdown` (L974-1116), `write_dashboard_markdown` (L1119-1158, the function that
  currently `sys.path.insert`s the script dir and imports `openteams_identity_dashboards`),
  `publish_gist_from_tab` (L1198-1236, the `--gist-only` entrypoint this story thins out),
  `publish_gist_files`/`publish_identity_gist`/`gist_file_names` (L1161-1195, the actuator logic
  that STAYS), `resolve_gist_id`/`gh_bin`/`GIST_ID_ENV`/`LOCAL_ENV_PATH` (L76-83, L270-297, stays
  unchanged), `GIST_SCHEMA`/`GIST_COLUMNS` (L84-121, the column-schema table the new markdown
  renderer's "## Column schema" section sources from — cross-reference Story 23.5's own column
  table rather than re-deriving).

**New pyforge-atlas surface:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/models.py` — add
  `build_identity_complete_export_model(table) -> SemanticModel`, mirroring the 28 existing
  `build_*_model` functions (e.g. `build_packages_model` L48, `build_feedstock_health_model`
  L93). Dimensions: `Core_Python_Package_Name`, `P`, `Work`, `identity_source`,
  `Local_Build_Status`, `OpenTeams_Issue_URL` (presence), `conda_purl`/`Conda-Forge_FeedStock_URL`
  (presence, for the `is_cf` classification), `primary_type`/`primary_purl` (for `is_pypi`).
  Measures: row count, filled-count per column (for the "## Column schema" `filled:` block), and
  grouped counts (`P` × `Local_Build_Status`, `Work` × issue-presence).
- New module: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/identity_gist.py` —
  `render_identity_gist_markdown(export_path: Path) -> tuple[str, str]` returning
  `(identity_row_catalog_md, dashboards_md)`. Loads `identity_complete_export.parquet` via the
  existing `models.duckdb_table_from_parquet` seam (mirrors every `dashboard/data.py` loader's own
  pattern), runs the BSL queries against `build_identity_complete_export_model`, and formats the
  two markdown bodies using ported `md_table`/`md_cell` helpers. This module carries the ONLY copy
  of the markdown-table-building logic post-port.
- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` — `write_gist_markdown`
  and `write_dashboard_markdown` are replaced by one call:
  `identity_row_catalog_md, dashboards_md = identity_gist.render_identity_gist_markdown(export_path)`
  (imported via the `PYTHONPATH` mechanism above), followed by the existing
  `publish_gist_files(gh, gist_id, ...)` actuator call, unchanged. `publish_gist_from_tab` is
  renamed/reworked to `publish_gist_from_export` and takes the Parquet path instead of `(xlsx,
  tab)` — `--gist-only`'s CLI contract stays the same operator-facing flag per
  `identity-contract.md` ("Inventory `--gist-only` reads complete export (post-23.6)").
- Test target: `src/shared/packages/pyforge-atlas/tests/dashboard/test_identity_gist_markdown.py`
  (new, sibling of the existing `tests/dashboard/` suite `dashboard-nl-test`/`dashboard-dryrun`
  runs) — value-parity test against `openteams_identity_dashboards.py::render()`'s legacy output
  on the frozen `tests/fixtures/inventory_identity/` corpus (extended by Story 23.5).
- `pixi.toml` — no new task required if the existing `--gist-only` CLI path is reused; if a
  standalone `pyforge-atlas` test task is added for `test_identity_gist_markdown.py`, it needs the
  same `PYTHONPATH=src/shared/packages/pyforge-atlas/src:src/shared/packages/pyforge-warden/src`
  pattern as the other `[feature.local-recipes.tasks.*]` dashboard entries (L959, L964, L969).

## Tasks & Acceptance

**Execution:**
- Add `build_identity_complete_export_model` to `semantic/models.py` per the dimensions/measures
  above.
- Add `pyforge.atlas.dashboard.identity_gist.render_identity_gist_markdown`, porting the section
  logic from `openteams_identity_dashboards.py::render()` section-by-section, replacing each raw
  `Counter`/dict aggregation with the corresponding BSL query:
  - Priority and work (`p_counts`, `work_counts`, `PRIORITY_DESC`/`WORK_DESC` tables) — BSL group-
    count over `P`/`Work`.
  - Packaging-issue gap (`have_issue`/`miss_issue`, `have_by_p`/`miss_by_p`, `miss_by_work`) — BSL
    group-count over `P`/`Work` × `OpenTeams_Issue_URL` presence.
  - Census (`fs_n`, `needs`, `local_n`, `green`/`skipped`/`failed`, `staged`, `no_pr`) — BSL
    group-count over `P` × (`Conda-Forge_FeedStock_URL` presence, `Local_Recipes_URL` presence,
    `Local_Build_Status`, `Staged_Recipes_PR_URL` presence).
  - "## Column schema" `filled:` block — BSL per-column non-null count over the full
    `identity_complete_export` column set.
- **Three sections cannot port unchanged — resolve each explicitly, do not silently drop:**
  1. "Local build by recipe type" + "Full cube" sections key on `row_recipe_type()`
     (`classify_recipe_text` reading live `recipes/<dir>/recipe.yaml` text for
     `noarch-python`/`noarch-generic`/`compiled`/`arch`) — this classification is NOT a column on
     `identity_complete_export.parquet` (confirmed against Story 23.5's 63-column table). Port
     `classify_recipe_text`/`row_recipe_type`/`load_local_recipe_type` byte-for-byte into the new
     module as a live-filesystem overlay applied AFTER the BSL-computed `Local_Build_Status`
     counts — this is a live-repo-state read, not a second aggregation-logic implementation, so it
     is not the "dual template logic" CAP-8d targets (same category as `overlay_live_local`'s
     existing `Local_Recipes_URL`/`Local_Build_Status` overlay upstream in Story 21.6).
  2. "CDO-ENT-JFROG → PyPI / conda-forge" map currently reads the `CDO-ENT-JFROG` `xlsx` tab
     directly (`read_xlsx_tab(xlsx, "CDO-ENT-JFROG")`) — replace with a BSL query over
     `enterprise_jfrog_consumption.parquet` (Story 23.2) filtered to
     `repository_source == "CDO-ENT-JFROG"`, joined against `identity_complete_export`'s
     `primary_type`/`conda_purl`/`Conda-Forge_FeedStock_URL` for the `is_pypi`/`is_cf`
     classification — both are already Kedro Parquet by the time this story dispatches (Stories
     23.2 and 23.5 done).
  3. "Workbook tabs" census (`sheet_stats`, iterating `wb.sheetnames`) has no Kedro equivalent —
     `complete-export-contract.md` §7 explicitly puts the Excel workbook out of scope for closure.
     DROP this section from the ported dashboards markdown; do not fabricate a substitute. Record
     the removal in this story's frontmatter/Design Notes as an intentional, cited scope
     narrowing (same rigor as Story 21.2's `seed_gaps` carve-out), not a silent regression.
  - `EXTERNAL_LIVE` (the hardcoded, dated 2026-08-15 external-source-count table in
    `openteams_identity_dashboards.py` L49-58) — replace with a live BSL row-count query over the
    actual Tier 0-3 raw datasets (`core_channeldata_raw`, `discovery_basilisk_packages_raw`,
    `discovery_aoss_free_python_raw`, etc.) now that they are materialized Parquet — this turns a
    stale hardcoded copy into a real aggregate and is a net improvement over today's output, not
    merely a port.
- Thin out `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`'s
  `--gist-only` path per Code Map; keep `resolve_gist_id`/`gh_bin`/`publish_gist_files` unchanged.
- New test `test_identity_gist_markdown.py`: value-parity assertions (every count/crosstab number
  in the new BSL-rendered markdown matches `render()`'s legacy computation on the same frozen
  fixture) for every section EXCEPT the three explicitly resolved above; a dedicated assertion
  that the "Workbook tabs" heading is absent from the new output (proves the drop is deliberate,
  not accidental); `--skip-gist` offline mode, no live `gh` call in tests.

**Acceptance Criteria:**
- Given `identity_complete_export.parquet` materialized by Story 23.5, when
  `render_identity_gist_markdown` runs, then every BSL-sourced count/crosstab value matches
  `openteams_identity_dashboards.py::render()`'s legacy output on the frozen fixture corpus.
- Given the three sections this story cannot port unchanged (recipe-type classification, JFROG
  map source, workbook sheet-stats), when the new markdown renders, then recipe-type and JFROG-map
  sections are present with correct values via their documented alternate source, and the
  workbook-tabs section is absent (documented drop, not silent).
- Given the `--gist-only` CLI path, when invoked with `--skip-gist` against the fixture corpus,
  then no `gh` subprocess call is made and no network fetch occurs.
- Given a live `gh` + resolvable gist id, when `--gist-only` runs against a real
  `identity_complete_export.parquet`, then `gh gist edit` publishes both markdown files, and the
  actuator code path (`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`)
  contains no aggregation/table-building logic beyond the single call into
  `pyforge.atlas.dashboard.identity_gist`.
- Given `identity_complete_export.parquet` absent, when `--gist-only` runs, then it fails loudly
  (non-zero exit, clear message) rather than publishing an empty or garbage gist body.

## Auto Run Result

- **Summary:** Ported gist markdown rendering to `pyforge.atlas.dashboard.identity_gist` with BSL
  aggregates via `build_identity_complete_export_model`; thinned `--gist-only` to call the new
  renderer and keep only gist-id/`gh` actuator logic in `scripts/`.
- **Files changed:**
  - `semantic/models.py` — `build_identity_complete_export_model`
  - `dashboard/identity_gist.py` — new renderer
  - `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` — thin gist path
  - `tests/dashboard/test_identity_gist_markdown.py` — parity tests
- **Verification:** `pixi run -e pyforge-atlas pytest tests/dashboard/test_identity_gist_markdown.py`
  — run locally to confirm (agent shell unavailable).
- **Residue:** Workbook-tabs section dropped from dashboard markdown (Design Notes item 3). Canvas
  writers still use legacy `openteams_identity_dashboards` (Story 22.6).

## Spec Change Log

- 2026-08-30: Initial draft. Written ahead of Story 23.5 (`depends_on`) and, transitively, Story
  23.2 (needed for the JFROG-map resolution) — see Design Notes, mirroring the
  `spec-21-8-end-to-end-verification-gate.md` / `spec-23-5` precedent for a closing/porting story
  specced before its inputs exist.
- 2026-08-30 (same-day reconciliation pass): confirmed `spec-23-4-deliverable-a-packaging-candidate-status.md`
  (landed concurrently, `status: ready-for-dev`) independently references
  `enterprise_jfrog_consumption`/`enterprise_conda_maintainers` as Story 23.2's assumed dataset
  names, corroborating (not proving) this spec's own JFROG-map resolution. No change to scope or
  Acceptance Criteria required. Self-review against a READY-FOR-DEVELOPMENT bar passed; `status`
  set to `ready-for-dev`.

## Design Notes

**This story cannot be dispatched yet.** Story 23.5 (this spec's `depends_on`) is itself not yet
implemented (see `spec-23-5-identity-complete-export-parquet.md`'s own Design Notes) — confirmed
by grep that `identity_complete_export.parquet` / `identity_complete_export` do not exist anywhere
in the repo as of this drafting. The JFROG-map resolution (Tasks item 2) additionally needs Story
23.2's `enterprise_jfrog_consumption.parquet`. Re-verify both are `status: done` at dispatch time,
not against this spec's drafting-time snapshot.

**Three legacy dashboard sections needed an explicit, non-obvious resolution** (see Tasks) rather
than a mechanical "swap the data source" port: recipe-type classification reads the live
`recipes/` tree and has no Parquet column anywhere in the closure contract; the JFROG map's
today's source is an Excel tab with no Kedro equivalent named in any companion doc, resolved here
by mapping it onto Story 23.2's `enterprise_jfrog_consumption.parquet` (a reasonable, but not
contract-mandated, inference — confirm the join shape against 23.2's actual landed schema at
dispatch time); and the workbook-tabs census section has no possible Kedro equivalent at all and
is dropped per §7's explicit workbook-out-of-scope non-goal. This `enterprise_jfrog_consumption`
inference is corroborated (though not proven) by `spec-23-3-priority-rules-in-kedro.md` and
`spec-23-4-deliverable-a-packaging-candidate-status.md` (both now exist, written concurrently with
this spec), which independently consume `enterprise_jfrog_consumption`/`enterprise_conda_maintainers`
as Story 23.2's landed dataset names for their own priority/role joins — the same names this
story's JFROG-map resolution assumes.

**Why `status: ready-for-dev` despite the hard dependency.** As with `spec-21-8` and `spec-23-5`,
the spec itself is complete and actionable — Intent, Boundaries, the section-by-section port plan,
the three explicitly-resolved gaps, Tasks & Acceptance — what is missing is upstream Parquet that
Stories 23.2 and 23.5 have not produced yet, a dispatch-ordering constraint recorded in `Block If`
above, not an ambiguity in what this story must do.

## Verification

**Commands (run once Story 23.5, and 23.2 for the JFROG-map task, are done and this story
dispatches):**
- `pixi run -e pyforge-atlas kedro-test` — expected: new
  `tests/dashboard/test_identity_gist_markdown.py` passes, including the value-parity assertions
  and the "Workbook tabs section absent" assertion.
- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py --gist-only
  --skip-gist` against a fixture `identity_complete_export.parquet` — expected: exit 0, no `gh`
  subprocess call, markdown bodies match the value-parity fixture.
- Manual read-through of the thinned `--gist-only` code path — expected: no `Counter`/dict
  aggregation or markdown-table-building code remains in `scripts/`, only gist-id resolution and
  the `gh gist edit` actuator calls.
