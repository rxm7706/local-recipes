---
title: "27.3: The read surfaces render what DESIGN.md specifies, and prove it on fixture data"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: '1f67f67105f9e9417012d45e07b45c77f36de221'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 21 open deferred-work rows (8 medium, 13 low) raised by Stories 18.2 and 19.1-19.5 against Atlas's read surfaces: `PlaneBoot.library` raises a raw duckdb closed-connection error once the boot yields to the HTTP face; the face-parity fixture never exercises NULL, date, timestamp, decimal or blob values; all 19 ported pages use the minimal card-and-grid shape instead of the controls DESIGN.md and EXPERIENCE.md specify; the scan-project and env-inspect pages have no submit control; the dashboard has only ever been checked against an empty data root; the page select and content carry no navigation or main landmark; and the dashboard tests, docstrings, README and portal chrome carry the lows listed below.

**Approach:** Type the yielded state; widen the parity fixture; let each `PageDef` declare its DESIGN.md controls and have `_data_page` render them; give the two scan pages a path input and submit control that run the scan through `pyforge.core.process`; run the e2e suite against a data root materialized from the fixture Parquet; add the landmarks; and fix the tests, notes, README and `base.html` lows on the way.

Ledger key: `27-3-the-read-surfaces-render-what-design-specifies-on-real-data`.
Type / Effort / Deps: fix / L / S-26.1.
Rows: 21 (8 medium, 13 low).

### Living CAP citations

- The atlas capabilities that shipped each behaviour (see each row's source story); a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the boot has yielded the in-process connection When a caller queries `PlaneBoot.library` Then it raises a typed error naming the HTTP face
- Given a parity fixture with NULL, DATE, TIMESTAMP, DECIMAL and BLOB columns When the face-parity gate runs on an ephemeral port Then both faces agree, and a seeded divergence in any of those columns fails it
- Given `PAGE_INVENTORY` When the dashboard builds Then each page renders the filter and chart controls its `PageDef` declares, and a test compares every page's declared controls with DESIGN.md's per-page table
- Given the scan-project or env-inspect page When a path is submitted Then the scan runs through `pyforge.core.process` and the page shows the new result
- Given a data root materialized from the static fixture Parquet When the dashboard e2e suite runs Then every grounded page renders rows, the page select sits in a navigation landmark and the content in a main landmark
- Given each defect this story fixes When its new test runs against the tree before the fix Then it fails, and after the fix it passes
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-20-1`, `DW-FU-20-2-2`, `DW-FU-20-5`, `DW-FU-20-5-8`, `DW-FU-20-5-2`, `DW-FU-20-5-9`, `DW-FU-20-5-4`, `DW-FU-20-5-11`, `DW-FU-20-2-3`, `DW-FU-20-3`, `DW-FU-20-3-2`, `DW-FU-20-3-3`, `DW-FU-20-5-3`, `DW-FU-20-5-10`, `DW-FU-20-5-5`, `DW-FU-20-5-12`, `DW-FU-20-5-6`, `DW-FU-20-5-13`, `DW-FU-20-5-7`, `DW-FU-20-5-14`, `DW-FU-19-2` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Keep MCP tool bodies to their two shapes and `mcp/server.py`'s lazy fastmcp import. Run any process through `pyforge.core.process`. Keep semantic-layer reads pure Ibis (FR-8). Give the e2e suite its real Chromium, as the CI lane provisions it. Fix each defect where the shipped behaviour lives now and pin it with a test that fails without the fix. A re-ingested twin closes with the row it repeats, citing the same fix.

**Never:** Never import `subprocess`, `sqlite3`, Dagster or `kedro-mcp` under `src/pyforge/atlas` outside the sanctioned seams (AD-1, AD-4). Never load a CDN script into the portal chrome. Never read the gitignored Tier-3 `sprint-status.yaml` from a test. Never close a row without a landed fix and a cited `verified:` line (no blanket closure).

</intent-contract>

## Deferred-work rows this story closes (operator ruling 2026-10-03, deferral burn-down Phase 4+5)

- `DW-FU-20-1` (medium) — Once the boot yields the in-process connection, `PlaneBoot.library`'s query methods raise a typed error naming the HTTP face, not a raw duckdb closed-connection error.
- `DW-FU-20-2-2` (medium) — The face-parity fixture table gains NULL, DATE, TIMESTAMP, DECIMAL and BLOB columns, and the parity gate compares them across both faces.
- `DW-FU-20-5` (medium) — Each `PageDef` declares its DESIGN.md controls (filter columns, chart kind) and `_data_page` renders a `vm.Filter` per declared column and the declared `vm.Graph`; a test compares every page's declared controls with DESIGN.md's per-page table.
- `DW-FU-20-5-8` (medium) — Re-ingested twin of `DW-FU-20-5` (same text, later intake); closed by the same fix and test.
- `DW-FU-20-5-2` (medium) — The scan-project and env-inspect pages gain a path input and a submit control whose callback runs the scan through `pyforge.core.process` (no `subprocess` import, AD-4) and refreshes the cached result the page reads.
- `DW-FU-20-5-9` (medium) — Re-ingested twin of `DW-FU-20-5-2` (same text, later intake); closed by the same fix and test.
- `DW-FU-20-5-4` (medium) — The data-present visual pass: the dashboard e2e suite runs against a data root materialized from the static fixture Parquet and asserts every grounded page renders rows (the residual DW-D2-3 names; the story records the same evidence there).
- `DW-FU-20-5-11` (medium) — Re-ingested twin of `DW-FU-20-5-4` (same text, later intake); closed by the same fix and test.
- `DW-FU-20-2-3` (low) — The face-parity test binds an ephemeral free port and passes it to `boot_query_plane`, so a taken port cannot surface as an opaque startup failure.
- `DW-FU-20-3` (low) — The stale "renders empty until the composed store lands (DW-D2)" notes in `PAGE_INVENTORY`, `dashboard/__init__.py` and the provenance comment describe the shipped state.
- `DW-FU-20-3-2` (low) — The README's pipeline inventory matches `find_pipelines()`; a test fails when its count or list drifts.
- `DW-FU-20-3-3` (low) — The duplicate-key test in `tests/pipelines/semantic_packages/test_nodes.py` also covers `core_downloads`, `core_feedstock_attribution` and `vcs_archived_feedstocks`.
- `DW-FU-20-5-3` (low) — The page select renders inside a navigation landmark and the page content inside a main landmark; the e2e ARIA test asserts both.
- `DW-FU-20-5-10` (low) — Re-ingested twin of `DW-FU-20-5-3` (same text, later intake); closed by the same fix and test.
- `DW-FU-20-5-5` (low) — Each composite-score page (find-alternative's similarity, mapping-gap's match confidence and the rest) reads a column a pipeline node produces, or shows the honest-empty state naming the missing producer; a test pins each composite column to its producing node.
- `DW-FU-20-5-12` (low) — Re-ingested twin of `DW-FU-20-5-5` (same text, later intake); closed by the same fix and test.
- `DW-FU-20-5-6` (low) — `test_factory_status_reads_the_real_sprint_status` reads a fixture sprint-status file passed through `_default_paths`' parameter, never the gitignored Tier-3 file, so it passes in a fresh worktree.
- `DW-FU-20-5-13` (low) — Re-ingested twin of `DW-FU-20-5-6` (same text, later intake); closed by the same fix and test.
- `DW-FU-20-5-7` (low) — A test asserts that each page's `resolve_for_file(...)` in `build_dashboard()` is built from that page's own Parquet constant (a table of page to constant).
- `DW-FU-20-5-14` (low) — Re-ingested twin of `DW-FU-20-5-7` (same text, later intake); closed by the same fix and test.
- `DW-FU-19-2` (low) — `django_pyforge/base.html` loads the htmx runtime from a vendored static file, so the atlas portal slice's `hx-*` poll attributes run.

## Binding

Parent: The atlas capabilities that shipped each behaviour; a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `27-3-the-read-surfaces-render-what-design-specifies-on-real-data`.
Ledger status at mint: `backlog`.
Deps: S-26.1.
Surface: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_boot.py`, `src/shared/packages/pyforge-atlas/tests/query_plane/`, `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/` (`app.py`, `data.py`, `factory_status.py`, `__init__.py`), `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/`, `src/shared/packages/pyforge-atlas/tests/dashboard/`, `src/shared/packages/pyforge-atlas/tests/integration/dashboard/`, `src/shared/packages/pyforge-atlas/tests/pipelines/semantic_packages/`, `src/shared/packages/pyforge-atlas/README.md`, `src/shared/packages/django-pyforge/` (`base.html` and a vendored htmx static file), the atlas deferred-work ledger.
Minted 2026-10-03 from the operator's Phase 4+5 ruling (open medium and low deferrals fixed together, split by package area, at most about 30 rows per story).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.

- 2026-10-04, landing regression (hotfix): Story 27.3's `dashboard/scan_submit.py` shelled `env-inspect` through `-e local-recipes`. Steward's `test_no_station_assumes_local_recipes.py` refuses that, because only `pyforge-guild` exists at runtime (spec-pyforge-steward:CAP-152). The PR's CI never ran `steward-test`, since 27.3 touched no steward path, so the violation reached main. Atlas 27.4's PR surfaced it. Fixed: `env-inspect` runs `.claude/scripts/conda-forge-expert/env_inspect.py` in `pyforge-guild`, which needs nothing the guild env lacks. The test `test_env_inspect_runs_in_the_guild_env_never_local_recipes` pins it.
