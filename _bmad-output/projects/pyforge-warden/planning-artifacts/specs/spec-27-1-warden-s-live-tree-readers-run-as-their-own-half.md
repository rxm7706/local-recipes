---
title: "27.1: Warden's live-tree readers run as their own half"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a test task split: a CI job and a test task (spec-feature-flag-governance Q1; the roster list), the form doctor Story 55.4 used
difficulty: 'medium'
story: '27.1'
spec: _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
surface:
  - src/shared/packages/pyforge-warden/pyproject.toml
  - src/shared/packages/pyforge-warden/tests/meta/test_station_persona.py
  - src/shared/packages/pyforge-warden/tests/meta/test_skf_domain_skill.py
  - src/shared/packages/pyforge-warden/tests/meta/test_portal_audit_start_get.py
  - src/shared/packages/pyforge-warden/tests/meta/test_engine_version_range_sync.py
  - src/shared/packages/pyforge-warden/tests/meta/test_pixi_range_floor_matches_workspace.py
  - src/shared/packages/pyforge-warden/tests/meta/test_live_tree_marker.py
  - src/shared/packages/pyforge-warden/tests/integration/test_pixi_lock_environment_scope.py
  - src/shared/packages/pyforge-warden/tests/integration/test_fix_solver_real_pixi.py
  - src/shared/packages/pyforge-warden/tests/unit/test_currency.py
  - src/shared/packages/pyforge-warden/tests/unit/test_currency_cfe_parity.py
context:
  - src/shared/packages/pyforge-warden/pyproject.toml
  - src/shared/packages/pyforge-doctor/pyproject.toml
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-55-4-doctor-s-live-tree-readers-run-as-their-own-half.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D2, a relay of `spec-pyforge-steward:CAP-175`. Seven warden test modules read this repository outside the package, so the suite cannot serve a second root as an oracle as it stands; two of them skip when the tree is absent, so the guard they carry cannot fire (the audit's hollow test).

**Approach:** `pyproject.toml`: add the `live_tree` marker beside `slow`, with doctor's wording (`src/shared/packages/pyforge-doctor/pyproject.toml:61-64`). Whole-module `pytestmark = pytest.mark.live_tree` on the three meta modules that read `.claude/skills` and `django-warden`, and on `tests/integration/test_pixi_lock_environment_scope.py`; `test_fix_solver_real_pixi.py` keeps `slow` and gains `live_tree` in its `pytestmark` list. Two modules split so their package-local tests stay in the package half: the readers of `ROOT_PIXI_TOML` in `test_engine_version_range_sync.py` move into the new marked `test_pixi_range_floor_matches_workspace.py`; `test_bundled_registry_matches_the_cfe_canonical_source_when_present` moves from `tests/unit/test_currency.py` into the new marked `tests/unit/test_currency_cfe_parity.py`. In the live-tree half a missing root `pixi.lock` or CFE registry is a failure, not a skip: drop the `skipif` in `test_pixi_lock_environment_scope.py` and the `pytest.skip` in `test_currency.py` (the hollow-guard fix, CAP-18's proof). `test_live_tree_marker.py`: the marker is in `pyproject.toml`; an AST scan of every unmarked module finds no outside read (a path climbed above the package root, a `_repo_root` walker, `changed_paths_since`, a literal naming `.claude/`, `_bmad-output/`, `docs/`, `src/platform`, another package, or the root `pixi.lock` or `pixi.toml`); every marked module has one; a negative test on synthetic source. The modules Stories 26.1, 26.2 and 26.3 add carry the marker and pass this guard. The export check is the oracle proof: a module it fails on that this spec did not list is marked or split here.

For steward's Story 124.1: pytest path `src/shared/packages/pyforge-warden/tests`; today's task is two segments (unit and meta under `--cov=pyforge.warden --cov-branch` writing `.steward/coverage/warden-unit.json`, then the rest with `--ignore` of unit and meta), both `-n auto --dist loadgroup`; coverage target `pyforge.warden`; env `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts`.

Ledger key: `27-1-warden-s-live-tree-readers-run-as-their-own-half`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (relay: each station suite runs as its package-local and live-tree halves); no warden CAP or FR.
- `flag-exempt: detector-or-gate`, the form doctor Story 55.4 used.

## Boundaries & Constraints

**Always:**
- Keep every test's assertion; move a test only to split a reader out of the package half.
- Read every verdict from the exit code, never through a pipe; run the export check with `TMPDIR` on a disk.

**Never:**
- Do not edit `pixi.toml`, a workflow or steward's trigger map (steward Stories 124.1 and 124.2).
- Do not let a live-tree test skip for a missing tree.

</intent-contract>

## Acceptance Criteria

- **AC1 — The marker is registered and every outside reader carries it.** Run from the repo root, verdict from the exit code (never through a pipe):
  `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_live_tree_marker.py -q`
  Expect: exit 0, including a negative test on a synthetic unmarked reader.
- **AC2 — The two halves together collect exactly what the default suite collected, and the live half is not empty.** Run from the repo root, verdict from the exit code (never through a pipe):
  `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden python3 -c "import subprocess,sys;c=lambda m:sum('::' in l for l in subprocess.run([sys.executable,'-m','pytest','src/shared/packages/pyforge-warden/tests','--co','-q','-m',m],capture_output=True,text=True).stdout.splitlines());a,b,t=c('not slow and not live_tree'),c('live_tree and not slow'),c('not slow');print(a,b,t);sys.exit(0 if a+b==t and b>0 and a>0 else 1)"`
  Expect: prints three counts with first + second = third, exit 0.
- **AC3 — The package half passes from an export outside this repository.** Run from the repo root, verdict from the exit code (never through a pipe):
  `bash -c 'set -euo pipefail; E="$(mktemp -d)"; git archive HEAD src/shared/packages/pyforge-warden | tar -x -C "$E"; P="$E/src/shared/packages/pyforge-warden"; PYTHONPATH="$P/src" pixi run --frozen -e pyforge-warden pytest "$P/tests" -c "$P/pyproject.toml" --rootdir "$P" -q -m "not slow and not live_tree" -p no:cacheprovider'`
  Expect: exit 0 (run after committing; TMPDIR on a disk, not tmpfs).
- **AC4 — The live-tree half passes in the repository and skips nothing for a missing tree.** Run from the repo root, verdict from the exit code (never through a pipe):
  `bash -c 'PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "live_tree and not slow" -rs > "${TMPDIR:-/tmp}/warden-live.txt" 2>&1; rc=$?; ! grep -q "not present" "${TMPDIR:-/tmp}/warden-live.txt" && exit $rc'`
  Expect: exit 0.
- **AC5 — Post-condition (Story 124.2 runs it): Cross-unit: steward's trigger map accepts the marked modules and their declared handoffs.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q`
  Expect: exit 0 once steward Stories 124.1 and 124.2 carry the paths and handoffs this story names (shared requests); red before them by design (other units' new reads).
- **AC6 — Station suite and lint.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-warden pyforge-warden-test && pixi run -e pyforge-guild lint-types`
  Expect: exit 0.

## Binding

- Story: `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` § *Story 27.1: Warden's live-tree readers run as their own half*.
- Dream: `docs/dreams/pyforge-warden.md`, Realization log, *2026-11-10 (the cutover readiness audit)*; the operator's rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, second addendum).
- Ledger key: `27-1-warden-s-live-tree-readers-run-as-their-own-half`.
- Deps: —.
- Flag: none (`flag-exempt: detector-or-gate`).
- Cross-station: `steward:S-124.1` (the pixi task halves, the workflow job, the coverage merge) and `steward:S-124.2` (the trigger map). Until they land, `pyforge-warden-test` still collects both halves, so nothing is unrun; AC5 passes once they are on the branch.
