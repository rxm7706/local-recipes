---
title: '121.2: steward cutover plans the ledger and no longer copies trees'
type: 'feature'
created: '2026-11-10'
status: 'blocked'
flag:
  key: pyforge.steward.cutover_ledger_write
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: "plan --regenerate and plan --append refuse with steward's usage code and write nothing; plan --check and flip are unchanged"
  cleanup: "90 days after ON in every environment (Q4) the owning station files the removal story"
difficulty: heavy
story: 121.2
spec: python-foundry-cutover
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py
  - src/shared/packages/pyforge-steward/tests/unit/test_cutover.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-124.4).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** Ruling 2: `steward cutover apply` and the move-manifest form of `plan` retire, `flip` stays, and the tests that pin the fold are replaced. The code is wrong here by ruling; 20 of 36 tests encode the retired intent. This story owns the cli.py cutover hunk (steward-station handed it over).

**Approach:** `_HELP['cutover']` reads `the capability ledger's generator and validator, and the root-of-record flag (spec-python-foundry-cutover fnd:CAP-8, fnd:CAP-9)`. `CutoverDuty.run` has no apply branch (argparse refuses it). Delete the 20 manifest and apply tests; keep the 16 flip and loop tests under their names; add duty tests for plan and the switch. If no remaining test reads the live tree, drop the module's `live_tree` mark. Read the flag with `read_boolean`, the `deploy_nic_packs.py` precedent, not through `cli.RETROFIT_KEY_VERBS`, which would gate `plan --check` too.

Ledger key: `121-2-steward-cutover-plans-the-ledger-and-no-longer-copies-trees`. Type / Effort / Deps: feature / L / S-121.1, S-121.6, S-124.4.

### Living CAP citations

- **`spec-python-foundry-cutover`** — fnd:CAP-2, fnd:CAP-8 (the writer lock), fnd:CAP-9 (the ledger generator) and fnd:CAP-11, amended 2026-11-10 by memlog and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Land before steward-station Stories 122.2 (contract.md cutover rows) and 122.3 (help strings in cli.py).
- Story 29.5 recompiles the steward skill and `docs-station-cli` regenerates the cheat sheet after this lands.

**Never:**
- Never change `flip`'s behaviour or its precondition.
- Never gate `plan --check` behind the switch.
- Never append a `Surface reconcile` line or stamp.

## Acceptance Criteria

- **AC1 — the cutover tests.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover.py -q -p no:cacheprovider
  ```
- **AC2 — no copy, no manifest, no phase, no A-tree literal in the module.** Expected: 0.
  ```bash
  grep -c -E 'shutil|_PHASE_RULES|manifest|CUTOVER_FOUNDRY_ROOT|apply_phase|src/shared/packages' src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py
  ```
- **AC3 — no test pins the fold.** Expected: 0.
  ```bash
  grep -c -E 'apply_phase|plan_regenerate|plan_append|_preserve_moved|moved' src/shared/packages/pyforge-steward/tests/unit/test_cutover.py
  ```
- **AC4 — the case-list test survives under its nodeid.** Expected: 1.
  ```bash
  grep -c '^def test_flip_refused_while_loop_running' src/shared/packages/pyforge-steward/tests/unit/test_cutover.py
  ```
- **AC5 — apply is gone from the CLI.** Expected: exit 2 (argparse: invalid choice).
  ```bash
  pixi run -q -e pyforge-guild pyforge steward cutover apply --phase 1a
  ```
- **AC6 — plan --check runs and judges.** Expected: exit 0, 3 tests selected.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover.py -q -p no:cacheprovider -k 'plan_check_ok or plan_check_findings_exit_1 or plan_bad_ledger_is_a_failed_result'
  ```
- **AC7 — the kill switch refuses the write modes only.** Expected: exit 0, at least 2 tests selected (regenerate refused and file unchanged; check still runs).
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover.py -q -p no:cacheprovider -k 'write_switch_off'
  ```
- **AC8 — the help line cites qualified ids and no apply.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-steward python -c "from pyforge.steward import cli;h=cli._HELP['cutover'];print(h);raise SystemExit(0 if 'fnd:CAP-8' in h and 'fnd:CAP-9' in h and 'apply' not in h else 1)"
  ```
- **AC9 — both steward halves, coverage, lint.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json && pixi run -e pyforge-steward pyforge-steward-live-test && pixi run -e pyforge-steward pyforge-steward-coverage-gate && pixi run -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

Parent: `spec-python-foundry-cutover` fnd:CAP-8, fnd:CAP-9

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 121.
- Ledger key: `121-2-steward-cutover-plans-the-ledger-and-no-longer-copies-trees` (`backlog` at mint).
- Deps: S-121.1, S-121.6, S-124.4.
- Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py`, `src/shared/packages/pyforge-steward/tests/unit/test_cutover.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` (in `cli.py`, only `_HELP['cutover']` and `_add_cutover_subparsers`).
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover.py -q -p no:cacheprovider` — expected: exit 0.

## Notes

- `test_cli.py` needs no change (it lists duty names only).
- The kill switch is a new verb mode's switch, not a retrofit: the 2026-11-11 decision on the `spec-python-foundry-cutover` memlog reads the second addendum's ruling 5 ('No retrofit kill switch is added') as forbidding only switches retrofitted onto capabilities already shipped, so `pyforge.steward.cutover_ledger_write` stays (registered by Story 124.4).
