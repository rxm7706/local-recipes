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
