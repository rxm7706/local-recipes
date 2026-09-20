---
title: '51.12: A dispatch-only checkout still has fleet rows'
type: 'fix'
created: '2026-09-20'
status: 'done'
baseline_revision: '00e52b3d37a064c94e28ab06ada03cc1fa60d4fb'
final_revision: '09b45a2a130fe98b2b9a71d065098b7f1ea1cdda'
review_loop_iteration: 1
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** with the 51.10 probe fix installed, `marshal status --project pyforge-marshal --format json` from the marshal clone (`lr-m50`) still returned `homes: []` at 2026-09-20 00:47Z while marshal 51.7's dispatch session ran — `run_status` builds its fleet from the git worktrees whose branch starts with `loop/`, and a dispatch-only clone (one station per clone, MRS-DISP-041) has none, so the dispatch overlay has no row to land on and `marshal watch` reads the station idle.

**Approach:** the fleet sweep also admits stations discovered from this checkout's own Tier-3 (`_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/`, through `cli/dispatch.py`'s own locators); each such station not already in the loop-home fleet gets the Spec's "home with no run yet" placeholder row (`FleetHomeFacts(slug, branch="loop/<slug>")`, `has_run=False`) and the existing `_merge_dispatch_overlay` fills it from the run journal exactly as it fills a loop-home row.

## Boundaries & Constraints

**Always:**
- A loop-home station is never duplicated by its own Tier-3 run; `--project` scopes a dispatch-only station like any other
- The placeholder never engages `derive_home_state` or `journal_unreadable` (no loop run exists to read); `_gather_failed_patches` is skipped for a `None` home
- Discovery reads `latest_dispatch_run_dir` — never a second directory convention

**Never:**
- Do not fabricate loop-run facts (supervisor pid, budget, tasks) for a dispatch-only row — every non-overlay field stays the placeholder default
- Do not change `_merge_dispatch_overlay` or `_apply_dispatch_overlay` — the overlay is the same code path for both row kinds

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| dispatch-only clone, live run | no `loop/` worktrees; one Tier-3 run with a `story_key` | one row: `slug`, `branch: loop/<slug>`, `dispatch_run_id`, state `running` | n/a |
| loop home + its own Tier-3 run | `loop/acme` worktree and a Tier-3 run for acme | one row (overlaid), never two | n/a |
| `--project beta` | acme loop home, beta dispatch-only | only beta's row | n/a |
| no `_bmad-output/projects/` | fresh checkout | no dispatch-only rows; loop-home sweep unchanged | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-259`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` (`_dispatch_only_slugs`, the fleet sweep and the per-home loop in `run_status`), `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` (`TestDispatchOnlyCheckoutRows`).
Ledger key: `51-12-a-dispatch-only-checkout-still-has-fleet-rows`.
Minted 2026-09-20 from `epics.md`; hand-driven in the 51.10 PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- From `lr-m50` (no loop homes, marshal 51.7 live): `marshal status --project pyforge-marshal --format json` names the live run with state `running`; `marshal watch --fleet` with that clone's own binary names it.

## Review Triage Log

### 2026-09-20 — hand-driven pass (same PR as 51.10)
  - `[high]` `[patch]` `run_status` built the fleet only from `loop/`-prefixed git worktrees; a dispatch-only clone yielded no row, so the overlay never ran. Fixed: `_dispatch_only_slugs(repo_root)` via `cli/dispatch.py::latest_dispatch_run_dir`; `(slug, None)` fleet entries; a `FleetHomeFacts(slug, branch="loop/<slug>")` placeholder; `_gather_failed_patches` skipped for a `None` home.
  - `[low]` `[patch]` the 46.5 test fixture's journal lines carry no `id`/`ts`/`run_id`, so `fold` quarantines them (`MRS-JOURNAL-001`) and `story_key` never parses — the new test writes a real-shape launch intent (`ts` at millisecond precision) ahead of the fixture's lines.
  - `[low]` `[reject]` add a `dispatch_only: true` marker field to the row — the JSON contract is externally read; `has_run=False` plus the overlay fields already say it; not added.

## Auto Run Result

**Status:** done
**Summary:** from `lr-m50` (no loop homes, marshal 51.7 live) the worktree's binary now reports `('pyforge-marshal', 'pyforge-marshal-20260919T235245280Z-a215d473', 'running')` for `marshal status --project pyforge-marshal --format json`, where the pre-fix binary returned `homes: []`. `TestDispatchOnlyCheckoutRows` (3 tests) covers the row, the no-duplication/`--project` scoping, and the no-projects-dir case.
**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` 8278 passed, 1 skipped; `pixi run --frozen -e pyforge-ci pyforge-deps-test` 130 passed, 3 skipped.
**Files changed:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_status.py`.
**Residual risks:** `marshal watch --fleet` reports the checkout its binary is installed in (`cli/config.py::repo_root()` is package-relative, by design) — an operator with three dispatch clones runs it per clone; a fleet-of-clones roll-up is not in scope.
**Follow-up review recommendation:** false
