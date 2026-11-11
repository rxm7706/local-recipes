---
title: "117.1: Every core test module that reads the repository carries the live_tree marker"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a test task and its lane (spec-feature-flag-governance Q1; roster list): the suite is a gate, and a gated gate reports a silent green
difficulty: medium
story: '117.1'
spec: pyforge-core
surface:
  - src/shared/packages/pyforge-core/pyproject.toml
  - src/shared/packages/pyforge-core/tests/meta/conftest.py
  - src/shared/packages/pyforge-core/tests/meta/test_atomic_write_sole_ownership.py
  - src/shared/packages/pyforge-core/tests/meta/test_cli_parity_matrix.py
  - src/shared/packages/pyforge-core/tests/meta/test_conformance_lane_wired.py
  - src/shared/packages/pyforge-core/tests/meta/test_coverage_gate_ci_trigger_companion.py
  - src/shared/packages/pyforge-core/tests/meta/test_exception_root_sole_ownership.py
  - src/shared/packages/pyforge-core/tests/meta/test_flag_gate_ci_trigger_companion.py
  - src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py
  - src/shared/packages/pyforge-core/tests/meta/test_preserve_refs_sole_grammar.py
  - src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py
  - src/shared/packages/pyforge-core/tests/meta/test_verdict_lattice_sole_ownership.py
  - src/shared/packages/pyforge-core/tests/unit/test_roster.py
  - src/shared/packages/pyforge-core/tests/unit/test_roster_matches_the_guild_roster.py
  - src/shared/packages/pyforge-core/tests/unit/test_league_measure.py
  - src/shared/packages/pyforge-core/tests/unit/test_league_measure_reads_the_tracked_catalog.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-doctor/pyproject.toml
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
  - src/shared/packages/pyforge-steward/tests/integration/conftest.py
  - .github/workflows/pyforge-pip-install.yml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D2 of the 2026-11-10 design pass and the audit's finding on meta-tests bound to A's layout: at `82a2b18828` the core suite cannot be told apart from the tree. `pyforge-core` registers no `live_tree` marker; ten meta modules read the repository; `test_roster.py` and `test_league_measure.py` mix pure tests with tests that read `docs/governance/guild-roster.json` and the tracked measure catalog. A second root therefore has no oracle it can run for the leaf every station imports.

**Approach:** Realizes spec-pyforge-core:CAP-14 (with Story 117.7, which splits the one mixed module left) and the spec-pyforge-core:CAP-8 amendment, both in the memlog of 2026-11-10 and rendered by Story 117.5. No product code changes. The marker block copies doctor's `pyproject.toml` (`[tool.pytest.ini_options] markers = ["unit: ...", "live_tree: ..."]`). Module-level `pytestmark = pytest.mark.live_tree` goes on the ten meta modules steward's Scanner flags; `test_leaf_constraint.py` reads only its package and stays unmarked. `tests/meta/conftest.py` carries the same line with a comment that pytest ignores `pytestmark` in a conftest and the line is the trigger-map Scanner's declaration (precedent: steward's `tests/integration/conftest.py`). `test_stations_matches_guild_roster_json` and its root finder move, names unchanged, to `tests/unit/test_roster_matches_the_guild_roster.py`; `test_cite_on_allowed` and `test_live_repo_catalog_has_eight_on_rows` move, names unchanged, to `tests/unit/test_league_measure_reads_the_tracked_catalog.py`, which builds the root from `Path(__file__).resolve().parents[5]` (no `Path.cwd()`) and reads the catalog through a literal path. The two new live modules stay under `tests/unit`, so the pip-install lane keeps running them. `test_conformance_lane_wired.py` accepts two wirings and reds a dropped half: today's single `core-test` job running `pyforge-core-test`, or the split steward:S-124.1 and steward:S-124.2 land (a package-half job and a live-half job gated on `CORE_CHANGED`, with `pyforge-core-test` kept as the aggregate of both); the new mutated-copy tests are named `test_detector_fires_when_a_half_is_dropped_*`. Because `pyforge-core-test` stays the whole suite, marshal's dispatch verify, steward's preflight lane keys and the `pyforge-station-tests` aggregate keep their meaning.

Ledger key: `117-1-every-core-test-module-that-reads-the-repository-carries-the-live-tree-marker`. Type / Effort / Deps: feature / M / S-117.5.

## Boundaries & Constraints

**Always:**
- Every test keeps its name and body; a move is a move, and no test is lost.
- A live module reads nothing at import time beyond path constants, so a bare copy of the package collects it.
- `pyforge-core-test` stays the whole suite.

**Never:**
- Never delete, skip or re-mark a test to make a half pass.
- Never edit core's pixi task or CI job here: steward:S-124.1 and steward:S-124.2 split them after this story lands.
- Never append a `Surface reconcile` line to any Spec's memlog and never run `spec_surface_check.py --write-baseline`: the governed paths go in this spec's `surface:`, Story 117.8 reconciles core and the testing charter, and doctor:S-58.4 stamps once.

## Acceptance Criteria

- **AC1 — The whole core suite still passes as wired.**

  ```bash
  pixi run --frozen -e pyforge-core pyforge-core-test
  ```

  Expected: exit 0.

- **AC2 — Package half passes and the marker is registered.**

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests -q -m "not live_tree" --strict-markers -p no:cacheprovider
  ```

  Expected: exit 0.

- **AC3 — Live-tree half passes on the repository.**

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests -q -m live_tree --strict-markers -p no:cacheprovider
  ```

  Expected: exit 0.

- **AC4 — The two halves are the whole suite.**

  ```bash
  pixi run --frozen -e pyforge-core python -c "import re,subprocess,sys; n=lambda *a: int(re.match(r'(\d+)', subprocess.run(['pytest','src/shared/packages/pyforge-core/tests','--collect-only','-q','-p','no:cacheprovider',*a],capture_output=True,text=True).stdout.strip().splitlines()[-1]).group(1)); a,b,c=n('-m','not live_tree'),n('-m','live_tree'),n(); print(a,b,c); sys.exit(not (a>0 and b>0 and a+b==c))"
  ```

  Expected: exit 0; prints three numbers, both halves above 0 and their sum equal to the third.

- **AC5 — Steward's derivation finds an outside read only in the one module Story 117.7 splits (after `git add`).**

  ```bash
  pixi run --frozen -e pyforge-steward python -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('tm','src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py'); tm=importlib.util.module_from_spec(s); sys.modules['tm']=tm; s.loader.exec_module(tm); pkg='src/shared/packages/pyforge-core'; reads=lambda rel: (lambda sc: (sc.scan(rel), bool(sc.reads or sc.handoffs))[1])(tm.Scanner(pkg)); bad=sorted(r for r in tm.tracked_files() if r.startswith(pkg+'/tests/') and r.endswith('.py') and reads(r) and not tm._live_tree_marked(r)); print(bad); sys.exit(bad!=['src/shared/packages/pyforge-core/tests/unit/test_flags.py'])"
  ```

  Expected: exit 0, prints `['src/shared/packages/pyforge-core/tests/unit/test_flags.py']`.

- **AC6 — The lane-wired test accepts the whole-suite job or the two halves, and reds a dropped half.**

  ```bash
  pixi run --frozen -e pyforge-core python -c "import re,subprocess,sys; r=subprocess.run(['pytest','src/shared/packages/pyforge-core/tests/meta/test_conformance_lane_wired.py','-q','-p','no:cacheprovider','-k','half_is_dropped'],capture_output=True,text=True); m=re.search(r'(\d+) passed',r.stdout); print(r.returncode, m and m.group(1)); sys.exit(r.returncode or not m or int(m.group(1))<2)"
  ```

  Expected: exit 0; at least 2 mutated-copy tests named `test_detector_fires_when_a_half_is_dropped_*` pass, and the whole module passes on today's pixi.toml and workflow.

- **AC7 — The pip-install lane's own file list still passes.**

  ```bash
  pixi run --frozen -e pyforge-core pytest -q -p no:cacheprovider src/shared/packages/pyforge-core/tests/unit src/shared/packages/pyforge-core/tests/meta/test_cli_parity_matrix.py src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py
  ```

  Expected: exit 0 (.github/workflows/pyforge-pip-install.yml:113-119 runs exactly these; the two new live modules stay under tests/unit so that lane keeps them).

- **AC8 — The 17 k-core case-list nodeids still resolve.**

  ```bash
  python3 -c "import re,pathlib,sys; rows=re.findall(r'\| k-core-[a-z-]+ \| core \| \x60(?:pyforge-core/tests|\u2026)/([^:\x60]+)::(\w+)\x60', pathlib.Path('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md').read_text(encoding='utf-8')); base=pathlib.Path('src/shared/packages/pyforge-core/tests'); bad=[(f,t) for f,t in rows if ('def '+t) not in (base/(f if f.startswith(('unit','meta')) else 'unit/'+f)).read_text(encoding='utf-8')]; print(len(rows),bad); sys.exit(len(rows)!=17 or bool(bad))"
  ```

  Expected: exit 0, prints `17 []`.

- **AC9 — Lint and types.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-core` (spec-pyforge-core:CAP-14; memlog 2026-11-10, rendered by Story 117.5) and the spec-pyforge-core:CAP-8 amendment; FR-252 <- spec-pyforge-core:CAP-14, written by Story 114.1 after Story 117.5's render; AD-66, AD-68 (the guards' verdicts unchanged). Kinship: spec-pyforge-steward:CAP-175 (the two-halves mechanism).

- Epic: Epic 117 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 117.1: Every core test module that reads the repository carries the live_tree marker`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Same-project dependency: Story 117.5 renders spec-pyforge-core:CAP-14 and the spec-pyforge-core:CAP-8 amendment first.
- Cross-station: must land before steward:S-124.1 and steward:S-124.2 touch core's task and job (their own rule: the marking story lands first); steward:S-124.2 declares the new live module's root handoff to `validate_measure_cite` in `ROOT_HANDOFF_INPUTS`.
- The two ci-trigger companions' docstrings change `pyforge-core-test runs on any single-station change` to name the live half.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (core and the testing charter: Story 117.8; marshal: Story 116.5; steward and the host: steward:S-122.5), and doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). Its open Deps (S-117.5, later in this epic) name no later epic of this station, so the one forward-dependency policy of this PR's mints (a story is minted `blocked` only when its Deps name a later epic) leaves it `backlog`; the integration branch's wave order and marshal's Deps-aware drain hold them. The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-core` came first; `SPEC.md` is rendered by Story 117.5.
