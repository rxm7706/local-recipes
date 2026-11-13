---
title: "39.1: The factory-island build is a mason capability, and its error names only what exists"
type: 'fix'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py
  - src/shared/packages/pyforge-mason/tests/unit/test_factory_island.py
surface:
  - src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py
  - src/shared/packages/pyforge-mason/tests/unit/test_factory_island.py
deferred:
  - id: factory-island-docker-build-reports-a-directory-it-never-writes
    summary: "The Docker build of a factory-island recipe builds nothing from the island and reports an island artifact directory the script never wrote: cfe.py runs [interpreter, build-locally.py, config], build-locally.py reads neither factory variable, and cfe.py reports <factory root>/build_artifacts/<config>. Wiring it is a conda-forge-expert change, A-only by operator ruling 2026-11-10, and --docker on a factory path stays as recorded."
    location: src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py:1296
    severity: medium
  - id: ship-and-submit-root-does-not-follow-the-root-of-record
    summary: "Mason's ship and submit root does not follow the root of record, and no test asserts a ship never targets local-recipes: a conda-forge ship and a submit resolve <cfe-root>/recipes/<name> only (package.py:819). Blocked on steward Stories 44.8 and 44.9 (operator ruling 2026-11-10)."
    location: src/shared/packages/pyforge-mason/src/pyforge/mason/package.py:819
    severity: medium
  - id: mason-runtime-capabilities-have-no-kill-switch
    summary: "Mason's runtime capabilities have no kill switch; the 2026-10-26 retrofit skipped mason because its inventory read 7 capabilities (docs/governance/flag-inventory/pyforge-mason.md: CAP rows 7, runtime 0; src/platform/config/flags.json holds no pyforge.mason key). No retrofit switch is added in this change (operator ruling 2026-11-10)."
    location: docs/governance/flag-inventory/pyforge-mason.md
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Steward Story 44.7 wired `mason recipe build factory/recipes/<r>` into the package on 2026-09-13 and no mason capability carried it (memlog only), so a rebuild from Dream, memlog and Spec would not produce it; CAP-36, minted 2026-11-10, carries it now. Two real defects sit in that code, both fixed here: the unresolved-root error tells the user to set `--foundry-root`, a flag that does not exist (audit MUST 4), and the path normalizer treats `../factory/recipes/x`, `/factory/recipes/x` and `..factory/recipes/x` as island paths. The island is wired for the native build only; the Docker path is recorded, not built. Five tests cover the island today and the error branches have none.

**Approach:**
- The message at `resolve.py:314-318` names `MASON_FOUNDRY_ROOT` and the walk marker only; no flag is added (AD-13's six-flag set is closed).
- The normalizer strips one leading `./` instead of `.lstrip("./")` at `resolve.py:262` and `:327`. Not optional: CAP-36's success clause names the rejected shapes.
- `cfe.py` does not change: the Docker artifact directory stays as it is and is recorded as a `deferred:` row (operator ruling 2026-11-10: `--docker` stays as recorded).
- The identifier `factory:missing-island` and the two variable names do not change (Story 38.1's contract lists them). No new exception class and no new subprocess call site.
- `tests/unit/test_factory_island.py` grows to 12 or more tests: the walk, the variable, the unresolved root and its message, the missing lock, the empty slug, the missing recipe, the three rejected path shapes, the native recipe argument and child environment, the unchanged caller mapping, the artifact directory, and exit 1 through `main()` with a fake CFE root.

Ledger key: `39-1-the-factory-island-build-is-a-mason-capability-and-its-error-names-only-what-exists`.
Ledger status: `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **CAP-36** (minted 2026-11-10; FR-58): `mason recipe build` builds a factory-island recipe natively from either root. The mint wrote it at `(ready 2026-11-10)`; Story 37.1 writes `(shipped <day this story's test landed>)`.
- spec-python-foundry-cutover:CAP-4 (Mason's half, steward Story 44.7); AD-1, AD-13.
- `spec-feature-flag-governance` Q1: a fix carries no flag; the kill-switch question is a `deferred:` row (operator ruling 2026-11-10).

## Boundaries & Constraints

**Always:**
- Keep `factory:missing-island` and the two variable names.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never refuse `--docker` on a factory path (new behaviour; the operator kept it as recorded).
- Never read `pyforge.cutover_root`.
- Never edit `cfe.py`.
- Never change behaviour beyond the two defect fixes, and never add a flag (operator ruling 2026-11-10: no new behaviour and no new kill switch in this PR).
- Never append a `Surface reconcile` line to another Spec's memlog and never run `spec_surface_check.py --write-baseline`: Story 37.4 writes mason's reconcile event, each other Spec's closer writes its own, and doctor Story 58.4 runs every scoped stamp once, after the last edit (cutover readiness plan, integration 2026-11-10).

## Acceptance Criteria

**AC1 — The error no longer advertises a flag that does not exist.**

```bash
grep -c -- '--foundry-root' src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py
```

Expect: prints 0 (grep exits 1); today 1.

**AC2 — Only island-relative paths are factory paths.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:src/shared/packages/pyforge-core/src python3 -c "import sys; from pyforge.mason.resolve import is_factory_recipe_path as f; sys.exit(0 if f('factory/recipes/x') and f('./factory/recipes/x') and not f('../factory/recipes/x') and not f('/factory/recipes/x') and not f('..factory/recipes/x') and not f('recipes/x') else 1)"
```

Expect: exit 0 (exit 1 today).

**AC3 — The factory-island tests cover every native branch.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_factory_island.py -q; echo $?
```

Expect: 0, with 12 or more tests (5 today): the walk, the variable, the unresolved root and its message, the missing lock, the empty slug, the missing recipe, the three rejected path shapes, the native recipe argument and child environment, the unchanged caller mapping, the artifact directory, and exit 1 through `main()` with a fake CFE root.

**AC4 — The touched module meets the unit floor.**

```bash
pixi run --frozen -e pyforge-mason pyforge-mason-coverage-gate; echo $?
```

Expect: 0.

**AC5 — The Docker gap, the ship root and the kill switch are recorded, not built.**

```bash
python3 - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-39-1-*.md' 'Docker' 'ship and submit root' 'kill switch' <<'EOF'
"""Exit 0 when a story spec's frontmatter `deferred:` list carries one row for each phrase given (case-
insensitive match in the row's summary). Run from the repo root. argv: story spec path (glob allowed),
then one or more phrases."""
import glob
import sys

import yaml

path = sorted(glob.glob(sys.argv[1]))[0]
text = open(path, encoding="utf-8").read()
fm = yaml.safe_load(text.split("\n---", 1)[0].lstrip("-\n")) or {}
rows = [str(r.get("summary", "")).lower() for r in (fm.get("deferred") or []) if isinstance(r, dict)]
missing = [p for p in sys.argv[2:] if not any(p.lower() in r for r in rows)]
print(f"{path}: deferred rows={len(rows)} missing={missing}")
sys.exit(1 if missing else 0)
EOF
```

Expect: exit 0 once the build has written the three rows listed under Notes into this story spec's `deferred:`: the Docker-island row, the ship-root row and the kill-switch row (exit 1 at mint, where `deferred: []`: the rows are written at build, not at mint, and Story 37.4's intake mints their DW-mason twins).

**AC6 — Lint and types.**

```bash
pixi run -e pyforge-guild lint-types; echo $?
```

Expect: 0.

</intent-contract>

## Binding

- Parent: `spec-pyforge-mason` CAP-36 (minted).
- Requirements: FR-58 ← CAP-36.
- Dream: `docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*.
- Epic 39, `### Story 39.1: The factory-island build is a mason capability, and its error names only what exists` in `planning-artifacts/epics.md`.
- Wave: BUILD-1 (cutover readiness plan).
- Findings closed: MUST 4; PLAN: factory path normalizer over-matches; PLAN: the factory island is native-only; Docker reports an island artifact directory it never writes.

## Notes

- `resolve.py` is co-governed by `spec-pyforge-core`: the core-kit closer writes that Spec's reconcile line; mason's is Story 37.4's.
- The compiled station skill does not mention the island; that is steward's recompile (steward:S-29.5).
- Rows this story writes to its `deferred:` at build (not at mint, so no row sits in frontmatter without a ledger twin; Story 37.4's intake mints each DW-mason twin, and `deferred-work-check` reads the rows as `spec-frontmatter-only-deferral` until then):
  - id `factory-island-docker-build-reports-a-directory-it-never-writes`; severity medium; location `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py:1296`; summary: "The Docker build of a factory-island recipe builds nothing from the island and reports an island artifact directory the script never wrote: cfe.py runs [interpreter, build-locally.py, config], build-locally.py reads neither factory variable, and cfe.py reports <factory root>/build_artifacts/<config>. Wiring it is a conda-forge-expert change, A-only by operator ruling 2026-11-10, and --docker on a factory path stays as recorded."
  - id `ship-and-submit-root-does-not-follow-the-root-of-record`; severity medium; location `src/shared/packages/pyforge-mason/src/pyforge/mason/package.py:819`; summary: "Mason's ship and submit root does not follow the root of record, and no test asserts a ship never targets local-recipes: a conda-forge ship and a submit resolve <cfe-root>/recipes/<name> only (package.py:819). Blocked on steward Stories 44.8 and 44.9 (operator ruling 2026-11-10)."
  - id `mason-runtime-capabilities-have-no-kill-switch`; severity medium; location `docs/governance/flag-inventory/pyforge-mason.md`; summary: "Mason's runtime capabilities have no kill switch; the 2026-10-26 retrofit skipped mason because its inventory read 7 capabilities (docs/governance/flag-inventory/pyforge-mason.md: CAP rows 7, runtime 0; src/platform/config/flags.json holds no pyforge.mason key). No retrofit switch is added in this change (operator ruling 2026-11-10)."

## Gate findings (build, BUILD-1)

- 2026-11-11, `pixi run -e pyforge-guild deferred-work-check` (exit 2): `spec-frontmatter-only-deferral` for this spec's three frontmatter `deferred:` rows (the Docker island build, the ship and submit root, the kill switch), none with a twin in `pyforge-mason/planning-artifacts/deferred-work-ledger.md`. Not fixed here, by plan (Notes above): the mason ledger belongs to Story 37.4 (BUILD-9), whose intake mints each DW-mason twin. The findings stay red at each wave gate until 37.4 lands, unless the orchestrator moves the intake earlier.
