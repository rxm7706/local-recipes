---
title: "103.3: `pyforge-ci` is stdlib-only, as its tasks say"
type: 'fix'
created: '2026-10-14'
status: 'done'
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
  guard on any library, and a guard inside a test on a runtime library, that no CI library task runs; AC4 catches
  the named runtime libraries. It does not police imports of the tools' own libraries, nor a guard inside a test on
  a library outside the runtime list (today `apscheduler`, `DW-scribe-103-3-1`).
- Installing `pyforge-guild` adds time to `scripts-suite`. `lint-types`, `ci-canary` and `copilot-setup-steps` already
  install it.
- (Added at review, 2026-10-17.) `scripts-lib-test` runs serially: `pyforge-guild` has no `pytest-xdist`, and adding it
  would change another environment's packages (AC1/AC2). Measured 56-156 s for its 876 tests (102 s in the review's
  run), and steward's preflight selection makes it an always-on lane in every touched `pr-preflight`, because the
  `scripts-suite` job has no paths filter. That is over CAP-159 FR-32's advisory 60 s single-station budget; the lane
  belongs in the next preflight budget review.
- (Added at review.) The guard test's mirror assertion (every library a library task's files guard imports where the
  task runs) runs in CI for `scripts-lib-test` only, from `pyforge-guild`. Its `pyforge-doctor` half asserts only when
  the file is run in `pyforge-doctor`: the aggregate task's command is Doctor's and lists its two files (Boundaries:
  never edit Doctor's tasks' commands).
- (Added at re-review.) A possible follow-up for that doctor half: a static check that bites in CI, mapping every
  module the aggregate's files guard to a package `[feature.pyforge-doctor.dependencies]` declares. Not built here.
- (Added at re-review.) Two guards no library env can satisfy are pinned, not run: `apscheduler`
  (`DW-scribe-103-3-1`) and `pyforge.warden` (`DW-warden-103-3-1`). Their four tests skip in every `scripts-suite` step
  until their owners act.

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

## Auto Run Result

Status: in-review (implemented by hand on the chain branch `chain-steward-103-3-pyforge-ci-stdlib-2026-10-17`, cut
from `05fed5cb19`; the adversarial review is a separate session)

Summary: `spec-kit` has its own feature, composed right after `python` by the 13 other environments that compose
`python`, and not by `pyforge-ci`; `ruamel.yaml` left the `pyforge-ci` feature. Nothing the definition names imports in
`pyforge-ci`. The 33 `tests/scripts` files that need a library guard it at module level and skip there; 32 run in the
new `scripts-lib-test` (pyforge-guild), the 33rd (`test_detectors_doctor_sources.py`) in the doctor aggregate step.

Files changed:
- `pixi.toml` — `[feature.spec-kit.dependencies]` (the `spec-kit` line unchanged, a comment above it); the 13
  environments compose `spec-kit` after `python`; `ruamel.yaml` out of `[feature.pyforge-ci.dependencies]`; the
  stdlib-only definition in the `pyforge-ci` env comment; the six claims, the `default` env comment and the
  `docs-gen-test` description point to it; new `[feature.guild-tasks.tasks.scripts-lib-test]`; `pr-preflight-lanes`
  gains the leg (after `docs-gen-test`) and its thirteenth-leg paragraph
- `pixi.lock` — `pixi lock` only: 188 lines removed, all in the `pyforge-ci` environment
- `environment.yaml`, `docs/how-to/pixi-tasks.md`, `docs/map.yaml`, `docs/reference/environments.md` — regenerated
- `docs/dreams/pyforge-unifying-strategy.md` — its measured Pixi environment matrix regenerated
  (`pixi_env_matrix.py --update --dream …`: the lock digest, and `pyforge-ci` 146 → 106); see the Spec Change Log
- `docs/reference/library-llms-full.md` — the environment table names the `spec-kit` feature (and `grayskull`'s `crm`,
  which it already composed); the `pyforge-ci` row and the `spec-kit` entry say `pyforge-ci` does not compose it
- `.github/workflows/detectors.yml` — `scripts-suite`: comments, `setup-pixi` installs `pyforge-guild`, third step
  `pixi run --frozen -e pyforge-guild scripts-lib-test`
- `tests/scripts/scripts-lib-test.txt` (new) — the 32 files, one per line, read by pytest as an argument file
- `tests/scripts/test_pyforge_ci_is_stdlib_only.py` (new) — 14 tests, stdlib + pytest
- `tests/scripts/` guards (module-level `pytest.importorskip`, each library the file or its script needs, measured by
  blocking each candidate import in `pyforge-guild` and reading which tests stop passing):
  - added `yaml`: `test_bmad_drift_check_tier3_classify.py`, `test_bmad_loop_baseline_drift_check.py`,
    `test_cfe_rebuild_guard_check.py`, `test_deck_facts.py`, `test_deferred_work_intake.py`,
    `test_deferred_work_promote.py`, `test_fleet_picture_baseline_drift_attention.py`, `test_fleet_picture_ci_pauses.py`,
    `test_fleet_picture_pages_liveness.py`, `test_lint_types_gate.py`, `test_pixi_env_matrix.py`,
    `test_skf_provenance_gap_dispatch.py`, `test_workflow_push_tag_filters.py`, `test_ci_surface_gates.py` (beside its
    `jsonschema`), `test_realization_register_check.py` (beside its `jsonschema`), `test_docs_map_render.py` (beside its
    `jsonschema`); `yaml` + `requests`: `test_build_pixi_mirror.py`; `yaml` + `ruamel.yaml`:
    `test_failure_catalog_check.py`; `yaml` + `packaging`: `test_session_denial_forms.py` (steward's parser needs PyYAML,
    mason's `packaging`); `packaging` beside the existing `jsonschema` + `yaml`: `test_pin_policy_check.py`,
    `test_pin_policy_restore.py`
  - already guarded, no guard change: the six `docs-gen-test` files, `test_flag_gate_check.py`,
    `test_flag_inventory.py`, `test_flag_rule.py` (docstrings corrected: PyYAML no longer "arrives transitively"),
    `test_sbom_laptop_gate.py`, `test_upstream_todos_check.py`
  - `test_detectors_doctor_sources.py` — `_doctor_dispatch` guards `yaml` and `jsonschema` first; docstring;
    `test_apply_verification_verdicts.py` — `pytest.importorskip("yaml")` before its `pyforge.doctor.sources.chain`
    guard, so it skips in either collection order
  - stale docstrings and comments in `test_deferred_work_promote.py`, `test_docs_gen_common.py`,
    `test_docs_map_render.py`, `test_flag_inventory.py`, `test_session_denial_forms.py`; pre-existing E402 / F541 in
    `test_bmad_drift_check_tier3_classify.py`, `test_deck_facts.py`, `test_pin_policy_check.py`,
    `test_fleet_picture_baseline_drift_attention.py`
- `src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py` — `scripts-lib-test` is an always-on lane
  (the `scripts-suite` job has no paths filter)
- Memlogs and scoped stamps: see Verification below

Measurements (linux-64 unless named; exit codes read directly, 2026-10-17):
- AC2: `pixi lock` then `pixi lock --check` 0. `pyforge-ci` loses exactly the spec-kit-only packages and
  `ruamel.yaml` / `ruamel.yaml.clib` and gains nothing: linux-64 146 → 106 (the 40 Intent lists), osx-arm64 135 → 92,
  win-64 130 → 86 (on those two `cffi`, `cryptography`, `pycparser`, and on win-64 `pywin32`, were reachable only through
  `spec-kit`). The other 35 environments: `pixi list --frozen --json -e <env>` before (a `git archive` of `05fed5cb19`)
  and after, compared by name, version and build, identical; the lock's per-environment, per-platform package URLs
  (86 pairs) identical outside the three `pyforge-ci` pairs.
- AC4: `find_spec` of `yaml`, `jsonschema`, `ruamel`, `mcp`, `pydantic`, `httpx`, `openfeature` in `pyforge-ci`: `None`
  for each. `test_pyforge_ci_is_stdlib_only.py`: 14 passed in `pyforge-ci`; 13 passed, 1 skipped (the env assertion)
  in `pyforge-guild`.
- AC5: `pyforge-doctor-scripts-test` in `pyforge-ci` exit 0: 754 passed, 62 skipped, 0 failed, 0 errors. Every guarded
  file skips with `could not import '<module>'` naming its first missing library. Before the guards (the lock change
  alone): 76 failed, 9 errors, 852 passed, 44 skipped, across 33 files, each for want of `yaml`.
- AC6: `scripts-lib-test` in `pyforge-guild` exit 0: 876 passed, 0 skipped. `pyforge-doctor-aggregate-scripts-test`
  in `pyforge-doctor` exit 0: 59 passed, 0 skipped. Doctor's `test_preflight_mirrors_scripts_suite.py` exit 0
  (5 passed).
- AC7: in `pyforge-ci`, `-p no:xdist`, both orders: `test_apply_verification_verdicts.py` skips (`could not import
  'yaml'`), the four dispatch tests skip (`could not import 'yaml'`), the file's other 19 tests pass; exit 0 both ways.
- AC8: baseline `pyforge-doctor-scripts-test` in `pyforge-ci` at `05fed5cb19`: 1618 passed, 28 skipped. After, by
  `--junitxml` node id: step 1 (`pyforge-ci`) 754 passed, step 2 (doctor aggregate) 59, step 3 (`scripts-lib-test`)
  876; every one of the 1618 baseline node ids passes in at least one step (0 lost).
- AC3: `pixi run -e pyforge-steward pyforge steward estate reconcile` exit 3 ("spec-surface-check failed after scoped
  stamps (exit 2)", expected before this story's memlog entries). It regenerated `environment.yaml` (`spec-kit` now
  listed after `truststore`, by feature order), `docs/how-to/pixi-tasks.md`, `docs/map.yaml` and
  `docs/reference/environments.md`; its other generators (library floors, bmad-estate catalog, env matrix,
  `generate-bmad-suite` from the journal's batch) wrote nothing. It did not change `.steward/estate-refresh/2026-10-14.json`
  or `recipes/bmad-suite/recipe.yaml` (Story 103.2 landed). It did append a generic memlog event to
  `spec-pyforge-doctor`, `spec-pyforge-marshal` and `spec-pyforge-unifying-strategy`, `git add` three generated files
  and stamp the baseline: the memlog events and the stamp were reverted, and this story's own entries and stamps
  written last. Its eight `GATING_CHECKS`, run one by one as it runs them: all exit 0. `docs_pixi_tasks.py --check` 0,
  `docs_environments.py --check` 0, `pixi project export conda-environment -e build` byte-identical to
  `environment.yaml`.
- AC10 / station: `pyforge-steward-test` exit 0 (2882 passed, 2 skipped). `pixi run --frozen -e pyforge-guild
  pyforge-station-tests` exit 0: core 2484, testing-kit 95, atlas 2355 + 103, doctor 3785 + 4, herald 2049,
  marshal 13170, mason 1622 + 12, scribe 428, steward 2882, warden 2440 passed, 0 failed. The steward coverage gate
  (`coverage_gates_ci.py --paths-file <staged paths> --suites unit`, `COVERAGE_GATES_STATIONS=steward`, steward env)
  exit 0: no touched steward source module. `lint-types` 0.
- Memlog entries (`uv run _bmad/scripts/memlog.py append`, citing `pyforge-steward:CAP-5`) on the nine Specs
  `spec-surface-check` names: `spec-pixi-candidate-currency`, `spec-pyforge-doctor`, `spec-deck-family-currency`,
  `spec-deck-family-lockstep`, `spec-pyforge-pages`, `spec-pyforge-core`, `spec-pyforge-marshal`,
  `spec-pyforge-steward`, `spec-pyforge-unifying-strategy`; then `git add`, one scoped `--write-baseline --spec` each
  (all exit 0), and `spec-surface-check` exit 0, re-run after the last governed edit.
- Detectors: `detectors-ci` 0; `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`,
  `deferred-work-check`, `ledger-regression-check`, `story-status-check`, `flag-gate-check`,
  `chain-currency-sweep-check`, `tea-playwright-check` 0; `ci_surface_gates.py --check` 0; `llms-full-check` 0;
  `pyforge-deps-test` in `pyforge-ci` 0 (130 passed, 3 skipped). `pixi_env_matrix.py --check` 0 after the regeneration
  (it was the one new `detectors-ci` warning, `pixi-env-matrix-stale`). `pr-preflight` is the orchestrator's to run.

Mutations (AC9 and the guard's other rules), each on a `git archive` copy of the staged tree with `pyforge-ci`'s
interpreter and `PIXI_ENVIRONMENT_NAME=pyforge-ci`, never in the worktree:
- control: 14 passed;
- `spec-kit` back in `[feature.python.dependencies]`: `test_the_composition_keeps_pyforge_ci_stdlib_only` fails;
- `pyforge-ci` composing `spec-kit`: the same test fails;
- `build` composing `python` without `spec-kit`: the same test fails;
- a new `tests/scripts` file with a module-level `pytest.importorskip("yaml")` in no library task:
  `test_every_guarded_file_runs_in_a_library_task` fails (and the two exact-list self-tests);
- `ruamel.yaml` back in the `pyforge-ci` feature: `test_the_composition_keeps_pyforge_ci_stdlib_only` fails;
- `test_deck_facts.py` dropped from `scripts-lib-test.txt`: `test_every_guarded_file_runs_in_a_library_task` fails;
- `scripts-lib-test` listing its files inline in `cmd`: `test_no_detector_maps_to_a_library_task` fails;
- a `yaml` package importable in `pyforge-ci` (a stub on `PYTHONPATH`): `test_no_runtime_library_is_importable_in_pyforge_ci`
  fails;
- `test_deck_facts.py`'s guard replaced by a bare `import yaml`: that file errors at collection in `pyforge-ci`;
- `scripts-lib-test` dropped from `pr-preflight-lanes`' `depends-on`: doctor's
  `test_every_scripts_suite_step_is_a_pr_preflight_leg` fails.

Review pass 1 fixes (2026-10-17, on `40afdc3cf1`; exit codes read directly):
- Files: `tests/scripts/test_pyforge_ci_is_stdlib_only.py` (guard detection rewritten; 27 tests),
  `tests/scripts/scripts-lib-test.txt` (34 files: adds `test_worktree_sweep.py` and the guard test), `pixi.toml`
  (definition and `scripts-lib-test` text only), `docs/how-to/pixi-tasks.md` and `docs/map.yaml` (regenerated), three
  ledger rows (`DW-steward-103-3-2`, `DW-doctor-103-3-1`, `DW-scribe-103-3-1`), nine memlog entries, nine scoped stamps.
- `test_pyforge_ci_is_stdlib_only.py`: 25 passed, 2 skipped in each of `pyforge-ci`, `pyforge-guild` and
  `pyforge-doctor` (each skips the two environment assertions that are not its own; the `pyforge-doctor` run asserts
  the aggregate's half of the mirror).
- `pyforge-doctor-scripts-test` in `pyforge-ci` 0: 765 passed, 64 skipped, 0 failed, 0 errors.
  `pyforge-doctor-aggregate-scripts-test` 0: 59 passed. `scripts-lib-test` 0: 957 passed, 2 skipped (the guard
  test's `pyforge-ci` and `pyforge-doctor` assertions; none for a missing library), 65 s; it now runs
  `test_preserve_refs_flag_states_decorator_contract[on]` / `[off]` (passed). AC8 re-checked: 0 of the 1618 baseline
  node ids lost. The only library skips left in CI are `test_scribe_install_nightly_trigger.py`'s three
  `apscheduler` tests (`DW-scribe-103-3-1`).
- `pyforge-steward-test` 0 (2882 passed, 2 skipped); `lint-types` 0; doctor's `test_preflight_mirrors_scripts_suite.py`
  0 (5 passed); `pyforge-deps-test` 0; `pixi lock --check` 0; `ci_surface_gates.py --check` 0; `llms-full-check` 0;
  `docs_pixi_tasks.py --check` 0 after the regeneration; `docs_environments.py --check` 0; `pixi_env_matrix.py
  --check` 0; the `environment.yaml` export identical. Planning detectors (chain-completeness, dream-chain,
  dreams-hygiene, deferred-work, ledger-regression, story-status, flag-gate, chain-currency-sweep, tea-playwright)
  all 0; `deferred-work-check` reads the three new rows clean.
- Mutations, on a `git archive` copy of the staged tree (controls: 25 passed, 2 skipped in `pyforge-ci` and in
  `pyforge-guild`). Each fails the named test:
  - M1 `spec-kit` back in `python`, M2 `pyforge-ci` composing it, M3 `build` without it, M5 `ruamel.yaml` back in
    the `pyforge-ci` feature: `test_the_composition_keeps_pyforge_ci_stdlib_only`;
  - the review's M3b (a guarded file named only in `docs-gen-test`), M3c (a module-level `yaml` guard in no task), the
    review's M4 (a guard in a module-level `if`), M4b (`from pytest import importorskip`), M4c (a `pytestmark`
    `skipif` on a `try: import yaml` flag), M6 (`test_deck_facts.py` off the list), the review's M8 (a function-level
    `importorskip("openfeature")`), M8b (`test_worktree_sweep.py` off the list), M8c (a test taking `flag_provider`):
    `test_every_guarded_file_runs_in_a_library_task` (plus the exact-list self-tests);
  - M7 (the list inline in `cmd`): `test_no_detector_maps_to_a_library_task`;
  - M9 (the `scripts-lib-test` step removed from `detectors.yml`): `test_every_library_task_is_a_scripts_suite_step_in_its_environment`;
  - M10 (a `yaml` stub importable in `pyforge-ci`): `test_no_runtime_library_is_importable_in_pyforge_ci`;
  - M11 / M11b (`yaml` / `openfeature` blocked in `pyforge-guild`):
    `test_every_module_a_library_task_file_guards_imports_where_the_task_runs[scripts-lib-test]`.

Re-review fixes (2026-10-17, on `570690b7de`; exit codes read directly):
- Files: `tests/scripts/test_pyforge_ci_is_stdlib_only.py` (36 tests), `tests/scripts/scripts-lib-test.txt` (36 files:
  adds `test_bmad_estate_check.py` and `test_exit_code_domains_are_declared.py`), `pixi.toml` (definition and
  `scripts-lib-test` description text only), `docs/how-to/pixi-tasks.md` and `docs/map.yaml` (regenerated), the warden
  ledger (`DW-warden-103-3-1`), nine memlog entries, nine scoped stamps.
- `test_pyforge_ci_is_stdlib_only.py`: 34 passed, 2 skipped in each of `pyforge-ci`, `pyforge-guild` and
  `pyforge-doctor`.
- `pyforge-doctor-scripts-test` in `pyforge-ci` 0: 774 passed, 64 skipped, 0 failed, 0 errors. Aggregate 0: 59 passed.
  `scripts-lib-test` 0: 976 passed, 3 skipped (the pinned warden test, and the guard test's `pyforge-ci` and
  `pyforge-doctor` assertions), 65 s; `test_bmad_estate_check.py`'s five tests and
  `test_doctor_projects_fail_to_2_and_never_uses_1` pass there. AC8: 0 of the 1618 baseline node ids lost.
- Mutations on a `git archive` copy of the staged tree (controls 34 passed, 2 skipped in `pyforge-ci` and
  `pyforge-guild`), each failing the named test:
  - R-M9b (the step commented out) and M9 (removed): `test_every_library_task_is_a_scripts_suite_step_in_its_environment`
    (and `test_a_commented_out_step_reads_as_absent`);
  - R-M14, R-M16, R-M17 (`boto3`), R-M18 (`test_bmad_estate_check.py` off the list), R-M19
    (`test_exit_code_domains_are_declared.py` off the list), R-M20 (the `apscheduler` pin removed), and pass 1's M3b,
    M4, M8: `test_every_guarded_file_runs_in_a_library_task`;
  - R-M21 (the warden pin removed), run in `pyforge-guild` where `scripts-lib-test` runs it: the mirror
    `…[scripts-lib-test]` (in `pyforge-ci` it survives, as the file is covered and the mirror is guild's);
  - R-M22 (the pinned guard gone from its file) and R-M23 (the row's id gone from the definition):
    `test_every_pinned_exception_still_guards_its_library_and_has_its_row`;
  - R-M24 (`_library` exempting every `pyforge.*` again): four tests, among them
    `test_the_live_tree_has_guarded_files_to_check` and `…[a-pyforge-station-package]`;
  - M1, M7, M10, M11 (`yaml` blocked in `pyforge-guild`), M11c (`pyforge.scribe` blocked there): as before.

## Review Triage Log

### 2026-10-17 — Review pass 1 (independent review of `b1270318ed`)
- verdict: FAIL — 1 should-fix, 5 nits; two out-of-surface defects confirmed
- findings:
  - `[should-fix]` `[patch]` `tests/scripts/test_worktree_sweep.py:682` guards `openfeature` inside a test and no library
    task ran the file, so its `flag_states` tests ran nowhere in CI; `test_scribe_install_nightly_trigger.py`'s three
    `apscheduler` tests are the same shape. Fixed: `test_worktree_sweep.py` is listed in `scripts-lib-test.txt`
    (`pyforge-guild` carries `openfeature-sdk`; 56 passed there, 0 skipped). `apscheduler` is in no library env
    (`pyforge-scribe` and `pyforge-foundry-full` only), so the definition names it as the one exception and
    `DW-scribe-103-3-1` records it for scribe. The guard test now flags a guard inside a test on a runtime library
    (`importorskip`, `skipif`, the `flag_provider` / `flag_states` hooks) in a file no library task runs.
  - `[nit]` `[patch]` `LIBRARY_TASKS` counted `docs-gen-test` and `docs-map-render-test`, which no CI step runs. Fixed:
    only `scripts-lib-test` (pyforge-guild) and `pyforge-doctor-aggregate-scripts-test` (pyforge-doctor) count, and a
    test pins each as a `scripts-suite` step in its environment.
  - `[nit]` `[patch]` module-level guard detection missed a guard in a module-level `if` / `try`, `from pytest import
    importorskip`, and a `pytestmark` `skipif`. Fixed: every statement that runs at import is read (module-level
    blocks and class bodies, never function bodies), a `pytest` alias and an imported `importorskip` count, and a
    `pytestmark` `skipif` resolves its library from a `find_spec` / `import_module` string or a `try: import` flag.
  - `[nit]` `[patch]` nothing failed if the library steps all skipped. Fixed: the mirror of the import assertion —
    where each library task runs, every library its files guard imports — and `scripts-lib-test` runs the guard test.
  - `[nit]` `[patch]` `typing_extensions` did not leave `pyforge-ci`. Fixed in the definition; the change-log
    deviation is withdrawn.
  - `[nit]` `[defer]` `scripts-lib-test` runs serially, over CAP-159 FR-32's advisory 60 s. Recorded in Residual risk.
  - `[defer]` (a) `estate_reconcile.py:113-121` passes the Dream path positionally, so the `env-matrix` generator exits
    2 unreported: `DW-steward-103-3-2`. (b) `scripts/detectors.py:166-167` matches a detector to its task by
    substring: `DW-doctor-103-3-1` (no Spec surface governs the file; Doctor's ledger owns the registry's mapping).

### 2026-10-17 — Re-review of `570690b7de`
- verdict: RESOLVED — the six pass-1 findings fixed; five non-blocking nits, the last round
- findings:
  - `[nit]` `[patch]` `_scripts_suite_steps` matched comment lines, so a commented-out step passed (R-M9b). Fixed: only
    a `run:` line counts.
  - `[nit]` `[patch]` two guard shapes went unseen: a module-level `pytest.skip(..., allow_module_level=True)` under an
    ImportError handler (R-M14), and an in-test `find_spec`-then-`pytest.skip` (R-M16). Fixed: a `pytest.skip` reached
    from an ImportError handler, or from an `if` whose condition tests a library, is a guard on that library (module
    level when it passes `allow_module_level=True` at import).
  - `[nit]` `[patch]` the in-test rule covered only the runtime libraries (R-M17, `boto3`). Fixed: a guard on any
    library, in a file no library task runs, reds unless `PINNED_EXCEPTIONS` pins it, and a test keeps each pin
    honest (the file still guards it, the owner's ledger has the row, the definition names it).
  - `[nit]` `[patch]` `_library` exempted every `pyforge.*` package, wider than the definition. Fixed: only the in-repo
    `pyforge.core` and `pyforge.testing_kit` are exempt. `test_bmad_estate_check.py` (its two `pyforge.scribe` tests
    pass in `pyforge-guild`) and `test_exit_code_domains_are_declared.py` (its doctor test runs there) join
    `scripts-lib-test.txt`; `pyforge-guild` has no `pyforge.warden`, so its warden test is pinned against the new
    warden-owned `DW-warden-103-3-1`.
  - `[nit]` `[defer]` the mirror's doctor half never runs in CI: a static check is named as a possible follow-up in
    Residual risk; not built (coordinator's ruling).

## Spec Change Log

- 2026-10-14: minted from `DW-doctor-47-1-1` and the operator's ruling "yes stdlib only" (2026-10-14). `type: fix`,
  no flag, no CAP. Bound to `spec-pyforge-steward` CAP-5.
- 2026-10-17 (implementation, at `05fed5cb19`): drift from `846d8383f5` and deviations, each with its reason.
  - Line drift. The six claims sit at `pixi.toml:651-652`, `:830-832`, `:837`, `:840-847`, `:1624` (was `:1638`) and
    `:3068` (was `:3078`); the `pyforge-ci` env comment at `:1020-1034` (was `:1039-1050`), `pyforge-ci = …` at `:1035`
    (was `:1051`), the `default` env at `:1019` (was `:1035`); `_doctor_dispatch` at
    `tests/scripts/test_detectors_doctor_sources.py:257`. `detectors.yml`'s comments and the
    `test_apply_verification_verdicts.py:31` guard did not move.
  - Count drift. The baseline `pyforge-ci` run passes 1618 tests, not 1554. A 33rd file needs a library:
    `tests/scripts/test_fleet_picture_pages_liveness.py` (doctor Story 48.2, landed after `846d8383f5`). It is guarded
    and listed, so `scripts-lib-test` runs 32 files, not 31. `pyforge-ci`'s package counts match the Intent (146 → 106 on
    linux-64).
  - `scripts-lib-test` reads its files from a pytest argument file, `tests/scripts/scripts-lib-test.txt`
    (`python -m pytest @tests/scripts/scripts-lib-test.txt -q`), not from a list in `cmd`. With the list inline,
    `scripts/detectors.py`'s `discover()`, which maps a detector to the first task whose `cmd` contains its file name,
    mapped six detectors (`bmad_loop_baseline_drift_check`, `cfe_rebuild_guard_check`, `ci_surface_gates`,
    `failure_catalog_check`, `flag_gate_check`, `upstream_todos_check`) to `scripts-lib-test`, because
    `test_flag_gate_check.py` contains `flag_gate_check.py`; `test_flag_gate_check.py`'s registry test caught it.
    `scripts/detectors.py` is outside this story's surface and unchanged; the guard test resolves `@path` arguments
    and gains a fifth rule: no detector maps to a library task.
  - The guards name `requests` (`test_build_pixi_mirror.py`) and `packaging` (`test_session_denial_forms.py`, the two
    pin-policy files) beside PyYAML, because blocking each in `pyforge-guild` fails those tests (AC5: each library the
    file or its script needs). Both stay in `pyforge-ci` through the tools' trees, so those guards do not decide the skip
    there.
  - `test_session_denial_forms.py` skips whole in `pyforge-ci`: one of its 17 tests needs PyYAML (steward's parser) and
    `packaging` (mason's), and AC5 asks for a module-level guard; its 17 tests run in `scripts-lib-test`.
  - (Withdrawn at review, 2026-10-17; the reason was wrong.) The first cut's definition dropped `typing_extensions`
    from what `gitpython` brings, on the reading that `typing-extensions` is one of the 40 packages that leave
    `pyforge-ci`. Only the `typing-extensions` metapackage leaves; `typing_extensions-4.16.0-pyhcf101f3_0` stays, as a
    dependency of `gitpython`, `rich` and `exceptiongroup`, and the module imports in the new env. The definition
    names it again, as the spec's Intent did.
  - `src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py`, outside the Surface line, changes:
    its oracle lists the always-on lanes, and the new `scripts-suite` step makes `scripts-lib-test` one.
  - Healed tissue in touched files: test docstrings that said PyYAML "arrives transitively" in `pyforge-ci`, or that
    called a file stdlib-only, corrected; pre-existing E402 / F541 fixed in four touched test files.
  - AC3's reconcile run exits 3 before this story's memlog entries; see the Auto Run Result for what it wrote and
    what was reverted. `DW-steward-103-3-1` stays open: today the bare run did not rewrite the journal, but it still
    appends a memlog event naming the 2026-10-14 journal, stages generated files and stamps the baseline.
  - `DW-doctor-47-1-1` closes at landing, citing the merge, as Binding says; not edited here.
  - The Dream's measured environment matrix (`docs/dreams/pyforge-unifying-strategy.md`) is regenerated by hand with
    `python scripts/pixi_env_matrix.py --update --dream docs/dreams/pyforge-unifying-strategy.md`: the lock change made
    it stale (`detectors-ci`'s `bmad-drift` warned `pixi-env-matrix-stale`), and `estate reconcile`'s own `env-matrix`
    generator did not rewrite it, because it passes the Dream path positionally
    (`estate_reconcile.py` `_build_generators`), which `pixi_env_matrix.py` refuses with exit 2 ("unrecognized
    arguments"). That generator defect is outside this story's surface and is not fixed here.
- 2026-10-17 (review pass 1 fixes, on `40afdc3cf1`, after merging `origin/main` with marshal 101.1): the Review Triage
  Log's six findings. `tests/scripts/scripts-lib-test.txt` adds `test_worktree_sweep.py` and
  `test_pyforge_ci_is_stdlib_only.py` (34 lines); the guard test reads every guard form, counts only CI-run library
  tasks, flags runtime-library guards inside tests, and asserts the mirror; the `pyforge-ci` definition in
  `pixi.toml` names the `apscheduler` exception and `typing_extensions` again, and the `scripts-lib-test` comment and
  description say what the task now runs; Residual risk records the serial cost and the mirror's doctor half. New
  rows: `DW-steward-103-3-2`, `DW-doctor-103-3-1`, `DW-scribe-103-3-1`. All scoped stamps re-taken after the merge.
  Status stays `in-review`.
- 2026-10-17 (re-review fixes, on `570690b7de`): the Review Triage Log's second pass. The guard test reads only
  `run:` steps, sees a `pytest.skip` reached on a missing library, flags any unpinned library guarded inside a test,
  pins `apscheduler` and `pyforge.warden` with their owners' rows, and exempts only the in-repo core and testing kit;
  `scripts-lib-test.txt` adds `test_bmad_estate_check.py` and `test_exit_code_domains_are_declared.py`; the
  definition in `pixi.toml` names both pinned exceptions and treats the other pyforge station packages as libraries;
  new row `DW-warden-103-3-1`. Status stays `in-review`.
- 2026-10-17 (landing): the second re-review RESOLVED; its nits 1-4 fixed, nit 5 recorded as a follow-up. The orchestrator corrected `test_exit_code_domains_are_declared.py`'s comment, which said the warden test runs in `pyforge-warden` (no CI step does; DW-warden-103-3-1). Status `done`; the ledger key and `epic-103` `done`.
