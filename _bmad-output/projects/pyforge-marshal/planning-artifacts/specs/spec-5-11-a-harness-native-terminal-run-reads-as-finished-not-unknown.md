---
title: 'A harness-native terminal run reads as finished, not `unknown`'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: '9109bb0f8e381c9db6de3f051d4c02fbe51e604c'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      Live pyforge-steward acceptance fixture not encoded in CI — steward home
      must be verified manually with `marshal status --project pyforge-steward`.
    evidence: |-
      The steward loop home is operator-local; the diff uses synthetic tmp_path
      fixtures with the same run id shape (20260820-140536-988f).
    severity: low
---

<intent-contract>

## Intent

**Problem:** A run bmad-loop started directly (without `marshal factory spin`) writes journal
events in bmad-loop's own vocabulary (`run-start`, `story-start`, `session-start`/`session-end`,
`story-done`, `run-stop`) with no `run-launch`/`run-resume` entry — the only shape
`_gather_run_journal_facts` folds for a launch pid. So `launch_pid` is `None`,
`cli/status.py`'s `journal_unreadable` branch fires, and the row degrades to `unknown` forever,
even when the journal and `state.json` both plainly record the run as finished
(`finished: true`, `stopped: true`, `crashed: false`). A station stuck at `unknown` is a station
`fleet-picture` cannot assert liveness for — the precondition for the duplicate-dispatch class
recorded 2026-08-27.

**Approach:** Add a `HarnessPort` capability that answers whether a launch-pid-less run is
terminal, implemented in `adapters/harness_bmadloop.py` so no bmad-loop-specific journal
vocabulary leaks outside the adapter; `_gather_run_journal_facts` consults it when the pid is
unrecoverable instead of degrading immediately.

## Boundaries & Constraints

**Always:** A run the port reports terminal shows a finished state with a WARN naming the gap
(mirroring `journal_unreadable`'s own shape) — never a healthy state with no signal. `pyforge-steward`'s
existing home (`.bmad-loop/runs/20260820-140536-988f`) is the acceptance fixture: it must read as
finished after this story, with no re-spin.

**Never:** `cli/status.py` and `core/status.py` learn no bmad-loop journal kind — no
harness-specific string appears outside the adapter (the seam this story routes through exists
precisely to prevent that coupling). A run the port cannot classify, or reports non-terminal,
never gets upgraded past `unknown` — `is_run_live` stays conservatively live; this narrows a false
positive and must never weaken a destructive guard.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No launch pid, port reports terminal | journal has `run-stop`, no `run-launch` | Row reports finished, WARN naming the gap | Never a silent healthy state |
| No launch pid, port cannot classify | ambiguous journal shape | Row stays `unknown`, `is_run_live` stays conservatively live | Never a false positive |
| No launch pid, port reports non-terminal | run genuinely still going or unclear | Row stays `unknown` | Same as above |
| Normal marshal-launched run | `run-launch` present | Unchanged existing behavior | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` — `build_fleet_row` / `FleetHomeFacts.harness_native_terminal`
- `cli/status.py` — `_gather_home_facts` consults `HarnessPort.run_terminal_verdict` when `launch_pid` is unrecoverable
- `ports/harness.py` — `HarnessPort.run_terminal_verdict` declaration
- `adapters/harness_bmadloop.py` — terminal classification via `state.json`

## Tasks & Acceptance

**Execution:**
- `ports/harness.py` — declare the new terminal-run-classification capability
- `adapters/harness_bmadloop.py` — implement it against bmad-loop's `state.json`
- `cli/status.py` — `_gather_home_facts` consults the port when `launch_pid` is unrecoverable
- `core/status.py` — finished-with-WARN rendering for `harness_native_terminal`

**Acceptance Criteria:**
- Given a loop-home run with no `run-launch`/`run-resume` entry, when `_gather_run_journal_facts` returns `launch_pid=None`, then the derivation consults the new `HarnessPort` capability rather than degrading on the spot
- Given a run the port reports terminal, then the row reports finished with a WARN naming the gap, never a healthy state with no signal
- Given a run the port cannot classify or reports non-terminal, then the row stays `unknown` and `is_run_live` stays conservatively live
- Given `pyforge-steward`'s existing home as the acceptance fixture, when this story lands, then it reads as finished without a re-spin

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 12 findings — high 0, medium 2, low 3, false 4, maybe-false 0, reject 3
- findings:
  - `[medium]` `[patch]` Missing budget USD/savings fields on harness_native_terminal fleet row — added budget_consumed_usd, layer_savings, layer_savings_usd and escalated-artifact fallback
  - `[medium]` `[patch]` No tests for _latest_bmad_loop_run_id selection — added TestLatestBmadLoopRunId
  - `[low]` `[patch]` Adapter unit tests untracked — committed test_harness_bmadloop_run_terminal_verdict.py
  - `[low]` `[patch]` is_run_live not asserted for non-terminal path — added assertion in test_non_terminal_verdict_stays_unknown
  - `[low]` `[patch]` Port docstring claimed journal.jsonl read — aligned docstring with state.json-only implementation
  - `[false]` `[reject]` Consultation must live in _gather_run_journal_facts — _gather_home_facts is the correct CLI boundary; journal facts stay FsPort-only
  - `[false]` `[reject]` Adapter must read run-stop journal kinds — state.finished is bmad-loop's authoritative terminal flag
  - `[false]` `[reject]` Must not reuse journal_unreadable for non-terminal — existing MRS-STATUS-002 shape is the spec's unknown row; is_run_live stays conservative
  - `[false]` `[reject]` Lexicographic latest run id always wrong — acceptable for harness-native homes with no marshal launch correlation (DW-STATUS-2026-09-08-1)
  - `[reject]` `[defer]` pyforge-steward live fixture in CI — operator-local; deferred with manual verification note
  - `[reject]` `[defer]` Terminal verdict + missing snapshot path — intentional fallback to journal_unreadable until product decides otherwise
  - `[patch]` `[patch]` MRS-STATUS-012 missing from _CLASSIFY_TABLE — added alongside MRS-STATUS-013 (pre-existing registration gap)

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expect green (7657 passed)
- `marshal status --project pyforge-steward` -- expect a finished row (with WARN), not `unknown`, against the existing acceptance-fixture home

## Auto Run Result

**Summary:** Added `HarnessPort.run_terminal_verdict` and wired `_gather_home_facts` to consult it when Marshal's journal reads successfully but yields no launch pid. Terminal harness-native runs surface as `stopped` with WARN `MRS-STATUS-013` instead of perpetual `unknown`.

**Files changed:**
- `ports/harness.py` — new `HarnessRunTerminalVerdict` type and port method
- `adapters/harness_bmadloop.py` — `run_terminal_verdict` via `load_state` / `finished`
- `cli/status.py` — `journal_readable`, `_latest_bmad_loop_run_id`, harness-native fallback in `_gather_home_facts`
- `core/status.py` — `harness_native_terminal` fact + `build_fleet_row` branch + `MRS-STATUS-013`
- `core/findings.py`, `core/verdict.py` — register/classify MRS-STATUS-013 (and 012 gap-fill)
- Tests: `test_status.py`, `test_harness_bmadloop_run_terminal_verdict.py`, `test_findings.py`
- `sprint-status-ledger.yaml` — story 5-11 → done

**Review:** 5 patches applied, 2 deferred (steward live fixture; terminal+no-snapshot path), 7 rejected/false.

**Follow-up review recommended:** false (0 high patches; 2 medium patches only).

**Verification:** `pixi run -e pyforge-marshal pyforge-marshal-test` — 7657 passed, 12 deselected.

**Residual risks:** Multi-run homes pick the lexicographically latest `.bmad-loop/runs/` entry when no marshal launch pid exists; steward acceptance requires manual `marshal status --project pyforge-steward`.
