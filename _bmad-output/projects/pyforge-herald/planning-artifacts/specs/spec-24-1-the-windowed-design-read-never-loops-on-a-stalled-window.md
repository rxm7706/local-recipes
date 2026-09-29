---
title: '24.1: The windowed Design read never loops on a stalled window'
type: 'fix'
created: '2026-09-18'
status: 'done'
baseline_revision: 'ed367a47d8fb4e2da2275f1f0504e5084840d7c2'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `_windowed_read` breaks only when `window.last_line >= window.total_lines` and never checks that `last_line` advanced between calls, so a server that repeatedly returns the same window loops forever (Story 23.2's Edge Case Hunter finding; every live call paged forward, so reachability is unproven)

**Approach:** a window whose `last_line` did not advance past the previous window's raises a typed pagination error naming the file and the stalled line

## Boundaries & Constraints

**Always:**
- a fake transport returning the same `(last_line, total_lines)` pair twice raises that error on the second window, and every existing live-shaped fixture (the 3377-line and 136,293-byte pulls) still pages to completion byte-exact
- the error is a refusal that names the file, never a warning or a silent truncation

**Never:**
- Do not re-mint a verb, build or command that exists — bind to it; do not add a second Pages deployment or a second PR gate; a live proof stays opt-in and operator-run (the Epic 24 HARD boundaries in `epics.md`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the deferral's own case | the DW row's evidence reproduced as a fixture | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-48`.
Surface: `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` (`_windowed_read`), a typed error in the pipeline's error module, `tests/unit/test_deck_pipeline.py`, `planning-artifacts/deferred-work-ledger.md` (DW-FU-23-2 → done with the test as evidence).
Ledger key: `24-1-the-windowed-design-read-never-loops-on-a-stalled-window`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-24-1-the-windowed-design-read-never-loops-on-a-stalled-window.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- A fake transport returning the same `(last_line, total_lines)` pair twice raises the typed pagination error on the second window; the 3377-line and 136,293-byte live-shaped fixtures still page to completion byte-exact; DW-FU-23-2 is marked done citing the test.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 5 findings — high 0, medium 1, low 3, false 1, maybe-false 0
- findings:
  - `[low]` `[patch]` `PaginationStalledError` was spliced between two Story-15.1 classes in `errors.py`, breaking the file's chronological-by-story ordering — moved the class to after `InvalidContentPlanError`, immediately before `_EXIT_BY_ERROR`.
  - `[medium]` `[patch]` `spec-pyforge-herald/SPEC.md:326`'s CAP-48 catalog line still read `(ready 2026-09-18)` while other in-flight capabilities (CAP-37–39) are tracked live as `in-progress` — updated the CAP-48 line's tag to `(in-progress 2026-09-18)`.
  - `[low]` `[patch]` The new test covered only the exact-equality stall case; the guard's `<=` comparison also covers a window whose `last_line` regresses below the previous window's, left untested — added `test_windowed_read_raises_pagination_stalled_error_on_a_regressed_window` covering the regression branch.
  - `[low]` `[patch]` `PaginationStalledError`'s docstring cited `"(CAP-2, Story 23.2)"` with no spec-name qualifier, risking confusion with `spec-pyforge-herald`'s own unrelated CAP-2 ("releases are proclaimed from the ledger") — added the `"from spec-design-sync-loop"` qualifier, matching `test_deck_pipeline.py`'s own section-header convention for this code.
  - `[false]` `[reject]` DW-FU-23-2 was marked `status: done 2026-09-18` mid-review, before the story landed, unlike DW-FU-23-1's landing-based closure precedent — refuted: this spec's own Binding section explicitly directs `planning-artifacts/deferred-work-ledger.md (DW-FU-23-2 → done with the test as evidence)`; the closure is spec-mandated, not an implementation deviation.

## Auto Run Result

Status: done

**Summary:** `_windowed_read`'s pagination loop now tracks the previous window's `last_line` and raises a new `errors.PaginationStalledError` — naming the file and the stalled line — the moment a paged-for window's own `last_line` fails to advance past it, instead of looping forever (DW-FU-23-2, Story 23.2's Edge Case Hunter finding).

**Files changed:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` — `_windowed_read` gained a `previous_last_line` tracker and a stall guard raised before the existing end-of-file check.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` — added `PaginationStalledError(HeraldError)`, placed after `InvalidContentPlanError` (chronological-by-story order), falling through to the default exit code.
- `src/shared/packages/pyforge-herald/tests/unit/test_deck_pipeline.py` — two new tests: exact-equality stall and regressed-window stall, both asserting exactly 2 transport calls (never a loop, never a third call).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md` — DW-FU-23-2 marked `status: done 2026-09-18` with a `verified:` note citing the fix and both new tests, per this spec's own Binding directive.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md` — CAP-48's catalog line updated from `(ready 2026-09-18)` to `(in-progress 2026-09-18)` to match the live-tracking convention used by CAP-37–39.

**Review findings breakdown:** 5 findings from the Blind Hunter layer (Edge Case Hunter, Verification Gap Reviewer, and Intent Alignment Auditor reported none). Patched: 4 (1 medium — stale capability-catalog tag; 3 low — error-class ordering, missing regression-branch test coverage, ambiguous CAP-2 docstring citation). Rejected: 1 (`false` — the claim that DW-FU-23-2 was closed prematurely; refuted by this spec's own Binding section, which explicitly mandates that exact closure).

**Follow-up review recommendation:** false. This pass patched 0 high and 1 medium entry (threshold for `true` is any high, or 2+ medium) — below the recommend-follow-up threshold.

**Verification performed:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` run independently after the patch pass — 1478 passed, 4 skipped (4 pre-existing skips, unrelated). Matrix Test Audit: the intent-contract's sole I/O row ("the deferral's own case") is covered by `test_windowed_read_raises_pagination_stalled_error_on_a_non_advancing_window`, confirmed running and passing via a targeted `-k pagination_stalled` run. Both pre-existing live-shaped fixture tests (3377-line multi-window pull, 136,293-byte single-call pull) still pass unchanged.

**Residual risks:** None identified. The fix, typed error, both edge-case tests (exact-equality and regression), and the ledger closure are all in place and green.
