---
title: '27.6: The distribution-breakdown e2e test waits for its grid to mount'
type: 'fix'
created: '2026-10-24'
status: 'in-progress'
baseline_revision: '9ab7ef1cf1'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-27-5-the-distribution-breakdown-facet-filter-builds-its-control.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
  - src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_e2e.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `test_declared_controls_render_against_real_rows` fails under parallel load while the page it tests is
healthy, because its last assertion carries all of the page's data-callback and render time under Playwright's 5 s
default. Line numbers below are at `9ab7ef1cf1`.

- **What failed.** A full-scope `pr-preflight` for Story 37.13 (PR #2300) on 2026-10-24 red the `pyforge-atlas-test`
  lane on `tests/integration/dashboard/test_dashboard_e2e.py::test_declared_controls_render_against_real_rows`
  (`:217`, assertion at `:242`): `AssertionError: Locator expected to contain text 'linux-64'` on
  `locator("#distribution-breakdown--grid")`, timeout 5000 ms. The call log shows the grid `data-dash-is-loading="true"`,
  then empty. The suite took 3:57 there against about 44 s alone; the test passed the preflight run before and three
  times alone (about 6 s each). It failed the same way in Story 31.1's preflight on 2026-10-15, recorded as
  `DW-atlas-retro-2026-10-15-1` (medium, open).
- **How the page renders.** Vizro 0.1.60's `AgGrid.build` returns an empty `html.Div(id=<grid id>)` placeholder;
  the page's `on_page_load` callback fills it with the real `dash_ag_grid.AgGrid`, and the browser then fetches and
  parses AG Grid's own script (`async-community.js`) when the grid first mounts. The facet filter is built from the
  layout (static since Story 27.5) and the chart's `#…--chart` container is in the layout too, so the test's three
  15 s waits (`:238`-`:240`) do not wait for the callback. The grid assertion alone carried the callback, the browser
  applying its output, and AG Grid's script, under the 5 s default.
- **Where the time goes.** An in-page timeline (a `MutationObserver` plus the browser's resource timings) under
  Chromium CPU throttling at 1x, 4x, 8x, 12x, 16x and 24x: the `on_page_load` request answers within 130 ms at every
  rate, so the server is not the cost. At 24x the answer arrives 7.1 s after the page opens, the browser finishes
  applying it at 25.4 s, fetches `async-community.js` at 26.2 s and mounts the grid at 32.4 s; at every rate the
  `linux-64` row is in the DOM within 4 ms of the grid's `.ag-root-wrapper`.
- **Reproduced under load.** 32 copies of the real test body (a scratch harness that calls the test function) on 16
  xdist workers beside 48 busy-loop processes on this 16-core host ran 3:52 and failed 4 of the 24 copies that got a
  server with the preflight's message; one call log reads `data-dash-is-loading="true"` then empty, as the preflight's
  did. The other 8 copies errored in the fixture, the server not binding within 60 s at that load; the preflight run
  did not hit that. At 32 busy loops the same harness failed 4 of 31 (one setup error).
- **Timed under load.** A scratch timing harness (the same page, every step waited up to 180 s, 32 copies on 16
  workers) at 48 busy loops: the grid mounted 6.6-22.3 s after `goto` (median 14.4 s), up to 16.0 s after the chart;
  the facet dropdown appeared 2.4-20.4 s after `goto`, always before the grid mounted; the row was in the DOM within
  0.5 s of the mount. At 32 busy loops: mount 6.5-21.2 s, dropdown up to 17.5 s, mount up to 11.4 s after the chart
  (3 of 32 copies over 5 s, the before-fix failure rate). A first fix, a 15 s mount wait after the chart, passed two
  batches at 48 busy loops and failed 3 of 24 copies in the third, on the dropdown's own 15 s wait: per-step budgets
  do not fit a page whose every element can wait on the same busy main thread.
- **Ruled out.** The fixture: the server is bound before the test starts (`wait_for_server`), and the callback
  answers quickly. A defect in the page: alone the grid mounts about 140 ms after the callback output lands and holds
  the row. `networkidle`: it settles before the callback output is applied under throttling (1.2 s at 8x, row at 9.4
  s), so it is no wait on the grid.

**Approach:**
1. In `test_declared_controls_render_against_real_rows`, right after `networkidle`, wait for the AG Grid to mount
   inside `#distribution-breakdown--grid` (`.ag-root-wrapper` attached) with `timeout=60_000`, the budget this suite
   gives a loaded host (the fixture's `wait_for_server` 60 s, the WASM smoke's 60 s ready wait). The grid is the
   element the page draws last, so this one wait carries the whole render, about 2.7 times the slowest mount
   measured (22.3 s). It is the grid's loaded state: it does not pass on the placeholder, and it does not depend on
   the row.
2. Keep the filter, dropdown and chart checks and their 15 s timeouts unchanged, now after the mount, and keep the row
   assertion last with its default timeout: the row is in the DOM when the grid mounts, so a mounted grid without it
   fails within 5 s, showing the grid's text.
3. Replace the comment above the waits: the filter and the chart's container render from the layout, the grid from
   the data callback, and why the mount wait is first and 60 s.
4. Close `DW-atlas-retro-2026-10-15-1` with a `resolution:` naming this story and a `verified:` line citing the
   `path:line` it fixed. Its proposed fix (`timeout=15_000` on the row assertion) is refined: a wait on the row text
   alone reads a grid that never mounts and a mounted grid without the row the same way.

Ledger key: `27-6-the-distribution-breakdown-e2e-test-waits-for-its-grid-to-mount`.
Type / Effort / Deps: fix / S / S-27.5.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-8** (the read surface is declared once and consumed everywhere): the Vizro board this
  test proves. A `fix`, so no CAP, no FR and no flag (`spec-feature-flag-governance` Q1).
- **AD-11** (gates are never weakened): no assertion is loosened, and no skip, `xfail`, retry or rerun is added.
- **Origin.** `docs/dreams/pyforge-atlas.md` Realization log, 2026-10-24 (the distribution-breakdown grid wait under
  load); the starting session's ask, after Story 37.13's preflight lost a run to it.

## Acceptance Criteria

- **AC1 — Waits on the mount first.** The test's first check after `networkidle` asserts
  `#distribution-breakdown--grid .ag-root-wrapper` is attached with `timeout=60_000`; the filter, dropdown, chart and
  `linux-64` row checks follow it unchanged.
- **AC2 — Stable under load.** With the harness that failed 4 of 24 before the fix (32 copies, 16 workers, 48 busy
  loops), no copy fails its assertions, over at least three batches; setup errors from the server not binding are
  counted and reported, not counted as passes.
- **AC3 — A missing row still fails.** Against a fixture data root whose `derived_distribution_breakdown` has no
  `linux-64` row, the fixed test fails on `Locator expected to contain text 'linux-64'`, and the failure shows the
  grid's actual text (the other rows), not a timeout on the mount.
- **AC4 — Nothing weakened.** The test keeps every assertion it had; `git diff` adds no `skip`, `xfail`, `rerun`,
  `flaky`, `retry` or `sleep`; under `src/` only `test_dashboard_e2e.py` changes.
- **AC5 — Suites.** `pixi run -e pyforge-atlas pyforge-atlas-test`, `kedro-test` and `kedro-catalog-check` pass.
- **AC6 — Row closed.** `DW-atlas-retro-2026-10-15-1` reads `status: closed` with a `resolution:` naming Story 27.6
  and a `verified:` line citing the test's `path:line`.

## Boundaries & Constraints

- Test-only: `src/pyforge/atlas/**` does not change; the page renders as it does today.
- Only `test_declared_controls_render_against_real_rows` changes; the file's other tests and the fixture stay as they
  are.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| the fixture root, an idle host | passes in about 6 s, as today |
| the fixture root, the load harness | passes; the mount wait absorbs the callback and AG Grid's script |
| a root without the `linux-64` row | fails on the row assertion, showing the grid's text |
| a callback that never fills the grid | fails on the mount wait after 60 s, naming `.ag-root-wrapper` |
| a filter that never builds its selector (Story 27.5's defect) | fails on the dropdown check, 15 s after the mount |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-8 (a `fix`; no CAP minted).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-24 (the distribution-breakdown grid wait
  under load) entry.
- Epic: Epic 27, which owns this test (Stories 27.3 and 27.5) and reopens: the sync rolls `epic-27` from `done` to
  `in-progress` while this story is open, and back to `done` when it is promoted (doctor Story 41.5 lets
  `ledger-regression` accept the reopen).
- Ledger key: `27-6-the-distribution-breakdown-e2e-test-waits-for-its-grid-to-mount`.
- Ledger status at mint: `backlog`.
- Deps: S-27.5 (done).
- Surface: `src/shared/packages/pyforge-atlas/**`, inside Epic 27's `[epic_surfaces]` entry.
- Minted and implemented 2026-10-24 in one session; reviewed by an independent reviewer against this spec before
  landing (behavioural guideline 8).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-atlas pytest "src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_e2e.py" -q -p no:cacheprovider` — expected: every test passes.
- AC2, the load harness, on a scratch file placed beside the test and removed afterwards: a parametrized test that
  calls `test_declared_controls_render_against_real_rows(dashboard_server)` 32 times, run with `-n 16` beside 48
  `python3 -c "while True: pass"` processes — expected: no failed copy, exit code read directly.
- AC3, on the same scratch file: a fixture that copies the fixture data root without the `linux-64` row and points
  `FIXTURE_DATA_ROOT` at it — expected: `1 failed`, `Locator expected to contain text 'linux-64'`, actual text
  showing `osx-arm64`.
- AC4: `git diff origin/main...HEAD -- src/ | grep -E '^\+.*(skip|xfail|rerun|flaky|retry|sleep)'` — expected: no
  output; `git diff --name-only origin/main...HEAD -- src/` — expected: only the test file.
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` — expected: pass (AC5).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped
  stamps.
- `TMPDIR=$HOME/.cache/pyforge-preflight-tmp PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` —
  expected: exit 0.

## Spec Change Log

- 2026-10-24: minted with Story 27.6 under Epic 27 from the Dream entry of that date; implemented the same session.
  The cause was measured (CPU throttling timeline, load harness) before the fix.

## Auto Run Result

- Implemented by hand in worktree `.claude/worktrees/exciting-faraday-1e4549` from `9ab7ef1cf1`.
- Reproduction before the fix: load harness at 48 busy loops, 4 of 24 copies failed (3:52); see Intent.
