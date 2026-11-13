---
title: "117.4: The leaf's public surface is written down, and the suite reds what it lacks"
type: 'feature'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a document and a check that judges; nothing a user reaches at runtime (roster flag_exemptions)
difficulty: medium
story: '117.4'
spec: pyforge-core
surface:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/contract.md
  - src/shared/packages/pyforge-core/tests/meta/test_public_contract.py
  - src/shared/packages/pyforge-core/README.md
  - src/shared/packages/pyforge-core/src/pyforge/core/__init__.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-core/src/pyforge/core/
  - src/shared/packages/pyforge-core/README.md
  - src/shared/packages/pyforge-core/pyproject.toml
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D1 of the 2026-11-10 design pass, applied to core as its public Python surface: at `82a2b18828` the Spec covers six of seventeen modules, the README and the package docstring omit most of the rest, and a second root has no list of what stations import.

**Approach:** Realizes spec-pyforge-core:CAP-12 (memlog 2026-11-10, rendered by Story 117.5). No runtime code changes (the `__init__` docstring only). `contract.md` layout, fixed so the checks are exact: `## Modules` with one ``### `pyforge.core.<module>` `` heading each (governed by; public names as backticked identifiers; estate-bound constants where any); `## Environment variables`; `## Feature-flag keys`; `## Exit codes` (dispatch's `EXIT_USAGE` 2 and `EXIT_NOT_FOUND` 127, and the verdict lattice's exit-code domain in `verdict.py`; flags defines none); `## Entry points` (console script `pyforge = pyforge.core.dispatch:main`; group `pyforge.core.hooks`); `## Python floor` (3.14, decision D6); `## Not part of the contract` (underscored names, `__version__`). Public means a top-level name with no leading underscore; no `__all__` is added. Flag keys are string constants shaped `pyforge.<x>` or `pyforge.<x>.<y>`. Estate-bound constants: `LOCAL_DEV_RELATIVE`, `MEASURE_CATALOG_RELATIVE`, `PRESERVE_PURGE_LIST_REL`, `PRE_CONVENTION_RECOVERY_COMMITS`, the `urn:local-recipes:` schema id, dispatch's packages-root arithmetic and `FORGE_SLUGS`. The test reads the Spec folder, so it carries `pytestmark = pytest.mark.live_tree`; the two synthetic-input tests are `test_a_public_name_unlisted_in_the_contract_is_reported` and `test_a_contract_name_missing_from_the_source_is_reported`. Starting map of module to governor, each verified at build: atomic_write spec-pyforge-core:CAP-2; verdict spec-pyforge-core:CAP-3; report spec-pyforge-core:CAP-4; errors spec-pyforge-core:CAP-5; process spec-pyforge-core:CAP-6; dispatch spec-pyforge-unifying-strategy:CAP-5 and spec-pyforge-unifying-strategy:CAP-11; client, assertion and station_port spec-pyforge-unifying-strategy:CAP-6; hooks spec-pyforge-unifying-strategy:CAP-18; flags spec-feature-flag-governance:CAP-5 and spec-feature-flag-governance:CAP-7 with spec-pyforge-unifying-strategy:CAP-13; cutover_root fnd:CAP-8 and spec-pyforge-core:CAP-13; roster spec-pyforge-steward:CAP-137; landing_evidence a spec-pyforge-marshal capability (resolve the number); preserve_refs spec-pyforge-marshal:CAP-287 with spec-pyforge-steward:CAP-165; published_loop (resolve between spec-pyforge-unifying-strategy:CAP-17 and the marshal capability serving `list_loop_story_tasks`); league_measure spec-pyforge-steward:CAP-46, no importer.

Ledger key: `117-4-the-leaf-s-public-surface-is-written-down-and-the-suite-reds-what-it-lacks`. Type / Effort / Deps: feature / M / S-117.1, S-117.2, S-117.3, S-117.5.

## Boundaries & Constraints

**Always:**
- Runs after Stories 117.2 and 117.3, so `root_of_record`, `RootOfRecord`, `forge_slug_for`, `FORGE_SLUGS` and the new `ContentGateReason` member are in the first version.
- The README gains a module table that points at `contract.md`, and the `__init__` docstring stops naming stories.

**Never:**
- No `__all__` is added and no runtime module changes.
- Never type a count of modules or names into the contract or the Spec.
- Never append a `Surface reconcile` line to any Spec's memlog and never run `spec_surface_check.py --write-baseline`: the governed paths go in this spec's `surface:`, Story 117.8 reconciles core and the testing charter, and doctor:S-58.4 stamps once.

## Acceptance Criteria

- **AC1 — Contract and source agree.**

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_public_contract.py -q --strict-markers -p no:cacheprovider
  ```

  Expected: exit 0.

- **AC2 — Both directions are proven on synthetic input.**

  ```bash
  pixi run --frozen -e pyforge-core python -c "import re,subprocess,sys; r=subprocess.run(['pytest','src/shared/packages/pyforge-core/tests/meta/test_public_contract.py','-q','-p','no:cacheprovider','-k','unlisted or missing'],capture_output=True,text=True); m=re.search(r'(\d+) passed',r.stdout); print(r.returncode, m and m.group(1)); sys.exit(r.returncode or not m or int(m.group(1))<2)"
  ```

  Expected: exit 0, at least 2 passed (a public name the contract lacks is reported; a contract name the source lacks is reported).

- **AC3 — One section per module, computed from the source.**

  ```bash
  python3 -c "import re,sys,pathlib; mods={p.stem for p in pathlib.Path('src/shared/packages/pyforge-core/src/pyforge/core').glob('*.py') if p.stem!='__init__'}; t=pathlib.Path('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/contract.md').read_text(encoding='utf-8'); heads=set(re.findall(r'^### \x60pyforge\.core\.(\w+)\x60', t, re.M)); print(sorted(mods-heads), sorted(heads-mods)); sys.exit(mods!=heads)"
  ```

  Expected: exit 0, prints `[] []`.

- **AC4 — Environment variables and flag keys are listed.**

  ```bash
  for k in PYFORGE_FLAGS_PATH PYFORGE_ENVIRONMENT STATION_REMOTE PYFORGE_HOST PYFORGE_IDP_BEARER_FILE PYFORGE_PREFLIGHT_PRESERVE_TAGS_PROOF pyforge.cutover_root pyforge.marshal.front_door_environment; do grep -q "$k" _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/contract.md || echo MISSING $k; done
  ```

  Expected: prints nothing.

- **AC5 — The contract module is a live-tree module.**

  ```bash
  grep -c '^pytestmark = pytest.mark.live_tree$' src/shared/packages/pyforge-core/tests/meta/test_public_contract.py
  ```

  Expected: prints 1.

- **AC6 — README names every module.**

  ```bash
  python3 -c "import pathlib,sys; mods=[p.stem for p in pathlib.Path('src/shared/packages/pyforge-core/src/pyforge/core').glob('*.py') if p.stem!='__init__']; t=pathlib.Path('src/shared/packages/pyforge-core/README.md').read_text(encoding='utf-8'); miss=[m for m in mods if 'pyforge.core.'+m not in t]; print(len(mods), miss); sys.exit(bool(miss))"
  ```

  Expected: exit 0, prints the module count and `[]`.

- **AC7 — The whole core suite still passes as wired.**

  ```bash
  pixi run --frozen -e pyforge-core pyforge-core-test
  ```

  Expected: exit 0.

- **AC8 — Lint and types.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-core` (spec-pyforge-core:CAP-12; memlog 2026-11-10, rendered by Story 117.5); FR-250 <- spec-pyforge-core:CAP-12, written by Story 114.1 after Story 117.5's render; AD-66, AD-68.

- Epic: Epic 117 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 117.4: The leaf's public surface is written down, and the suite reds what it lacks`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Same-project dependencies: Stories 117.1 (the marker), 117.2, 117.3 and 117.5.
- Cross-station: steward:S-124.2 adds `contract.md` to the core live job's paths; warden's `contract.md` points at this file for `PYFORGE_FLAGS_PATH` and `PYFORGE_ENVIRONMENT` (warden's request).
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (core and the testing charter: Story 117.8; marshal: Story 116.5; steward and the host: steward:S-122.5), and doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). Its open Deps (S-117.1, S-117.2, S-117.3 and S-117.5, all in this epic) name no later epic of this station, so the one forward-dependency policy of this PR's mints (a story is minted `blocked` only when its Deps name a later epic) leaves it `backlog`; the integration branch's wave order and marshal's Deps-aware drain hold them. The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-core` came first; `SPEC.md` is rendered by Story 117.5.
