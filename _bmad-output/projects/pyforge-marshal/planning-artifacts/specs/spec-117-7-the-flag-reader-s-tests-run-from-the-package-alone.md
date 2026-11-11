---
title: "117.7: The flag reader's tests run from the package alone"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a test task and its lane (spec-feature-flag-governance Q1; roster list): the suite is a gate, and a gated gate reports a silent green
difficulty: heavy
story: '117.7'
spec: pyforge-core
surface:
  - src/shared/packages/pyforge-core/tests/unit/test_flags.py
  - src/shared/packages/pyforge-core/tests/unit/test_flags_reader.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-core/tests/unit/test_flags.py
  - src/shared/packages/pyforge-core/src/pyforge/core/flags.py
  - src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - docs/reference/story-spec-flag-block.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** An audit defect of 2026-11-10 and the review blocker on spec-pyforge-core:CAP-14: `tests/unit/test_flags.py` mixes about 900 lines of hermetic flag-reader tests with three groups that read `src/platform/config` and a tracked-path literal. On a root without that tree those groups skip, so the package half reads as green while still reading outside, and steward's package-half derivation is not empty.

**Approach:** Realizes spec-pyforge-core:CAP-14 with Story 117.1 (memlog 2026-11-10, rendered by Story 117.5). No product code changes. Direction: the hermetic tests move out and the shipped-tree groups stay, because other code binds this exact path and these dict names: marshal's landing auto-heal (`core/dispatch_landing.py` `FLAG_REGISTRY_PYTHON_TARGETS` names this path with `_SHIPPED_CLOCKS`, `expected`, `per_environment`), `core/dispatch_verify_fix.py`, `dispatch_land.py`'s post-heal pytest, marshal's heal, landing and verify-fix tests, `docs/reference/story-spec-flag-block.md`, five stations' `marshal-policy.toml` and the team-memory flag-tables entry. Moving the tables would silently stop marshal healing flag-registry conflicts. What moves to `test_flags_reader.py`: the helpers, the tree matrix, the resolver and Q3 tests and Story 76.1's overlay tests; Story 76.2's metadata tests on synthetic trees; the flagd provider test; the autouse `_no_ambient_environment` fixture is copied to both modules. What stays in `test_flags.py`, now `pytestmark = pytest.mark.live_tree`: `_SHIPPED_CLOCKS`, `_shipped`, `_RETROFIT_KILL_SWITCHES`, `_LATER_KILL_SWITCHES` and the function-local `expected` and `per_environment`. The one changed line: `test_no_second_tree_resolver_exists_in_pyforge_core` compares with `str(cutover_root.LOCAL_DEV_RELATIVE)` instead of the literal path, so the Scanner no longer counts a tracked-path literal in the package half. Size: a move (`git diff -B -M --stat` counts about 850 changed lines; `git diff --color-moved` shows the moved blocks; AC1 proves nothing else moved).

Ledger key: `117-7-the-flag-reader-s-tests-run-from-the-package-alone`. Type / Effort / Deps: feature / L / S-117.1 (the same-station key, as in `epics.md`; the cross-station dependency steward:S-124.4 is in Notes).

## Boundaries & Constraints

**Always:**
- Every test function keeps its name and body, that one literal excepted.
- The shipped-flag tables stay in `tests/unit/test_flags.py` under their names.

**Never:**
- Never move the shipped-flag tables or rename their dicts.
- Never delete, skip or re-mark a test to make a half pass.
- Never append a `Surface reconcile` line to any Spec's memlog and never run `spec_surface_check.py --write-baseline`: the governed paths go in this spec's `surface:`, Story 117.8 reconciles core and the testing charter, and doctor:S-58.4 stamps once.

## Acceptance Criteria

- **AC1 — A pure move: every test function keeps its body, one literal excepted.**

  ```bash
  python3 -c "import ast,subprocess,sys,pathlib; b=subprocess.run(['git','merge-base','origin/main','HEAD'],capture_output=True,text=True,check=True).stdout.strip(); old=subprocess.run(['git','show',b+':src/shared/packages/pyforge-core/tests/unit/test_flags.py'],capture_output=True,text=True,check=True).stdout; f=lambda t:{n.name:ast.dump(n) for n in ast.parse(t).body if isinstance(n,ast.FunctionDef)}; p='src/shared/packages/pyforge-core/tests/unit/'; a=f(pathlib.Path(p+'test_flags.py').read_text(encoding='utf-8')); r=f(pathlib.Path(p+'test_flags_reader.py').read_text(encoding='utf-8')); o=f(old); dup=(set(a)&set(r))-{'_no_ambient_environment'}; new={**a,**r}; diff=sorted(k for k in o if new.get(k)!=o[k]); extra=sorted(set(new)-set(o)); print(len(o),sorted(dup),diff,extra); sys.exit(bool(dup) or bool(extra) or set(o)!=set(new) or diff!=['test_no_second_tree_resolver_exists_in_pyforge_core'])"
  ```

  Expected: exit 0, prints the old function count, `[]`, `['test_no_second_tree_resolver_exists_in_pyforge_core']`, `[]`.

- **AC2 — The shipped-flag tables stay at the path marshal's landing heal binds to.**

  ```bash
  grep -cE '^(_SHIPPED_CLOCKS|_LATER_KILL_SWITCHES) = \{$|^pytestmark = pytest\.mark\.live_tree$' src/shared/packages/pyforge-core/tests/unit/test_flags.py
  ```

  Expected: prints 3.

- **AC3 — Marshal's heal, landing and verify-fix tests still bind.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest -q -p no:cacheprovider src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_heal.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py
  ```

  Expected: exit 0.

- **AC4 — No unmarked core test module reads outside the package (after `git add`).**

  ```bash
  pixi run --frozen -e pyforge-steward python -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('tm','src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py'); tm=importlib.util.module_from_spec(s); sys.modules['tm']=tm; s.loader.exec_module(tm); pkg='src/shared/packages/pyforge-core'; reads=lambda rel: (lambda sc: (sc.scan(rel), bool(sc.reads or sc.handoffs))[1])(tm.Scanner(pkg)); bad=sorted(r for r in tm.tracked_files() if r.startswith(pkg+'/tests/') and r.endswith('.py') and reads(r) and not tm._live_tree_marked(r)); print(bad); sys.exit(bad!=[])"
  ```

  Expected: exit 0, prints `[]`.

- **AC5 — Package half runs from the package alone, and no skip names an outside path.**

  ```bash
  ( D=$(mktemp -d) && mkdir -p "$D/src/shared/packages" && cp -r src/shared/packages/pyforge-core "$D/src/shared/packages/" && pixi run --frozen -e pyforge-core env -C "$D" python -m pytest src/shared/packages/pyforge-core/tests -q -m "not live_tree" -p no:cacheprovider -rs > "$D/out.txt"; rc=$?; grep -cE "src/platform|_bmad-output|guild-roster|pixi\.toml|django" "$D/out.txt"; exit $rc )
  ```

  Expected: prints 0, exit 0.

- **AC6 — The whole core suite still passes as wired.**

  ```bash
  pixi run --frozen -e pyforge-core pyforge-core-test
  ```

  Expected: exit 0.

- **AC7 — The two halves are the whole suite.**

  ```bash
  pixi run --frozen -e pyforge-core python -c "import re,subprocess,sys; n=lambda *a: int(re.match(r'(\d+)', subprocess.run(['pytest','src/shared/packages/pyforge-core/tests','--collect-only','-q','-p','no:cacheprovider',*a],capture_output=True,text=True).stdout.strip().splitlines()[-1]).group(1)); a,b,c=n('-m','not live_tree'),n('-m','live_tree'),n(); print(a,b,c); sys.exit(not (a>0 and b>0 and a+b==c))"
  ```

  Expected: exit 0.

- **AC8 — Lint and types.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-core` (spec-pyforge-core:CAP-14; memlog 2026-11-10, rendered by Story 117.5); FR-252, written by Story 114.1 after Story 117.5's render; AD-66.

- Epic: Epic 117 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 117.7: The flag reader's tests run from the package alone`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Same-project dependency: Story 117.1 (the marker).
- Cross-station: absorbs steward-station's first Story 124.4 split (same two files, same direction) and builds after steward:S-124.4 adds the cutover kill switch to the tables; steward:S-124.4 edits only the tables. That dependency is not in the `epics.md` Deps line, because marshal's Deps parser drops a station prefix and would read it as a marshal key 124.4 that does not exist; only the integration branch's wave order (plan.json) holds it.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (core and the testing charter: Story 117.8; marshal: Story 116.5; steward and the host: steward:S-122.5), and doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). Its Deps (S-117.1, earlier in this epic) name no later epic of this station, so the one forward-dependency policy of this PR's mints (a story is minted `blocked` only when its Deps name a later epic) leaves it `backlog`; the integration branch's wave order and marshal's Deps-aware drain hold it. Its cross-station dependency steward:S-124.4 is in Notes, not in the Deps line, and only the integration branch's wave order holds it, since marshal's Deps parser is station-local. The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-core` came first; `SPEC.md` is rendered by Story 117.5.
- 2026-11-11: fix pass after the third review of the mint. steward:S-124.4 left the Deps line here and in `epics.md` (marshal's Deps parser read it as a marshal key 124.4, which does not exist, so the story could never read ready); it stays in Notes, and the entry above no longer says marshal's drain holds it.
