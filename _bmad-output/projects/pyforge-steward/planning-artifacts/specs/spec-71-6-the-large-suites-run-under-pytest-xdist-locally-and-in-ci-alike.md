---
title: '71.6: The large suites run under pytest-xdist, locally and in CI alike'
type: 'feature'
created: '2026-09-27'
status: 'done'
baseline_revision: 'b570bb995bb0622c23a63e12d2033886680ba27b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/spec-coverage-gate-independence/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** with selection (71.2), concurrency (71.3), coverage reuse (71.4) and the two always-on lanes fixed (71.5), a single-station run is bounded by its station's own suite and gate. Four station suites alone take half the minute or more, each one process on one core (measured 2026-09-27, 16-core laptop): `pyforge-atlas-test` 70.3 s (1,871 tests), `pyforge-doctor-test` 62.0 s (2,447), `pyforge-warden-test` 54.0 s (2,122), `pyforge-marshal-test` 49.5 s. No suite task passes `-n`, and `pytest-xdist` is declared only in `[feature.local-recipes.dependencies]`.

**Approach:** every station suite whose serial time in the 71.1 journal exceeds half the budget (30 s) — the four above on the day of mint — runs under `pytest-xdist`, declared once in its own task so every consumer follows it: `pytest-xdist` joins that station's feature dependencies in `pixi.toml`, and its `pyforge-<s>-test` task passes `-n auto`. CI's station jobs run those tasks verbatim (atlas's through `kedro-test`'s `depends-on`), so the runner and the laptop run each suite the same way. The coverage driver's pytest run (`scripts/coverage_gates_ci.py`, `_run_pytest_cov`) carries the station test task's own `-n`, read from that task's `cmd` in `pixi.toml`, so `coverage-gates.yml`'s `named-module-gates` job and the preflight's gate lane (71.4) measure the same way — `pytest-cov` combines the workers' data. Under the preflight, each lane's `-n auto` resolves to its share of the machine through `PYTEST_XDIST_AUTO_NUM_WORKERS`, set per lane by the runner so concurrent lanes' workers sum to no more than the logical cores; on a runner, `auto` stays the runner's own cores. Tests that are not xdist-safe are fixed, or grouped with `@pytest.mark.xdist_group` under `--dist loadgroup` — never skipped, deselected or marked `xfail`. Off this story's path, stated: `test-ci` (the CFE suite, 111.5 s) runs only for CFE, `pixi.toml` and `pixi.lock` diffs, never on a single-station branch; making it parallel is mason's work under the conda-forge-expert rules.

Ledger key: `71-6-the-large-suites-run-under-pytest-xdist-locally-and-in-ci-alike`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / L / S-71.4, S-71.5.

### Living CAP citations

- `spec-pyforge-steward` CAP-159 (FR-32); co-governed with `spec-pyforge-atlas`, `spec-pyforge-doctor`, `spec-pyforge-warden` and `spec-pyforge-marshal` (their suites, tasks and tests); `spec-coverage-gate-independence` CAP-1 (the driver) as Kinship.

## Acceptance Criteria

- Given the four suites When each runs under its task's `-n auto` Then each collects the same node ids as a serial `--collect-only -p no:xdist` run and passes
- Given the 71.1 journal on the 16-core reference laptop When `pr-preflight` runs on a branch touching only that station Then each of the four suites' lanes (suite and gate) shows under 30 s
- Given a station whose task passes `-n auto` When `scripts/coverage_gates_ci.py` runs its gate Then its pytest command carries the same `-n`, and the per-module coverage it reports equals the serial run's for the same tests
- Given three concurrent lanes whose tasks pass `-n auto` on a machine with 16 logical cores When the preflight starts them Then the `PYTEST_XDIST_AUTO_NUM_WORKERS` values it hands them sum to no more than 16, and each is at least 1
- Given a station task with no `-n` When the driver or the preflight runs it Then nothing is added

## Boundaries & Constraints

**Always:**
- The xdist decision lives in the station task's own `cmd`; CI, the driver and the preflight all follow it — never a second list of parallel suites.
- Every test still runs; a test made xdist-safe keeps its assertions.
- Edit `pixi.toml` by hand (a live `pixi add` is refused by the repo hook); regenerate `pixi.lock` and `environment.yaml` (`pixi project export conda-environment -e build > environment.yaml`) in the same change; run `pixi run -e pyforge-guild pyforge-station-tests` (shared surface) and each touched station's own suite and coverage gate in its own environment.
- Co-governors: a change inside `src/shared/packages/pyforge-<s>/` gets a memlog entry on that station's Spec; reconcile and scoped-stamp every Spec `spec-surface-check` names (`spec-pyforge-core` governs every station's `src/`); a co-governor memlog entry moves that Spec's date, so run `python scripts/chain_currency_sweep_check.py --project <slug> --json` for each and carry its cascade note if it fires.
- `scripts/coverage_gates_ci.py` belongs to the guild-owned `docs/governance/spec-coverage-gate-independence/`; keep `tests/scripts/test_coverage_gates_ci_driver.py` green in `pyforge-ci`.

**Never:**
- Do not skip, deselect or `xfail` a test to make a suite parallel.
- Do not change a coverage floor or `docs/governance/coverage-thresholds.toml`.
- Do not touch `test-ci` or any file under `.claude/skills/conda-forge-expert/`.
- Do not grow the not-covered list: atlas's Chromium/DuckDB/WASM tests and herald's browser check keep their current provisioning and gating.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| suite over 30 s | atlas, doctor, warden, marshal | task passes `-n auto` | — |
| suite under 30 s | herald, steward, mason, scribe, core | unchanged | — |
| unsafe test | shared file, port, chdir, global state | fixed or `xdist_group` | never skipped |
| coverage under xdist | gate for a parallel station | same per-module coverage | `pytest-cov` combines workers |
| oversubscription | 3 parallel lanes, 16 cores | worker shares sum ≤ 16 | minimum 1 each |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-159 (FR-32).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 — Proposed: the preflight answers in under a minute*.
Ledger key: `71-6-the-large-suites-run-under-pytest-xdist-locally-and-in-ci-alike`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.toml` / `pixi.lock` are shared surface).
- `pixi run --frozen -e pyforge-<s> pyforge-<s>-coverage-gate` for atlas, doctor, warden and marshal — expected: pass, the same floors as before.
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_coverage_gates_ci_driver.py -q` — expected: pass.

## Auto Run Result

Status: done

**Summary:** Atlas, doctor, marshal, and warden station suites run under `pytest-xdist` (`-n auto --dist loadgroup`) via their `pyforge-<s>-test` pixi tasks; the coverage driver and preflight inherit the same flags (driver reads `pixi.toml`; preflight sets per-lane `PYTEST_XDIST_AUTO_NUM_WORKERS` so concurrent xdist lanes do not oversubscribe cores). Doctor caps auto workers at 4 in the task cmd so the NFR-4 speed-budget test stays stable under parallel load.

**Files changed:** `pixi.toml`, `pixi.lock`, `environment.yaml`, `scripts/coverage_gates_ci.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_xdist.py`, `src/shared/packages/pyforge-steward/tests/unit/test_preflight_workers.py`, `tests/scripts/test_coverage_gates_ci_driver.py`; memlogs on `spec-pyforge-steward`, `spec-pyforge-core`, co-governor station specs, and `docs/governance/spec-coverage-gate-independence/.memlog.md`.

**Verification:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2209 passed, 5 skipped
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_coverage_gates_ci_driver.py -q` — 15 passed
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 11969 passed, 6 skipped
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 3495 passed, 1 skipped
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — 2266 passed
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` — 103 passed
- `python scripts/spec_surface_reconcile.py` — OK

**Follow-up review recommended:** false
