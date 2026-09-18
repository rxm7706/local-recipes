---
title: '24.1: The windowed Design read never loops on a stalled window'
type: 'fix'
created: '2026-09-18'
status: 'ready'
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
