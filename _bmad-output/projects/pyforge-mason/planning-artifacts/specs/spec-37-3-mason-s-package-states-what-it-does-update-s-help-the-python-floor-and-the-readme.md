---
title: "37.3: Mason's package states what it does: update's help, the Python floor and the README"
type: 'fix'
created: '2026-11-10'
status: 'blocked'
blocking_condition: 'forward dependency (2026-11-10): Deps S-38.1 is a later epic; the operator unblocks it once it is done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md
  - src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-05.md
surface:
  - src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/models.py
  - src/shared/packages/pyforge-mason/tests/unit/test_recipe_update_help.py
  - src/shared/packages/pyforge-mason/pixi.toml
  - src/shared/packages/pyforge-mason/README.md
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-38.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** Code text is wrong where the behaviour is right. The operator ruled on 2026-09-14 that `recipe update` keeps writing by default; its verb help still promises a plan in both paths, against its own `--dry-run` line. Decision D6 sets the floor at 3.14 and the package manifest says 3.12 twice, with a `models.py` comment calling 3.12 the floor. The README and the manifest header describe Epics 2 to 4 as future work, and the README offers the MCP face as an equal route to the grammar when it runs no Mason verb (EGM MAS-R-F2, which steward asks mason to fix before the Story 29.5 recompile). No behaviour changes.

**Approach:**
- Only `_RECIPE_UPDATE_HELP` changes in `cli.py`; `recipe.py::update()` and the `--dry-run` flag do not.
- In `models.py` only the comment at :207 changes (`stdlib since 3.11, this package's floor is 3.14`).
- The new test is its own file, `tests/unit/test_recipe_update_help.py`, so `test_cli.py` stays with Story 38.2.
- `pixi.toml`: `[package.host-dependencies]` and `[package.run-dependencies]` `python` read `>=3.14`; the header comment is in the present tense.
- README: present tense; one paragraph that the `POST /stations/mason/mcp` face serves `start_build`, `get_build` and `run_build`, a supervised build stub that runs no Mason verb (MAS-R-F2); one line pointing at the Spec's `contract.md` for the JSON envelope, the ship states and the exit codes (MAS-R-F3, F5, F6; written by Story 38.1, hence the dependency).
- The floor change moves the `depends` strings of the conda_source records in `pixi.lock`, and a cached local pixi false-greens that drift: the lock regeneration is a steward request, and this story never runs `pixi update` or hand-edits the lock.

Ledger key: `37-3-mason-s-package-states-what-it-does-update-s-help-the-python-floor-and-the-readme`.
Ledger status: `blocked` (forward dependency, 2026-11-10; unblocked only with operator confirmation once its later-epic deps are done).
Type / Effort / Deps: fix / S / S-38.1.

### Living CAP citations

- **CAP-2** (its text is amended by Story 37.1), **CAP-5** and **CAP-6**.
- Operator ruling 2026-09-14 (update writes by default); decision D6 (floor 3.14); EGM finding MAS-R-F2.

## Boundaries & Constraints

**Always:**
- Change text only: a help string, one comment, the manifest floor and prose.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change `recipe.py::update()` or the `--dry-run` flag.
- Never run `pixi update` or hand-edit `pixi.lock`.
- Never edit `tests/meta/test_no_recipe_knowledge.py` (Story 38.2 fixes its three `>=3.12` comment lines).
- Never add behaviour or a flag (operator ruling 2026-11-10: no new behaviour and no new kill switch in this PR).
- Never append a `Surface reconcile` line to another Spec's memlog and never run `spec_surface_check.py --write-baseline`: Story 37.4 writes mason's reconcile event, each other Spec's closer writes its own, and doctor Story 58.4 runs every scoped stamp once, after the last edit (cutover readiness plan, integration 2026-11-10).

## Acceptance Criteria

**AC1 — The verb help and the --dry-run help say the same thing.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_recipe_update_help.py -q; echo $?
```

Expect: 0; the test asserts the `recipe update` description names the default write and --dry-run as the plan-only path, and never says the plan is shown in both paths.

**AC2 — The old claim is gone from the source.**

```bash
grep -c 'shows the plan before writing' src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py
```

Expect: prints 0 (grep exits 1); today 1.

**AC3 — The package manifest states the 3.14 floor in both tables.**

```bash
python3 -c "import tomllib,sys; d=tomllib.load(open('src/shared/packages/pyforge-mason/pixi.toml','rb'))['package']; sys.exit(0 if d['host-dependencies']['python']=='>=3.14' and d['run-dependencies']['python']=='>=3.14' else 1)"
```

Expect: exit 0 (exit 1 today).

**AC4 — No source comment calls 3.12 the floor.**

```bash
grep -rn '3\.12' src/shared/packages/pyforge-mason/src/pyforge/mason/models.py; echo $?
```

Expect: no output, then 1.

**AC5 — The README and the manifest header are in the present tense.**

```bash
grep -cE 'land story-by-story|will \*\*wrap\*\*' src/shared/packages/pyforge-mason/README.md src/shared/packages/pyforge-mason/pixi.toml
```

Expect: each file prints 0.

**AC6 — The README says what the MCP face is and points at the contract.**

```bash
grep -cE 'run_build|runs no Mason verb' src/shared/packages/pyforge-mason/README.md; grep -c 'spec-pyforge-mason/contract.md' src/shared/packages/pyforge-mason/README.md
```

Expect: 1 or more, then 1 or more.

**AC7 — Lint, types and the floor check.**

```bash
pixi run -e pyforge-guild lint-types; echo $?; pixi run -e pyforge-guild target-version-check; echo $?
```

Expect: 0 and 0.

**AC8 — The station suite, after steward-station regenerates pixi.lock for the new floor.**

```bash
pixi run --frozen -e pyforge-mason pyforge-mason-test; echo $?
```

Expect: 0.

</intent-contract>

## Binding

- Parent: `spec-pyforge-mason`.
- Requirements: none.
- Dream: `docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*.
- Epic 37, `### Story 37.3: Mason's package states what it does: update's help, the Python floor and the README` in `planning-artifacts/epics.md`.
- Wave: BUILD-2 (cutover readiness plan).
- Findings closed: SHOULD: update writes without the plan its help promises; SHOULD: Python floor; NICE: README future tense.

## Notes

- Cross-station: the `pixi.lock` regeneration for the new floor (steward:S-124.1's request lane).
- `cli.py` and `models.py` are co-governed by `spec-pyforge-core`: the core-kit closer writes that Spec's reconcile line; mason's is Story 37.4's.
- mypy: the `pyforge.mason.cli` override lives in `pyproject.toml`, Story 38.2's file, and 38.2 tightens it.
