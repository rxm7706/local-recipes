---
title: '95.1: The portal packages and the platform target Python 3.14'
type: 'feature'
created: '2026-10-11'
status: 'done'
followup_review_recommended: false
baseline_revision: 'b4722aeba9e0f476c129d057c150fb0c4fd25294'
flag-exempt: detector-or-gate   # the story changes target-version-check; a gated gate reports a silent green
review_loop_iteration: 0
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-66-1-lint-and-types-gate-the-ten-packages-locally-and-on-the-runners-alike.md
  - scripts/target_version_check.py
  - scripts/lint_types.py
  - src/platform/pyproject.toml
  - src/shared/packages/django-pyforge/pyproject.toml
  - pixi.toml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** everything that runs the nine portal packages and `src/platform` runs Python 3.14, but their
configuration still declares and targets 3.12, so ruff and mypy hold the code to an interpreter nothing uses, and no
check notices. Line numbers below are at `e4ab638bb6`; Story 93.1's tables are described as its spec writes them.

- **The interpreter is 3.14 everywhere.** `pixi.toml` pins `[feature.python.dependencies] python = ">=3.14.7,3.14.*"`
  (:36), and every one of the 36 environments in `pixi.lock` resolves Python 3.14.7 on every platform it lists. See
  *Verification of the runtime* below.
- **The configuration says 3.12.**
  - The nine `src/shared/packages/django-*/pyproject.toml` declare `requires-python = ">=3.12"` (:9 in each).
  - Story 93.1 gives each of them a `[tool.ruff]` table with `target-version = "py312"`, chosen to match that floor
    (its AC2).
  - `src/platform/pyproject.toml` keeps `[tool.mypy] python_version = "3.12"` (:47) and `[tool.ruff]
    target-version = "py312"` (:138).
  - `src/platform/.python-version` says `3.12`, `src/platform/.pre-commit-config.yaml` sets
    `default_language_version: python: python3.12` (:6), `src/platform/.readthedocs.yml` sets `python: '3.12'` (:11),
    and `src/platform/ingest/github_projects/README.md` says the dlt environment is Python 3.12 (:12).
  - `AGENTS.md`'s *Lint and types* line says `src/platform` "keeps its own `platform-ci` lane (py312 target)".
- **No check covers them.** `scripts/target_version_check.py` (Story 66.1, CAP-153) reads only
  `src/shared/packages/pyforge-*` (:64) and checks `[tool.ruff] target-version` and `[tool.mypy] python_version`
  against the pin (:40-:56). It never reads a `requires-python`, a portal package or `src/platform`.

**Why the targets were 3.12, and why that no longer holds:**
- `src/platform/pyproject.toml`'s `py312` and `3.12` came with Story 10.1's render (`4febffd7bf`, 2026-08-14). The
  portal packages' `>=3.12` came with them (`92365511b1` django-pyforge and `2641d098c2` the seven portal shells,
  2026-08-24).
- At the time, `spec-python-agent-platform`'s pap:AD-8 pinned the platform environment to `python = "3.12.*"`:
  "py3.12 env-scoped now, 3.14 as a release gate ... the pin flips to 3.14 the release after the langflow-base
  `bcrypt ==4.0.1` prerequisite clears (release gate, not entry gate)". The steward spine's stack table recorded
  "`3.12.*` today; **`3.14.*` target** (canopy:AD-23; flip in steward 43.6 after Mason 13.1 / 13.2)".
- Story 43.6 ("Platform image moves to Python 3.14") flipped the environment; the PRD's 2026-09-09 currency note
  records the floor `3.12.*` → `3.14.*` ("43.6 shipped 2026-09-03"). The targets were not raised with it. Story 66.1
  (2026-09-20) left "`src/platform`'s own `platform-ci` lane unchanged", and AGENTS.md has called it "(py312 target)"
  since.
- Story 93.1 (chained 2026-10-11) picked `py312` for the portal tables because "at `py314` the formatter rewrites
  `except (A, B):` to `except A, B:` (PEP 758), a SyntaxError on Python 3.12 and 3.13, which the packages declare they
  support". The operator's ask quotes that reasoning: "can we add a story to update to python 3.14 - configuration
  targets Python 3.12 on purpose: targeting 3.14 makes ruff".
- That reason holds only while some runtime is older than 3.14. None is (below), and this story raises the declared
  floors with the targets, so nothing still claims 3.12 or 3.13 support.

**Verification of the runtime** (2026-10-11, `e4ab638bb6`; nothing below 3.14 runs this code):
- **Environments.** All 36 environments in `pixi.lock` resolve `python-3.14.7` on each listed platform, including
  `platform-ci-test`, `platform-dev`, `python-agent-platform`, `dbgpt-sidecar`, `mcp-host`, `pyforge-container`,
  `pyforge-steward` and `pyforge-foundry-full(-stack)`. The portal packages reach an environment only through
  `PYTHONPATH` (`mcp-host-serve`, the portal wrapper contract task) or pytest's `pythonpath` (`src/platform`), never as
  a pip or conda install.
- **Images.** `src/platform/Containerfile` builds `python-agent-platform` (and `pyforge-steward` for its build gate),
  `compose/dbgpt/Containerfile` builds `dbgpt-sidecar`, `compose/mcp-host/Containerfile` builds `mcp-host`, and the root
  `Containerfile` builds `pyforge-container`, each with `pixi install --frozen`. Each runtime entrypoint sources the
  environment's shell hook, so the UBI9 system python never runs platform code.
- **Workflows.** `platform-ci.yml` runs on `platform-ci-test`; `platform-deploy.yml` on `platform-dev`. Every
  `actions/setup-python` in `.github/workflows` is `3.14`, and none of those jobs runs `src/platform` or a portal
  package (`pyforge-pip-install.yml` pip-installs `pyforge-core` and `pyforge-steward` only).
- **Recipes.** The only pyforge recipe, `recipes/pyforge-estate-catalog`, is `noarch: generic` catalog data with no
  portal or platform code.
- **Readers of `requires-python`.** None reads the portal packages' floor today; pip would, and nothing pip-installs
  them.
- **3.12 residue no lane runs.** `src/platform/.python-version`, `src/platform/.pre-commit-config.yaml` (the root
  `.pre-commit-config.yaml` is the one `steward setup` installs) and `src/platform/.readthedocs.yml` (Read the Docs reads
  only a root config, and this one installs `requirements/local.txt`, retired by Story 16.1). The ingest README line is
  stale: `python-agent-platform` resolves 3.14.7 with `dlt` 1.30.0.

**What ruff and mypy then produce** (measured 2026-10-11 on `e4ab638bb6`, ruff 0.16.9 and mypy 2.3.1, read-only; the
portal tables simulated with 93.1's AC2 table through `--config`):
- **Portal packages.** `ruff check` reports the same 64 findings at `py312` and `py314`. `ruff format` at `py314`
  differs from `py312` by exactly 13 PEP 758 rewrites in nine files; handlers with an `as` clause keep their
  parentheses:
  - `django-doctor`: `src/django_doctor_portal/pulse.py:58`;
  - `django-mason`: `src/django_mason_portal/apps.py:37`;
  - `django-pyforge`: `src/django_pyforge/assertion/jwks.py:102`, `assertion/middleware.py:53`,
    `assertion/views.py:42`, `celery_probes.py:36` and `:46`, `mcp_dual_era.py:140`, `:154` and `:174`,
    `queues.py:159`, `rate_limit.py:151` and `:275`.
- **`src/platform`.** At `py314`:
  - `ruff format` rewrites four sites: `tests/test_circuits_trip_on_async_too.py:47`,
    `tests/test_object_storage_client.py:52`, `tests/test_object_store_seam.py:85` and
    `tests/test_openfeature_file_flags.py:143`.
  - `ruff check` reports 11 findings. One has a safe fix: UP035 at `platformapp/front_door/celery_task_backend.py:14`
    (`ParamSpec` from `typing`).
  - The other ten are TC001, TC002 and TC003: imports used only in annotations, which 3.14 evaluates lazily. ruff marks
    their fix unsafe. They are at `config/settings/base.py:8` and `:14`, `platformapp/conftest.py:3`,
    `platformapp/users/tests/factories.py:1`, `platformapp/users/tests/test_forms.py:6`, `test_models.py:1`,
    `test_urls.py:4`, `test_views.py:11` and `:15`, and `platformapp/users/views.py:3`.
  - `mypy platformapp config tests --python-version 3.14` finds no issue in 185 files, as at 3.12.
  - pytest 9.1.1 collects a fixture whose annotation names a `TYPE_CHECKING`-only import.

**Approach:** raise the floors and the targets together, read every target from the one pin, and apply only what the
new target changes.
- **Floors and targets.**
  - The nine portal packages get `requires-python = ">=3.14"` and `target-version = "py314"` in their 93.1 tables.
    Nothing else in those tables changes.
  - `src/platform` gets ruff `target-version = "py314"` and mypy `python_version = "3.14"`.
- **One check, three surfaces.** `target_version_check.py` keeps its pin parsing and its exit domain (0 clean, 1 drift,
  2 could-not-run) and reads three surfaces. Every expected value comes from the pin:
  - the ten `pyforge-*` packages, as today: `[tool.ruff] target-version` and `[tool.mypy] python_version`;
  - the nine `django-*` packages: `[tool.ruff] target-version`. No `[tool.mypy]` is required, because 93.1 keeps mypy
    over `pyforge-*` only. A package without `[tool.ruff]` is a finding;
  - `src/platform/pyproject.toml`: `[tool.ruff] target-version` and `[tool.mypy] python_version`;
  - and, for every package that has a `[project]` table (all nineteen), the lower bound of `requires-python` must be
    the pinned minor. `src/platform` has no `[project]` table and is not asked for one.
  Fewer than ten `pyforge-*` or nine `django-*` packages, or no `src/platform/pyproject.toml`, is could-not-run.
- **The code the new target changes.**
  - `src/platform` takes everything ruff produces at `py314`: the four rewrites, the UP035 fix, and the ten imports
    moved under `if TYPE_CHECKING:`, each site reviewed.
  - The portal packages take only the 13 PEP 758 rewrites. Their other findings belong to each station's own fix
    story under the 2026-10-11 ruling "Gate all, clean herald (Recommended)", so 93.1's `NOT_YET_CLEAN` does not
    change. The rewrites clean no listed package, and `django-doctor` and `django-mason`, which are not listed for
    `ruff-format`, stay format-clean.
- **Stale lines.**
  - The 3.12 residue in `src/platform` becomes 3.14: `.python-version`, `.pre-commit-config.yaml`'s
    `default_language_version` and `.readthedocs.yml`'s `python`. The ingest README names `python-agent-platform` on
    3.14.
  - AGENTS.md's "(py312 target)", any 93.1 comment or test that says the portal tables target `py312` or why,
    `target_version_check.py`'s docstring, and the `target-version-check` task description in `pixi.toml` say what is
    now true.
- **Rejected:**
  - keeping `py312` (it holds the code to a runtime nothing uses);
  - running `ruff format` and `ruff check --fix` over the whole portal trees (it would do the stations' fix stories and
    empty the not-yet-clean list);
  - one requires-python floor for `src/platform` (it is not a package and has no `[project]` table);
  - deleting the dead `src/platform` residue files (out of scope; this story only stops them naming 3.12).

Ledger key: `95-1-the-portal-packages-and-the-platform-target-python-3-14`.
Type / Effort / Deps: feature / M / S-93.1.

### Living CAP citations

- **`spec-pyforge-steward` CAP-153** (lint and types gate the ten `pyforge-*` packages, locally and on the runners
  alike). Its intent names "a target-version registry check (like `pixi-version-check`) [that] reds a package whose
  target drifts from the interpreter". Story 66.1 built that check for the ten packages, and Story 93.1 brings the
  portal packages under the same gate. This story extends the check to them and to `src/platform` and moves their
  targets to the interpreter, so it adds no capability and mints no CAP. CAP-153's success clause, "`src/platform`'s
  own `platform-ci` lane unchanged", still holds: the lane's workflow and `platform-ci-local` do not change, only the
  targets they read.
- **pap:CAP-5** (one environment, factory-sourced, 3.14-bound) and **pap:AD-8**: the platform environment's 3.14 gate,
  flipped by Story 43.6. This story brings the platform's lint and type targets into line with it.
- **Flag:** `flag-exempt: detector-or-gate` (`docs/governance/guild-roster.json` `flag_exemptions`): the story changes a
  gate.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-11 (Python 3.14 floor for the portal packages
  and the platform). The operator's ask, verbatim: "can we add a story to update to python 3.14 - configuration
  targets Python 3.12 on purpose: targeting 3.14 makes ruff".

## Acceptance Criteria

- **AC1 — The floors.** Each of the nine `src/shared/packages/django-*/pyproject.toml` declares
  `requires-python = ">=3.14"`. No other `[project]` key changes.
- **AC2 — The targets.** Each portal package's `[tool.ruff]` table (93.1's AC2) has `target-version = "py314"` and is
  otherwise unchanged. `src/platform/pyproject.toml` has `[tool.ruff] target-version = "py314"` and `[tool.mypy]
  python_version = "3.14"`. The ten `pyforge-*` tables do not change.
- **AC3 — The check covers three surfaces, from the pin.** `python scripts/target_version_check.py`:
  - reads the minor from `pixi.toml`'s `[feature.python.dependencies] python` once, as today;
  - for the ten `pyforge-*` packages, checks ruff and mypy targets as today;
  - for the nine `django-*` packages, checks `[tool.ruff] target-version`, and reports a package with no `[tool.ruff]`
    table as a finding;
  - for `src/platform/pyproject.toml`, checks `[tool.ruff] target-version` and `[tool.mypy] python_version`;
  - for every package with a `[project]` table, checks that `requires-python`'s lower bound is the pinned minor, and
    reports a missing `requires-python` as a finding;
  - prints one drift line per finding, naming the package (or `src/platform`) and the key, and exits 1 on any finding;
  - exits 2, before checking anything, when the pin is unparseable, when fewer than ten `pyforge-*` or nine
    `django-*` packages exist, or when `src/platform/pyproject.toml` is missing;
  - exits 0 on the story's tree, and its ok line names the counts of all three surfaces.
- **AC4 — The code the new target changes.**
  - `src/platform`: `ruff check .` and `ruff format --check .` exit 0 at `py314`. The four PEP 758 rewrites, the UP035
    fix and the ten imports moved under `if TYPE_CHECKING:` are the only code changes. If a moved import turns out to
    be needed at runtime, it stays where it is with a `# noqa: TC00x` that says why, and the Auto Run Result names
    it.
  - The portal packages: the 13 PEP 758 rewrites listed under Intent are the only source changes under
    `src/shared/packages/django-*/src`. No test, other line or `noqa` changes.
  - 93.1's `NOT_YET_CLEAN` is unchanged, and `lint-types` reports each listed package exactly as before.
- **AC5 — The stale lines.**
  - `src/platform/.python-version` reads `3.14`, `.pre-commit-config.yaml`'s `default_language_version` is
    `python3.14`, and `.readthedocs.yml`'s `build.tools.python` is `'3.14'`.
  - The ingest README's environment line names `python-agent-platform` without the 3.12 claim.
  - AGENTS.md's *Lint and types* line no longer says `py312`.
  - The `target-version-check` description in `pixi.toml`, and `docs/how-to/pixi-tasks.md` regenerated from it, name
    the three surfaces. `environment.yaml` is regenerated and is expected unchanged.
  - Any comment or test from Story 93.1 that says the portal tables target `py312`, or explains why, says `py314`.
  - The AC5 grep under Verification finds nothing. On `e4ab638bb6` it finds exactly the fifteen lines this AC and AC1
    and AC2 change; with 93.1 landed, the nine `py312` table lines too.
- **AC6 — The gates are green.** On the story's tree, each of these exits 0:
  - `pixi run --frozen -e pyforge-guild lint-types`, which includes `target-version-check`;
  - `pixi run -e pyforge-guild platform-ci-local -- --test`, including its Ruff, Ruff format and mypy steps;
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test`;
  - `pixi run --frozen -e pyforge-guild pyforge-station-tests`, because `pixi.toml` changes.
- **AC7 — Tests that can fail.**
  - New unit tests in `src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py` load
    `scripts/target_version_check.py` by path and drive `main()` over a temporary repo root holding a `pixi.toml` pin,
    ten `pyforge-*` packages, nine `django-*` packages and `src/platform/pyproject.toml`.
  - They cover every AC3 row: clean; a portal target at `py312`; a portal `requires-python` at `>=3.12`; a portal
    package with no `[tool.ruff]`; `src/platform` ruff at `py312`; `src/platform` mypy at `3.12`; a `pyforge-*`
    `requires-python` below the pin; eight portal packages; no `src/platform/pyproject.toml`.
  - With the pin moved to `3.15` in the temporary `pixi.toml`, every expected value moves to `py315` / `3.15` / `>=3.15`.
  - `tests/scripts/test_lint_types_gate.py::test_live_tree_targets_match_the_interpreter` and 93.1's
    `tests/meta/test_lint_types_django_tables.py` pass, the latter expecting `py314`.
  - Each of these mutations fails a named test: dropping the `django-*` glob; dropping the `src/platform` check;
    hard-coding `py314`; removing the `requires-python` check. Each is reverted afterwards, and the Auto Run Result
    names the test each one failed.
- **AC8 — The surface is reconciled.** Every Spec `spec-surface-check` names gets a memlog entry naming its paths and
  this story, and one scoped stamp each, and `spec-surface-check` exits 0. Expected (the detector's own list wins):
  - `spec-pyforge-steward`: `scripts/target_version_check.py` and steward's tests;
  - `spec-pyforge-unifying-strategy`: the nine `pyproject.toml` files, the nine portal source files and the
    `src/platform` files;
  - `spec-pyforge-scribe`: `AGENTS.md`;
  - `spec-pyforge-doctor`: `docs/how-to/pixi-tasks.md` and `docs/map.yaml`;
  - every governor of `pixi.toml`.

## Boundaries & Constraints

**Always:**
- Derive every expected target and floor from `pixi.toml`'s pin; never write `py314` or `3.14` into the check.
- Keep the check's exit domain and its single pin read.
- Keep the portal packages' source diff to the 13 PEP 758 rewrites.

**Ask First:**
- Any change to `NOT_YET_CLEAN`, to a portal table other than `target-version`, to the ten `pyforge-*` tables, or to
  `mypy`'s scope.
- A moved `TYPE_CHECKING` import that breaks a test and needs more than a `noqa` to keep it at runtime.

**Never:**
- Never run `ruff format` or `ruff check --fix` over a whole portal package, and never fix a portal finding other than
  the 13 rewrites.
- Never change the platform environments, `pixi.lock`, the images, the `platform-ci` workflow or `platform-ci-local`.
- Never lower a floor or a target, and never add a dependency.

**Residual risk:**
- A future story that needs a pre-3.14 runtime for a portal package or the platform (a pip install outside pixi, an
  older image base) now meets `requires-python = ">=3.14"` and 3.14-only syntax. This story records the check that
  nothing does today.
- Moving annotation-only imports under `TYPE_CHECKING` relies on 3.14's lazy annotations. A library that evaluates
  annotations at runtime would raise `NameError`; the platform suite is the proof that none does on these ten sites.
- `CAP-153`'s `SPEC.md` text keeps saying "the ten `pyforge-*` packages" until a later `bmad-spec` pass folds a dated
  clause, as after 93.1.

## I/O & Edge-Case Matrix

| Situation | Today (`e4ab638bb6` + 93.1) | After |
|---|---|---|
| a portal package's `requires-python` is `>=3.12` | unchecked | drift, exit 1 |
| a portal table targets `py312` | unchecked | drift, exit 1 |
| a portal package has no `[tool.ruff]` | unchecked by this check (93.1's lint gate reports it) | drift, exit 1 |
| `src/platform` ruff `py312` or mypy `3.12` | unchecked | drift, exit 1 |
| a `pyforge-*` `requires-python` below the pin | unchecked | drift, exit 1 |
| `src/platform/pyproject.toml` missing, or fewer than nine portal packages | n/a | could-not-run, exit 2 |
| the pin moves to 3.15 | the ten `pyforge-*` drift | every surface drifts until raised |
| `ruff format --check` on a portal package at `py314` | 13 `except` sites would change | already applied |
| `ruff check .` in `src/platform` at `py314` | 11 findings | 0 |
| `NOT_YET_CLEAN` | 93.1's seed | unchanged |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-153, as built by Story 66.1 and extended by Story 93.1; pap:CAP-5
  for the platform environment. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-11 (Python 3.14 floor for the portal packages
  and the platform) entry.
- Epic: Epic 95 (new). Epic 66, which built the check, is `done`, so this story opens its own epic. `epic-95` and
  `epic-95-retrospective` are minted with it.
- Ledger key: `95-1-the-portal-packages-and-the-platform-target-python-3-14`.
- Ledger status at mint: `backlog`.
- Deps: S-93.1 (`93-1-the-lint-gate-covers-the-nine-django-portal-packages-and-its-not-yet-clean-list-only-shrinks`,
  station-local). This story edits 93.1's tables, its not-yet-clean list's surroundings and its meta test, so it is
  held until 93.1 is `done`.
- Spec: the `spec-pyforge-steward` memlog records the ask verbatim, the runtime verification, the rationale and design,
  and this mint; the `spec-pyforge-unifying-strategy` memlog records the incoming surface claim on its files.
- Surface: `marshal-policy.toml` `[epic_surfaces]."95"` (added with this mint) admits the paths this story names.
- Minted 2026-10-11 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass, with the new unit tests (the station's `verify_commands`; MRS-GATE-010 binding). The dispatch also runs `platform-ci-local -- --test` as its cross-surface check (MRS-GATE-015) because the diff touches `src/platform/`.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0, read from the exit code (AC3, AC4, AC6).
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0 (AC4, AC6).
- From `src/platform`: `ruff check .` and `ruff format --check .` with platform-ci-test's ruff — expected: exit 0 at `py314` (AC4).
- `git diff origin/main...HEAD -- 'src/shared/packages/django-*/src'` — expected: the 13 `except` lines and nothing else (AC4).
- The four AC7 mutations — expected: each fails its named test. Revert each.
- The AC5 grep, from the repo root: `grep -rn -E 'py312|python_version = "3.12"|>=3.12|python3\.12|3\.12' --include='*.toml' --include='*.yaml' --include='*.yml' --include='.python-version' --include='*.md' src/platform src/shared/packages/django-*` — expected: exit 1, no match.
- `pixi run --frozen -e pyforge-guild docs-pixi-tasks -- --check` — expected: exit 0 after the regeneration (AC5).
- `pixi project export conda-environment -e build > environment.yaml`, then `git diff --exit-code environment.yaml` — expected: no diff.
- `pixi run --frozen -e pyforge-guild pyforge-station-tests` — expected: pass (AC6).
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC8).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Review Triage Log

### 2026-10-12 — CI fix (implementer)
- PR #2154 went red on `marshal-test`, `named-module-gates (marshal)` and `scripts-suite`. Both tests pass on
  `origin/main` (`5beef7c9eb`) and fail on this branch, so this story's diff causes both. Neither was pre-existing.
- **Root cause 1, marshal** (`test_dispatch_ruff_format_trees.py::test_ac2_portal_uses_py314_table`):
  - This story moved the `django-fixture` table in marshal Story 95.1's test from `py312` to `py314` and renamed the test.
  - At `py314`, `ruff format` rewrites the fixture's `except (ValueError, TypeError):` to `except ValueError,
    TypeError:` (PEP 758), so marshal 95.1's AC2 assertion failed.
  - The fixture is not a live portal table. Marshal 95.1 AC2 keeps it at `py312` so it differs from the
    `pyforge-marshal` table (`py314`), and AC9 relies on that difference.
  - This story's AC5 covers only 93.1's tests and the real tables, so it never required this change.
  - Fix: restored the fixture to `py312` and the name to `test_ac2_portal_uses_py312_table`, as on `main`. Added a
    two-line comment saying why the fixture stays `py312`.
- **Root cause 2, scripts** (`tests/scripts/test_lint_types_gate.py::test_target_version_findings_name_the_drift`):
  - `findings_for` is now an alias of `findings_for_pyforge`, which adds the AC3 `requires-python` check.
  - The test's `bare.toml` has a `[project]` table without `requires-python`, so it now returns a third finding,
    `missing [project] requires-python`, as AC3 requires.
  - Fix: the expected list now includes that finding.
- Surface:
  - `test_dispatch_ruff_format_trees.py` is governed by `pyforge-marshal/spec-pyforge-marshal`. It got a memlog entry
    (2026-10-12), `git add`, then one scoped stamp (`--write-baseline --spec pyforge-marshal/spec-pyforge-marshal`).
  - That stamp also took in `pixi.toml` and `pyforge-core/tests/unit/test_flags.py`, which the memlog already names
    (93.1 and 91.1).
  - `tests/scripts/test_lint_types_gate.py` is allowlisted and has no governing Spec.
- Gates (exit codes read from files):
  - `pyforge-marshal-test` 0 (12468 passed);
  - `coverage_gates_ci.py` (marshal, `--suites unit`) 0;
  - `pyforge-doctor-scripts-test` (`pyforge-ci`) 0 (1446 passed);
  - `pyforge-steward-test` 0 (2396 passed; the not-yet-clean ceiling failure on `main` did not occur on this base);
  - `lint-types` 0; `target-version-check` 0; `spec-surface-check` 0; `platform-ci-local -- --test` 0 (all steps PASS).
- `detectors-ci` exits 1 on one finding: `ledger-direction` says herald `38-1-…` is landed-but-unpromoted.
  - Cause: the branch predates `main`'s promotion commit (`f1be3236b9`). The source is ok on `origin/main` (exit 0) and
    reads the branch's stale herald ledger row (`backlog`).
  - Not this story's diff. Merging `main` into the branch clears it.
  - A `git merge-tree` preview shows conflicts only in the `spec-pyforge-steward` and `spec-pyforge-unifying-strategy`
    memlogs, which can be resolved by union. `django-herald` is ruff-clean and format-clean at `py314` on `main`.

### 2026-10-11 — Review pass
- verdicts: 9 findings — high 0, medium 1, low 0, false 5, maybe-false 0, reject 3
- findings:
  - `[false]` `[reject]` Extra `mcp_dual_era.py` format beyond PEP 758 — reverted the collapsed `any(...)` line; portal diff is except-only again.
  - `[false]` `[reject]` Missing `environment.yaml` in diff — verified export: no diff vs tracked file (exit 0).
  - `[false]` `[reject]` AC8 scoped stamps missing — dispatch contract: reconcile via memlogs + `spec_surface_reconcile.py` only; no producer `--write-baseline`.
  - `[false]` `[reject]` Ledger not updated in diff — ledger sync is operator/harness after merge; story key unchanged at mint.
  - `[false]` `[reject]` `requires-python >=3.14` vs pin patch floor — AC3 requires minor match; patch segment is interpreter runtime, not package metadata floor.
  - `[medium]` `[patch]` Ingest README too terse — kept AC5 wording (`python-agent-platform` without stale 3.12 claim); dlt note removed per AC5.
  - `[false]` `[defer]` RTD yaml still present — AC5 only retargets to 3.14; deletion explicitly rejected in story.
  - `[false]` `[reject]` TYPE_CHECKING pytest risk — `platform-ci-local --test` passed (1256 tests).
  - `[false]` `[reject]` Live-tree gate test not extended — `test_live_tree_targets_match_the_interpreter` still calls `main()` on live tree; expanded checker covered by new unit tests.

## Auto Run Result

Status: done

Summary: Raised nine django-* and `src/platform` lint/type targets to Python 3.14, extended `target_version_check.py` to three surfaces (including `requires-python` floors), applied thirteen portal PEP 758 rewrites and platform py314 ruff fixes, refreshed stale 3.12 config/docs, and added AC7 surface tests.

Files changed (high level): `scripts/target_version_check.py`, `scripts/lint_types.py`, `pixi.toml`, `AGENTS.md`, nine django `pyproject.toml`, thirteen portal source sites, `src/platform/*` (pyproject, residue config, ruff-driven code), steward/marshal tests, generated `docs/how-to/pixi-tasks.md` and `docs/map.yaml`, spec memlogs on six governors.

Review: one medium finding (README) accepted as AC5-compliant; one patch reverted non-PEP758 format in `mcp_dual_era.py`; remainder rejected/false.

Follow-up review recommendation: false

Verification:
- `python scripts/target_version_check.py` — exit 0
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2350 passed
- `pixi run -e pyforge-guild platform-ci-local -- --test` — PASS (ruff, format, mypy, 1256 pytest)
- `python scripts/spec_surface_reconcile.py` — exit 0
- `pixi run --frozen -e pyforge-guild docs-pixi-tasks -- --check` — exit 0
- `environment.yaml` export — no diff
- AC5 grep on portal/platform paths — no matches

Memlogs (Story 95.1 surface reconcile 2026-10-11): `spec-pyforge-steward`, `spec-pyforge-unifying-strategy`, `spec-pyforge-scribe`, `spec-pyforge-doctor`, `spec-pyforge-marshal`, `spec-pyforge-core` — paths named in each `.memlog.md` event entry.

Residual risk: `requires-python = ">=3.14"` documents minor-only floor; runtime is 3.14.7 via pixi. TYPE_CHECKING import moves rely on 3.14 lazy annotations (platform suite is the proof).

## Spec Change Log

- 2026-10-11: minted from the operator's ask "can we add a story to update to python 3.14 - configuration targets
  Python 3.12 on purpose: targeting 3.14 makes ruff". `type: feature`, `flag-exempt: detector-or-gate`, no CAP; bound
  to `spec-pyforge-steward` CAP-153 through Stories 66.1 and 93.1; Deps S-93.1.
