---
title: '66.1: The detector run measures the doctor sources beside the script detectors'
type: 'chore'
created: '2026-11-26'
status: 'ready-for-dev'
story: 66-1-the-detector-run-measures-the-doctor-sources-beside-the-script-detectors
spec: spec-pyforge-doctor
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'scripts/detectors.py'
  - 'tests/scripts/test_detectors_jobs.py'
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

**Problem:** `scripts/detectors.py` runs the script detectors in a thread pool of subprocesses and then, when the pool has drained, gathers each ported doctor source in turn in its own process. The run therefore takes its longest script detector plus every source in a row: 84 s alone, 230 to 304 s inside a full preflight, 108 s of the Detectors job on a PR.

**Approach:** With `--jobs` above one, gather each source in a worker process (a library call, as now; never a script) while the script detectors run, the two kinds sharing the one job limit. Keep the rows in selection order. `--jobs 1` keeps today's path: everything in turn, in one process.

Ledger key: `66-1-the-detector-run-measures-the-doctor-sources-beside-the-script-detectors`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (the preflight and a PR's CI answer within a measured budget; realized here, no text change in this station's Spec).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline.
- Keep a row for every source, whatever happens to its worker.

**Never:**
- Never delete, skip or re-mark a test to gain time.
- Never change a status, a summary's meaning or the exit-code aggregation.
- Never let a failed worker drop a row or read as a pass.

## Acceptance Criteria

**Given** the run at `--jobs auto`
**When** the sources are gathered beside the script detectors
**Then** the rows, order, statuses and exit code equal those of `--jobs 1`
**And** the run takes under 55 s alone on 16 threads

- **AC1 — The jobs test passes, parallel against serial.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_detectors_jobs.py -q
  ```

- **AC2 — The detector run is green on the branch.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild detectors-ci
  ```

</intent-contract>

## Evidence (2026-11-26)

Standalone `detectors-ci`: 83.9 s wall, 141 CPU-seconds, 50 rows summing 104.2 s: `chain_currency_sweep_check` 41.5 s, `capability-effect` 15.8 s, `docs-currency` 9.5 s, `flag_gate_check` 5.6 s, `deferred-work` 4.4 s. Inside two full preflights: 230.3 s and 303.8 s.

## Review round (2026-11-26)

The independent review held one finding: the serial-against-parallel comparison (`test_detectors_jobs.py`) runs only in `pyforge-ci`, where Doctor does not import, so both sides read `unknown` and the comparison could not fail on this change. `tests/scripts/test_detectors_doctor_sources.py` now gathers real sources in turn and through a process pool and holds the rows equal; it runs where Doctor imports (`pyforge-doctor-aggregate-scripts-test`, `scripts-lib-test`). The new tests also first skipped by a guard of their own that failed in `pyforge-ci`; they use the file's existing guard.
