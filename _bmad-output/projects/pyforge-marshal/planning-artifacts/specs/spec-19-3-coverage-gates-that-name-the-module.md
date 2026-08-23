---
title: Coverage gates that name the module
type: test
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: 69c6b536d2501c2dc19ff3b9a3fd5e6e6b475529
deferred:
  - summary: >-
      Expand coverage-gates CI beyond the marshal home env (matrix / per-station
      pixi env) so non-marshal package touches are gated in the same workflow.
    evidence: |-
      Workflow installs only pyforge-marshal and sets COVERAGE_GATES_STATIONS=marshal;
      other stations rely on pixi *-test-coverage tasks / future matrix work.
    location: >-
      .github/workflows/coverage-gates.yml
    severity: medium
  - summary: >-
      Add parallel pixi `pyforge-*-test-coverage` tasks for non-marshal stations.
    evidence: |-
      Only pyforge-marshal-test-coverage was added; comments still refer to plural tasks.
    location: >-
      pixi.toml
    severity: low
  - summary: >-
      Upload coverage JSON / term-missing artifacts on gate failure for operators.
    evidence: |-
      CI currently relies on step stdout only.
    location: >-
      .github/workflows/coverage-gates.yml
    severity: low
---

<intent-contract>

## Intent

**Problem:** Coverage failures report a bare percentage; operators cannot see which module dropped below the station threshold (FR-131).

**Approach:** Wire CI so a PR that drops a touched package below its station threshold fails naming the uncovered module — unit >80% / integration >70% — not just printing a percentage.

## Acceptance Criteria

- CI fails when a touched package falls below the station's unit (>80%) or integration (>70%) threshold.
- Failure output names the uncovered module(s), not only an aggregate percentage.
- Thresholds are per-station (or documented station defaults) and fixture-covered where practical.
- Does not implement 19.4 test-architecture drift re-run.

## Boundaries & Constraints

**Never:** Implement 19.4. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward #675 / 15-1.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_gate.py` — FR-131 evaluator + CLI (`evaluate` / `touched` / `show-thresholds`); names under-threshold modules
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_thresholds.toml` — fleet defaults (unit 80 / integration 70) + optional `[stations.<slug>]` overrides
- `scripts/coverage_gates_ci.py` — PR path-filtered driver (touched stations + touched source modules; skip N/A suites; fail on pytest RC; `COVERAGE_GATES_STATIONS` allow-list)
- `scripts/run_station_coverage_gate.py` — full-package evaluate (pixi `pyforge-marshal-test-coverage`)
- `.github/workflows/coverage-gates.yml` — CI: fixture proof + marshal touched-module gates
- `src/shared/packages/pyforge-marshal/tests/meta/test_coverage_gate_names_module.py` — named-module failure fixtures
- `src/shared/packages/pyforge-marshal/tests/meta/test_coverage_gates_ci_driver.py` — driver skip / pytest-RC / allow-list contracts
- `pixi.toml` — `pytest-cov` on `pyforge-marshal` + `pyforge-marshal-test-coverage` task

## Verification

- Fixture / CLI: below-threshold evaluate names `pyforge.marshal.cli.spin` (exit 1)
- `pixi run --frozen -e pyforge-marshal pytest …/test_coverage_gate_names_module.py …/test_coverage_gates_ci_driver.py …/test_ad3_ad4_import_linter.py -q` — 36 passed
- Does not implement 19.4

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 3, medium 3, low 1)
- defer: 3: (high 0, medium 1, low 2)
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` Skip N/A suites without evaluating (no zero-fill) in `coverage_gates_ci.py` / `run_station_coverage_gate.py`
  - `[high]` `[patch]` Fold pytest non-zero exit into driver RC (was ignoring test failures)
  - `[high]` `[patch]` Restrict CI job to `COVERAGE_GATES_STATIONS=marshal` so foreign stations are not run in the marshal-only env
  - `[medium]` `[patch]` Ignore deleted/missing modules instead of forcing 0% (fixed path join to `src/pyforge/...`)
  - `[medium]` `[patch]` Harden git-diff fallback + unreadable JSON handling; guard unknown suites
  - `[medium]` `[patch]` Add `test_coverage_gates_ci_driver.py` for skip / RC / allow-list
  - `[low]` `[patch]` Failure copy says under-threshold (not uncovered); workflow paths include `run_station_coverage_gate.py`; safer `HEAD~1` fallback

## Auto Run Result

Status: done

Summary: Shipped FR-131 named-module coverage gates for marshal — library + thresholds TOML, PR CI driver (touched-module mode), pixi full-package task, fixtures + driver tests. Review patches fixed false-green pytest RC, N/A-suite zero-fill, and marshal-only CI allow-list.

Files changed:
- `coverage_gate.py` / `coverage_thresholds.toml` — evaluator + defaults
- `coverage_gates_ci.py` / `run_station_coverage_gate.py` — CI + pixi drivers
- `.github/workflows/coverage-gates.yml` — workflow
- meta tests + AD-3 import-linter + pyproject / pixi.toml / pixi.lock

Review findings: 7 patches applied; 3 deferred; 4 rejected (noise / R2-aligned scope). Follow-up review recommended: true (3 high patches; score from highs).

Verification: 36 meta tests passed; CLI evaluate below-floor names `pyforge.marshal.cli.spin` exit 1.

Residual risks: PR CI gates marshal only until matrix expansion; full-package pixi task may still red historically under-covered modules (CAP-4 non-goal).
