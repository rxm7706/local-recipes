---
title: '123.3: Estate plan refuses when its pixi dry run fails, and the share-tree tests say where they run'
type: 'fix'
created: '2026-11-10'
status: 'backlog'
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
