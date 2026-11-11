---
title: "38.2: Mason's suite runs as a package half and a live-tree half"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a test split and a meta-test (spec-feature-flag-governance Q1; roster list)
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - src/shared/packages/pyforge-steward/pyproject.toml
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-55-4-doctor-s-live-tree-readers-run-as-their-own-half.md
  - src/shared/packages/pyforge-mason/pyproject.toml
surface:
  - src/shared/packages/pyforge-mason/pyproject.toml
  - src/shared/packages/pyforge-mason/tests/conftest.py
  - src/shared/packages/pyforge-mason/tests/meta/test_live_tree_split.py
  - src/shared/packages/pyforge-mason/tests/meta/test_adapter_sole_caller.py
  - src/shared/packages/pyforge-mason/tests/meta/test_capability_tiers.py
  - src/shared/packages/pyforge-mason/tests/meta/test_cfe_import_floor_env_sync.py
  - src/shared/packages/pyforge-mason/tests/meta/test_cfe_independence.py
  - src/shared/packages/pyforge-mason/tests/meta/test_credential_isolation.py
  - src/shared/packages/pyforge-mason/tests/meta/test_dependency_direction.py
  - src/shared/packages/pyforge-mason/tests/meta/test_engine_version_range_sync.py
  - src/shared/packages/pyforge-mason/tests/meta/test_exit_code_ownership.py
  - src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py
  - src/shared/packages/pyforge-mason/tests/meta/test_namespace_is_implicit.py
  - src/shared/packages/pyforge-mason/tests/meta/test_no_config_file.py
  - src/shared/packages/pyforge-mason/tests/meta/test_no_recipe_knowledge.py
  - src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py
  - src/shared/packages/pyforge-mason/tests/meta/test_portal_last_diagnose.py
  - src/shared/packages/pyforge-mason/tests/meta/test_render_ownership.py
  - src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py
  - src/shared/packages/pyforge-mason/tests/unit/test_airgap_contract.py
  - src/shared/packages/pyforge-mason/tests/unit/test_boot_reconcile.py
  - src/shared/packages/pyforge-mason/tests/unit/test_build_hooks.py
  - src/shared/packages/pyforge-mason/tests/unit/test_cfe.py
  - src/shared/packages/pyforge-mason/tests/unit/test_cfe_rebuild_guard_merges.py
  - src/shared/packages/pyforge-mason/tests/unit/test_cli.py
  - src/shared/packages/pyforge-mason/tests/unit/test_doctor.py
  - src/shared/packages/pyforge-mason/tests/unit/test_engines.py
  - src/shared/packages/pyforge-mason/tests/unit/test_engines_condalock.py
  - src/shared/packages/pyforge-mason/tests/unit/test_engines_gh.py
  - src/shared/packages/pyforge-mason/tests/unit/test_engines_pep517.py
  - src/shared/packages/pyforge-mason/tests/unit/test_engines_pixi.py
  - src/shared/packages/pyforge-mason/tests/unit/test_engines_twine.py
  - src/shared/packages/pyforge-mason/tests/unit/test_environment.py
  - src/shared/packages/pyforge-mason/tests/unit/test_errors.py
  - src/shared/packages/pyforge-mason/tests/unit/test_exit_codes.py
  - src/shared/packages/pyforge-mason/tests/unit/test_fake_cfe_root_fixture.py
  - src/shared/packages/pyforge-mason/tests/unit/test_models.py
  - src/shared/packages/pyforge-mason/tests/unit/test_package.py
  - src/shared/packages/pyforge-mason/tests/unit/test_pypi_index.py
  - src/shared/packages/pyforge-mason/tests/unit/test_recipe.py
  - src/shared/packages/pyforge-mason/tests/unit/test_render.py
  - src/shared/packages/pyforge-mason/tests/unit/test_resolve.py
live_tree_modules:   # relative to src/shared/packages/pyforge-mason/tests/; each with why it reads outside the package
  - meta/test_cfe_import_floor_env_sync.py   # reads the root pixi.toml
  - meta/test_mason_skills.py   # reads .claude/skills and docs/how-to
  - meta/test_persona_consults_cfe.py   # reads the persona's golden transcript under .claude/skills
  - meta/test_portal_last_diagnose.py   # reads the django-mason and django-pyforge packages
  - meta/test_skf_mason_skill.py   # reads .claude/skills/pyforge-mason and AGENTS.md
  - unit/test_cfe_rebuild_guard_merges.py   # reads scripts/cfe_rebuild_guard_check.py
  - meta/test_public_contract.py   # Story 38.1: reads contract.md and two other packages
  - meta/test_cfe_adapter_argv_live.py   # Story 38.3: reads the real CFE scripts
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D2. Mason's suite is the rebuild's oracle, and the Spec says every test runs against a fake root, yet six modules (42 tests) read the repository outside the package with no marker, and nothing proves the rest passes away from this tree. Steward and doctor already split by the `live_tree` marker (spec-pyforge-steward:CAP-175, ruling D4); mason adopts the same marker.

**Approach:**
- Marker text and placement are steward's, word for word (`src/shared/packages/pyforge-steward/pyproject.toml`, the `live_tree` marker lines). `meta/test_engine_version_range_sync.py` reads the package's own `pixi.toml` and stays in the package half.
- The out-of-tree run is the real test: a unit test that silently finds this repository's CFE root through the cwd walk fails there, and is then fixed to use `fake_cfe_root` or a tmp start directory, or is marked `live_tree` if it must read the real tree (and added to `live_tree_modules:` with its reason).
- `tests/meta/test_live_tree_split.py` is in the package half and reads only the package's own tests directory.
- The three `>=3.12` comment lines in `meta/test_no_recipe_knowledge.py` become 3.14 here (decision D6).
- mypy: run `pixi run -e pyforge-guild mypy` once with the `pyforge.mason.cli` override removed, keep only the codes that still fire (today `["assignment", "attr-defined"]`; delete the override if neither fires), and record the output here.
- This `pyproject.toml` edit is the package's `code` stage for the chain-currency sweep: it obliges a mason retro within two days and a Spec, PRD and spine dated on or after it (Story 37.4 checks).

Ledger key: `38-2-mason-s-suite-runs-as-a-package-half-and-a-live-tree-half`.
Ledger status: `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- **CAP-7** (amended 2026-11-10; FR-61): the suite is two halves by the `live_tree` marker. The mint wrote the amendment at `(ready 2026-11-10)`; Story 37.1 writes the shipped marker and rewords the fake-root constraint.
- Relay of **spec-pyforge-steward:CAP-175** (ruling D4 of 2026-10-27); decisions D2 and D6.
- `spec-feature-flag-governance` Q2: `flag-exempt: detector-or-gate` (the exact form of doctor Story 55.4).

## Boundaries & Constraints

**Always:**
- Mark a module only because it reads the repository outside the package.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never delete, skip or re-mark a test to make a half pass.
- Never edit the modules other stories own: `unit/test_recipe_update_help.py` (37.3), `unit/test_factory_island.py` (39.1), `meta/test_public_contract.py` (38.1), `meta/test_cfe_adapter_argv_live.py` (38.3).
- Never touch the root `pixi.toml` or a workflow.
- Never add behaviour or a flag (operator ruling 2026-11-10: no new behaviour and no new kill switch in this PR).
- Never append a `Surface reconcile` line to another Spec's memlog and never run `spec_surface_check.py --write-baseline`: Story 37.4 writes mason's reconcile event, each other Spec's closer writes its own, and doctor Story 58.4 runs every scoped stamp once, after the last edit (cutover readiness plan, integration 2026-11-10).

## Acceptance Criteria

**AC1 — The marker is registered.**

```bash
grep -c 'live_tree: ' src/shared/packages/pyforge-mason/pyproject.toml
```

Expect: prints 1.

**AC2 — The marked modules are exactly the list the story spec records.**

```bash
python3 - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-38-2-*.md' <<'EOF'
"""Exit 0 when the set of Mason test modules that carry a module-level `live_tree` mark equals the
`live_tree_modules:` list recorded in Story 38.2's story spec (entries not yet on disk are skipped, so
the two modules Stories 38.1 and 38.3 add are listed before they land). Run from the repo root.
argv: the story spec path (glob allowed)."""
import glob
import pathlib
import re
import sys

import yaml

T = pathlib.Path("src/shared/packages/pyforge-mason/tests")
spec = sorted(glob.glob(sys.argv[1]))[0]
text = open(spec, encoding="utf-8").read()
fm = yaml.safe_load(text.split("\n---", 1)[0].lstrip("-\n"))
listed = {str(T / p) for p in fm["live_tree_modules"] if (T / p).is_file()}
mark = re.compile(r"^pytestmark\s*=\s*(?:\[[^\]]*)?pytest\.mark\.live_tree\b", re.M)
marked = {str(p) for p in T.rglob("test_*.py") if mark.search(p.read_text(encoding="utf-8"))}
for p in sorted(marked - listed):
    print("marked, not listed:", p)
for p in sorted(listed - marked):
    print("listed, not marked:", p)
print(f"marked={len(marked)} listed-on-disk={len(listed)}")
sys.exit(0 if marked == listed and marked else 1)
EOF
```

Expect: exit 0. The story spec's frontmatter `live_tree_modules:` lists, relative to the tests directory, the six readers (meta/test_cfe_import_floor_env_sync.py, meta/test_mason_skills.py, meta/test_persona_consults_cfe.py, meta/test_portal_last_diagnose.py, meta/test_skf_mason_skill.py, unit/test_cfe_rebuild_guard_merges.py), the two modules Stories 38.1 and 38.3 add (meta/test_public_contract.py, meta/test_cfe_adapter_argv_live.py), and any module the out-of-tree run had to move, each with its reason.

**AC3 — The package half passes in the tree.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit src/shared/packages/pyforge-mason/tests/meta -q -m "not slow and not live_tree"; echo $?
```

Expect: 0.

**AC4 — The package half passes from a copy outside the repository.**

```bash
pixi run --frozen -e pyforge-mason bash -c 'd=$(mktemp -d) && cp -r src/shared/packages/pyforge-mason "$d/pkg" && cd "$d/pkg" && PYTHONPATH=src python -m pytest tests/unit tests/meta -q -m "not slow and not live_tree" -p no:cacheprovider'; echo $?
```

Expect: 0 (mktemp must resolve outside any directory tree that holds .claude/scripts/conda-forge-expert).

**AC5 — The live-tree half passes in the tree.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit src/shared/packages/pyforge-mason/tests/meta -q -m "live_tree and not slow"; echo $?
```

Expect: 0.

**AC6 — No test was dropped: the halves sum to the whole.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason python -  <<'EOF'
"""Exit 0 when Mason's two halves together collect exactly what the whole `not slow` suite collects, and
the live half holds at least the 42 tests of the six known outside readers. Run from the repo root inside
the pyforge-mason environment (sys.executable is that environment's python). No argv."""
import re
import subprocess
import sys

T = "src/shared/packages/pyforge-mason/tests"
COUNT = re.compile(r"^(\d+)(?:/\d+)? tests? collected", re.M)


def collected(expr: str) -> int:
    out = subprocess.run(
        [sys.executable, "-m", "pytest", f"{T}/unit", f"{T}/meta", "--collect-only", "-q", "-m", expr, "-p", "no:cacheprovider"],
        capture_output=True, text=True,
    ).stdout
    m = COUNT.search(out)
    return int(m.group(1)) if m else -1


whole = collected("not slow")
package = collected("not slow and not live_tree")
live = collected("live_tree and not slow")
print(f"not-slow={whole} package={package} live={live}")
sys.exit(0 if whole > 0 and package >= 0 and package + live == whole and live >= 42 else 1)
EOF
```

Expect: exit 0; it prints `not-slow=N package=P live=L` with P + L = N and L >= 42.

**AC7 — The split guards itself.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_live_tree_split.py -q; echo $?
```

Expect: 0; its planted case (a synthetic unmarked module text that walks to the repository root) makes the checker report that module.

**AC8 — The cli module's mypy override names only codes that still fire.**

```bash
grep -A1 'module = "pyforge.mason.cli"' src/shared/packages/pyforge-mason/pyproject.toml | tail -1
```

Expect: prints the `disable_error_code` list the story spec records from one mypy run with that override removed (today `["assignment", "attr-defined"]`; the override is deleted if the run reports neither).

**AC9 — Lint and types.**

```bash
pixi run -e pyforge-guild lint-types; echo $?
```

Expect: 0.

</intent-contract>

## Binding

- Parent: `spec-pyforge-mason`; amends CAP-7.
- Requirements: FR-61 ← CAP-7, spec-pyforge-steward:CAP-175.
- Dream: `docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*.
- Epic 38, `### Story 38.2: Mason's suite runs as a package half and a live-tree half` in `planning-artifacts/epics.md`.
- Wave: BUILD-1 (cutover readiness plan).
- Findings closed: SHOULD: mason tests read A's tree, no live_tree split.

## Notes

- Cross-station: the two task halves are steward:S-124.1, and the `mason_live` job, trigger lists and `ROOT_HANDOFF_INPUTS` re-key are steward:S-124.2; until they land, `pyforge-mason-test` runs both halves in one task and stays green.

## Spec Change Log

- 2026-11-11 (build): the mypy record. `pixi run -e pyforge-guild mypy` was run once with the `pyforge.mason.cli` override removed; mason reported 6 errors in 1 file (checked 23 source files), every other package `ok`:

  ```text
  src/pyforge/mason/cli.py:1335: error: Incompatible types in assignment (expression has type "BuildResult", variable has type "CfeResult")  [assignment]
  src/pyforge/mason/cli.py:1462: error: Incompatible types in assignment (expression has type "ShipTargetResult", variable has type "CfeResult")  [assignment]
  src/pyforge/mason/cli.py:1533: error: Incompatible types in assignment (expression has type "PackageBuildResult", variable has type "CfeResult")  [assignment]
  src/pyforge/mason/cli.py:1571: error: Incompatible types in assignment (expression has type "LockResult", variable has type "CfeResult")  [assignment]
  src/pyforge/mason/cli.py:1628: error: Incompatible types in assignment (expression has type "CheckResult", variable has type "CfeResult")  [assignment]
  src/pyforge/mason/cli.py:1637: error: "CfeResult" has no attribute "stale"  [attr-defined]
  ```

  Both codes still fire, so the override stays `disable_error_code = ["assignment", "attr-defined"]` (AC8).
- 2026-11-11 (build): the out-of-tree run (AC4, before any mark) failed only on the six listed readers, so no further module moved and `live_tree_modules:` is unchanged. One of the six, `unit/test_cfe_rebuild_guard_merges.py`, derived the root at import (`Path(__file__).resolve().parents[6]` at module level), which stops collection of the whole package half outside the repository: pytest imports a module before the `-m` expression deselects it. The derivation moved into `_load_guard()`; the test is unchanged. A marked module must likewise derive the root inside a function, never at import.
- 2026-11-11 (build): `tests/meta/test_live_tree_split.py` reads the syntax tree of every `test_*.py` under `tests/unit` and `tests/meta` and reports an unmarked module that derives the repository root: `Path(__file__)` climbed past the package (`.parents[N]`, a `.parent` chain, `os.path.dirname`, directly or through a variable), an upward walk over `.parents` or a `while` loop on `.parent` from `__file__` or the current directory, or `git rev-parse --show-toplevel`. Planted cases cover each form, marked and unmarked, and five package-local reads that must not be reported. `tests/integration` is outside both halves (its one outside reader is the `slow` delegation-fidelity test).
- 2026-11-11 (build, fix round 1): the split guard also enforces the import rule above. A second check reports a marked module whose import-time code (module-level statements, class bodies, decorators and default argument values; never a function or lambda body) derives the repository root in any of the forms above, because pytest imports a marked module before `-m` deselects it. Planted cases: a marked module deriving at module level, in a class body, in a decorator and in a default value is reported; the same derivation inside a function is not.
- 2026-11-11 (build, fix round 2): the import check also follows helper calls. A call made at import (module level, a class body, a decorator or a default value) to a module-level function of the same module whose body derives the root, directly or through another such function, is reported (`CONTRACT = _repo_root() / "x.md"`, a `parametrize` decorator over `_root() / "docs"`, a helper that walks upward, a helper that calls such a helper). The same helper called only inside a test or a lambda, and a package-local helper called at import, are not. The check does not follow a helper imported from another module, a method, or a call through any other name, so AC4's out-of-tree run stays authoritative for those (said in the module docstring too).
- 2026-11-11 (build, fix round 3): the orchestrator took the second route of round-2 disposition 1 and widened this story's `files_owned` to `meta/test_public_contract.py` (Story 38.1) and `meta/test_cfe_adapter_argv_live.py` (Story 38.3), for this one change only; it lifts § Boundaries' "Never edit" for those two modules and nothing else. Each now derives the repository root only when a test runs, in the shape of `unit/test_cfe_rebuild_guard_merges.py::_load_guard`. `test_public_contract.py`: the module-level `REPO_ROOT`, `CONTRACT`, `MCP_ASGI` and `ASSERTION_CLIENT` became the functions `_repo_root()`, `_contract()`, `_mcp_asgi()` and `_assertion_client()`, called only from `_real_inputs()` and the `contract_text` fixture; `PKG_ROOT` and `PKG_SRC` stay at module level (package-local). `test_cfe_adapter_argv_live.py`: the module-level `_REPO_ROOT` became `_repo_root()`, called inside the four tests; `_HERE` and the `_MASON_SRC` paths stay at module level (package-local). The tests and their assertions are unchanged, both modules keep `pytestmark = pytest.mark.live_tree`, and `live_tree_modules:` is unchanged. Steward's trigger-map scanner (`src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py`, `Scanner`) derives the same reads and handoffs for both modules at HEAD and after the change (three reads for `test_public_contract.py`, none for `test_cfe_adapter_argv_live.py`, no handoff), so the change moves nothing in spec-pyforge-steward:CAP-159's trigger derivation.

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build. Each finding, and what this round did with it:

1. **Major. AC4 is red.** Where: `tests/meta/test_cfe_adapter_argv_live.py:49` (Story 38.3) and `tests/meta/test_public_contract.py:54` (Story 38.1); neither file is in 38.2's `files_owned`. Problem: the package half run from a copy outside the repository exits rc 2 with two collection errors, `_REPO_ROOT = _HERE.parents[6]` (IndexError: 6) and `REPO_ROOT = PKG_ROOT.parents[3]` (IndexError: 3). Both modules carry the `live_tree` mark, but pytest imports a module before `-m` deselects it, so a root derivation at import stops collection of the whole half. 38.2's own diff is clean: the same run with only those two files ignored exits 0. Disposition: reproduced in this round (copy at `/tmp/tmp.Hmn7yCrvGQ`, rc 2, the same two IndexErrors). The fix belongs to Stories 38.1 and 38.3, which must move each derivation into a function or fixture, the way this story moved `unit/test_cfe_rebuild_guard_merges.py`'s into `_load_guard()`. This story does not edit those two files (§ Boundaries, Never). AC4 is re-run unchanged once they land; until then it stays red and is reported red.
2. **Minor. The guard skipped every marked module.** Where: `tests/meta/test_live_tree_split.py`, `unmarked_readers` (`if carries_live_tree_mark(...): continue`). Problem: a marked module that derives the root at import passes the whole in-tree suite (AC3, AC5, AC7) yet breaks the out-of-tree package half, and no CI lane runs the out-of-tree copy, so nothing kept the CAP-7 success claim true for this case. Disposition: fixed in this story (the Spec Change Log entry above). Consequence: until Stories 38.1 and 38.3 move their derivations, the new check reports those two modules, so AC7 and AC3 fail on exactly the condition that fails AC4, and turn green with it.

Round 1 verification (2026-11-11): AC1 prints 1; AC2 exit 0 (marked=8 listed-on-disk=8); AC3 rc 1 (1680 passed, 1 failed: the new import check names `meta/test_cfe_adapter_argv_live.py` line 49 and `meta/test_public_contract.py` line 54, nothing else); AC4 rc 2 (the two IndexErrors above); AC5 rc 0 (73 passed); AC6 exit 0 (`not-slow=1754 package=1681 live=73`); AC7 rc 1 (55 passed, the same one failure; every planted case passes); AC8 prints `disable_error_code = ["assignment", "attr-defined"]`; AC9 rc 0. Control: the AC4 command on a copy with only those two modules removed from the copy exits 0 (1681 passed, 48 deselected), so the rest of the package half, this story's guard included, passes outside the repository.

## Review findings (build, round 2, 2026-11-11)

An independent reviewer failed the round-1 fix. The issues it raised:

1. **Blocker.** Where: `tests/meta/test_public_contract.py:54` (Story 38.1) and `tests/meta/test_cfe_adapter_argv_live.py:49` (Story 38.3). This story's `tests/meta/test_live_tree_split.py::test_no_marked_module_derives_the_repository_root_at_import` surfaces both. Problem: round-1 finding 1 is not fixed, and three of this story's acceptance criteria are red on the current tree. AC4 (the out-of-tree copy) exits rc 2 with two collection errors, `_REPO_ROOT = _HERE.parents[6]` (IndexError: 6) and `REPO_ROOT = PKG_ROOT.parents[3]` (IndexError: 3); `test_public_contract.py` also builds `CONTRACT` and `MCP_ASGI` from `REPO_ROOT` at import. AC3 and AC7 are red because this story's import-time check reports exactly those two lines. The check is correct, but `pyforge-mason-test` runs both halves with `-m "not slow"`, so it is red in the tree and the PR cannot land. Neither sibling story spec carries the obligation, both reviews have finished, and nothing routes the fix to them. This story's own diff is clean: a copy with only those two modules removed exits 0 (1681 passed, 48 deselected). Reviewer's fix: no change to this story's files; the orchestrator routes a fix round to Stories 38.1 and 38.3 (or the operator widens this story's `files_owned`). Each moves its root derivation, and every module-level name built from it, into a function or fixture, in the shape of `unit/test_cfe_rebuild_guard_merges.py::_load_guard`, and never as a module-level call to a helper.
2. **Minor.** Where: `tests/meta/test_live_tree_split.py`, `root_derivations(..., at_import=True)` and `_import_time_nodes`. Problem: the import-time check reads only module-level code, so it misses a marked module that derives the root in a helper and calls that helper at import (`CONTRACT = _repo_root() / 'x.md'`, or a `parametrize` decorator over `_root() / 'docs'`). Both still raise at collection outside the repository, and no CI lane runs the out-of-tree copy. Moving the derivation into a helper while keeping the module-level constant is the likeliest way for 38.1 and 38.3 to fix their modules, and it would turn AC3 and AC7 green while AC4 stays red. Reviewer's fix: follow a module-level or decorator call of a module-local function whose body derives the root, or say in the module docstring and this Spec Change Log that the check does not follow helper calls and AC4 stays authoritative.

Dispositions:

1. **Blocker: not fixable in this story; the reviewer agrees.** Both lines are in modules Stories 38.1 and 38.3 own, which this story never edits (§ Boundaries, Never). Re-checked this round: both derivations are still at import (`test_public_contract.py:52-67` builds `PKG_ROOT`, `REPO_ROOT`, `CONTRACT` and `MCP_ASGI` at module level; `test_cfe_adapter_argv_live.py:48-49` builds `_HERE` and `_REPO_ROOT`). Routing it: the orchestrator sends a fix round to Stories 38.1 and 38.3, or the operator widens this story's `files_owned`. The fix shape is the reviewer's: move the derivation and every name built from it into a function or fixture, never a module-level call to a helper. The extended import check from finding 2 now reports that helper-call shape as well. AC3, AC4 and AC7 stay red until then and are reported red. Once both modules change, AC3, AC4 and AC7 are re-run unchanged, and AC4 is read from the out-of-tree run itself.
2. **Minor: fixed** (Spec Change Log, fix round 2). The import check follows calls to module-local helpers, transitively. The reviewer's two probes, a module-level `CONTRACT = _repo_root() / 'x.md'` and a `parametrize` decorator over `_root() / 'docs'`, are now planted cases and are reported. The limit that remains (an imported helper, a method, any other call form) is written in the module docstring and the Spec Change Log, and AC4 stays authoritative for it.

Round 2 verification (2026-11-11; outputs under the build scratch folder `38.2/r2-*.txt`):

- AC1 prints 1.
- AC2 exit 0 (marked=8, listed-on-disk=8).
- AC3 rc 1: 1687 passed and 1 failed. The failure is `test_no_marked_module_derives_the_repository_root_at_import`, naming only `meta/test_cfe_adapter_argv_live.py` line 49 and `meta/test_public_contract.py` line 54.
- AC4 rc 2 on the copy at `/tmp/tmp.f49abE4RbR`: IndexError: 6 and IndexError: 3, from the same two modules. Control: the same command on a copy with only those two modules removed exits 0 (1688 passed, 48 deselected).
- AC5 rc 0 (73 passed).
- AC6 exit 0 (`not-slow=1761 package=1688 live=73`).
- AC7 rc 1: 62 passed and the same 1 failure. Every planted case passes, including the 7 new ones.
- AC8 prints `disable_error_code = ["assignment", "attr-defined"]`.
- AC9 rc 0.

## Build round 3 (2026-11-11)

Round-2 finding 1 (the blocker) is fixed here, on the widened `files_owned` (Spec Change Log, fix round 3). Verification, every command run unchanged from § Acceptance Criteria (outputs under the build scratch folder `38.2/r3-*.txt`):

- AC1 prints 1.
- AC2 exit 0 (marked=8, listed-on-disk=8), with the system `python3` as written.
- AC3 rc 0: 1693 passed, 73 deselected.
- AC4 rc 0 on the copy at `/tmp/tmp.jVldVEdL5B` (no `.claude/scripts/conda-forge-expert` on any of its parents): 1693 passed, 73 deselected. Read from the out-of-tree run itself; no module was removed from the copy.
- AC5 rc 0: 73 passed, 1693 deselected.
- AC6 exit 0: `not-slow=1766 package=1693 live=73`.
- AC7 rc 0: 63 passed (the import check now reports nothing on the tree; every planted case passes).
- AC8 prints `disable_error_code = ["assignment", "attr-defined"]`.
- AC9 rc 1, and not from this story: every `ruff` lane, every other `ruff-format` lane and every `mypy` lane (`pixi run --frozen -e pyforge-guild mypy`, rc 0) is `ok`, mason and django-mason included; the one red lane on the last run is `ruff-format pyforge-steward` (`src/pyforge/steward/cutover_ledger_check.py`, untracked), a file another story of this wave is writing in the same worktree (an earlier run also showed `ruff-format pyforge-core` red on pyforge-core's untracked `tests/meta/test_public_contract.py`; it is `ok` now). From inside the package, `ruff check` and `ruff format --check` over the two modules this round edited and `tests/meta/test_live_tree_split.py` pass.
- AC9 as written has no `--frozen`, and the wave's path-dependency manifests (this story's `pyproject.toml` among them) no longer match the hashes in `pixi.lock`, so the literal command re-locks: its first run this round rewrote `pixi.lock` (path-dependency hashes, and atlas's dropped bokeh records). Only steward Story 124.3 re-locks, so the file was put back to its HEAD content (`git diff HEAD -- pixi.lock` empty) and AC9 was re-run as `pixi run --frozen -e pyforge-guild lint-types`, which reads the same lanes without re-locking.
