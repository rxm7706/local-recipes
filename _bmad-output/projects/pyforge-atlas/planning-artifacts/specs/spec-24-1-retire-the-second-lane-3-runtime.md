---
title: 'Story 25.1: Retire the second Lane-3 runtime'
type: 'refactor'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: 'e866da4ed6f94facde6ceb37975113d6eed142fa'
---

<intent-contract>

## Intent

**Problem:** The legacy Panel/Bokeh `views/` package is a second Lane-3 runtime that reads
SQLite `cf_atlas.db` via dynamic CLI imports, has zero production importers, and evades the F1
DuckDB-singularity gate — while the live Vizro/BSL dashboard (34 pages) is the sole operator
surface.

**Approach:** Delete `pyforge/atlas/views/` and its unit tests, drop the run-dependencies declared
solely for that module (`bokeh`, `tornado`, `starlette`), remove the Story 14.3 ASGI-containment
test that existed only to fence `views/`, update stale page-count literals to 34, and record the
supersession (`spec-atlas-query-dashboards` → `shipped`; close DW-14-2-1 / DW-14-3-2).

## Boundaries & Constraints

**Always:**
- Delete the entire `src/pyforge/atlas/views/` tree and `tests/unit/views/` tree.
- Remove `bokeh`, `tornado`, `starlette` from **both** member `pyproject.toml` and member
  `pixi.toml` (AUD-ATLAS-010 byte-for-byte sync).
- Remove `test_asgi_host_only_in_views_asgi_module` and its constants from
  `test_no_inline_io.py`.
- Update F1 singularity docstring in `test_duckdb_sole_engine.py` — remove the cli_bridge
  indirect-exception paragraph (no dynamic-import evasion remains).
- Fix page-count literals: live count is **34** `PageDef` entries in `PAGE_INVENTORY`
  (`dashboard/app.py:82+`); update stale 28/31 references in `dashboard/app.py:13`,
  `dashboard/__init__.py:8`, root `pixi.toml:1065`/`:1070`, and integration test docstrings.
- Flip `spec-atlas-query-dashboards/SPEC.md` status `in-progress` → `shipped` with memlog entry.
- Close `DW-14-2-1` and `DW-14-3-2` in `deferred-work-ledger.md` citing Story 25.1.
- Flip ledger key `25-1-retire-the-second-lane-3-runtime` to `done` via Tier-3 feed +
  `sprint-ledger-sync`.
- Scrub every dotted `views` package import-path reference across the repo (grep AC).

**Never:**
- Remove root `pixi.toml` `httpx` (Story 16.2 `lasuite_bringup.py` still needs it).
- Remove root `pixi.toml` `starlette` under `[feature.mcp-host.dependencies]` or root `bokeh`
  under `[feature.local-recipes.dependencies]` — those serve other surfaces.
- Resurrect the pluggable-widget-registry; re-introduce only if a Vizro page asks for it.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/` -- DELETE entire package (8 modules:
  `__init__.py`, `asgi.py`, `cli_bridge.py`, `live.py`, `registry.py`, `render.py`, `resources.py`,
  `widgets.py`).
- `src/shared/packages/pyforge-atlas/tests/unit/views/` -- DELETE entire test dir (7 files).
- `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_no_inline_io.py:442-475` -- remove
  ASGI-host denylist constants + `test_asgi_host_only_in_views_asgi_module`.
- `src/shared/packages/pyforge-atlas/tests/unit/singularity/test_duckdb_sole_engine.py:17-24` --
  remove cli_bridge indirect-exception paragraph from module docstring.
- `src/shared/packages/pyforge-atlas/pyproject.toml:66-76` -- remove bokeh/tornado/starlette + comments.
- `src/shared/packages/pyforge-atlas/pixi.toml:91-104` -- remove bokeh/tornado/starlette + comments.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py:13` -- 28 → 34 pages.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/__init__.py:8` -- 28 → 34 pages.
- `pixi.toml:1065,1070` -- 31 → 34 pages in task descriptions.
- `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_dryrun.py:5` --
  28 → 34.
- `src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_e2e.py:180` --
  28 → 34.
- `src/shared/packages/pyforge-atlas/AGENTS.md:83` -- remove `views/` from module layout list.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-query-dashboards/SPEC.md:3-5`
  -- status → `shipped`.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md:1857-1892` --
  close DW-14-2-1, DW-14-3-2.
- Planning docs with dotted import-path grep hits -- reword to path-based or past-tense references
  (`spec-14-1`, `spec-14-2`, `epics.md:2037`, steward research batch, marshal coverage baseline).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/` -- delete package -- retires second runtime.
- `src/shared/packages/pyforge-atlas/tests/unit/views/` -- delete tests -- no orphan test surface.
- `src/shared/packages/pyforge-atlas/pyproject.toml` + `pixi.toml` -- drop bokeh/tornado/starlette -- AUD-ATLAS-010.
- `tests/unit/catalog/test_no_inline_io.py` -- remove views ASGI test block -- module gone.
- `tests/unit/singularity/test_duckdb_sole_engine.py` -- trim docstring -- no evasion narrative.
- Page-count literal files (dashboard app/__init__, root pixi.toml, integration tests) -- 34 -- closes open question.
- `spec-atlas-query-dashboards/SPEC.md` + `.memlog.md` -- shipped + dated entry -- supersession recorded.
- `deferred-work-ledger.md` -- close DW-14-2-1, DW-14-3-2 -- moot with module deletion.
- Grep-scrub planning docs -- zero dotted import-path hits -- AC grep gate.
- Tier-3 `sprint-status.yaml` + `sprint-ledger-sync` -- ledger `done` -- status promotion.

**Acceptance Criteria:**
- Given `views/` deleted and deps dropped, when `grep -rn "atlas\.views"` runs across the repo,
  then it returns nothing.
- Given the retirement, when `pixi run -e pyforge-atlas pyforge-atlas-test` runs, then exit 0.
- Given the retirement, when `pixi run -e local-recipes dashboard-dryrun` runs, then exit 0.
- Given CAP-1..CAP-4 superseded, when `spec-atlas-query-dashboards` is read, then status is
  `shipped` and CAP-5..CAP-7 remain the live contract.

## Verification

**Commands:**
- `grep -rn "atlas\.views" .` -- expected: no matches (from repo root).
- `pixi run -e pyforge-atlas pyforge-atlas-test` -- expected: exit 0.
- `pixi run -e local-recipes dashboard-dryrun` -- expected: exit 0.
- `pixi run -e local-recipes sprint-ledger-sync -- --project pyforge-atlas` -- expected: exit 0,
  ledger key `25-1-retire-the-second-lane-3-runtime: done`.

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (no reviewer layers launched — deletion story; all verification gates green on first pass)

## Auto Run Result

Status: done

**Summary.** Retired the second Lane-3 runtime: deleted `pyforge/atlas/views/` (8 modules) and
`tests/unit/views/` (7 files), removed `bokeh`/`tornado`/`starlette` run-deps from member
`pyproject.toml` and `pixi.toml`, dropped the Story 14.3 ASGI-containment test, trimmed F1
singularity docstring, updated page-count literals to 34, flipped `spec-atlas-query-dashboards`
to `shipped`, closed DW-14-2-1 and DW-14-3-2, and promoted ledger key `25-1-…` to `done`.

**Verification.**
- `grep -rn "atlas\.views" .` — clean (exit 1)
- `pixi run -e pyforge-atlas pyforge-atlas-test` — exit 0
- `pixi run -e local-recipes dashboard-dryrun` — 71 passed, 1 skipped, exit 0
- `sprint-ledger-sync --project atlas --repair-feed` — wrote 142 keys (primary checkout feed)

**Follow-up review recommended:** false

**Residual risks:** PR will need `maintenance` label (changes outside `recipes/`). Tier-3 feed
updated on primary checkout; worktree ledger synced manually to match promote output.
