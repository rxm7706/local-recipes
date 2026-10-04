---
title: "27.5: The distribution-breakdown facet filter builds its control"
type: 'fix'
created: '2026-10-04'
status: 'in-progress'
baseline_revision: '3ec837c431a989d926417ed04fe7edda3c659a24'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-27-3-the-read-surfaces-render-what-design-specifies-on-real-data.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/DESIGN.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
  - src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_e2e.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the `distribution-breakdown` page declares a `facet` filter and a chart (DESIGN.md § 3.8). The filter often fails to build its control.

- **What renders:** Story 27.3's `test_declared_controls_render_against_real_rows` (`tests/integration/dashboard/test_dashboard_e2e.py:223`) fails intermittently. `#distribution-breakdown--filter-facet` renders as an empty 0×0 `div` with no children, while `#distribution-breakdown--chart` renders at 1240×173 on the same page.
- **Where it failed:** in CI on #1836 (it passed on a rerun) and on #1838. Locally it failed every time after one early pass, both alone and in the full file.
- **What did not help:** a longer wait (networkidle plus 15 s) and a `spawn` start method for the server. So the defect is in the filter build, not in the test.
- **Quarantine:** #1842 (`50aac7f535`) marked the test `xfail(strict=False)` (:216-222) and recorded `DW-atlas-27-3-1` (medium, open), which names this story.
- **Where the filter is built:** `dashboard/app.py::_declared_filters` (:445-485) runs the page's loader once at dashboard build time, then emits `vm.Filter(id=f"{page.id}--filter-{column}", column=column)` for each declared column with any non-null value. `_data_page` (:488-505) registers the same loader as the page's data source (`data_manager[f"data::{page.id}"] = loader`) and passes the filters as the page's `controls`. Vizro builds the control's selector from the data it holds for that source, so a selector built against a different frame, an empty one, or a stale one leaves the container without its child.

**Approach:**
- Reproduce the empty container deterministically, below the browser if possible. For example, build the dashboard against the fixture data root and inspect the filter's built selector and its options. Find why Vizro emits the container without its selector.
- Fix the build in `dashboard/app.py`, or in how the page's data source is registered, so the declared control is built from the rows the page shows, on every build and every page load.
- Pin the root cause with a test that fails without the fix and does not need a browser.
- Remove the `xfail` from `test_declared_controls_render_against_real_rows`, keeping its 15 s waits.
- Close `DW-atlas-27-3-1` with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed.

Ledger key: `27-5-the-distribution-breakdown-facet-filter-builds-its-control`.
Type / Effort / Deps: fix / S / S-27.3.

### Living CAP citations

- The atlas capability that shipped the read surfaces (Story 27.3, closing `DW-FU-20-5`: "every page renders its declared DESIGN.md controls"). This is a `fix`, so it mints no new CAP and no FR. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given the fixture data tree When the dashboard is built and `distribution-breakdown` is served Then `#distribution-breakdown--filter-facet` contains its selector, with one option per distinct non-null `facet` value in the fixture rows
- Given the root cause When its new test runs against the tree before the fix Then it fails, and after the fix it passes, with no browser
- Given `test_declared_controls_render_against_real_rows` with its `xfail` removed When it runs ten times in a row, each against a fresh server Then it passes every time
- Given a page whose data has no rows When the dashboard is built Then it carries no filter, as today (`_declared_filters`' honest-empty rule), and a declared column the loader does not project still raises
- Given this story lands When `DW-atlas-27-3-1` is read Then it is closed with a `resolution:` naming Story 27.5 and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:**
- Keep every gate fixture-based and non-credentialed (NFR-1).
- Respect atlas's import boundaries (`src/shared/packages/pyforge-atlas/AGENTS.md`, AD-1).
- Fix the defect where the build lives, and pin it with a test that fails without the fix.

**Never:**
- Never make the test pass by lengthening waits, retrying, or loosening its assertions. A longer wait was already tried, and it does not fix the defect.
- Never keep the `xfail`, or replace it with a skip.
- Never drop the declared filter from `PageDef` to make the page pass. DESIGN.md § 3.8 declares it.

</intent-contract>

## Binding

- Parent: Story 27.3 and its quarantine hotfix #1842 (`DW-atlas-27-3-1`).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-04 entry.
- Epic: Epic 27, which reopens. The sync rolls `epic-27` from `done` to `in-progress` while this story is open, and back to `done` when it lands. The operator ruled on 2026-10-04 that a fix goes into its own epic and reopens it, never a new epic, and doctor Story 41.5 lets `ledger-regression` accept the reopen.
- Ledger key: `27-5-the-distribution-breakdown-facet-filter-builds-its-control`.
- Ledger status at mint: `backlog`.
- Deps: S-27.3 (done).
- Surface: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/`, `src/shared/packages/pyforge-atlas/tests/integration/dashboard/` (`test_dashboard_controls.py` already tests `_declared_filters`) and the atlas deferred-work ledger, all inside Epic 27's `[epic_surfaces]` entry.
- Minted 2026-10-04 at the operator's request.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding). It runs the e2e test with its `xfail` removed.
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `for i in $(seq 10); do pixi run -e pyforge-atlas pytest -q src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_e2e.py::test_declared_controls_render_against_real_rows || exit 1; done` — expected: exit 0, with all ten runs passing.

## Review Triage Log

- No review has run yet.
