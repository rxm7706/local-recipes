---
title: '67.1: The contract mutation tests analyse each module once'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 67-1-the-contract-mutation-tests-analyse-each-module-once
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `tests/meta/test_public_contract.py` spends 215 single-thread seconds of `pyforge-doctor-live-test`, the most of any module across the eleven heaviest lanes. Each of its 22 mutation tests (81 cases with their parameters) adds one synthetic module and derives the facts of the whole package again: `_code_facts` parses and walks every module of `pyforge.doctor`, about 3 s a call.

**Approach:** Compute the per-module part of `_code_facts` (the parse, the constants, the literals, the walk, the methods, the environment names) once per module text in a run and reuse it; the part that reads across modules still runs on every call. A mutation then analyses its one synthetic module.

Ledger key: `67-1-the-contract-mutation-tests-analyse-each-module-once`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (realized here; no text change in this station's Spec).
- spec-pyforge-doctor CAP-97 (the public contract's test; its oracle is unchanged).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every assertion of the module; the facts a call returns are the facts it returned.
- Share nothing a caller can change: a cached analysis is read, never mutated.

**Never:**
- Never delete, skip or re-mark a test to gain time.

## Acceptance Criteria

**Given** the contract module, about 3 s per mutation case
**When** the per-module analysis is cached by module text
**Then** every test passes with the assertions it had, and the module takes under a quarter of its time alone

- **AC1 — The contract module passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py -q --durations=5
  ```

- **AC2 — Doctor's live half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test
  ```

</intent-contract>

## Evidence (2026-11-26)

`pyforge-doctor-live-test` alone on 16 threads with `--durations`: 81 entries of `test_public_contract.py` of about 3 s each (215 s in all), its module fixture derived again in 11 workers at 3.2 s each.

## Result (2026-11-26)

`test_public_contract.py` alone: 69.0 s before, 16.5 s after (24%), 100 passed with the new test that holds the cache changes no fact. The per-module part now includes each module's flag reads, the costliest per-module step (87 of 139 s under the profiler). `pyforge-doctor-live-test` alone: 50.6 s before, 25.3 s after.
