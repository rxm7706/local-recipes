---
title: '27.6: The distribution-breakdown e2e test waits for its grid to mount'
type: 'fix'
created: '2026-10-24'
status: 'done'
baseline_revision: '9ab7ef1cf1'
review_loop_iteration: 3
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
healthy, because its last assertion carried all of the page's data-callback and render time under Playwright's 5 s
default. Line numbers below are at `9ab7ef1cf1` unless marked.

- **What failed.** A full-scope `pr-preflight` for Story 37.13 (PR #2300) on 2026-10-24 red the `pyforge-atlas-test`
  lane on `tests/integration/dashboard/test_dashboard_e2e.py::test_declared_controls_render_against_real_rows`
  (`:217`, assertion at `:242`): `AssertionError: Locator expected to contain text 'linux-64'` on
  `locator("#distribution-breakdown--grid")`, timeout 5000 ms. The call log shows the grid `data-dash-is-loading="true"`,
  then empty. The suite took 3:57 there against about 44 s alone; the test passed the preflight run before and three
  times alone (6-7 s each). It failed the same way in Story 31.1's preflight on 2026-10-15, recorded as
  `DW-atlas-retro-2026-10-15-1` (medium, open).
- **How the page renders.** Vizro 0.1.60's `AgGrid.build` returns an empty `html.Div(id=<grid id>)` placeholder;
  the page's `on_page_load` callback fills it with the real `dash_ag_grid.AgGrid`, `rowData` included, and the
  browser then applies that output and loads dash-ag-grid's lazy grid chunk (`async-community.js`: ag-grid-react and
  the Dash wrapper; AG Grid's core is in the eagerly loaded `dash_ag_grid.min.js`) before the grid mounts. The facet
  filter is built from the layout (static since Story 27.5) and the chart's `#…--chart` container is in the layout
  too, so the test's three 15 s waits (`:238`-`:240`) did not wait for the callback. The grid assertion alone carried
  the callback, the browser applying its output, and the chunk, under the 5 s default.
- **Reproduced under load.** A scratch harness (a parametrized test that calls the real test function 32 times, run
  with `-n 16`) beside `python3 -c "while True: pass"` busy loops on this 16-core host. At 48 busy loops: 4 of the 24
  copies that got a server failed with the preflight's message; one call log reads `data-dash-is-loading="true"` then
  empty, as the preflight's did. At 32 busy loops: 4 of 31. After a host reboot, the original test body at 48 busy
  loops again: 4 of 25. The remaining copies errored in the fixture, its server not binding within 60 s at that
  synthetic load; no real preflight run has hit that.
- **Where the time goes (in the page, under load).** A `MutationObserver` plus a 50 ms poll in the page recorded when
  each element first showed, for 25 copies at 48 busy loops: the filter's container and the chart's were visible
  1.5-4.8 s after navigation, 3.9-16.9 s before the grid mounted, the dropdown 0.4-16.3 s before; the grid mounted
  6.3-20.8 s after navigation (median 13.3 s), and
  the `linux-64` row was in the DOM within 1 ms of the mount in every copy. The `on_page_load` request took 0.4-1.9 s,
  so most of the time is the busy browser, not the Vizro server. Under Chromium CPU throttling alone (1x-24x, an idle
  host), the same order held and the request took at most 130 ms.
- **Why one budget.** A first fix waited 15 s for the mount after the chart. At 48 busy loops it passed one counted
  batch (a second is discounted, see the Auto Run Result) and failed 3 of 24 copies in a third, on the dropdown's own
  15 s wait: Playwright-side, from `goto`, the grid
  mounted up to 22.3 s and the dropdown showed up to 20.4 s. Every step of this page waits on the same busy main
  thread, so per-step budgets do not fit it; one budget on the element drawn last does.
- **The same exposure elsewhere in the file.** `test_dashboard_e2e_navigation_and_rendering` (`:134`-`:137`,
  `:147`-`:149`, `:160`-`:162`, `:172`) and `test_every_grounded_page_renders_rows_on_the_fixture_data_root`
  (`:210`-`:212`) check grids that Vizro fills the same way, under the same 5 s default (review 2, should-fix 3). Their
  pages draw no chart, so they render sooner: 16 copies of each at 48 busy loops failed 0 of 30. The exposure is
  real but did not reproduce; the change there is for consistency with the measured mechanism.
- **Ruled out.** The fixture: the server is bound before the test starts (`wait_for_server`). A defect in the page:
  alone the grid mounts about 140 ms after the callback output lands and holds the row. `networkidle` (`:236`): it
  settled before the callback output was applied (1.2 s at 8x throttling, row at 9.4 s), so it waited on nothing the
  test checks while carrying render time on its own 30 s default.

**Approach:**
1. Add one helper, `expect_grid_mounted(grid)`, that waits for the AG Grid to replace Vizro's placeholder
   (`.ag-root-wrapper` attached inside the grid's id) with `GRID_MOUNT_TIMEOUT_MS = 60_000`, the budget this suite
   gives a loaded host (the fixture's `wait_for_server` 60 s, the WASM smoke's 60 s ready wait,
   `tests/integration/wasm/test_wasm_smoke.py:168`): 2.7 times the slowest mount measured (22.3 s). It is the grid's
   loaded state: it cannot match the placeholder, and it does not depend on the row.
   In `test_declared_controls_render_against_real_rows` it is the first check after `goto`.
2. Drop `page.wait_for_load_state("networkidle")`: the mount wait replaces it. `goto` keeps Playwright's 30 s default
   for the `load` event; it took at most 4.0 s at 48 busy loops.
3. Keep the filter, dropdown and chart checks and their 15 s timeouts unchanged, now after the mount, where those
   elements are already drawn; keep the row assertion last with its default 5 s, since the row is in the DOM within
   1 ms of the mount. A mounted grid without the row fails within 5 s, showing the grid's text.
4. Replace the comment above the waits: the grid is drawn after the filter, its dropdown and the chart's container,
   so its mount is the one wait that carries the page's render. The old comment's claim that #1836 and #1838 were a
   loaded runner outrunning 5 s goes: those runs were Story 27.5's filter defect (`DW-atlas-27-3-1`).
4a. In the navigation test and the grounded-pages test, each page's grid is mounted (the helper, right after that
   page's `goto`) before its checks run; their assertions and timeouts do not change. The file's layout-only checks
   (headings, cards, the scan pages' fields, the landmarks) are not grid checks and stay as they are.
5. Close `DW-atlas-retro-2026-10-15-1` with a `resolution:` naming this story and a `verified:` line citing the
   `path:line` it fixed. Its proposed fix (`timeout=15_000` on the row assertion) is refined: under load the whole
   render, not only the row, outruns a 15 s step, and putting the whole budget on the row would make a real missing
   row take 60 s to report.

Ledger key: `27-6-the-distribution-breakdown-e2e-test-waits-for-its-grid-to-mount`.
Type / Effort / Deps: fix / S / S-27.5.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-8** (the read surface is declared once and consumed everywhere): the Vizro board this
  test proves. A `fix`, so no CAP, no FR and no flag (`spec-feature-flag-governance` Q1).
- **AD-11** (gates are never weakened): no assertion is loosened, and no skip, `xfail`, retry or rerun is added.
- **Origin.** `docs/dreams/pyforge-atlas.md` Realization log, 2026-10-24 (the distribution-breakdown grid wait under
  load); the starting session's ask, after Story 37.13's preflight lost a run to it.

## Acceptance Criteria

- **AC1 — Waits on the mount first.** The test's first check after `goto` is `expect_grid_mounted(grid)`, which
  asserts `.ag-root-wrapper` is attached inside `#distribution-breakdown--grid` with `timeout=60_000`; there is no
  `networkidle` wait; the filter, dropdown, chart and `linux-64` row checks follow it unchanged.
- **AC1b — Every grid check waits on its mount.** In the navigation and grounded-pages tests, each grid the test
  asserts on is passed to `expect_grid_mounted` after its page's `goto` and before its first check; under the load
  harness neither test fails its assertions.
- **AC2 — Stable under load.** With the harness that failed 4 of 24 before the fix (32 copies, 16 workers, 48 busy
  loops), no copy fails its assertions, over at least three batches, plus at least one batch at 32 busy loops; setup
  errors from the fixture's server not binding are counted and reported apart, never as passes.
- **AC3 — A missing row still fails.** Against a fixture data root whose `derived_distribution_breakdown` has no
  `linux-64` row, the fixed test fails on `Locator expected to contain text 'linux-64'`, and the failure shows the
  grid's actual text (the other rows), not a timeout on the mount.
- **AC4 — Nothing weakened.** Every test in the file keeps every assertion it had (this test: two `assert`s and four
  `expect`s); `git diff` adds no `skip`, `xfail`, `rerun`, `flaky`, `retry` or `sleep`; under `src/` only
  `test_dashboard_e2e.py` changes.
- **AC5 — Suites.** `pixi run -e pyforge-atlas pyforge-atlas-test`, `kedro-test` and `kedro-catalog-check` pass.
- **AC6 — Row closed.** `DW-atlas-retro-2026-10-15-1` reads `status: closed` with a `resolution:` naming Story 27.6
  and a `verified:` line citing the test's `path:line`.

## Boundaries & Constraints

- Test-only: `src/pyforge/atlas/**` does not change; the page renders as it does today.
- Only `test_dashboard_e2e.py` changes: the helper, this test, and the grid checks of the navigation and
  grounded-pages tests, plus a doubled line in the semantic-navigation test's docstring. The fixture, the scan-pages
  test and the semantic-navigation test's code stay as they are.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| the fixture root, an idle host | passes in 6-7 s, as today |
| the fixture root, the load harness | passes; the mount wait absorbs the callback and the lazy grid chunk |
| a root without the `linux-64` row | fails on the row assertion within 5 s of the mount, showing the grid's text |
| a callback that never fills the grid | fails on the mount wait after 60 s, naming `.ag-root-wrapper` |
| a filter that never builds its selector (Story 27.5's 0×0 container) | fails on `expect(facet_filter).to_be_visible`, 15 s after the mount |

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
  `python3 -c "while True: pass"` processes (three batches), and beside 32 (at least one) — expected: no copy fails
  its assertions; setup errors (`dashboard server did not bind port … within 60s`) counted apart.
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

## Review Triage Log

### 2026-10-24 — Review 1 (independent subagent, read-only): FAIL
- verdicts: 1 blocker, 4 should-fix, 7 nits; all accepted.
- B1 (DW row closed on evidence the spec did not record): the Auto Run Result below now records every batch, AC3 and
  AC5.
- S1 (surface reconcile and scoped stamps missing): done before landing, on `spec-pyforge-atlas` and its co-governor
  `pyforge-steward/spec-pyforge-unifying-strategy`.
- S2 (`goto` and `networkidle` still carried render time on smaller budgets): `networkidle` dropped; `goto`'s 30 s
  `load` default kept, measured at most 4.0 s under load.
- S3 (the ordering evidence was circular, the timing harness waited in sequence): re-measured in the page with a
  `MutationObserver` under 48 busy loops; the order holds in every copy (Intent).
- S4 ("every copy passes" cannot hold while the fixture errors at that load): reworded to "no copy fails its
  assertions; setup errors counted apart" in the epic, the Dream and AC2.
- N1 (`async-community.js` is dash-ag-grid's lazy chunk, not AG Grid's core), N2 (CPU throttling says nothing about
  the server under host load; the in-page run now times `on_page_load` under load), N3 (one-decimal figures), N5 (the
  0×0 filter fails on `facet_filter` visibility), N6 (the DW resolution's argument), N7 (status `in-review`, this
  log): fixed. N4 (row check at 15 s): declined; the in-page run puts the row within 1 ms of the mount, so the
  default 5 s keeps a real missing row's report fast.

### 2026-10-24 — Review 2 (independent subagent, read-only): PASS, 0 blockers
- verdicts: 3 should-fix, 7 nits; all fixed.
- S1 (the comment's #1836/#1838 "loaded runner" claim): dropped; those runs were Story 27.5's filter defect.
- S2 (the epic's Given still said "AG Grid's own script"): reworded, and the base's `networkidle` named.
- S3 (the file's other grid checks shared the 5 s exposure): fixed here rather than recorded (the repo's fix-now
  rule): one helper, `expect_grid_mounted`, now gates every grid check in the file; measured before and after under
  load (Auto Run Result).
- N1 (DW wording), N2 (six assertions, not five), N3 (memlog figures, corrected in the reconcile entry appended at
  landing), N4 (one
  measurement pair in the comments: in-page 20.8 s and 16.9 s), N5 ("the chart's container"), N6 ("one counted
  batch"), N7 (idle 6-7 s everywhere): fixed. The docstring duplicate the reviewer noted (`:281`-`:282` at
  `2777973183`) is fixed too.

### 2026-10-24 — Review 3 (independent subagent, read-only, on the widened delta): PASS, 0 blockers
- verdicts: 3 should-fix, 6 nits; all fixed.
- S1 (no memlog entry recorded the widening or corrected the figures): the landing's surface reconcile entry does
  both, on `spec-pyforge-atlas` and its co-governor.
- S2 (the layout residual risk claimed "none failed" for tests never load-tested, and its 4.8 s was absolute while
  the Intent gave relative times): reworded to name the two tests not load-tested; the absolute range is in the
  Intent.
- S3 (the "final" evidence predated the helper change): AC3, the alone runs, the whole file, AC5 and the full-scope
  preflight re-run on the final commit; every row names its commit.
- N1 (boundaries and epic surface now name the docstring fix), N2 (cite revision), N3 (per-test split of the other
  tests' batches), N4 (DW resolution names #1836/#1838 as Story 27.5's defect), N5 (Dream qualifier, 0 of 30), N6
  (this entry, iteration 3): fixed.

## Spec Change Log

- 2026-10-24: minted with Story 27.6 under Epic 27 from the Dream entry of that date; implemented the same session.
  The cause was measured (CPU throttling timeline, load harness) before the fix.
- 2026-10-24: redesigned before review. The first fix (a 15 s mount wait after the chart, `35f5beed9e`) failed 3 of
  24 copies in one load batch on the dropdown's own 15 s wait; the mount wait moved first with one 60 s budget
  (`9c39037823`).
- 2026-10-24: review 1 fixes: `networkidle` dropped and the comment corrected (`bb0c148438`); Intent re-measured in
  the page; ACs, matrix and the DW row reworded.
- 2026-10-24: review 2 fixes: scope widened from one test to every grid check in the file (AC1b, Approach 4a), one
  helper; the #1836/#1838 claim dropped.

## Auto Run Result

- Implemented by hand in worktree `.claude/worktrees/exciting-faraday-1e4549` from `9ab7ef1cf1`. The host rebooted
  once mid-session (16:02, a clean systemd reboot); the before-fix batch was re-run after it under the same
  conditions as the after-fix batches.
- Load harness: 32 copies of the test body, `-n 16`, beside N busy loops; "served" = copies whose fixture server
  bound. Setup errors are the fixture's `dashboard server did not bind port … within 60s`, never counted as passes.

| Code | Busy loops | Failed / served | Setup errors | Failing check |
|---|---|---|---|---|
| before (`9ab7ef1cf1`) | 48 | 4 / 24 | 8 | grid `to_contain_text`, 5 s |
| before | 32 | 4 / 31 | 1 | grid `to_contain_text`, 5 s |
| before, after the reboot | 48 | 4 / 25 | 7 | grid `to_contain_text`, 5 s |
| first fix (`35f5beed9e`, 15 s mount wait after the chart) | 48 | 0 / 25, 0 / 21 (a), 3 / 24 | 7, 11, 8 | dropdown `to_be_visible`, 15 s |
| first fix | 32 | 0 / 30 | 2 | — |
| one 60 s mount wait first (`9c39037823`) | 48 | 0 / 17, 0 / 22, 0 / 32 | 15, 10, 0 | — |
| `9c39037823` | 32 | 0 / 32, 0 / 32 | 0, 0 | — |
| final (`bb0c148438`, no `networkidle`) | 48 | 0 / 27, 0 / 28, 0 / 27 | 5, 4, 5 | — |
| final | 32 | 0 / 30 | 2 | — |
| final, with the helper (`9a0215fb36`) | 48 | 0 / 32 | 0 | — |
| navigation test, before (`2777973183`, 16 copies) | 48 | 0 / 15 | 1 | — |
| grounded-pages test, before (`2777973183`, 16 copies, same batch) | 48 | 0 / 15 | 1 | — |
| navigation test, with `expect_grid_mounted` (`9a0215fb36`'s code) | 48 | 0 / 13 | 3 | — |
| grounded-pages test, with `expect_grid_mounted` (same batch) | 48 | 0 / 11 | 5 | — |

- (a) A commit's pre-commit hook stashed the then-unstaged test file while this batch's workers started, so it may
  have run the original test; it is not counted as evidence for either version.
- AC1: `test_dashboard_e2e.py:255` (`expect_grid_mounted(grid)`; the helper at `:75`-`:77` attaches
  `.ag-root-wrapper` with `GRID_MOUNT_TIMEOUT_MS = 60_000`, `:72`) is the first check after `goto`; `:256`-`:260`
  unchanged. AC1b: `:137`, `:155`, `:168`, `:182` (navigation) and `:226` (grounded pages).
- `9a0215fb36` is the last commit that touches `src/`; the runs below marked with it ran on that test file.
- The whole file alone (`9a0215fb36`): 5 passed in 33.6 s (34.9 s on the working tree before that commit).
- An earlier full-scope `pr-preflight` on `2777973183` plus the uncommitted matrix row, before the helper change:
  exit 0, 21 of 37 lanes. The landing preflight on the final commit is recorded below.
- AC3 (`9a0215fb36`): the test against a fixture root without the `linux-64` row → `1 failed`,
  `AssertionError: Locator expected to contain text 'linux-64'` on `to_contain_text … with timeout 5000ms`, actual
  value the grid's three other rows (`osx-arm64`, `3.12`, `3.11`).
- Alone (`9a0215fb36`): 3 of 3 passed, 6.1-6.4 s each (6.3-6.6 s on `bb0c148438`).
- AC4: `git diff 9ab7ef1cf1..HEAD -- src/` touches only `test_dashboard_e2e.py`, adds no `skip`, `xfail`, `rerun`,
  `flaky`, `retry` or `sleep`, and keeps every assertion in the file (this test's two `assert`s and four `expect`s).
- AC5 (`9a0215fb36`, scratch harness moved out first): `pixi run --frozen -e pyforge-atlas kedro-test` (it runs
  `pyforge-atlas-test`) exit 0, 3,478 passed and 20 skipped, then 103 passed; `kedro-catalog-check` exit 0, 71
  passed. The same on `bb0c148438`.
- Residual risk: at 48 busy loops on 16 cores (a load past any measured preflight) the shared `dashboard_server`
  fixture can fail to bind within its 60 s; it errors at setup, visibly, and no real preflight run has hit it. Not
  changed here: no real run has failed on it, and the fixture serves the whole file.
- Residual risk: the file's layout-only checks (headings, cards, the scan pages' fields, landmarks) keep Playwright's
  5 s default. In the page, at 48 busy loops, the distribution-breakdown page's layout elements showed 1.5-4.8 s after
  navigation (Intent), a thin margin at a load past any measured preflight. The scan-pages and semantic-navigation
  tests, which hold most of those checks, were not load-tested; the declared-controls, navigation and grounded-pages
  tests were, and none failed.
