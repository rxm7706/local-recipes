---
title: "115.2: A landing reaches the spec-surface verdict through Doctor's command, never an import"
type: 'fix'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: medium
story: '115.2'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/doctor_cli.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_no_doctor_internals_import.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_doctor_cli_adapter.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/steward_cli.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** At `82a2b18828` the dispatch landing is marshal's one station-port bypass: `dispatch_land.py` inserts the worktree's Doctor source on `sys.path` and imports `pyforge.doctor.sources.chain`, at the first read (`:484`) and again at the re-read inside the reconcile loop (`:829`). AGENTS.md: reach another station through its CLI grammar, never its internals.

**Approach:** A fix under CAP-261 (its part (b) amendment is in the memlog of 2026-11-10); no CAP minted. `adapters/doctor_cli.py` mirrors `adapters/steward_cli.py`: one function `read_spec_surface(worktree, process) -> Verdict | Unavailable`. Argv: `[sys.executable, '-c', BOOTSTRAP, 'spec-surface', '--json']`, cwd the worktree, run with `process.run(argv, cwd=worktree, timeout_s=_DOCTOR_VERDICT_TIMEOUT_S)` (300.0); `BOOTSTRAP` inserts the worktree-relative `src/shared/packages/pyforge-doctor/src` at `sys.path[0]` and calls `runpy.run_module('pyforge.doctor.sources', run_name='__main__', alter_sys=True)`, so the verdict is the worktree's own Doctor, through Doctor's documented command module (the one the `spec-surface-check` task runs); `ProcessPort` carries no env parameter, hence the bootstrap rather than `PYTHONPATH`. Verdict rule: stdout that parses as a JSON list is the verdict for rc 0 and rc 2 (Doctor exits 2 on any FAIL row, and `drift` is FAIL); anything else is unavailable, never a parse of prose. Each row becomes a small frozen record with `check`, `message` and `evidence` (`to_json_dict()`'s keys; extra keys ignored), which `_group_surface_findings` already reads by attribute. `test_dispatch_landing.py`'s FakeProcess gains `timeout_s=None` and the 15 `sys.modules` fake-chain sites become scripted process results.

Ledger key: `115-2-a-landing-reaches-the-spec-surface-verdict-through-doctor-s-command-never-an-import`. Type / Effort / Deps: fix / M / none.

## Boundaries & Constraints

**Always:**
- An unavailable first read is MRS-DISP-047 (warn, no refusal); an unavailable re-read is MRS-DISP-048 (refuse), as the in-process re-read's raise is today.
- The seven other landing test files pass unchanged.

**Never:**
- Never import `pyforge.doctor` from marshal source.
- Never parse Doctor's prose; never treat rc 2 with empty stdout as a verdict.
- Never take `seed/detect/referenced_deps.py:203-213` as the model: it drops rc 2.

## Acceptance Criteria

- **AC1 — No marshal module imports Doctor.**

  ```bash
  ! git grep -nE '^\s*(from|import) pyforge\.doctor' -- src/shared/packages/pyforge-marshal/src
  ```

  Expected: exit 0 (at `82a2b18828`: 1 hit).

- **AC2 — The guard and its failing fixture pass (a synthetic module with `from pyforge.doctor.sources.chain import x` is named).**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_no_doctor_internals_import.py -q
  ```

  Expected: exit 0.

- **AC3 — The adapter reads Doctor's exit domain: rc 0 with a JSON list and rc 2 with a JSON list are both the verdict; rc 2 with empty stdout (argparse), rc 1, rc 130, a ProcessError (launch or timeout) and stdout that is not a JSON list are each unavailable.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_doctor_cli_adapter.py -q
  ```

  Expected: exit 0.

- **AC4 — The reconcile through the adapter: rc 2 with own-path drift rows reaches `_group_surface_findings` and reconciles; rc 2 with a foreign-path drift row refuses with MRS-DISP-048; rc 2 with empty stdout on the first read is MRS-DISP-047 and no refusal; an unavailable re-read after a stamp refuses with MRS-DISP-048.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py -q -k 'rc_2 or foreign_drift or empty_stdout or unavailable_reread'
  ```

  Expected: exit 0; 4 or more selected.

- **AC5 — The argv runs through the landing's ProcessPort, with the worktree as cwd.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py -q -k 'doctor_argv'
  ```

  Expected: exit 0; 1 or more selected.

- **AC6 — The landing's other test files pass unchanged.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_spec_block.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_survival.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py src/shared/packages/pyforge-marshal/tests/unit/test_status_landing_superseded.py src/shared/packages/pyforge-marshal/tests/unit/test_findings.py src/shared/packages/pyforge-marshal/tests/meta/test_fleet_picture_landing_findings.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py -q
  ```

  Expected: exit 0, with `git diff origin/main --stat` showing no change to the first seven files.

- **AC7 — Import contracts, lint and types hold.**

  ```bash
  pixi run -e pyforge-guild lint-types && pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py -q
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-261 (amended 2026-11-10). FR-248 (written by Story 114.1).

- Epic: Epic 115 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 115.2: A landing reaches the spec-surface verdict through Doctor's command, never an import`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Cost: each reconcile pass now pays one interpreter start plus the verdict, bounded by the number of Specs governing the branch's paths.
- DW-FU-53-2-2 (a stale in-process module) is moot by design; Story 116.5 closes it. `harness_bmadloop.py:443-446` is a comment and stays.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
