---
title: "116.3: The four largest landing and challenge test modules keep their package-local tests in the package half"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: heavy
story: '116.3'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/tests/**/*.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Marking the four largest candidate modules whole would move about 420 tests out of the package half for the few that read the tree: `test_dispatch_landing.py` (137), `test_dispatch_land_heal.py` (132), `test_factory_challenge.py` (79) and `test_dispatch_verify_fix.py` (72).

**Approach:** Each of the four splits: its reading tests move to a `*_live_tree.py` sibling. `test_dispatch_landing.py` is rewritten by Story 115.2 first (its Doctor fakes), hence the order through Story 116.2. A fixture literal that names a tracked path is rewritten as a path join or a made-up name when it only names a fixture (steward's `scan_strings` reads a bare three-segment literal of a tracked path as a read; doctor Story 58.1's practice); a test whose literal cannot change moves to the live sibling with its reason in this spec. Shared helpers go to a private module under `tests/unit/` only when both files need them.

Ledger key: `116-3-the-four-largest-landing-and-challenge-test-modules-keep-their-package-local-tests-in-the-package-half`. Type / Effort / Deps: chore / L / S-116.2.

## Boundaries & Constraints

**Always:**
- None of the four is marked `live_tree`; each sibling is.

**Never:**
- Never delete, skip or re-mark a test to make a half pass.

## Acceptance Criteria

- **AC1 — Each of the four keeps its package-local tests unmarked and has a marked live sibling only if it read the tree.**

  ```bash
  for m in src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_heal.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py; do ! grep -q '^pytestmark = .*live_tree' $m || exit 1; s=${m%.py}_live_tree.py; test ! -e $s || grep -q '^pytestmark = pytest.mark.live_tree' $s || exit 1; done
  ```

  Expected: exit 0.

- **AC2 — Steward's derivation finds no outside read in marshal's package half.**

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q -k 'package_half_reads_nothing'
  ```

  Expected: exit 0, with the `[marshal]` case among the passed.

- **AC3 — The partition and the 90% floor still hold.**

  ```bash
  python3 -c "import subprocess,re,sys;n=lambda m:int(re.search(r'(\d+)(?:/\d+)? tests? collected',subprocess.run(['pixi','run','--frozen','-e','pyforge-marshal','pytest','src/shared/packages/pyforge-marshal/tests','--collect-only','-q','-p','no:cacheprovider','-m',m],capture_output=True,text=True).stdout).group(1));a=n('not slow and not live_tree');b=n('live_tree and not slow');c=n('not slow');print(a,b,c,round(a/c,3));sys.exit(0 if a+b==c and b>0 and a>=0.9*c else 1)"
  ```

  Expected: exit 0.

- **AC4 — No test was lost.**

  ```bash
  python3 -c "import subprocess,re,pathlib,sys;rx=re.compile(r'^\s*(?:async )?def test_',re.M);h=sum(len(rx.findall(p.read_text())) for p in pathlib.Path('src/shared/packages/pyforge-marshal/tests').rglob('*.py'));fs=[f for f in subprocess.run(['git','ls-tree','-r','--name-only','origin/main','src/shared/packages/pyforge-marshal/tests'],capture_output=True,text=True).stdout.split() if f.endswith('.py')];b=sum(len(rx.findall(subprocess.run(['git','show','origin/main:'+f],capture_output=True,text=True).stdout)) for f in fs);print(b,h);sys.exit(0 if h>=b else 1)"
  ```

  Expected: exit 0.

- **AC5 — Both halves pass, selected by marker.**

  ```bash
  pixi run --frozen -e pyforge-marshal env PYTHONPATH=src/shared/packages/pyforge-marshal/src pytest src/shared/packages/pyforge-marshal/tests/unit src/shared/packages/pyforge-marshal/tests/meta -q -m 'not slow and not live_tree' && pixi run --frozen -e pyforge-marshal env PYTHONPATH=src/shared/packages/pyforge-marshal/src:scripts pytest src/shared/packages/pyforge-marshal/tests/unit src/shared/packages/pyforge-marshal/tests/meta src/shared/packages/pyforge-marshal/tests/integration -q -m 'live_tree and not slow'
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal:CAP-305` (memlog 2026-11-10; rendered by Story 114.1). FR-247 (written by Story 114.1).

- Epic: Epic 116 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 116.3: The four largest landing and challenge test modules keep their package-local tests in the package half`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Cross-station: steward:S-124.1 adds the task halves after the last marking story; doctor:S-58.1 is the precedent for rewriting fixture literals.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
