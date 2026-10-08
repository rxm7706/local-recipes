---
title: '71.3: Selected lanes run concurrently and share no mutable state'
type: 'feature'
created: '2026-09-27'
status: 'done'
baseline_revision: '61253849842913b8d2bbe7548547d61a7af4d5e0'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** pixi runs `depends-on` one lane at a time (`pixi.toml`, `pyforge-station-tests`: "depends-on runs the nine in order"), and the runner of Story 71.1 keeps that order — one core of sixteen works. Each lane already lives in its own pixi environment, but lanes still share mutable state that makes naive concurrency unsafe: pixi builds path dependencies into `.pixi/bld` when an environment needs (re)installing; pytest's temp root and its cache dir default to shared locations; coverage data files default to `.coverage` in the working directory; scribe's suite and its coverage gate both use the one Postgres on port 5433.

**Approach:** the runner gains two phases. **Install:** every environment the selection (Story 71.2) needs is installed with `pixi install --frozen -e <env>`, one at a time, before any lane starts — journaled as its own entry with its wall time — so no two lanes ever build under `.pixi/bld` at once. **Run:** the lanes run in a pool bounded by `--jobs N` (default: the machine's logical core count). Each lane gets its own scratch directory under `.steward/preflight/<run-id>/<lane>/`, exported as `TMPDIR`, as pytest's `--basetemp` and `-o cache_dir=…` (appended to any `PYTEST_ADDOPTS` already set) and as `COVERAGE_FILE`. Lanes whose CI counterpart job (found by Story 71.2) declares a `services:` container share that service and run one at a time among themselves — derived from the workflows, never listed. Each lane's stdout and stderr go to `.steward/preflight/<run-id>/<lane>.log`, printed whole when the lane ends, so no two lanes' output interleaves. The first red lane stops the rest — each lane runs in its own process group, terminated and journaled `cancelled` — unless `--keep-going`, which runs every lane and reports every red. An interrupt terminates every child process group before the runner exits. The journal gains each lane's start offset, so the critical path is readable from it.

Ledger key: `71-3-selected-lanes-run-concurrently-and-share-no-mutable-state`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-71.2.

### Living CAP citations

- `spec-pyforge-steward` CAP-159 (FR-32).

## Acceptance Criteria

- Given three fake lanes that each sleep one second When the preflight runs with `--jobs 3` Then all three finish in under two seconds of wall clock and the journal shows overlapping start offsets
- Given the same lanes When each records its environment Then each saw a distinct `TMPDIR`, pytest basetemp, pytest cache dir and `COVERAGE_FILE`, all under that run's `.steward/preflight/<run-id>/`
- Given two fake lanes whose counterpart jobs declare a `services:` container When the preflight runs with `--jobs 4` Then their journaled run intervals never overlap
- Given a fake `pixi` that records call order When the preflight runs Then every `pixi install --frozen -e <env>` call precedes the first lane, one at a time, and the install phase is journaled
- Given one fake lane that exits 1 while two others still run When the preflight runs Then it exits 1, the other two are terminated and journaled `cancelled`, and no child process is left running
- Given `--keep-going` and two red lanes When the preflight runs Then every lane runs, it exits 1, and both reds are named
- Given two lanes that each print many lines When both run concurrently Then each lane's output appears as one contiguous block
- Given an interrupt (SIGINT) mid-run When the runner exits Then no lane's process group is still alive

## Boundaries & Constraints

**Always:**
- Concurrent lanes share no mutable state: `.pixi/bld` (install first), temp dirs, the pytest cache, coverage data files, and any CI service container.
- A lane's verdict is its exit code; the run's verdict is 0 only when every selected lane exited 0.
- Which lanes need exclusive access to a service is read from the workflow files (the counterpart job's `services:`), never a hand-kept list.

**Never:**
- Do not change which lanes run (Story 71.2) or what a lane runs (Stories 71.4–71.6).
- Do not start Postgres or any other service — scribe's Postgres stays on the not-covered list (`scribe-pg-up` first); the not-covered list does not grow.
- Do not write outside `.steward/` and the lanes' own scratch dirs.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| independent lanes | 3 lanes, `--jobs 3` | run together | — |
| shared service | 2 lanes whose jobs declare `services:` | one at a time | — |
| env not installed | selection needs `pyforge-atlas` | installed before any lane | install failure → exit 1, no lane runs, journaled |
| red lane | one exits 1 | others cancelled, exit 1 | process groups terminated |
| `--keep-going` | two reds | all run, both named, exit 1 | — |
| interrupt | SIGINT | every child group terminated | exit 130, journaled |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-159 (FR-32).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 — Proposed: the preflight answers in under a minute*.
Ledger key: `71-3-selected-lanes-run-concurrently-and-share-no-mutable-state`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild pr-preflight -- --keep-going` on a branch touching `pixi.toml` — expected: the same per-lane exit codes as `pixi run -e pyforge-guild pr-preflight-lanes` reaches, and a journaled wall time bounded by the slowest lane plus the install phase, not by the sum.

## Auto Run Result

Status: done  
Verification: `pixi run --frozen -e pyforge-steward pyforge-steward-test` (2185 passed); `python scripts/spec_surface_reconcile.py` (exit 0 after memlog reconcile on `spec-pyforge-steward`).
