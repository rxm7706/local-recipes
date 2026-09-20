---
title: '51.13: The watch reads the dispatch verdict in the supervisor''s own vocabulary'
type: 'fix'
created: '2026-09-20'
status: 'done'
baseline_revision: 'c8277c03c117ff4779d54a2ff9d900f519415971'
final_revision: '7c14d4cf134c694699870db12d33ae5558bd3ad7'
review_loop_iteration: 1
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** at 2026-09-20 01:25Z, the moment Story 51.10 made the `marshal_home` probe return data, doctor 26.1's two-minute-old dispatch read **finished** in `marshal watch --fleet`. `marshal status` reports `dispatch_completion_verdict: live` for a running session (the supervisor's vocabulary is `live | completed | failed | stopped_externally`, `core/dispatch_completion.py::DispatchSessionVerdict`), and `cli/watch.py::_snapshot_dispatch` treated any verdict outside its own invented set `{"", "None", "pending", "in-progress"}` as terminal; `_session_completions` carried the same set and would have reported "completion live". `test_watch.py` asserted with `passed`/`pending` — values the supervisor never emits — which is how the wrong predicate stayed green.

**Approach:** one predicate, `_dispatch_verdict_is_terminal`, reads the enum: finished iff the verdict is a `DispatchSessionVerdict` member other than `LIVE`; `live`, absent, empty and unknown values are not terminal and the row keeps the home's own state. Both call sites use it. The tests are rewritten in the real vocabulary and a meta-test refuses any `dispatch_completion_verdict` literal in the file that is not an enum member.

## Boundaries & Constraints

**Always:**
- The watch imports the enum; it never restates the vocabulary as strings
- A run with an unknown verdict reads as its home state, never as finished (the classifier narrows, never widens)
- `_session_completions` / `_currently_running` keep their reporting shape

**Never:**
- Do not add `live` to a string set — the fix is the enum, not one more literal
- Do not touch `_gather_station` or the probe (51.6 / 51.10 own them)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 01:25Z row | state `running`, verdict `live`, story 26.1 | status `running`, `finished: false` | n/a |
| completed / failed / stopped_externally | any state | status `finished`, `finished: true`; completion line reported | n/a |
| absent / empty / unknown verdict | any state | home's own state; no completion line | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-260`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py` (`_dispatch_verdict_is_terminal`; `_snapshot_dispatch` and `_session_completions` use it), `src/shared/packages/pyforge-marshal/tests/unit/test_watch.py` (rewritten literals; `test_dispatch_verdict_terminality_is_the_enum`, `test_live_dispatch_row_snapshots_as_running_not_finished`, `test_watch_tests_use_only_the_supervisor_verdict_vocabulary`).
Ledger key: `51-13-the-watch-reads-the-dispatch-verdict-in-the-supervisor-s-own-vocabulary`.
Minted 2026-09-20 from `epics.md`; hand-driven the same night.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- `marshal watch --fleet` from each dispatch clone reads its live run `running`.

## Review Triage Log

### 2026-09-20 — hand-driven pass
  - `[high]` `[patch]` `_snapshot_dispatch`'s terminal test was an invented string set; `live` fell through as finished. Fixed with the enum predicate.
  - `[medium]` `[patch]` `_session_completions` carried the same set (would report "completion live"). Routed through the same predicate.
  - `[medium]` `[patch]` four test literals (`passed`, `pending`) were not supervisor values; rewritten, and a meta-test now refuses any non-member literal in the file.

## Auto Run Result

**Status:** done
**Summary:** the enum is the predicate at both call sites; the watch's tests speak the supervisor's vocabulary and refuse any other.
**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pyforge-deps-test` — see the PR body for counts; `test_watch.py` 86 passed.
**Files changed:** `cli/watch.py`, `tests/unit/test_watch.py`.
**Residual risks:** none from this change.
**Follow-up review recommendation:** false
