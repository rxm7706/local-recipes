---
title: '`factory spin` refuses a second launch against a live loop home'
type: 'fix'
created: '2026-09-10'
status: 'ready-for-dev'
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

## Spec Change Log

## Review Triage Log
