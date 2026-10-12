---
title: '93.1: The lint gate covers the nine django portal packages, and its not-yet-clean list only shrinks'
type: 'feature'
created: '2026-10-11'
status: 'done'
baseline_revision: '3c85a29a64ef834074b323740402dbec08fe1597'
flag-exempt: detector-or-gate   # the story changes the lint gate itself; a gated gate reports a silent green
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-66-1-lint-and-types-gate-the-ten-packages-locally-and-on-the-runners-alike.md
  - scripts/lint_types.py
  - scripts/target_version_check.py
  - .github/workflows/lint-types.yml
  - src/shared/packages/pyforge-herald/pyproject.toml
  - src/shared/packages/django-herald/pyproject.toml
  - tests/scripts/test_lint_types_gate.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** nothing lints the nine portal packages under `src/shared/packages/django-*` (atlas, doctor, herald,
marshal, mason, pyforge, scribe, steward, warden). Herald Story 37.1's review found it on 2026-10-11. Line numbers
below are at `2b5e0d649b`.

- **The gate skips them.** `pixi run -e pyforge-guild lint-types` runs `scripts/lint_types.py`, whose `packages()`
  globs only `pyforge-*` (:36-:37) and whose count check expects ten (:55-:58). `.github/workflows/lint-types.yml` and
  `pr-preflight`'s first leg call the same task (Story 66.1, CAP-153).
- **No other lane covers them.** `scripts/platform-ci-local.sh` runs ruff and ruff format over `src/platform` only
  (:280-:281), and so does the `platform-ci` workflow it mirrors.
- **Their verdict depends on the ruff release.** None of the nine `pyproject.toml` files has a `[tool.ruff]` table, and
  no `ruff.toml`, `.ruff.toml` or `[tool.ruff]` table sits above them. A hand run of the guild ruff (0.16.9) therefore
  applies ruff's own default selection: 413 rules in 38 families at line length 88, with the target inferred as py312
  from `requires-python = ">=3.12"` (`ruff check --show-settings` and `--isolated` differ only in that target). Any
  ruff release that changes its defaults changes the verdict with no code change.

**Evidence** (measured 2026-10-11 on `2b5e0d649b`, from each package directory, `--no-cache`; read-only):

| package | ruff defaults: check | defaults: files to reformat | shared table at py312: check | py312: files to reformat |
|---|---|---|---|---|
| django-atlas | 14 | 0 | 4 (I001) | 1 |
| django-doctor | 7 | 0 | 2 (I001) | 0 |
| django-herald | 17 | 7 | 5 (4 I001, 1 F401) | 3 |
| django-marshal | 7 | 1 | 1 (I001) | 1 |
| django-mason | 10 | 0 | 5 (I001) | 0 |
| django-pyforge | 106 | 14 | 35 (I001) | 10 |
| django-scribe | 6 | 0 | 1 (I001) | 0 |
| django-steward | 8 | 0 | 1 (I001) | 1 |
| django-warden | 40 | 4 | 10 (8 I001, 2 F401) | 3 |
| **total** | **215** | **26** | **64** (all safe fixes) | **19** |

- The "shared table" is the `[tool.ruff]` table all ten `pyforge-*` packages carry today (line length 120,
  `extend-exclude = ["*/migrations/*.py"]`, `select = ["E", "F", "W", "I"]`, `ignore = ["E501"]`, per-file ignores
  `__init__.py` F401 and `**/tests/**` E402), measured with `--config` overrides and with `target-version = "py312"`.
- At `py314` the formatter rewrites `except (A, B):` to `except A, B:` (PEP 758), a SyntaxError on Python 3.12 and
  3.13, which the packages declare they support. Measured in `django-doctor`'s `pulse.py:58` and `django-mason`'s
  `apps.py:37`.
- The platform's own table (`src/platform/pyproject.toml`, about 45 rule families, line length 88) was measured too:
  305 findings and 24 files to reformat.
- `ruff format --check` is not clean today under any of these configs, so the format verb needs the list as much as
  the check verb does.

**Approach:** run the gate's `ruff` and `ruff-format` verbs over the django packages too, give each package an explicit
table, and list the packages not yet clean in a list that only shrinks.

- **One explicit table per package.** Each `django-*/pyproject.toml` gains the ten packages' shared `[tool.ruff]`
  table, with one change: `target-version = "py312"`, the floor of the package's own `requires-python`. A table per
  package, not one shared file passed with `--config`, because:
  - ruff reads a package's own table with no flags, so a hand run, an editor and the gate agree;
  - a shared file resolves `extend-exclude`, per-file ignores and isort's `src` against its own directory, not the
    package's;
  - a shared file would be a new path outside the foundry target tree.
  The nine files have one governor, `spec-pyforge-unifying-strategy`, so this is one reconcile, not nine.
- **The not-yet-clean list.** `NOT_YET_CLEAN` is a module constant in `scripts/lint_types.py` that maps a django
  package's directory name to the verbs it is not yet clean for (`ruff`, `ruff-format`). It is seeded from the
  measurement at implementation time. On `2b5e0d649b` that is all nine for `ruff`, and atlas, herald, marshal, pyforge,
  steward and warden for `ruff-format`. Per verb:
  - an unlisted package fails on any finding, as today;
  - a listed package's findings print, and its exit 1 does not fail the verb;
  - a listed package that is clean fails the verb, naming the entry to remove (the ratchet);
  - a listed package whose tool exits anything other than 0 or 1 still fails;
  - an entry that names a missing package, a `pyforge-*` package or an unknown verb makes the run could-not-run
    (exit 2).
  A steward test holds the seeded map as a ceiling, so an entry can leave but never come back.
- **No silent fallback.** A django package whose `pyproject.toml` has no `[tool.ruff]` table is a finding, so ruff
  never quietly applies its own defaults to it.
- **Counts.** The "expected ten `pyforge-*` packages" check counts `pyforge-*` alone, so the nine django packages can
  never mask a missing station package. Fewer than nine django packages is could-not-run.
- **The mutator stays in its lane.** `ruff-format --fix` (`ruff-format-fix`) skips a package listed for
  `ruff-format`, so it never rewrites another station's package.
- **mypy is out of scope.** The `mypy` verb stays over the ten `pyforge-*` packages; mypy over the django packages is
  out of scope for this effort.
- **Rejected:** a `--config` file shared by the nine (see above); the platform's broader table (305 findings, with no
  owner asked to clear them); pinning ruff's current default selection (413 rules nobody chose, at line length 88);
  fixing the findings here (the ruling gives each station its own fix story, herald's first).

Ledger key: `93-1-the-lint-gate-covers-the-nine-django-portal-packages-and-its-not-yet-clean-list-only-shrinks`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-153** (lint and types gate the ten `pyforge-*` packages, locally and on the runners
  alike). Story 66.1 built it as one set of tasks that one CI lane and `pr-preflight`'s leg call verbatim. This story
  runs the same tasks, lane and leg over nine more packages, for ruff and ruff format, so it adds no capability and
  mints no CAP. CAP-153's text still says "the ten `pyforge-*` packages"; this story does not change `SPEC.md`.
- **Flag:** `flag-exempt: detector-or-gate` (`docs/governance/guild-roster.json` `flag_exemptions`): the story changes
  a gate.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-11 (django portal packages under lint-types).
  The operator's request, verbatim: "Do this task here: Lint django-herald package and add it to a gate". Asked how
  wide to go, the operator chose, verbatim label "Gate all, clean herald (Recommended)": "Two stories. Steward's story
  extends lint-types to every django-* package and adds an explicit 'not yet clean' list that can only shrink.
  Herald's story clears django-herald's 17 findings and takes it off that list. The other stations follow later as
  their own fix stories."

## Acceptance Criteria

- **AC1 — Both ruff verbs cover the django packages.** `python scripts/lint_types.py ruff` and `ruff-format` run over
  every `src/shared/packages/pyforge-*` and `src/shared/packages/django-*` directory that has a `pyproject.toml`,
  sorted, each with `cwd` = the package and the trees `src` and `tests` where present, as today. The `mypy` verb is
  unchanged and runs over `pyforge-*` only. Each package prints one status line, as today.
- **AC2 — Each django package declares its table.** Each of the nine `django-*/pyproject.toml` files carries this
  table and no other change:

  ```toml
  [tool.ruff]
  target-version = "py312"
  line-length = 120
  extend-exclude = ["*/migrations/*.py"]

  [tool.ruff.lint]
  select = ["E", "F", "W", "I"]
  ignore = ["E501"]

  [tool.ruff.lint.per-file-ignores]
  "__init__.py" = ["F401"]
  "**/tests/**" = ["E402"]
  ```

  A django package whose `pyproject.toml` has no `[tool.ruff]` table is a finding for both verbs (exit 1, naming the
  package). The ten `pyforge-*` tables do not change.
- **AC3 — The not-yet-clean list.** `NOT_YET_CLEAN` in `scripts/lint_types.py` maps a django package's directory name
  to a frozen set of verbs from `{"ruff", "ruff-format"}`. It is seeded from the measurement on the story's base, and
  its comment says it only shrinks and that each station's fix story removes its own entry. For each verb:
  - an unlisted package (every `pyforge-*` package included) fails the verb on a tool exit of 1;
  - a listed package's tool output prints, and a tool exit of 1 does not fail the verb; its status line says it is
    not yet clean and listed;
  - a listed package whose tool exits 0 fails the verb (exit 1), and its status line names the entry to remove;
  - a listed package whose tool exits anything other than 0 or 1 fails the verb;
  - an entry naming a directory that is not a `django-*` package under `src/shared/packages/`, or a verb outside the
    two, makes the run exit 2 (could-not-run) before any tool runs, naming the entry.
- **AC4 — The list only shrinks.** A steward test holds the seeded map as a ceiling: every live entry's package and
  verbs must be in it. Adding a package or a verb back fails the test. Removing an entry passes it.
- **AC5 — Counts.** Fewer than ten `pyforge-*` packages is could-not-run (exit 2), counted without the django
  packages. Fewer than nine `django-*` packages is could-not-run.
- **AC6 — `--fix` skips listed packages.** `ruff-format --fix` does not run on a package listed for `ruff-format`, and
  prints that it skipped it. It still formats every unlisted package.
- **AC7 — The gate is green on the story's tree.** `pixi run --frozen -e pyforge-guild lint-types` exits 0. Every
  django package prints a listed, not-yet-clean status for each verb it is listed for, the unlisted django packages and
  the ten `pyforge-*` packages print `ok`, and `mypy`, `target-version-check` and `precommit-config-check` are
  unchanged.
- **AC8 — The stale lines are fixed.** Every line that says ruff or ruff format runs over "the ten `pyforge-*`
  packages" now names the django packages and the list: `lint_types.py`'s docstring, the header comment of
  `.github/workflows/lint-types.yml`, the `ruff`, `ruff-format` and `ruff-format-fix` descriptions in `pixi.toml` and
  their comment block, and the *Lint and types* line in `AGENTS.md`. `docs/how-to/pixi-tasks.md` is regenerated by
  `docs-pixi-tasks`, and `environment.yaml` is regenerated (expected unchanged). Lines about `mypy` and
  `target-version-check` still say `pyforge-*`, because that stays true.
- **AC9 — Tests that can fail.**
  - New unit tests in `src/shared/packages/pyforge-steward/tests/unit/test_lint_types_not_yet_clean.py` load
    `scripts/lint_types.py` by path. They drive `main()` over a temporary packages directory with a stubbed runner, so
    the steward env needs no ruff, and cover every AC3, AC5 and AC6 row and the missing-table finding.
  - A new meta test in `src/shared/packages/pyforge-steward/tests/meta/test_lint_types_django_tables.py` reads the live
    tree: the nine tables equal AC2's, `NOT_YET_CLEAN` is within the ceiling (AC4) and names only live django
    packages, and `.github/workflows/lint-types.yml`'s `paths` still include `src/shared/packages/**`.
  - Each of these mutations fails a named test: removing the stale-entry check; failing a listed package's exit 1;
    passing a listed package's exit 2; dropping `django-*` from the glob; counting `django-*` toward the ten; letting
    `--fix` rewrite a listed package. Each is reverted afterwards, and the Auto Run Result names the test each one
    failed.
- **AC10 — No finding is fixed.** Outside each `pyproject.toml`'s new table, no line under `src/shared/packages/django-*`
  changes.
- **AC11 — The surface is reconciled.** Every Spec `spec-surface-check` names gets a memlog entry naming its paths and
  this story, and one scoped stamp each, and `spec-surface-check` exits 0. Expected (the detector's own list wins):
  `spec-pyforge-steward` (`scripts/lint_types.py`, the workflow, steward's tests), `spec-pyforge-unifying-strategy`
  (the nine `pyproject.toml` files), `spec-pyforge-scribe` (`AGENTS.md`), `spec-pyforge-doctor`
  (`docs/how-to/pixi-tasks.md`, `docs/map.yaml`) and every governor of `pixi.toml`.

## Boundaries & Constraints

**Always:**
- Keep one gate: the `lint-types` task, its CI lane and `pr-preflight`'s leg call the same tasks they call today.
- Keep every package's run in its own directory with its own table, as Story 66.1 does.
- Keep the seeded list exactly equal to what the tools report on the story's base; AC7 proves it.

**Ask First:**
- Any change to the ten `pyforge-*` tables, to the rule selection of AC2's table, or to `mypy`'s scope.

**Never:**
- Never fix a finding in a django package, run `ruff check --fix` or `ruff format` over one, or add a `noqa`: each
  station's own fix story does that (herald Story 38.1 first).
- Never add a task, a CI lane, a workflow or a `pr-preflight` leg; never change `target_version_check.py`,
  `src/platform` or `platform-ci-local`.
- Never let a listed package's tool error (exit 2) pass, and never let a pyforge-* package be listed.

**Residual risk:**
- A story that edits a listed package's files and happens to clean it turns `lint-types` red until it removes the
  entry. That is the ratchet working. Marshal's pre-verify ruff pass (Stories 83.9 and 83.15) covers only
  `pyforge-*` files, so once a django package is unlisted, a dispatched story that edits it gets no automatic format
  pass, and `lint-types` in `pr-preflight` and CI catches what it misses.
- `CAP-153`'s `SPEC.md` text keeps saying "the ten `pyforge-*` packages" until a later `bmad-spec` pass folds a dated
  clause.

## I/O & Edge-Case Matrix

| Situation | Today (`2b5e0d649b`) | After |
|---|---|---|
| a `pyforge-*` package with a finding | the verb fails | unchanged |
| a django package with a finding, listed for that verb | never linted | reported; the verb does not fail |
| a django package with a finding, not listed | never linted | the verb fails |
| a listed django package that is clean | never linted | the verb fails, naming the entry to remove |
| a listed package whose ruff exits 2 | never linted | the verb fails |
| a django package with no `[tool.ruff]` table | ruff's defaults on a hand run | a finding |
| `NOT_YET_CLEAN` names a missing package, a `pyforge-*` package or an unknown verb | n/a | could-not-run (exit 2) |
| an entry re-added after removal | n/a | the ceiling test fails |
| a `pyforge-*` package goes missing while the nine django ones exist | could-not-run (exit 2) | still could-not-run |
| `ruff-format --fix` over a listed package | not run | skipped, and the skip is printed |
| `mypy` | ten `pyforge-*` packages | unchanged |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-153, as built by Story 66.1. No CAP is minted, and no `SPEC.md`
  text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-11 (django portal packages under
  lint-types) entry.
- Epic: Epic 93 (new). Epic 66, which built the gate, is `done`, so this story opens its own epic. `epic-93` and
  `epic-93-retrospective` are minted with it.
- Ledger key: `93-1-the-lint-gate-covers-the-nine-django-portal-packages-and-its-not-yet-clean-list-only-shrinks`.
- Ledger status at mint: `backlog`.
- Deps: none. Herald Story 38.1 (`38-1-django-herald-is-lint-clean-and-leaves-the-not-yet-clean-list`) waits on this
  story as a `blocked` row in herald's ledger.
- Spec: the `spec-pyforge-steward` memlog records the ruling verbatim, the evidence and design, and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."93"` (added with this mint) admits the paths this story names.
- Minted 2026-10-11 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass, with the new unit and meta tests (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0, read from the exit code (AC7).
- The six mutations of AC9 — expected: each fails its named test. Revert each.
- `pixi run --frozen -e pyforge-guild docs-pixi-tasks -- --check` — expected: exit 0 after the regeneration (AC8).
- `pixi project export conda-environment -e build > environment.yaml`, then `git diff --exit-code environment.yaml` — expected: no diff.
- `pixi run --frozen -e pyforge-guild pyforge-station-tests` — expected: pass (the `pixi.toml` change is shared surface).
- `git diff origin/main...HEAD -- src/shared/packages/django-*` — expected: only the nine new `[tool.ruff]` tables (AC10).
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC11).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Review Triage Log

### 2026-10-11 — Review pass
- verdicts: 6 findings — high 0, medium 2, low 0, false 3, maybe-false 1
- findings:
  - `[medium]` `[patch]` NOT_YET_CLEAN_CEILING aliased NOT_YET_CLEAN — split frozen ceiling from live map in scripts/lint_types.py; meta test checks subset within ceiling.
  - `[medium]` `[patch]` Listed django missing [tool.ruff] could stay green — missing_table always fails the verb.
  - `[false]` `[reject]` Empty [tool.ruff] passes has_ruff_table — tomllib still has tool.ruff key; empty table is operator error, not introduced here.
  - `[false]` `[reject]` SEEDED duplicate in meta test — intentional AC4 oracle duplicate of module seed.
  - `[false]` `[reject]` No unknown-verb test — added test_not_yet_clean_unknown_verb_could_not_run.
  - `[maybe-false]` `[reject]` Listed missing-table untested — covered by missing_table always failing verb; no separate listed case required for AC7.

## Auto Run Result

Status: done

**Summary:** Extended `scripts/lint_types.py` so `ruff` and `ruff-format` run over all nine `django-*` portal packages with a shrink-only `NOT_YET_CLEAN` map, explicit `[tool.ruff]` tables (`target-version = "py312"`) in each django `pyproject.toml`, steward unit/meta tests, and doc/task string updates. No django source findings were fixed (AC10).

**Files changed:**
- `scripts/lint_types.py` — django coverage, NOT_YET_CLEAN / ceiling, missing-table and listed-package logic, `--fix` skip.
- Nine `src/shared/packages/django-*/pyproject.toml` — shared ruff table only.
- `src/shared/packages/pyforge-steward/tests/unit/test_lint_types_not_yet_clean.py` — AC3/AC5/AC6 matrix tests (mutation-named).
- `src/shared/packages/pyforge-steward/tests/meta/test_lint_types_django_tables.py` — AC2/AC4 live-tree checks.
- `.github/workflows/lint-types.yml`, `pixi.toml`, `AGENTS.md`, `docs/how-to/pixi-tasks.md` — AC8 stale-line updates.

**Review:** 2 medium patches applied; 3 false, 1 maybe-false rejected. `followup_review_recommended: false`.

**Verification:**
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
- `pixi run --frozen -e pyforge-steward pytest …/test_lint_types_*.py` — 13 passed.
- `pixi run --frozen -e pyforge-guild docs-pixi-tasks -- --check` — exit 0.
- `environment.yaml` export — no diff.
- `python scripts/spec_surface_reconcile.py` — exit 0 (memlogs below; no `--write-baseline` in this run).
- AC9 mutation guards: named tests in `test_lint_types_not_yet_clean.py` / `test_lint_types_django_tables.py`.

**Residual risk:** Station fix stories must shrink `NOT_YET_CLEAN` and `NOT_YET_CLEAN_CEILING` together when a package cleans up; herald 38.1 is next.

## Spec Change Log

- 2026-10-11: minted from the operator's ruling "Gate all, clean herald (Recommended)". `type: feature`,
  `flag-exempt: detector-or-gate`, no CAP; bound to `spec-pyforge-steward` CAP-153 through Story 66.1.
- 2026-10-11: bmad-build-auto implementation landed (lint gate + NOT_YET_CLEAN ratchet).
