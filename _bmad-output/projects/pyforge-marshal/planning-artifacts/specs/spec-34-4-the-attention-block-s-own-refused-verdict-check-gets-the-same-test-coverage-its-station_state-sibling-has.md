---
title: "The ATTENTION-block's own refused-verdict check gets the same test coverage its station_state() sibling has"
type: 'chore'
created: '2026-09-10'
status: 'in-progress'
baseline_revision: 'be8c100c055b201a0083d0cc1be729e458f1a515'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `fleet_picture.py`'s live 2026-09-10 fix (`fix/fleet-picture-stale-dispatch-verdict`)
closed a real bug at TWO call sites: `station_state()`'s STUCK cell and `main()`'s ATTENTION-block
`needs.append` line. Both checked a `refused` dispatch verdict without confirming it belonged to
the currently-live engine, so a station running a healthy `factory spin` session got mislabeled
off a 10-day-stale `factory dispatch` verdict. Only the first call site got direct unit coverage
(`test_not_stuck_when_refused_verdict_is_stale_and_a_different_engine_is_running`); the second is
an inline branch inside `main()` verified only by hand against the live fleet at fix time.

**Approach:** Add a test that exercises `main()`'s ATTENTION-block branch directly, mocking
`subprocess.run` for the `marshal status --format json` call — the same technique
`test_fleet_picture_verification_staleness.py` already uses for a different ATTENTION probe in
the same file — rather than driving the real fleet's own tracked-ledger state. No behavior
change; this story is test-coverage-only.

## Boundaries & Constraints

**Always:**
- The test mocks `subprocess.run`'s `marshal status --format json` call, not the real fleet state.
- Pin both outcomes: a genuine refused verdict (live `dispatch_phase` set) DOES produce the
  ATTENTION line; a stale refused verdict (`dispatch_phase=None`, a different engine live) does
  NOT.

**Never:**
- Never changes `fleet_picture.py`'s actual behavior — the fix already landed; this story adds
  coverage only.
- Never requires a real tracked `sprint-status-ledger.yaml` fixture on disk if the existing test
  harness's `_load_fleet_picture()` + mocked subprocess approach is sufficient (matches the
  established pattern in the same test file).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Genuine refused verdict | Live run, `dispatch_phase` set, `verification_verdict: refused` | ATTENTION block includes the `dispatch verify REFUSED` line | n/a |
| Stale refused verdict (the regression this guards) | Live run via a different engine, `dispatch_phase: None`, `verification_verdict: refused` (stale) | ATTENTION block does NOT include the line | n/a |

</intent-contract>

## Code Map

- `scripts/fleet_picture.py` — `main()`'s ATTENTION-block `needs.append` branch (no source change expected, coverage-only).
- `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_dispatch_phase.py` or a new sibling test file — the new fixture(s).

## Tasks & Acceptance

**Execution:**
- `chore` — add a test mocking `subprocess.run`'s `marshal status --format json` response to drive `main()`'s ATTENTION-block branch directly.
- `chore` — pin the genuine-refusal case (line present) and the stale-refusal case (line absent, `dispatch_phase=None`).

**Acceptance Criteria:**
- Given the 2026-09-10 fix closed the stale-verdict bug at both `station_state()` and the ATTENTION-block site, but only the first has direct unit coverage, when a test exercises `main()`'s ATTENTION-block branch with a mocked `marshal status` response, then it pins both outcomes: a genuine live-dispatch refusal produces the ATTENTION line, and a stale refusal from a different live engine does not.
- No behavior change to `fleet_picture.py` itself.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: full suite green, including the new ATTENTION-block staleness test

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch, to avoid the `core.gate.check_spec_binding` (Story 2.7, MRS-GATE-010) refusal `spec-34-2`'s own dispatch run hit for the identical omission.

## Review Triage Log
