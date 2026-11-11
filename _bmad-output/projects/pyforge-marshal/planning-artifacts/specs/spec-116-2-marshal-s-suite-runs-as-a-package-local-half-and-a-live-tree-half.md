---
title: "116.2: Marshal's suite runs as a package-local half and a live-tree half"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: heavy
story: '116.2'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/tests/**/*.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/pyproject.toml
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Steward and Doctor split their suites; steward's trigger map still lists marshal as unsplit (`test_station_tests_trigger_map.py:1782`, `UNSPLIT_ON_A_PLANNING_EDIT = {"marshal"}`). The package half a second repository could run does not exist yet.

**Approach:** The module list is derived, not chosen: run steward's `derive_reads` (`test_station_tests_trigger_map.py:1046`) over marshal's job and mark exactly the modules with an outside read or a root hand-off; the regex pre-count finds 35 candidate modules (1289 tests). A candidate with 20 tests or fewer is marked whole; one with more is split as Story 116.1 does (only its reading tests move to `*_live_tree.py`): here `test_promote_sprint_status_regressions.py` (36), `test_landing_ci_pauses.py` (23) and `test_repo_root.py` (22); the four largest (`test_dispatch_landing.py` 137, `test_dispatch_land_heal.py` 132, `test_factory_challenge.py` 79, `test_dispatch_verify_fix.py` 72) are Story 116.3's. The modules that hand the repository root to code under test are recorded in this spec for steward's `ROOT_HANDOFF_INPUTS`. The package half drops `scripts` from `PYTHONPATH`: a package-half test that imports a repo script is a live read.

Ledger key: `116-2-marshal-s-suite-runs-as-a-package-local-half-and-a-live-tree-half`. Type / Effort / Deps: chore / L / S-114.2, S-114.3, S-115.1, S-115.2, S-115.3, S-115.4, S-116.1.

## Boundaries & Constraints

**Always:**
- The halves partition the suite; the package half keeps at least 90% of the collected tests.
- Acceptance runs the two marker selections directly; steward:S-124.1 adds the task halves after the last marking story.

**Never:**
- Never delete, skip or re-mark a test to make a half pass (steward Story 117.4's Never list).
- Never mark one of the four largest modules whole.

## Acceptance Criteria

- **AC1 — The halves partition the suite, the live half is not empty, and the package half keeps at least 90% of the collected tests.**

  ```bash
  python3 -c "import subprocess,re,sys;n=lambda m:int(re.search(r'(\d+)(?:/\d+)? tests? collected',subprocess.run(['pixi','run','--frozen','-e','pyforge-marshal','pytest','src/shared/packages/pyforge-marshal/tests','--collect-only','-q','-p','no:cacheprovider','-m',m],capture_output=True,text=True).stdout).group(1));a=n('not slow and not live_tree');b=n('live_tree and not slow');c=n('not slow');print(a,b,c,round(a/c,3));sys.exit(0 if a+b==c and b>0 and a>=0.9*c else 1)"
  ```

  Expected: exit 0; prints A B C and the share.

- **AC2 — No module with more than 20 tests is marked whole, except the three whose every test reads the tree (named in the command).**

  ```bash
  python3 -c "import re,sys,pathlib;W=set(sys.argv[1:]);bad=[str(p) for p in pathlib.Path('src/shared/packages/pyforge-marshal/tests').rglob('test_*.py') if re.search(r'^pytestmark = .*live_tree',p.read_text(),re.M) and not p.name.endswith('_live_tree.py') and len(re.findall(r'^\s*(?:async )?def test_',p.read_text(),re.M))>20 and p.name not in W];print(bad);sys.exit(1 if bad else 0)" test_derived_context_skill_contract.py test_planning_graph_skill_contract.py test_local_recipes_empty_plan.py
  ```

  Expected: exit 0; prints `[]` (the four modules Story 116.3 splits are not marked by this story).

- **AC3 — No test was lost.**

  ```bash
  python3 -c "import subprocess,re,pathlib,sys;rx=re.compile(r'^\s*(?:async )?def test_',re.M);h=sum(len(rx.findall(p.read_text())) for p in pathlib.Path('src/shared/packages/pyforge-marshal/tests').rglob('*.py'));fs=[f for f in subprocess.run(['git','ls-tree','-r','--name-only','origin/main','src/shared/packages/pyforge-marshal/tests'],capture_output=True,text=True).stdout.split() if f.endswith('.py')];b=sum(len(rx.findall(subprocess.run(['git','show','origin/main:'+f],capture_output=True,text=True).stdout)) for f in fs);print(b,h);sys.exit(0 if h>=b else 1)"
  ```

  Expected: exit 0.

- **AC4 — Both halves pass, selected by marker.**

  ```bash
  pixi run --frozen -e pyforge-marshal env PYTHONPATH=src/shared/packages/pyforge-marshal/src pytest src/shared/packages/pyforge-marshal/tests/unit src/shared/packages/pyforge-marshal/tests/meta -q -m 'not slow and not live_tree' && pixi run --frozen -e pyforge-marshal env PYTHONPATH=src/shared/packages/pyforge-marshal/src:scripts pytest src/shared/packages/pyforge-marshal/tests/unit src/shared/packages/pyforge-marshal/tests/meta src/shared/packages/pyforge-marshal/tests/integration -q -m 'live_tree and not slow'
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal:CAP-305` (memlog 2026-11-10; rendered by Story 114.1); mechanism spec-pyforge-steward:CAP-175. FR-247 (written by Story 114.1).

- Epic: Epic 116 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 116.2: Marshal's suite runs as a package-local half and a live-tree half`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Owns a glob over marshal's tests, so it depends on every story that owns a marshal test file (114.2, 114.3, 115.1 to 115.4, 116.1).
- Cross-station: steward:S-124.1 reads the marking list, the paths and the `--cov` target from this spec and adds the task halves; steward:S-29.5 asks which stories move marshal source lines.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
