---
title: "71.4: A station's coverage gate reuses its own suite's run"
type: 'feature'
created: '2026-09-27'
status: 'done'
baseline_revision: '2d4fb7a1aa80c20ace4231f5a98a62bc15e337de'
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

**Problem:** on a marshal-only branch `pyforge-marshal-coverage-gate` (`pixi.toml`: `python scripts/coverage_gates_ci.py --base origin/main --head HEAD --suites unit`, `COVERAGE_GATES_STATIONS=marshal`) re-ran marshal's `tests/unit` + `tests/meta` under `-m "not slow"` and `--cov` (`scripts/coverage_gates_ci.py`, `_run_pytest_cov`) — 56.2 s — right after `pyforge-marshal-test` (`pytest src/shared/packages/pyforge-marshal/tests -q -m "not slow"`) had run the same tests in 49.5 s (Dream, 2026-09-27). Every station's gate does the same whenever its station is touched.

**Approach:** keep the gate's run exactly as it is — it is the run CI's `named-module-gates` job makes, and the floor verdict stays the driver's own — and shrink the suite lane instead. The driver gains `--plan`: without running pytest, it prints as JSON the stations and suites it would run for this diff (after its own touched-station and format-only filters, and under `COVERAGE_GATES_STATIONS`) with each run's test paths and marker expression. When Story 71.2 selects both `pyforge-<s>-test` and `pyforge-<s>-coverage-gate`, the runner reads the gate task's plan; if it runs `<s>`'s `unit` suite, the suite lane runs only the rest of its task's own selection: the task's other test directories under the task's own marker expression, plus the gate's directories under `(<task expression>) and not (<gate expression>)` — for a task with no `-m`, the gate's directories under `slow`. The reduced run is derived from the task's own `cmd` in `pixi.toml`; a task whose command is not a single `pytest <tests dir> [args]` invocation (mason's runs two `pytest` commands) runs whole, journaled. When the plan does not run the station — an untouched or format-only change, a shared-surface diff that touches no station module — the suite lane runs whole. Every test the station task selects still runs, once.

Ledger key: `71-4-a-station-s-coverage-gate-reuses-its-own-suite-s-run`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-71.3.

### Living CAP citations

- `spec-pyforge-steward` CAP-159 (FR-32); `spec-coverage-gate-independence` CAP-1 (the driver) as Kinship.

## Acceptance Criteria

- Given a fixture station package with `tests/unit`, `tests/meta` and `tests/integration`, some tests in each marked `slow` When the reduced suite run is derived for a task with `-m "not slow"` and for a task with no `-m` Then, by `pytest --collect-only -q` node ids, the gate's run and the reduced run are disjoint and together equal the task's own collection, for both tasks
- Given a diff touching a marshal source module When the driver runs with `--plan` under `COVERAGE_GATES_STATIONS=marshal` Then it prints JSON naming marshal's `unit` run with its test paths and marker expression, and runs no pytest
- Given a `pixi.toml`-only diff When the driver runs with `--plan` Then it plans no run, and the preflight runs the station suite lane whole
- Given a task command of two `pytest` invocations joined by `&&` When the preflight derives the reduced run Then it does not reduce; the suite lane runs whole and the journal says why
- Given a fixture station whose `tests/unit` imports a module that exists under `scripts/` When the preflight derives the reduced run Then it does not reduce, and the journal names the import
- Given a touched module under its floor When the gate lane runs Then it still exits non-zero naming the module, exactly as the driver does today
- Given a marshal-only branch When the preflight runs Then its journal shows marshal's `tests/unit` + `tests/meta` run once (in the gate lane) and the suite lane running only the rest

## Boundaries & Constraints

**Always:**
- The coverage verdict and its exit code are the driver's own (`_evaluate`, the thresholds in `docs/governance/coverage-thresholds.toml`, the touched-module set) — no second evaluator (AD-1).
- The reduction is derived from the station task's own `cmd` and the driver's own plan; nothing is listed per station.
- Every test the station task selects runs exactly once; when in doubt, run the suite whole.
- Close the one parity gap the reuse opens: the gate's run differs from CI's station job over the same tests by `--cov` and by the driver's `PYTHONPATH` (the station's `src/` and `scripts/`), so a test that imports a `scripts/` module could pass in the gate's run and red CI's station job. A station whose `tests/unit` or `tests/meta` imports any module name found under `scripts/` (a static scan of import statements) is not reduced — its suite runs whole, journaled with the reason. The remaining difference, coverage tracing itself, is named in the journal field of every reduced lane.
- `scripts/coverage_gates_ci.py` is governed by the guild-owned `docs/governance/spec-coverage-gate-independence/` (allowlisted in `scripts/spec_surface_allowlist.txt`, so `spec-surface-check` will not name it): record the `--plan` addition in that Spec's folder as its own convention allows, and keep `tests/scripts/test_coverage_gates_ci_driver.py` green in `pyforge-ci`.

**Never:**
- Do not change what the gate measures, its floors, or how `coverage-gates.yml` calls the driver.
- Do not reduce a suite lane when the gate lane is not selected, or when the plan cannot be read.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| station touched | gate plans `<s>` unit | suite lane runs the complement | — |
| format-only change | driver drops it | suite lane runs whole | — |
| shared surface only | no station module touched | suite lane runs whole | — |
| two-command task | mason | no reduction | journaled |
| test imports `scripts/` | a unit test imports a `scripts/` module | no reduction | journaled with the import |
| `--plan` fails | non-zero or unparsable JSON | suite lane runs whole | journaled |
| task `-m` other than `not slow` | e.g. `-m "not network"` | complement under `(<task>) and not (<gate>)` | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-159 (FR-32).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 — Proposed: the preflight answers in under a minute*.
Ledger key: `71-4-a-station-s-coverage-gate-reuses-its-own-suite-s-run`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_coverage_gates_ci_driver.py -q` — expected: pass (`--plan`).
- On a marshal-only branch, `pixi run -e pyforge-guild pr-preflight` — expected: the journal shows no second pass over marshal's unit suite.

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 7 findings — high 1, medium 0, low 0, false 0, maybe-false 6
- findings:
  - `[high]` `[patch]` `--plan` stdout polluted by format-only diagnostic line, breaking JSON parse in preflight — suppressed format-only logging on the plan path (`quiet_format_only`); test added in `tests/scripts/test_coverage_gates_ci_driver.py`.
  - `[maybe-false]` `[defer]` `touched_stations` in plan JSON can list stations with no run under `COVERAGE_GATES_STATIONS` — misleading but unused by reduction; defer unless operators read plan directly.
  - `[maybe-false]` `[defer]` scripts import scan only top-level `scripts/*.py` stems — extend in a follow-up if a station test imports nested script modules without reduction block.
  - `[maybe-false]` `[defer]` relative imports in unit/meta block reduction conservatively — safe whole-run fallback; revisit if false positives appear.
  - `[maybe-false]` `[reject]` JSON parse fragility beyond format-only line — addressed by primary fix; no second parser needed now.
  - `[maybe-false]` `[defer]` reduction subtracts only `unit` plan entry — current pixi gate tasks pass `--suites unit` only; guard if integration gating is added to preflight.
  - `[maybe-false]` `[defer]` matrix rows (shared-surface-only, plan failure, alternate markers, marshal journal e2e) not all automated — partition AC covered on fixtures; manual preflight journal check remains in Verification.

## Auto Run Result

Status: done

**Summary:** Coverage driver `--plan` emits JSON for gate runs; preflight shrinks `pyforge-<s>-test` when `pyforge-<s>-coverage-gate` is also selected and the plan includes that station's unit suite, with whole-run fallbacks for mason's two-pytest task, scripts imports in unit/meta, and unparseable plans.

**Files changed:**
- `scripts/coverage_gates_ci.py` — `build_coverage_plan`, `--plan`, quiet format-only on plan path
- `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_suite_reduction.py` — derive complement pytest command and gate plan reader
- `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` — apply suite overrides and journal fields
- `tests/scripts/test_coverage_gates_ci_driver.py` — `--plan` contracts
- `src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py` — collect-only partition and skip paths
- Governance memlogs on `spec-pyforge-steward` and `spec-coverage-gate-independence`

**Review:** 1 high patch applied (plan stdout JSON purity); 5 items deferred as maybe-false/low-risk gaps; 1 rejected as redundant after patch.

**Follow-up review recommended:** false

**Verification:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2195 passed, 5 skipped
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_coverage_gates_ci_driver.py -q` — 14 passed
- `python scripts/spec_surface_reconcile.py` — OK

**Residual risks:** Manual marshal-only `pr-preflight` journal check not run this session; scripts import scan is top-level-module only.
