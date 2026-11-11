---
title: "116.1: A marshal test fails, never skips, when the tree it reads is absent"
type: 'fix'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: medium
story: '116.1'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/pyproject.toml
  - src/shared/packages/pyforge-marshal/tests/integration/test_local_recipes_empty_plan.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_derived_context_skill_contract.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_planning_graph_skill_contract.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_chain_regen.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_model_cost.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_policy.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_spin.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_upstream_cli.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_land_epic_rollups.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_bmad_loop_status_vocabulary.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_chain_regen_live_tree.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_live_tree.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification_live_tree.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_model_cost_live_tree.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_policy_live_tree.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_spin_live_tree.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_upstream_cli_live_tree.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_land_epic_rollups_live_tree.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/pyproject.toml
  - src/shared/packages/pyforge-steward/pyproject.toml
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Hollow tests at `82a2b18828`: 13 `pytest.skip` sites fire when a live-tree file is missing, 2 `importorskip("pyforge.doctor...")` sites and 11 `importorskip("bmad_loop...")` sites skip when the import fails, so the suite false-greens on a tree that is not this one. `pyproject.toml` registers only the `slow` marker.

**Approach:** Realizes spec-pyforge-marshal:CAP-305 with Stories 116.2 to 116.4. In the large unit modules only the tests that read the tracked tree move, into a sibling `*_live_tree.py` module with `pytestmark = pytest.mark.live_tree` and an assertion in place of the skip, so the package half keeps the rest; the two skill-contract meta modules and the empty-plan integration module are live as a whole (marked, skip replaced by a failure). `importorskip("bmad_loop...")` becomes a plain import: bmad-loop is a declared dependency. Doctor is not in the marshal env and is not added: the ledger-regression test moves to `test_land_epic_rollups_live_tree.py` and runs Doctor's own command, `python -c <bootstrap> ledger-regression --base <parent> --head <commit> --json` with the tree's `src/shared/packages/pyforge-doctor/src` put on `sys.path` by the bootstrap (the form Story 115.2's adapter uses), and asserts exit 0 and one row with status `ok` and `evidence.ledgers_compared == 1`. The marker text copies steward's (`pyforge-steward/pyproject.toml:82`).

Ledger key: `116-1-a-marshal-test-fails-never-skips-when-the-tree-it-reads-is-absent`. Type / Effort / Deps: fix / M / none.

## Boundaries & Constraints

**Always:**
- The marker is registered once.
- Flag-parametrization skips and platform skips stay.

**Never:**
- No marshal test imports `pyforge.doctor`.
- Never delete or skip a test; no test is lost.

## Acceptance Criteria

- **AC1 — No test skips on a missing live-tree file.**

  ```bash
  ! git grep -nE 'pytest\.skip\(f?"(not running inside the local-recipes|live planning tree not present|marshal-policy\.toml not present|no tracked story specs|tracked (project policy|register) file not present|repo-level skill file not present)' -- src/shared/packages/pyforge-marshal/tests
  ```

  Expected: exit 0 (at `82a2b18828`: 13 hits).

- **AC2 — No test skips on a missing Doctor or bmad-loop import.**

  ```bash
  ! git grep -nE 'importorskip\("(pyforge\.doctor|bmad_loop)' -- src/shared/packages/pyforge-marshal/tests
  ```

  Expected: exit 0 (at `82a2b18828`: 13 hits).

- **AC3 — The marker is registered once.**

  ```bash
  grep -c 'live_tree:' src/shared/packages/pyforge-marshal/pyproject.toml
  ```

  Expected: prints 1.

- **AC4 — Every new module is marked live_tree at module level.**

  ```bash
  for f in src/shared/packages/pyforge-marshal/tests/unit/test_chain_regen_live_tree.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_live_tree.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification_live_tree.py src/shared/packages/pyforge-marshal/tests/unit/test_model_cost_live_tree.py src/shared/packages/pyforge-marshal/tests/unit/test_policy_live_tree.py src/shared/packages/pyforge-marshal/tests/unit/test_spin_live_tree.py src/shared/packages/pyforge-marshal/tests/unit/test_upstream_cli_live_tree.py src/shared/packages/pyforge-marshal/tests/unit/test_land_epic_rollups_live_tree.py; do grep -q '^pytestmark = pytest.mark.live_tree' $f || exit 1; done
  ```

  Expected: exit 0.

- **AC5 — The Doctor ledger-regression test is collected and passes in the marshal env, through Doctor's command.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_land_epic_rollups_live_tree.py -q -m live_tree -k ledger_regression
  ```

  Expected: exit 0; 1 selected, 1 passed, 0 skipped.

- **AC6 — No test was lost (test functions on HEAD at least those on origin/main).**

  ```bash
  python3 -c "import subprocess,re,pathlib,sys;rx=re.compile(r'^\s*(?:async )?def test_',re.M);h=sum(len(rx.findall(p.read_text())) for p in pathlib.Path('src/shared/packages/pyforge-marshal/tests').rglob('*.py'));fs=[f for f in subprocess.run(['git','ls-tree','-r','--name-only','origin/main','src/shared/packages/pyforge-marshal/tests'],capture_output=True,text=True).stdout.split() if f.endswith('.py')];b=sum(len(rx.findall(subprocess.run(['git','show','origin/main:'+f],capture_output=True,text=True).stdout)) for f in fs);print(b,h);sys.exit(0 if h>=b else 1)"
  ```

  Expected: exit 0.

- **AC7 — The suite passes.**

  ```bash
  pixi run --frozen -e pyforge-marshal pyforge-marshal-test
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal:CAP-305` (memlog 2026-11-10; rendered by Story 114.1); mechanism spec-pyforge-steward:CAP-175. FR-247 (written by Story 114.1).

- Epic: Epic 116 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 116.1: A marshal test fails, never skips, when the tree it reads is absent`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Cross-station: until steward:S-124.1 adds the `-m "not slow and not live_tree"` task halves, the one task still runs both halves.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
