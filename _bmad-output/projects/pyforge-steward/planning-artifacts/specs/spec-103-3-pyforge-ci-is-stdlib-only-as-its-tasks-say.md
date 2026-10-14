---
title: "103.3: `pyforge-ci` is stdlib-only, as its tasks say"
type: 'fix'
created: '2026-10-14'
status: 'ready-for-dev'
baseline_revision: '846d8383f5b4a1f86cbb09f6fd8ae8616b34950f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-47-1-the-aggregate-scripts-test-checks-scope-filtering-without-gathering.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
  - pixi.toml
  - .github/workflows/detectors.yml
  - tests/scripts/conftest.py
  - tests/scripts/test_detectors_doctor_sources.py
  - tests/scripts/test_apply_verification_verdicts.py
  - src/shared/packages/pyforge-doctor/tests/meta/test_preflight_mirrors_scripts_suite.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/estate_reconcile.py
  - docs/reference/library-llms-full.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** six places in `pixi.toml` say `pyforge-ci` is stdlib-only or carries no runtime library, and it is not.
It composes the `python` feature, whose `spec-kit` pulls in `jsonschema` (through `mcp`), `pyyaml`, `pydantic`,
`httpx` and 33 more packages, and its own feature declares `ruamel.yaml` for one test. So tests built to skip in
`pyforge-ci` run there, and 32 `tests/scripts` files have come to need a library that only `spec-kit` happens to
provide. Operator ruling 2026-10-14, verbatim: "yes stdlib only", answering "should `pyforge-ci` stay stdlib-only?"
with the lean option "move `spec-kit` out of the `python` feature". Line numbers are at `846d8383f5`.

- **The six claims** (`DW-doctor-47-1-1`, `grep -n "carries no runtime\|unavailable in \`pyforge-ci\`\|stdlib-only\|pure stdlib" pixi.toml`):
  `:651-652` (the `pyforge-steward-container-gates-test` comment, "deliberately zero runtime deps"), `:830-832` (the
  `pyforge-deps-test` comment, "carries no runtime libraries at all"), `:837` (its description, "pure stdlib; no
  runtime deps required", true of the check), `:840-847` (the comment and description of
  `pyforge-doctor-scripts-test`), `:1638` (`pr-preflight-lanes`, "jsonschema (unavailable in `pyforge-ci` …)"), and
  `:3078` (`pyforge-doctor-aggregate-scripts-test`, "pyforge-ci, stdlib-only by design"). The env comment above
  `pyforge-ci = …` (`:1039-1050`), the `default` env's comment (`:1035`), `detectors.yml`'s `scripts-suite` comments
  (`:68-75`, `:98-105`) and `_doctor_dispatch`'s docstring (`tests/scripts/test_detectors_doctor_sources.py:258`)
  also describe the composition.
- **The composition.** `pyforge-ci = { features = ["python", "pyforge-ci"] }` (`pixi.toml:1051`). `python`
  (`:35-44`) holds `python`, `pixi`, `gh`, `gitpython`, `nodejs`, `pnpm`, `bmad-method`, `spec-kit` and `truststore`;
  `pyforge-ci` (`:814-822`) holds `hatchling`, `python-build`, `pytest`, `pytest-xdist`, `ruamel.yaml`,
  `pixi-build-python`, `pixi-build-rattler-build` and `twine`. 14 environments compose `python`: `linux`, `osx`,
  `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `pyforge-guild`, `default`, `vuln-db`, `gcloud`,
  `pyforge-ci`, `pyforge-foundry-full` and `pyforge-foundry-full-stack`.
- **Measured, linux-64, from the lock at `846d8383f5`** (`pixi list --frozen -e pyforge-ci`, `pixi tree --frozen -e
  pyforge-ci`):
  - `pyforge-ci` holds 146 packages. 38 are reachable only through `spec-kit`: `annotated-doc`, `annotated-types`,
    `anyio`, `attrs`, `click`, `h11`, `httpcore`, `httpcore2`, `httpx`, `httpx2`, `json5`, `jsonschema`,
    `jsonschema-specifications`, `mcp`, `mcp-types`, `opentelemetry-api`, `platformdirs`, `pydantic`,
    `pydantic-core`, `pyjwt`, `python-dotenv`, `python-multipart`, `pywin32-on-windows`, `pyyaml`, `readchar`,
    `referencing`, `rpds-py`, `shellingham`, `sniffio`, `socksio`, `spec-kit`, `sse-starlette`, `starlette`, `typer`,
    `typing-extensions`, `typing-inspection`, `uvicorn`, `yaml`. Two more, `ruamel.yaml` and `ruamel.yaml.clib`, come
    only from the `pyforge-ci` feature's `ruamel.yaml`.
  - `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts -q -n auto --dist loadgroup`: 1554 passed, 28
    skipped (23 s). `tests/packaging` (`pyforge-deps-test`): 130 passed, 3 skipped.
  - The same run with those 38 import names blocked by a `sitecustomize` finder (which subprocesses inherit): 845
    passed, 73 failed, 9 collection errors, 44 skipped. Every failure and error is `No module named 'yaml'`. The 32
    files that fail, error or newly skip are listed under AC5.
  - Blocking also `ruamel`, `requests`, `git`, `truststore`, `rich`, `cryptography`, `keyring`, `docutils`, `twine`,
    `hatchling` and the rest of the tools' Python libraries changes nothing: 845 passed, the same files fail, and
    `tests/packaging` still passes 130. Outside those 32 files, what `pyforge-ci` runs imports only the stdlib,
    `pytest` and the in-repo `pyforge-core` / `pyforge-testing-kit` sources that `tests/scripts/conftest.py` puts on
    `sys.path`.
  - The 32 files in `pyforge-guild`, serially: 836 passed, 0 skipped, 0 failed (56 s). In `pyforge-doctor` with
    xdist: 789 passed, 1 skipped, 2 collection errors (`test_build_pixi_mirror.py` needs `requests`;
    `test_failure_catalog_check.py` needs `ruamel.yaml`).
- **Doctor's tests in `pyforge-ci` today.** `_doctor_dispatch()` imports `pyforge.doctor.sources.__main__`, which
  imports `yaml` and `jsonschema`; both are there, so the four dispatch tests run in `pyforge-ci` as well as in
  `pyforge-doctor`. `tests/scripts/test_apply_verification_verdicts.py:31` skips only because pytest collects it
  before `test_detectors_doctor_sources.py` puts Doctor's source on `sys.path`.

**What "stdlib-only" means for `pyforge-ci`** (stated once, in the `pyforge-ci` env comment; every other mention
points to it):
- **The code it runs is stdlib-only.** Every test that runs, rather than skips, in `pyforge-ci`'s tasks
  (`pyforge-deps-test`, `pyforge-doctor-scripts-test`) imports only the standard library, `pytest`, and the in-repo
  `pyforge-core` and `pyforge-testing-kit` sources. A `tests/scripts` file that needs any other library skips there,
  and runs in a step whose environment declares it.
- **No runtime library is importable there.** None of the import names `yaml`, `jsonschema`, `ruamel`, `mcp`,
  `pydantic`, `httpx` or `openfeature` (the libraries `pyforge-doctor`'s run-dependencies or a `tests/scripts` guard
  name) can be imported in `pyforge-ci`.
- **What it still carries, each an explicit decision:**
  - the binaries and CLIs of the `python` feature: `python`, `pixi`, `gh`, `nodejs`, `pnpm`, `bmad-method`;
  - `gitpython` (with `gitdb`, `smmap`, `typing_extensions`) and `truststore`, from the `python` feature. Every one of
    the 14 environments composes that feature, no `pyforge-ci` test imports either (measured above), and moving them
    would change 13 other environments' composition for no consumer;
  - its own build, test and upload tools: `hatchling`, `python-build`, `pytest`, `pytest-xdist`, `twine`,
    `pixi-build-python`, `pixi-build-rattler-build`, and the Python libraries they bring (`packaging`, `pluggy`,
    `requests`, `urllib3`, `rich`, `cryptography`, `keyring`, `docutils` and the rest of twine's tree). They are the
    tools the env exists for. A test may not rely on them: `test_build_pixi_mirror.py`, which imports `requests`, also
    needs `yaml`, so it runs in the library step.
- **What leaves, beside `spec-kit`:** `ruamel.yaml`. Its one consumer, `tests/scripts/test_failure_catalog_check.py`,
  also needs `yaml` (through `scripts/failure_catalog_check.py:50`), so it can no longer run in `pyforge-ci`. It runs
  in the library step, and the declaration has no reason to stay.

**Approach:**
- **The composition.** `spec-kit = ">=1.2.0"` moves, line and comment unchanged, from `[feature.python.dependencies]`
  to a new `[feature.spec-kit.dependencies]`. The 13 environments that compose `python`, other than `pyforge-ci`,
  compose `spec-kit` right after it. `ruamel.yaml` leaves `[feature.pyforge-ci.dependencies]`. No version or other
  entry moves. `pixi lock`, never `pixi add` or `pixi update`.
- **The guards.** Each of the 32 files needing a library `pyforge-ci` lacks carries a module-level
  `pytest.importorskip(<module>)` for each library it, or the script it runs, needs. A bare module-level import of
  such a library becomes the guard. So `pyforge-doctor-scripts-test` in `pyforge-ci` collects every file with no error
  and no failure.
- **The library step.** A new `guild-tasks` task, `scripts-lib-test`, runs `pytest` over 31 of those files in
  `pyforge-guild`, the environment that declares every one of their libraries. The 32nd,
  `test_detectors_doctor_sources.py`, stays with `test_apply_verification_verdicts.py` in
  `pyforge-doctor-aggregate-scripts-test`, which already runs both in `pyforge-doctor`.
  - The 31 include the seven files `docs-gen-test` and `docs-map-render-test` run. Those two legs run only in
    `pr-preflight`; in CI the seven files run today only because `pyforge-ci` happens to have `yaml`. Listing them in
    the task keeps CI running them. The two legs stay as they are.
  - The Detectors `scripts-suite` job gains the step `pixi run --frozen -e pyforge-guild scripts-lib-test`, and its
    `setup-pixi` installs `pyforge-guild` beside `pyforge-ci` and `pyforge-doctor`.
  - `pr-preflight-lanes` gains the leg, which doctor's `test_preflight_mirrors_scripts_suite.py` requires.
- **A guard that keeps it true.** A new stdlib-only test, `tests/scripts/test_pyforge_ci_is_stdlib_only.py`, asserts:
  - in `pyforge-ci` (`PIXI_ENVIRONMENT_NAME`), that none of the runtime libraries named above can be imported
    (`importlib.util.find_spec(<name>)` is `None` for each top-level name), and skips elsewhere;
  - from `pixi.toml`, that `[feature.python.dependencies]` has no `spec-kit`, `pyforge-ci` composes no `spec-kit`
    feature, every other environment that composes `python` composes `spec-kit`, and
    `[feature.pyforge-ci.dependencies]` declares exactly the seven tools named above;
  - for every `tests/scripts/test_*.py` with a module-level `pytest.importorskip` of a module outside the stdlib and
    `pyforge`, that a library task (`scripts-lib-test`, `pyforge-doctor-aggregate-scripts-test`, `docs-gen-test` or
    `docs-map-render-test`) names it, and every file those tasks name exists.
- **The descriptions.** The six claims, the two composition comments, the `scripts-suite` comments and
  `_doctor_dispatch`'s docstring say what is true and point to the one definition. `pr-preflight-lanes`' description
  names the new leg. `docs/reference/library-llms-full.md`'s `spec-kit` entry and its environment table name the
  `spec-kit` feature and say `pyforge-ci` does not compose it.
- **The derived surfaces.** `environment.yaml` and the generated docs are regenerated through `pixi run -e
  pyforge-steward pyforge steward estate reconcile`. See Residual risk for what a bare reconcile also does today.

**Rejected:**
- **Change the six descriptions to match the env.** The operator ruled for stdlib-only.
- **A separate `python-ci` feature for `pyforge-ci`.** It would copy eight pins; the env comment's rule is that
  `pyforge-ci` references features by name, never by copied pins.
- **Declare `pyyaml` in the `pyforge-ci` feature.** It keeps 32 files running there by declaring the very library the
  ruling removes, and it would still leave Doctor's verdict-writer test skipping by collection order.
- **Run the whole of `tests/scripts` again in `pyforge-guild` or `pyforge-doctor`.** In `pyforge-doctor` one test,
  `test_detectors_jobs.py::test_jobs_one_matches_parallel_repo_scope`, took 420 s of the full run's 429 s (the whole
  tree takes 23 s in `pyforge-ci`). The library step runs only the files that need it.
- **Move `gitpython` and `truststore` out of `python` too.** No `pyforge-ci` test imports them, and the move would
  recompose 13 environments. They stay, named.

Ledger key: `103-3-pyforge-ci-is-stdlib-only-as-its-tasks-say`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-5: the environment and task registry. Features are composed by
  name and never copied, a task exists in exactly one feature, and back-compatibility comes from environment
  composition (CAP-5's constraint). No steward CAP names `pyforge-ci` (`grep -n pyforge-ci` of steward's `SPEC.md`
  finds none); CAP-5 is the CAP whose rules govern this composition, and it already names the `python` feature in the
  Guild's. This story moves one package between features and keeps every other environment's package set. It mints
  no CAP and changes no `SPEC.md`.
- **Governance.** `pixi.toml` is on seven Specs' surfaces (`spec-pixi-candidate-currency`, `spec-deck-family-currency`,
  `spec-deck-family-lockstep`, `spec-pyforge-pages`, `spec-pyforge-core`, `spec-pyforge-marshal`,
  `spec-pyforge-unifying-strategy`); `pixi.lock` on `spec-pixi-candidate-currency`'s; `environment.yaml` on
  `spec-pyforge-marshal`'s and `spec-pyforge-unifying-strategy`'s; `docs/reference/library-llms-full.md` on
  `spec-pyforge-marshal`'s and `spec-pyforge-steward`'s (`scripts/.spec-surface-baseline.json`).
  Six of the 32 test files (`test_ci_surface_gates.py`, `test_pin_policy_check.py`, `test_pin_policy_restore.py`,
  `test_realization_register_check.py`, `test_sbom_laptop_gate.py`, `test_upstream_todos_check.py`) are on
  `spec-pyforge-steward`'s surface; the other 26, `.github/workflows/detectors.yml` and `tests/scripts/conftest.py`
  are on no Spec's surface.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Origin.** `DW-doctor-47-1-1` (doctor `deferred-work-ledger.md`, owner pyforge-steward), from doctor Story 47.1's
  independent review; operator ruling 2026-10-14 "yes stdlib only"; `docs/dreams/pyforge-steward.md` Realization
  log, 2026-10-14 (CI and estate follow-ups).

## Acceptance Criteria

- **AC1 — The composition.** `spec-kit` sits only in `[feature.spec-kit.dependencies]`, with its line and comment
  unchanged. The 13 environments named above compose `spec-kit` and `pyforge-ci` does not. `ruamel.yaml` is gone from
  `[feature.pyforge-ci.dependencies]`, and no other dependency line in `pixi.toml` changes.
- **AC2 — The lock.** `pixi lock` (never `pixi add` or `pixi update`) leaves `pixi lock --check` exit 0, and:
  - on every platform `pyforge-ci` solves for, its package list loses `spec-kit`, the packages only `spec-kit` brings
    and `ruamel.yaml` / `ruamel.yaml.clib`, and gains nothing (linux-64: the 40 listed under Intent, 146 → 106);
  - every other environment's resolved packages are identical before and after (`pixi list --frozen --json -e <env>`,
    compared by name, version and build, for each environment in `pixi.toml`).
- **AC3 — The derived surfaces.** `pixi run -e pyforge-steward pyforge steward estate reconcile` regenerates
  `environment.yaml` and the generated docs, and its gating checks exit 0 (`llms-full-check`, `pixi-lock-check` and
  the rest of `GATING_CHECKS`). The change commits what it regenerated, and no change to `recipes/bmad-suite/recipe.yaml`
  or `.steward/estate-refresh/2026-10-14.json` (see Residual risk).
- **AC4 — `pyforge-ci` is stdlib-only, as defined.** `pixi run --frozen -e pyforge-ci python -c "<find_spec of each
  of yaml, jsonschema, ruamel, mcp, pydantic, httpx, openfeature>"` prints `None` for each, and
  `tests/scripts/test_pyforge_ci_is_stdlib_only.py` passes in `pyforge-ci` and skips its env assertion elsewhere.
  Its static assertions pass everywhere, and each fails on a mutation (AC9).
- **AC5 — The 32 files skip cleanly in `pyforge-ci`.** `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`
  exits 0 with 0 failed and 0 errors. Each of these files carries a module-level `pytest.importorskip` naming each
  library it or the script it runs needs, and skips there with that reason:
  `test_bmad_drift_check_tier3_classify.py`, `test_bmad_loop_baseline_drift_check.py`, `test_build_pixi_mirror.py`,
  `test_cfe_rebuild_guard_check.py`, `test_ci_surface_gates.py`, `test_deck_facts.py`, `test_deferred_work_intake.py`,
  `test_deferred_work_promote.py`, `test_failure_catalog_check.py`, `test_flag_gate_check.py`,
  `test_flag_inventory.py`, `test_flag_rule.py`, `test_fleet_picture_baseline_drift_attention.py`,
  `test_fleet_picture_ci_pauses.py`, `test_lint_types_gate.py`, `test_pin_policy_check.py`,
  `test_pin_policy_restore.py`, `test_pixi_env_matrix.py`, `test_realization_register_check.py`,
  `test_sbom_laptop_gate.py`, `test_session_denial_forms.py`, `test_skf_provenance_gap_dispatch.py`,
  `test_upstream_todos_check.py`, `test_workflow_push_tag_filters.py`, the six `docs-gen-test` files
  (`test_docs_gen_common.py`, `test_docs_pixi_tasks.py`, `test_docs_environments.py`, `test_docs_detectors.py`,
  `test_docs_skills_catalog.py`, `test_docs_station_cli.py`) and `test_docs_map_render.py`; the 32nd,
  `test_detectors_doctor_sources.py`, keeps its stdlib tests running and skips the four dispatch tests (AC7). A file
  the implementer finds needs no guard after all, because a test needed only a fixture change, is recorded in the
  Auto Run Result with its reason.
- **AC6 — Each runs where its libraries are.** `pixi run --frozen -e pyforge-guild scripts-lib-test` exits 0 with
  0 skipped for a missing library, over every AC5 file except `test_detectors_doctor_sources.py`.
  `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` runs that file and
  `test_apply_verification_verdicts.py` (exit 0, the dispatch tests passing, none skipped). `scripts-suite` in `.github/workflows/detectors.yml` has the step, and its `setup-pixi` installs
  `pyforge-guild`. `pr-preflight-lanes`' `depends-on` names `scripts-lib-test`, and doctor's
  `test_preflight_mirrors_scripts_suite.py` passes.
- **AC7 — Doctor's tests behave as intended in `pyforge-ci`.** In `pyforge-ci`:
  - the four `_doctor_dispatch` tests in `test_detectors_doctor_sources.py` skip, and the reason names `yaml` or
    `jsonschema`; the file's other tests pass;
  - `test_apply_verification_verdicts.py` skips whether it is collected before or after
    `test_detectors_doctor_sources.py` (both orders, run in one process with `-p no:xdist`).
  In `pyforge-doctor`, `pyforge-doctor-aggregate-scripts-test` runs both files and none of their tests skips.
- **AC8 — No test stops running.** Every test node id that passes in `pixi run --frozen -e pyforge-ci
  pyforge-doctor-scripts-test` at `846d8383f5` (1554) passes in at least one of the job's three steps after the change
  (`--junitxml` from each, compared by node id). The Auto Run Result records the three counts and the comparison.
  The `scripts-suite` job passes on the PR.
- **AC9 — The descriptions are true, and so is the guard.** Each of the six claims, the `pyforge-ci` and `default`
  env comments, the `scripts-suite` comments in `detectors.yml` and `_doctor_dispatch`'s docstring reads true against
  the definition, with the definition written once, in the `pyforge-ci` env comment. `docs/reference/library-llms-full.md`
  names the `spec-kit` feature, and `llms-full-check` exits 0. Each mutation fails
  `test_pyforge_ci_is_stdlib_only.py`, and the Auto Run Result records which assertion:
  - `spec-kit` back in `[feature.python.dependencies]`;
  - `pyforge-ci` composing `spec-kit`;
  - an environment that composes `python` without `spec-kit`;
  - a `tests/scripts` file with a module-level `pytest.importorskip("yaml")` named in no library task.
- **AC10 — Green, and the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test` and
  `pixi run -e pyforge-guild pyforge-station-tests` exit 0 (a `pixi.toml` change fires every station suite in CI).
  Every changed governed path gets a surface-reconcile entry on each governing Spec's memlog (the seven `pixi.toml`
  governors, `spec-pixi-candidate-currency` for `pixi.lock`, `environment.yaml`'s and `library-llms-full.md`'s
  governors, `spec-pyforge-steward` for its six test files, `spec-pyforge-doctor` for a regenerated
  `docs/how-to/pixi-tasks.md` or `docs/map.yaml`), then one scoped stamp per Spec, and
  `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Move `spec-kit` by environment composition, never by a copied pin; keep every other environment's package set.
- Guard a library-needing test with `pytest.importorskip` at module level, so a missing library is a skip that names
  it, never a collection error.
- Run every guarded file, unskipped, in a `scripts-suite` step whose environment declares its libraries, and mirror
  that step in `pr-preflight-lanes`.
- Reconcile every governed path the change touches on each governing Spec's memlog, then stamp each scoped (AGENTS.md
  pre-PR item 5). The PR carries the `maintenance` label.

**Never:**
- Never `pixi add`, `pixi update`, `pip` or `conda install`; `pixi lock` only.
- Never move another pin, raise a floor, or touch a `postgresql` / `libpq` pin or a psycopg cap.
- Never weaken or delete a test or assertion to make `pyforge-ci` pass; a test leaves `pyforge-ci` only by its guard.
- Never edit Doctor's sources: Doctor's run-dependencies, `pyforge.doctor.sources` and its tasks' commands stay.
- Never commit an `estate reconcile` change to `recipes/bmad-suite/recipe.yaml` or to an earlier refresh's journal.

**Residual risk:**
- **A bare `estate reconcile` rewrites the latest refresh's journal.** With no `journal_path`, `run_reconcile`
  (`estate_reconcile.py:322`) loads the latest tracked journal, `.steward/estate-refresh/2026-10-14.json`, builds its
  generators from that journal's `moves` (so it runs `generate-bmad-suite`, which resolves the suite from the network
  until Story 103.2 lands), and writes its reconcile block back into that file. The steward CLI passes no journal
  path. AC3's run therefore moves files this story must not commit; restore them, and record the run's summary in the
  Auto Run Result. Recorded as `DW-steward-103-3-1`; not fixed here.
- A library a future `tests/scripts` file imports without a module-level guard, and which only a tool's tree brings
  into `pyforge-ci` (`requests`, `packaging`, `rich`), would still pass there. The guard test catches a module-level
  `importorskip` that no library task names, and AC4 catches the named runtime libraries. It does not police
  imports of the tools' own libraries.
- Installing `pyforge-guild` adds time to `scripts-suite`. `lint-types`, `ci-canary` and `copilot-setup-steps` already
  install it.

## I/O & Edge-Case Matrix

| Situation | Today (`846d8383f5`) | After |
|---|---|---|
| `import yaml` in `pyforge-ci` | succeeds (via `spec-kit`) | `ModuleNotFoundError` |
| `specify --version` in `pyforge-guild`, `local-recipes`, `build` | works | works (the `spec-kit` feature) |
| `test_deck_facts.py` in `pyforge-ci` | runs and passes | skips, "could not import 'yaml'" |
| `test_deck_facts.py` in CI | runs in step 1 | runs in `scripts-lib-test` (`pyforge-guild`) |
| Doctor's dispatch tests in `pyforge-ci` | run (yaml, jsonschema present) | skip, naming the library |
| `test_apply_verification_verdicts.py` in `pyforge-ci` | skips by collection order | skips in either order |
| `test_failure_catalog_check.py` | runs in `pyforge-ci` (yaml via spec-kit, ruamel declared) | runs in `pyforge-guild`; `ruamel.yaml` leaves `pyforge-ci` |
| a new test file with a module-level `importorskip("yaml")` and no library task | skips silently forever | the guard test reds |
| `pixi list -e pyforge-guild` | 13 envs carry `spec-kit` via `python` | the same packages, via `python` + `spec-kit` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-5 (the environment and task registry: features composed by name,
  tasks in one feature). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (CI and estate follow-ups) entry, item 3.
- Epic: Epic 103 (new). Epic 63, which shipped CAP-5's Guild environment, is `done`.
- Ledger key: `103-3-pyforge-ci-is-stdlib-only-as-its-tasks-say`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 103.2 removes one of AC3's hazards (the network-resolved suite) but not the journal rewrite, so
  103.3 does not wait for it.
- Closes: `DW-doctor-47-1-1` (doctor `deferred-work-ledger.md`, owner pyforge-steward); close it citing this story's
  merge. Records: `DW-steward-103-3-1` (steward `deferred-work-ledger.md`), open.
- Spec: the `spec-pyforge-steward` memlog records the operator's ruling, the evidence, the design and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."103"` (added with this mint) covers `pixi.toml`, `pixi.lock`,
  `environment.yaml`, `.github/workflows/detectors.yml`, `tests/scripts/**`, the library catalog and the generated
  docs.
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass. This is the station's
  `verify_commands` (MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: exit 0, 0 failed, 0 errors (AC5, AC7).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` — expected: exit 0, no skip (AC6, AC7).
- `pixi run --frozen -e pyforge-guild scripts-lib-test` — expected: exit 0, no skip for a missing library (AC6).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: exit 0.
- `pixi lock --check` and the per-environment `pixi list --frozen --json` comparison — expected: exit 0, and only `pyforge-ci` changed (AC2).
- The AC8 node-id comparison against `846d8383f5` — expected: no node id lost.
- The AC9 mutations, one at a time — expected: each fails `test_pyforge_ci_is_stdlib_only.py`. Revert each.
- `pixi run -e pyforge-guild pyforge-station-tests` and `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC10).
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Spec Change Log

- 2026-10-14: minted from `DW-doctor-47-1-1` and the operator's ruling "yes stdlib only" (2026-10-14). `type: fix`,
  no flag, no CAP. Bound to `spec-pyforge-steward` CAP-5.
