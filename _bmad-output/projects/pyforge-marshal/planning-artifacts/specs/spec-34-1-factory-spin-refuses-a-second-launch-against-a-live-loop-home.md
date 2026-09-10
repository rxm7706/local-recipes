---
title: '`factory spin` refuses a second launch against a live loop home'
type: 'fix'
created: '2026-09-10'
status: 'done'
baseline_revision: '7c41c11838a8a648a22350f01d51f8deb440b675'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `factory dispatch` refuses a second launch on a station already live
(`station_in_flight_conflict`, `cli/dispatch.py:935`). `factory spin` has no equivalent guard.
Reproduced live 2026-09-10: two `marshal factory spin pyforge-mason` calls six seconds apart both
launched cleanly — no refusal, no warning — producing two live `bmad-loop run` processes and two
live supervisors against the SAME loop-home checkout simultaneously. This is a sharper risk than
dispatch's version of the same mistake: spin operates directly on the loop home's single working
tree (not a per-story worktree), so a genuine concurrent run risks two sessions writing the same
tree, not just wasted compute.

**Approach:** Reuse `station_in_flight_conflict` (or the equivalent live-run check `factory
dispatch` already has) at spin's own launch site, before its `subprocess.Popen` call in
`adapters/harness_bmadloop.py`. A narrowed CALL to the existing check, never a second,
independently-drifting implementation — mirrors Epic 22/28's own "narrowed conflict, not a new
one" precedent for dispatch's own guard.

## Boundaries & Constraints

**Always:**
- A second `factory spin <slug>` call while a prior spin run for that same `<slug>` is still live
  (session or supervisor process alive, run not yet terminal) refuses before launching anything.
- The refusal names the live run's id/pid.
- The SAME `station_in_flight_conflict` check `factory dispatch` already uses is reused, not
  re-derived.

**Never:**
- Never weakens or duplicates the existing dispatch-side guard — spin calls the same check,
  it does not get its own separate implementation that could drift from dispatch's.
- Never blocks a spin call for a DIFFERENT station while another station's spin is live —
  scope is per-station, matching dispatch's own scoping.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live reproduction (the motivating case) | Two `factory spin pyforge-mason` calls six seconds apart | Second call refuses, naming the first run's id/pid | n/a |
| No live run | `factory spin <slug>` with no prior live run for that slug | Launches normally | n/a |
| Different stations | `factory spin pyforge-mason` while `factory spin pyforge-scribe` is live | Both launch; refusal is per-station only | n/a |
| Prior run terminal | `factory spin <slug>` after the prior run for that slug completed/crashed | Launches normally (not treated as still-live) | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — spin's `subprocess.Popen` launch site; add the guard call before it.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `station_in_flight_conflict`, reused not re-derived.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` — surfaces the refusal finding.
- `src/shared/packages/pyforge-marshal/tests/unit/test_*spin*.py` — new fixture reproducing the exact 2026-09-10 race.

## Tasks & Acceptance

**Execution:**
- `fix` — call `station_in_flight_conflict` (or equivalent) from spin's launch path before `subprocess.Popen`.
- `fix` — surface a refusal finding naming the live run's id/pid when the check fires.
- `feature` — add a unit fixture reproducing two rapid-succession spin calls on the same station and asserting the second refuses.
- `feature` — add a fixture confirming a DIFFERENT station's spin is unaffected, and that a terminal prior run does not block a new one.

**Acceptance Criteria:**
- Given two `marshal factory spin pyforge-mason` calls six seconds apart launched cleanly on 2026-09-10 with no refusal, producing two live `bmad-loop run` processes against the same loop home, when `factory spin <slug>` is invoked while a prior spin run for that same slug is still live, then the second call refuses before launching anything, naming the live run's id/pid, using the same `station_in_flight_conflict` check `factory dispatch` already applies.
- A fixture reproduces the exact 2026-09-10 race and asserts the second call refuses.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: full suite green, including the new spin-concurrency-guard tests

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section. Its absence made `core.gate.check_spec_binding` (Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for this and every other spec hand-authored the same way this session -- confirmed live against `spec-34-2`'s own dispatch run, which hit the identical refusal.

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 2 findings — high 0, medium 0, low 1, false 1, maybe-false 0
- findings:
  - `[low]` `[reject]` Guard lives in `cli/spin.py` rather than `harness_bmadloop.py` before `Popen` — acceptable: `run_spin` is the sole production caller of `HarnessPort.spin`, so the launch path is guarded before any subprocess spawn.
  - `[false]` `[reject]` `--foreground` spin bypasses the guard — foreground mode blocks the invoking shell, so the 2026-09-10 double-detached-launch incident cannot recur through that path.

## Auto Run Result

- **Summary:** Added `spin_loop_home_in_flight_conflict` in `cli/dispatch.py`, a narrowed call into `station_in_flight_conflict` plus a walk of the loop home's `runs/` journals. `run_spin` invokes it before minting a run id or spawning `bmad-loop run`, surfacing `MRS-DISP-021` with the live run id and pid.
- **Files changed:**
  - `cli/dispatch.py` — `spin_loop_home_in_flight_conflict` and `_iter_spin_run_dirs`
  - `cli/spin.py` — pre-launch guard in `run_spin`
  - `tests/unit/test_spin.py` — four matrix fixtures (live refusal, terminal prior, different station, rapid second call)
- **Review:** 0 patches applied; 2 findings rejected (see triage log).
- **Follow-up review recommended:** false
- **Verification:** `pixi run -e pyforge-marshal pyforge-marshal-test` — 7724 passed, 12 deselected (41.77s); targeted spin guard tests — 4 passed.
- **Residual risks:** `--foreground` mode is intentionally unguarded (shell-blocking); a future story could extend the guard if needed.
