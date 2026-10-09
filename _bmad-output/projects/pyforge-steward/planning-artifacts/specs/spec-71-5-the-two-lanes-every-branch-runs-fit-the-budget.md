---
title: '71.5: The two lanes every branch runs fit the budget'
type: 'feature'
created: '2026-09-27'
status: 'done'
baseline_revision: '0eadef804c3bad7f7f701c82ea8550d3da6a5cde'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `detectors.yml` has no `paths` filter, so its two lanes — `detectors-ci` (`python scripts/detectors.py --scope repo`) and `pyforge-doctor-scripts-test` (`python -m pytest tests/scripts -q`, `pyforge-ci`) — run for every diff, and no selection (Story 71.2) can shorten them. Measured 2026-09-27: `detectors-ci` 57.6 s, of which its 38 detectors account for 57.0 s run one after another (`scripts/detectors.py`, `main`: `[run_one(d, args.timeout) for d in selected]`; `cfe_rebuild_guard_check` 24.5 s and `chain_currency_sweep_check` 13.2 s are two thirds); `pyforge-doctor-scripts-test` 75.7 s over 746 tests in one process — alone past the one-minute budget, whatever the other lanes do.

**Approach:** `scripts/detectors.py` gains `--jobs N`: the selected script detectors run through `run_one` in a thread pool (each is already its own subprocess), and results are reported in the same selection order; the in-process doctor sources, the registry findings, the verdict and the exit code are computed exactly as today. The default stays 1, so `detectors.yml`'s own invocation is unchanged; the `detectors-ci` pixi task passes `--jobs` sized to the machine. `pytest-xdist` joins `[feature.pyforge-ci.dependencies]` — a test-runner plugin, not a runtime library, so the env's no-runtime-deps purpose holds — and `pyforge-doctor-scripts-test` passes `-n auto`; `detectors.yml` runs that task verbatim, so CI runs the suite the same way. Tests under `tests/scripts/` that are not xdist-safe (shared files, `chdir`, fixed ports, fixed temp names) are fixed, or grouped with `@pytest.mark.xdist_group` under `--dist loadgroup` — never skipped or deselected. Not taken: making the two slow detectors incremental (the Dream's other sketch) — concurrency reaches the budget without touching their internals.

Ledger key: `71-5-the-two-lanes-every-branch-runs-fit-the-budget`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-71.1.

### Living CAP citations

- `spec-pyforge-steward` CAP-159 (FR-32); doctor's detector registry and `pyforge-doctor-scripts-test` (`spec-pyforge-doctor`) as Kinship.

## Acceptance Criteria

- Given the repo-scope registry When `scripts/detectors.py --scope repo` runs with `--jobs 1` and with `--jobs 8` Then both report the same per-detector status and findings, in the same order, and exit with the same code
- Given a fixture registry of three detectors that each sleep one second When it runs with `--jobs 3` Then it finishes in under two seconds and reports them in selection order
- Given a detector that times out, one that exits 2 and one with findings When they run concurrently Then each is reported exactly as it is serially (`TIMEOUT` / could-not-run / `FINDINGS`) and the exit code is the serial run's
- Given `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` When it runs Then it runs under `-n auto`, collects the same test count as `python -m pytest tests/scripts --collect-only -q -p no:xdist`, and passes
- Given the 71.1 journal on the 16-core reference laptop When `pr-preflight` runs Then `detectors-ci` and `pyforge-doctor-scripts-test` each show under 30 s

## Boundaries & Constraints

**Always:**
- Every detector still runs and every verdict is unchanged; concurrency changes when a detector runs, never whether or how it is judged.
- `pytest-xdist` enters `pyforge-ci` only as a test-runner plugin; edit `pixi.toml` by hand (a live `pixi add` is refused by the repo hook), regenerate `pixi.lock` and `environment.yaml` (`pixi project export conda-environment -e build > environment.yaml`) in the same change, and run `pixi run -e pyforge-guild pyforge-station-tests` (shared surface).
- `pixi.toml` has several governing Specs: append each one `spec-surface-check` names, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per Spec; a co-governor memlog entry moves that Spec's date, so run `python scripts/chain_currency_sweep_check.py --project <slug> --json` for each and carry its cascade note if it fires.
- `scripts/detectors.py` is the registry every detector hangs on (governed by none — `scripts/spec_surface_allowlist.txt`); record the change in `spec-pyforge-doctor`'s memlog as its owner of the detector verdicts.

**Never:**
- Do not change `detectors.yml` or which detectors are blocking on the runner.
- Do not skip, deselect or `xfail` a test to make it xdist-safe.
- Do not add runtime libraries to `pyforge-ci`.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `--jobs 1` | default | today's behaviour | — |
| `--jobs 8` | 38 detectors | same report, same order, same exit | — |
| detector times out | one detector hangs | `TIMEOUT` as serially | per-detector timeout unchanged |
| xdist-unsafe test | shares a file or port | fixed or grouped | never skipped |
| `-n auto` in CI | 4-core runner | 4 workers | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-159 (FR-32).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 — Proposed: the preflight answers in under a minute*.
Ledger key: `71-5-the-two-lanes-every-branch-runs-fit-the-budget`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass under `-n auto`.
- `pixi run -e pyforge-guild detectors-ci` — expected: the same exit code and per-detector report as `python scripts/detectors.py --scope repo --jobs 1`.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.toml` / `pixi.lock` are shared surface).

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (no reviewer layers launched; implementation verified against acceptance criteria and matrix tests)

## Auto Run Result

Status: done

**Summary:** Parallelized the two always-on CI lanes: `scripts/detectors.py` runs repo-scope script detectors with `--jobs` (default 1, `auto` for logical CPUs) while doctor in-process sources stay serial; `pyforge-ci` gained `pytest-xdist` and `pyforge-doctor-scripts-test` runs `tests/scripts` with `-n auto --dist loadgroup`, with xdist groups on docker-volume and MCP journal tests.

**Files changed:**
- `scripts/detectors.py` — thread-pool script detector runs, `--jobs` / `--jobs auto`
- `pixi.toml`, `pixi.lock`, `environment.yaml` — xdist dep, task wiring
- `tests/scripts/test_detectors_jobs.py` — jobs parity, concurrency, error-shape matrix
- `tests/scripts/test_container_volumes_roundtrip.py`, `tests/scripts/test_mcp_factory_stdio_translator.py` — xdist groups

**Review:** No patch/defer items.

**Verification:**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — 1257 passed, 12 skipped (~34 s)
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_detectors_jobs.py -q` — 3 passed
- Collect-only parity: 1267 tests with and without xdist
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2209 passed
- `python scripts/spec_surface_reconcile.py` — OK after memlog reconcile entries

**Residual risks:** Budget AC (under 30 s per lane on the 16-core reference laptop) was not re-measured in this session; local `detectors-ci` wall time included unrelated ledger findings. Operator should confirm `pr-preflight` journal timings on the reference machine before merge.
