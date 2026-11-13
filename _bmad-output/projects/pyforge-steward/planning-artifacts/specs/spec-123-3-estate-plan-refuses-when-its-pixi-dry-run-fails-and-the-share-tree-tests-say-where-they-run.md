---
title: '123.3: Estate plan refuses when its pixi dry run fails, and the share-tree tests say where they run'
type: 'fix'
created: '2026-11-10'
status: 'done'
difficulty: medium
story: 123.3
spec: pyforge-steward
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/estate.py
  - src/shared/packages/pyforge-steward/tests/unit/test_estate.py
  - src/shared/packages/pyforge-steward/tests/unit/test_provision_module_installers.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/session.py
  - src/shared/packages/pyforge-steward/tests/unit/test_session.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Two oracle defects (DW-steward-119-2; the share-tree skips) and a guard that cannot fire, which the operator ruled a verified defect on 2026-11-10.

**Approach:** The dry run executes before the `--due` branch, and `--due` already uses exit 1 for 'overdue', so a failed pixi takes 3, the code estate already uses for 'could not act'. Session check finding (2) drops the in-process doctor import and takes the verdict of `pixi run -e pyforge-guild bmad-drift-check` everywhere (the subprocess path `run_bmad_drift_integrity` already runs).

Ledger key: `123-3-estate-plan-refuses-when-its-pixi-dry-run-fails-and-the-share-tree-tests-say-where-they-run`. Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-steward` CAP-167** (FR-40) — estate plan; **CAP-18..CAP-20** — the provision tests; **CAP-162** — `steward session check`.

## Boundaries & Constraints

**Always:**
- Keep the share-tree tests Guild-environment tests (the steward feature carries no bmad share package; adding one is an estate-pin decision, a deferred row).

**Never:**
- Never change `--due`'s overdue exit.
- Never add a pin to the steward feature.
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — a failed dry run refuses with exit 3.** Expected: exit 0 with at least 3 tests selected: a runner returning a non-zero exit gives `DutyResult.ok` False with `details['exit_code'] == EXIT_ESTATE_REFUSAL` (3) and a summary naming pixi's exit code, on the plain path, on `--json`, and on `--due`.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_estate.py -q -k 'plan and pixi_fails'
  ```
- **AC2 — --due keeps exit 1 for overdue only.** Expected: exit 0, including a case where pixi fails and the refresh is overdue: the result is the refusal (3), never 'overdue' (1).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_estate.py -q -k due
  ```
- **AC3 — a green dry run is unchanged.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_estate.py -q
  ```
- **AC4 — the skip reason names the environment read.** Expected: prints 0.
  ```bash
  grep -c 'local-recipes pixi env share data' src/shared/packages/pyforge-steward/tests/unit/test_provision_module_installers.py
  ```
- **AC5 — the two share-tree tests run where the Guild env exists.** Expected: exit 0; `2 passed`, no SKIPPED line.
  ```bash
  pixi run --frozen -e pyforge-guild env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_provision_module_installers.py -q -rs -k 'live_share or live_utility'
  ```
- **AC6 — session check finding (2) imports no doctor module (operator ruling 2026-11-10).** Expected: exit 0; prints `[]`.
  ```bash
  python3 -c "import ast,sys;t=ast.parse(open('src/shared/packages/pyforge-steward/src/pyforge/steward/session.py').read());b=[n.module for n in ast.walk(t) if isinstance(n,ast.ImportFrom) and (n.module or '').startswith('pyforge.doctor')]+[a.name for n in ast.walk(t) if isinstance(n,ast.Import) for a in n.names if a.name.startswith('pyforge.doctor')];print(b);sys.exit(bool(b))"
  ```
- **AC7 — finding (2) takes bmad-drift-check's verdict everywhere and can fail.** Expected: exit 0 with at least 2 tests selected: a stubbed drift command exiting 1 makes finding (2) fail with the `bmad-drift-check` remedy whether or not `pyforge.doctor` is importable, and exit 0 makes it pass.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_session.py -q -k bmad_method
  ```
- **AC8 — the deferred row is resolved by this story.** Expected: exit 0; prints `True`.
  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md').read();m=re.search(r'^### DW-steward-119-2:.*?(?=^### )',t,re.S|re.M);b=m.group(0);ok='status: resolved' in b and '123.3' in b;print(ok);sys.exit(not ok)"
  ```
- **AC9 — package half.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json
  ```
- **AC10 — live-tree half.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```
- **AC11 — lint and types.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-167 (FR-40), CAP-18..CAP-20, CAP-162

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 123.
- Ledger key: `123-3-estate-plan-refuses-when-its-pixi-dry-run-fails-and-the-share-tree-tests-say-where-they-run` (`backlog` at mint).
- Deps: —.
- Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/estate.py`, `src/shared/packages/pyforge-steward/tests/unit/test_estate.py`, `src/shared/packages/pyforge-steward/tests/unit/test_provision_module_installers.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/session.py`, `src/shared/packages/pyforge-steward/tests/unit/test_session.py`, `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` (the DW-steward-119-2 entry only).
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_estate.py -q -k 'plan and pixi_fails'` — expected: exit 0 with at least 3 tests selected: a runner returning a non-zero exit gives `DutyResult.ok` False with `details['exit_code'] == EXIT_ESTATE_REFUSAL` (3) and a summary naming pixi's exit code, on the plain path, on `--json`, and on `--due`.
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_estate.py -q -k due` — expected: exit 0, including a case where pixi fails and the refresh is overdue: the result is the refusal (3), never 'overdue' (1).

## Notes

- Cross-station: none. Story 122.2 writes the contract row for exit 3 and depends on this story; Story 123.2 depends on it for an empty exception list.
- RULING 2026-11-10 (second addendum): session check finding (2) takes bmad-drift-check's verdict everywhere; session.py and test_session.py join this story's surface; size M. The deferred row the plan drafted for it (DW-steward-cutover-2026-11-10-1) is written resolved by Story 122.5.
- The ledger entry gains `status: resolved` and a `verified:` line naming Story 123.3; the mint's new rows are other hunks of the same file.
- Until Story 124.2 lands, steward's trigger-map test may red on other units' new reads (a planned red window); this story is judged by its own test modules and by steward's package half without that module.

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build attempt. Each finding, and what this round did with it:

1. **major** — `deferred-work-ledger.md`, entry DW-steward-119-2, the new `verified:` line. **Problem:** the line cited no `path:line` and no backtick-quoted command followed by its exit code, only test selectors with pass counts. A `verified:` line dated after the cutoff must cite one or the other, so `pixi run --frozen -e pyforge-guild deferred-work-check` failed (rc=2) with `verified-line-uncited: fail -- pyforge-steward/DW-steward-119-2`. AC8 did not catch it, because it tests only for `status: resolved` and `123.3`. **Fixed:** the line was rewritten in place. It is this story's own line, and `scripts/apply_verification_verdicts.py` only appends, so a second line would have left the bare one there, still red. The new line cites `estate.py:446` and the two AC commands, each with its exit code. `verified_line_cites` accepts it, and `deferred-work-check` no longer names DW-steward-119-2.
2. **minor** — `upgrade.py` `_BMAD_DRIFT_TASK_ARGV`, reached from `session.py` `_bmad_method_finding`. **Problem:** finding (2) now always starts `pixi run -e pyforge-guild bmad-drift-check` without `--frozen`. pixi does not pass `--frozen` to a child pixi, so under the session-start hook's `pixi run --frozen`, the nested run could re-solve and rewrite `pixi.lock`, or run past the 60 s timeout. **Fixed in this story's surface:** finding (2)'s default runner in `session.py` (`_run_drift_check`) runs the same argv with `PIXI_FROZEN=true`, pixi's documented environment form of `--frozen`. The seed check in the same module already runs with `--frozen`. Adding `--frozen` to the argv itself in `upgrade.py` is left to that file's owners (Stories 123.2 and 122.3); `upgrade.py` is outside this story's `files_owned`.
3. **minor** — `upgrade.py` `_run_bmad_drift_task`'s launch-error detail; `session.py` imports that private helper. **Problem:** when pixi fails to launch, the detail reads "pyforge.doctor not importable here and the pixi task failed to launch", which is wrong for session check. **Fixed for session check:** `_run_drift_check` turns a launch error into exit 2 (and a timeout into exit 124), so the text becomes `bmad-drift-check could-not-run (exit 2) …` with no mention of doctor. A test pins this. The cross-module private import stays: the only public entry point, `run_bmad_drift_integrity`, reads doctor first, and this story removes that read. Exposing a public helper, and rewording the detail at its source, belongs to the `upgrade.py` owners (Stories 123.2 and 122.3).
4. **minor** — `test_session.py`, the `_hide_doctor` docstring. **Problem:** it still described fallback tests that no longer exist. **Fixed:** it now says the helper is the doctor-hidden state of the parametrization.
5. **minor** — `test_deploy_nic_packs.py::test_run_nic_up_refuses_a_missing_pack_cli_before_nic_starts[off]`, which belongs to no story here. **Problem:** it failed once in the AC9 run and passed alone and on a second run. It looks order-dependent, or it was hit by another wave story's concurrent edit to `flags.json`. **No action for 123.3:** it is reported to the wave gate.
