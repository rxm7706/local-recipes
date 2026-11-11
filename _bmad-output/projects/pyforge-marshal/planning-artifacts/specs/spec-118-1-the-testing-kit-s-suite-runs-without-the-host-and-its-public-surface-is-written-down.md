---
title: "118.1: The testing kit's suite runs without the host, and its public surface is written down"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests and a document: the kit's suite is a gate, and a gated gate reports a silent green (roster flag_exemptions)
difficulty: medium
story: '118.1'
spec: pyforge-testing-charter
surface:
  - src/shared/packages/pyforge-testing-kit/pyproject.toml
  - src/shared/packages/pyforge-testing-kit/tests/conftest.py
  - src/shared/packages/pyforge-testing-kit/tests/unit/test_station_api_contract.py
  - src/shared/packages/pyforge-testing-kit/tests/unit/test_flags.py
  - src/shared/packages/pyforge-testing-kit/tests/meta/test_testing_kit_lane_wired.py
  - src/shared/packages/pyforge-testing-kit/tests/meta/test_flag_fixture_matches_the_platform_tree.py
  - src/shared/packages/pyforge-testing-kit/tests/meta/test_public_contract.py
  - src/shared/packages/pyforge-testing-kit/README.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/contract.md
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/
  - src/shared/packages/pyforge-testing-kit/tests/conftest.py
  - src/shared/packages/pyforge-testing-kit/README.md
  - src/shared/packages/pyforge-doctor/pyproject.toml
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
  - src/shared/packages/pyforge-core/tests/meta/test_conformance_lane_wired.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Ruling 3 of 2026-11-10 (the testing kit is `rebuild`), decisions D1 and D2 of the design pass and the audit's MUST 8: at `82a2b18828` the kit's conftest puts django-pyforge on `sys.path` and imports `django_pyforge` at session start, so none of its tests collects on a root without the host, and every kit module inherits outside reads. No list of the kit's public surface exists outside the source.

**Approach:** Realizes spec-pyforge-testing-charter:CAP-6, spec-pyforge-testing-charter:CAP-7 and the spec-pyforge-testing-charter:CAP-3 lane clause (memlog 2026-11-10, rendered by Story 118.2). No kit source module changes. `conftest.py` loses the `sys.path` insertion and the `pytest_configure` Django bootstrap (pyforge-core is a path dependency of the kit env, so it imports without the insertion); `test_station_api_contract.py` configures Django in a module-scoped fixture, imports `django_pyforge` inside fixture and test bodies and carries the marker, so collection is import-safe everywhere. `tests/unit/test_flags.py` keeps the fixture's own shape assertions; its comparison with `src/platform/config/flags.json` moves to the new live meta module. `pyproject.toml` gains `[tool.pytest.ini_options]` with the `live_tree` marker (doctor's text). `test_testing_kit_lane_wired.py` carries the marker and core's two-wiring rule (today's `testing-kit-test` job, or a package-half job plus a live-half job with `pyforge-testing-kit-test` as their aggregate); its mutated-copy tests are named `test_detector_fires_when_a_half_is_dropped_*`. `contract.md` layout: `## Modules` with ``### `pyforge.testing_kit` `` (the package's `__all__`) and one heading per submodule, `## Fixtures and markers`, `## Run-dependencies` (pyforge-core, openfeature-sdk), `## Estate-bound members` (`cfe_surface` is this repository's conda-forge-expert surface and stays A-only with it), `## Python floor` (3.14). The contract test is a live-tree module (it reads the Spec folder). The README gains the two families it omits (`branch_diff_guard`, `cfe_surface`) and a pointer to `contract.md`.

Ledger key: `118-1-the-testing-kit-s-suite-runs-without-the-host-and-its-public-surface-is-written-down`. Type / Effort / Deps: feature / M / S-118.2.

## Boundaries & Constraints

**Always:**
- Only `live_tree` modules name `django`.
- `pyforge-testing-kit-test` stays the whole suite.

**Never:**
- No file under `src/pyforge/testing_kit` changes.
- Never add `contract.md` to the lane test's `EXTRA_GATE_PATHS` here: that pin checks the workflow gate, so steward:S-124.2 adds the gate path and the pin together.
- Never delete, skip or re-mark a test to make a half pass.
- Never append a `Surface reconcile` line to any Spec's memlog and never run `spec_surface_check.py --write-baseline`: the governed paths go in this spec's `surface:`, Story 117.8 reconciles core and the testing charter, and doctor:S-58.4 stamps once.

## Acceptance Criteria

- **AC1 — The whole kit suite still passes as wired today.**

  ```bash
  pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test
  ```

  Expected: exit 0.

- **AC2 — Package half passes with no host on the path.**

  ```bash
  pixi run --frozen -e pyforge-testing-kit pytest src/shared/packages/pyforge-testing-kit/tests -q -m "not live_tree" --strict-markers -p no:cacheprovider
  ```

  Expected: exit 0 (the command sets no PYTHONPATH, so a `django_pyforge` import at collection fails it).

- **AC3 — Live-tree half passes on the repository.**

  ```bash
  pixi run --frozen -e pyforge-testing-kit env PYTHONPATH=src/shared/packages/django-pyforge/src:src/shared/packages/pyforge-core/src pytest src/shared/packages/pyforge-testing-kit/tests -q -m live_tree --strict-markers -p no:cacheprovider
  ```

  Expected: exit 0.

- **AC4 — The two halves are the whole suite.**

  ```bash
  pixi run --frozen -e pyforge-testing-kit python -c "import re,subprocess,sys; n=lambda *a: int(re.match(r'(\d+)', subprocess.run(['pytest','src/shared/packages/pyforge-testing-kit/tests','--collect-only','-q','-p','no:cacheprovider',*a],capture_output=True,text=True).stdout.strip().splitlines()[-1]).group(1)); a,b,c=n('-m','not live_tree'),n('-m','live_tree'),n(); print(a,b,c); sys.exit(not (a>0 and b>0 and a+b==c))"
  ```

  Expected: exit 0.

- **AC5 — Package half runs from the package alone, and no skip names an outside path.**

  ```bash
  ( D=$(mktemp -d) && mkdir -p "$D/src/shared/packages" && cp -r src/shared/packages/pyforge-testing-kit "$D/src/shared/packages/" && pixi run --frozen -e pyforge-testing-kit env -C "$D" python -m pytest src/shared/packages/pyforge-testing-kit/tests -q -m "not live_tree" -p no:cacheprovider -rs > "$D/out.txt"; rc=$?; grep -cE "src/platform|_bmad-output|guild-roster|pixi\.toml|django" "$D/out.txt"; exit $rc )
  ```

  Expected: prints 0, exit 0.

- **AC6 — Only live-tree modules name django.**

  ```bash
  python3 -c "import pathlib,sys; fs=[p for p in pathlib.Path('src/shared/packages/pyforge-testing-kit/tests').rglob('*.py') if 'django' in p.read_text(encoding='utf-8')]; bad=[str(p) for p in fs if 'pytestmark = pytest.mark.live_tree' not in p.read_text(encoding='utf-8')]; print(len(fs), bad); sys.exit(bool(bad))"
  ```

  Expected: exit 0, prints a count and `[]` (conftest.py no longer names django).

- **AC7 — No unmarked kit test module reads outside the package (after `git add`).**

  ```bash
  pixi run --frozen -e pyforge-steward python -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('tm','src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py'); tm=importlib.util.module_from_spec(s); sys.modules['tm']=tm; s.loader.exec_module(tm); pkg='src/shared/packages/pyforge-testing-kit'; reads=lambda rel: (lambda sc: (sc.scan(rel), bool(sc.reads or sc.handoffs))[1])(tm.Scanner(pkg)); bad=sorted(r for r in tm.tracked_files() if r.startswith(pkg+'/tests/') and r.endswith('.py') and reads(r) and not tm._live_tree_marked(r)); print(bad); sys.exit(bad!=[])"
  ```

  Expected: exit 0, prints `[]`.

- **AC8 — Contract and source agree, one section per module.**

  ```bash
  pixi run --frozen -e pyforge-testing-kit pytest src/shared/packages/pyforge-testing-kit/tests/meta/test_public_contract.py -q -p no:cacheprovider && python3 -c "import re,sys,pathlib; mods={p.stem for p in pathlib.Path('src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit').glob('*.py') if p.stem!='__init__'}; t=pathlib.Path('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/contract.md').read_text(encoding='utf-8'); heads=set(re.findall(r'^### \x60pyforge\.testing_kit\.(\w+)\x60', t, re.M)); print(sorted(mods-heads), sorted(heads-mods)); sys.exit(mods!=heads)"
  ```

  Expected: exit 0, prints `[] []`.

- **AC9 — README names every module.**

  ```bash
  python3 -c "import pathlib,sys; mods=[p.stem for p in pathlib.Path('src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit').glob('*.py') if p.stem!='__init__']; t=pathlib.Path('src/shared/packages/pyforge-testing-kit/README.md').read_text(encoding='utf-8'); miss=[m for m in mods if 'pyforge.testing_kit.'+m not in t]; print(len(mods), miss); sys.exit(bool(miss))"
  ```

  Expected: exit 0.

- **AC10 — The lane-wired test accepts the whole-suite job or the two halves, and reds a dropped half.**

  ```bash
  pixi run --frozen -e pyforge-testing-kit python -c "import re,subprocess,sys; r=subprocess.run(['pytest','src/shared/packages/pyforge-testing-kit/tests/meta/test_testing_kit_lane_wired.py','-q','-p','no:cacheprovider','-k','half_is_dropped'],capture_output=True,text=True); m=re.search(r'(\d+) passed',r.stdout); print(r.returncode, m and m.group(1)); sys.exit(r.returncode or not m or int(m.group(1))<2)"
  ```

  Expected: exit 0, at least 2 passed, and the whole module passes on today's pixi.toml and workflow.

- **AC11 — Lint and types.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-testing-charter` (spec-pyforge-testing-charter:CAP-6, spec-pyforge-testing-charter:CAP-7 and the spec-pyforge-testing-charter:CAP-3 lane clause; memlog 2026-11-10, rendered by Story 118.2); FR-253 <- spec-pyforge-testing-charter:CAP-6 and FR-254 <- spec-pyforge-testing-charter:CAP-7, written by Story 114.1 after Story 118.2's render; no AD. Kinship: spec-pyforge-steward:CAP-175 (the mechanism).

- Epic: Epic 118 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 118.1: The testing kit's suite runs without the host, and its public surface is written down`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Same-project dependency: Story 118.2 renders the capabilities first.
- Cross-station: steward:S-124.1 and steward:S-124.2 split the kit's task and job after this story; steward:S-124.2 adds the `contract.md` gate path and its pin.
- Deferred rows (written by Story 116.5): DW-marshal-118-1-1 (`cfe_surface` names this repository's conda-forge-expert layout inside a package routed `rebuild`; its expiry is mason:S-39.2), DW-marshal-118-1-2 (the portal and CLI header contract test lives in the kit's suite).
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (core and the testing charter: Story 117.8; marshal: Story 116.5; steward and the host: steward:S-122.5), and doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). Its open Deps (S-118.2, later in this epic) name no later epic of this station, so the one forward-dependency policy of this PR's mints (a story is minted `blocked` only when its Deps name a later epic) leaves it `backlog`; the integration branch's wave order and marshal's Deps-aware drain hold them. The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-testing-charter` came first; `SPEC.md` is rendered by Story 118.2.
