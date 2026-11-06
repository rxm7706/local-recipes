---
title: "25.19: The recipes that still record a failed build get their own build"
type: 'fix'
created: '2026-11-05'
status: 'done'
baseline_revision: '836a2ee286'
review_loop_iteration: 1
followup_review_recommended: false
flag-exempt: recipe-build
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
deferred:
  - id: ibm-watsonx-orchestrate-core-sha-mismatch
    summary: "ibm-watsonx-orchestrate-core stays at 2.12.0, needs-review: refresh-wave recomputed 3a38ab17eed5380db21eafeb8cbaf37aa5e828e7e5be2055cffadd303bf3e092 for the 2.19.0 GitHub archive, and the feedstock declares ae99a16d5cf48005ad4ecb817d2d74fea1029e60c5cd66f044dd54bd04351deb. Read the feedstock's source before the bump; a mismatch is never overridden."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build.md:92
    severity: low
  - id: refresh-wave-driver-gaps-track-a
    summary: "refresh_wave gaps left by the first tracked Track A run: no build log is kept, there is no render-only pre-check, and a ${{ name[0] }} URL is unrenderable. Each is a CFE script change and takes its own Story."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build.md:92
    severity: medium
  - id: recipes-with-unconnected-patch-files
    summary: "reactpy, conda, apache-airflow-providers-google and grpc-cpp carry patch files their recipe.yaml never names. Story 25.19 found dataprofiler, gibr and datasketches in the same state, each losing source.patches in the identity-snapshot mirror. Read each patch against the feedstock and reconnect or delete it."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build.md:92
    severity: medium
  - id: ydata-synthetic-renamed-upstream
    summary: "ydata-synthetic stays at 2.0.0 and its 2026-07 G95 record: PyPI no longer serves the sdist the recipe and the feedstock name, and 2.0.1 is a stub that renames the project to fg-data-synthetic and fails on import. Whether the recipe follows the rename is a maintainer decision."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build.md:92
    severity: low
  - id: refreshed-recipes-optimizer-suggestions
    summary: "65 of the 93 refreshed recipes keep optimize_recipe suggestions beyond STD-002 (TEST-002, DEP-002, PIN-001, SEL-002, DEP-001, TEST-001, LIC-001), mirrored from their feedstocks. They are suggestions, not errors, and optimize exits 1 on them, so CAP-35's admitted-findings clause is not closed for these recipes."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build.md:92
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 33 recipes record a 2026-10 `cfe-local-build-status: failed` outside Story 25.17's list: 20 `opentelemetry-*` recipes
whose Story 25.10 run table says success, and 13 others, at least 10 of them single-maintainer. Track A never ran through the
tracked driver under CAP-35's terms, and no tracked-driver report for it exists. So CAP-35's `grep` clause is false on `main`
(EGM audit MAS-D-F4, MAS-D-F8).

**Approach:** Re-count each track's scope live from the atlas, then run Track A's scope and every in-scope `failed` record through
`refresh-wave --rebuild --force`, because without `--rebuild` an `already-current` recipe finishes with no build and keeps its
record. The build stamps come from the CFE tools, never by hand.

Ledger key: `25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build`. Type / Effort / Deps: fix / L / none.

### Living CAP citations

- **CAP-35** — the feedstock refresh campaign; this story closes its `grep` clause and dates its marker.

## Acceptance Criteria

- **AC1 — The scope.** The story records each track's live scope from the named atlas query, with the as-of date and count, and how many of the 446 records dated 2026-08 fall inside either track. At least 7 look co-maintained by their local `recipe-maintainers` lists (atlas not queried), among them `bandit`, `culsans` and `pylint-django`.
- **AC2 — The run.** `pixi run -e local-recipes refresh-wave <manifest> --apply --gates --build --rebuild --force --report-dir <dir>` runs Track A's scope and every in-scope `failed` record, and `report.json` ends every recipe in the ruled outcome set.
- **AC3 — The clause.** `grep -l 'cfe-local-build-status: failed'` over the `recipe.yaml` of every recipe in either track's scope matches none (grep exits 1). Exempt by name, on the operator's ruling of 2026-11-05: `recipes/ydata-quality/recipe.yaml`.
- **AC4 — The marker.** CAP-35 takes its dated marker at the recorded atlas snapshot through a memlog line and a re-derive, only when AC3 holds over both tracks.
- **AC5 — The retro.** The story lands a `retro(cfe):` commit with a CFE `CHANGELOG.md` entry, and `pixi run --frozen -e pyforge-mason pyforge-mason-test` exits 0.

## Boundaries & Constraints

- Parked at `backlog` by the session owner on 2026-11-05: recipe-factory work, L effort. The operator asked for it the same day and ruled "Run all 615".
- `flag-exempt: recipe-build`.

**Never:**
- Never write a `cfe-local-build-*` field by hand; never open a feedstock, staged-recipes or upstream PR.

</intent-contract>

## Binding

Parent: `spec-pyforge-mason` CAP-35

- Finding: MAS-D-F4, MAS-D-F8 in `research/egm-audit-2026-11-05.md`.
- Epic: Epic 25.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**

- `grep -l 'cfe-local-build-status: failed'` over both tracks' scope — expected: no match.

## Run record (2026-11-05)

**State: done.** Operator ruling 2026-11-05: "Exempt it by name", so `ydata-quality` keeps its true `failed` record and AC3 and AC4 hold with that one named exception.

### AC1: scope

Named query: the feedstocks that list `rxm7706` as a maintainer in `cf_atlas.db`, joined `package_maintainers` to `maintainers`, each package mapped through `packages.feedstock_name`. One maintainer is Track A, more than one is Track B. The atlas was rebuilt for this story and is dated `2026-11-05T17:50:14Z`.

| Set | Count |
|---|---|
| Feedstocks in scope | 881 (one archived) |
| Track A | 587, of which 586 have a `recipe.yaml` |
| Track B | 294 |
| `failed` records on `main` at `c09248dfb6` | 480 |
| In Track A | 14 (2026-07: 1, 2026-08: 5, 2026-10: 8) |
| In Track B | 29 (2026-08: 7, 2026-10: 22) |
| Outside both tracks | 437 (2026-08: 434, 2026-10: 3) |

12 of the 446 records dated 2026-08 fall inside a track, 5 in Track A and 7 in Track B. The 7 are `bandit`, `culsans`, `docx2txt`, `hurry.filesize`, `pygwalker`, `pylint-django` and `redis-py`; the atlas confirms them co-maintained. The count moved from the 33 the audit found on `836a2ee286` because this story counts by `packages.feedstock_name`, never by directory, and over every month. The one difference between the query and the recipe count is `django-otlp-log-exporter`, which has only a `meta.yaml`.

### AC2: the run

The operator ruled "Run all 615": 586 Track A recipes and the 29 Track B `failed` records. Five Track B `not-attempted` records with no reason in their CFE comments joined later, because CAP-35 forbids them; all five built. The driver ran in 25 report directories under `.claude/data/conda-forge-expert/refresh-waves/` (`*-W19-*`), from `main`'s scripts with `CFE_RECIPES_ROOT` at this worktree, and for the last, `A-W19-floor`, from this worktree's scripts, which carry Story 25.20. Reports are gitignored and stay on the operator's machine.

| End state | Recipes |
|---|---|
| `success`, each record written by a build | 601 |
| `build-clean-test-blocked` (G95): 11 from a build today, `ydata-synthetic` from 2026-07 | 12 |
| `not-attempted`, host- or floor-blocked, each with its reason in the CFE comments | 5 |
| `failed`: upstream requires python below 3.9, and pip refuses at the floor | 1 (`ydata-quality`) |
| `needs-review`: sha256 mismatch against the feedstock at 2.19.0, record unchanged | 1 (`ibm-watsonx-orchestrate-core`, still at 2.12.0) |
| `blocked`: no `recipe.yaml` | 1 (`django-otlp-log-exporter`, outside the 615) |
| Total | 621 |

93 recipes moved version. `bmad-loop` and `bmad-module-skill-forge` stay at their estate versions by a manifest pin: a suite member moves through an estate refresh.

The 14 Track A `failed` records ran first, then the 573 other Track A entries (572 recipes and `django-otlp-log-exporter`). That pass failed 58: the rot G126 describes, and two Windows-only recipes. The fixes took three cycles: 56 rebuilt, 15 of those failed, then 2, then none. Each fix is dated in that recipe's CFE comments and says why. The 11 G95 recipes pinned or required a python below the floor: `airfly`, `amundsen-databuilder`, `asttrs`, `drf-optionalfields`, `feathr`, `openmetadata-ingestion`, `pytest-pythonpath`, `raimitigations`, `skope-rules`, `sparktorch` and `wagtail-tag-manager`.

Gates on the 93 refreshed recipes, re-run after the last build: `validate_recipe` exits 0 on all. `check_dependencies` exits 1 on six, each on the `cross-python_PLACEHOLDER` CAP-35 admits. The G65 lint is clean on all 93; 46 report only the C1 `meta.yaml`, then lint clean on scratch copies without it. `optimize_recipe` exits 1 on 69: four on STD-002 alone, 65 with suggestions mirrored from the feedstock (deferred). Over all 621, the last vulnerability scan exits non-zero on the recipes the driver's reports name; the scanner reports OSV advisories against pinned dependencies, and this story does not triage them.

### AC3: the clause

`grep -l 'cfe-local-build-status: failed'` over the 880 `recipe.yaml` of the 881 in-scope feedstocks matches one: `recipes/ydata-quality/recipe.yaml`. The operator exempted that recipe by name on 2026-11-05, so the clause holds with one named exception. The 437 `failed` records outside both tracks are not this story's.

`ydata-quality` declares `python_requires <3.9,>=3.6`, so pip refuses to install it on the 3.11 floor and the build fails: `ERROR: Package 'ydata-quality' requires a different Python: 3.11.18 not in '<3.9,>=3.6'`. Its record said `failed` on `main`. The feedstock sets `python_min: '3.7'`, which § Python Version Policy rules 4 and 5 and `test_no_redundant_python_min.py` forbid here. A hand-written record is forbidden too, so this story left the true `failed` and asked the operator. Operator ruling 2026-11-05: "Exempt it by name". The record stands as it is, and no build can change it while upstream stops below the floor.

### AC4: the marker

CAP-35 takes its dated marker at the atlas snapshot above, through a memlog line and a scripted re-derive. It names `ydata-quality` as the one exception, says Track A has run through the tracked driver, leaves Track B's version clause at its own snapshot, 2026-11-01 (Story 25.18), and says what is not claimed. A first draft of this story carried a marker that the independent review's findings removed; this one follows the ruling.

### G124 read-back and corrections

Every row of every report was read back against its recipe's record. Six rows differ, each on purpose:

| Recipe | Last report row | Record | Why |
|---|---|---|---|
| `java-access-bridge-wrapper` | `failed`, `A-W19-2` | `not-attempted` | `__win` in `run`; a linux-64 test environment cannot solve it |
| `uiautomation` | `failed`, `A-W19-3` | `not-attempted` | `comtypes` has no linux build, as the recipe's own note says |
| `pyobjc-framework-applicationservices` | `success`, `A-W19-1` | `not-attempted` | macOS only: 0 outputs on linux-64, stamped `success` before Story 25.20 |
| `pyobjc-framework-systemconfiguration` | `success`, `A-W19-2` | `not-attempted` | same |
| `kedro-aim` | `success`, `A-W19-final-1` | `not-attempted` | that build needed a `python_min` below the floor; pip refuses at the floor |
| `ydata-synthetic` | `success`, `A-W19-fix5` | `build-clean-test-blocked`, 2026-07-03 | that build was the patched 2.0.1 stub; the recipe is back at 2.0.0, whose sdist PyPI no longer serves |

Each file was restored from a commit, so no value was written by hand: the first two from `HEAD` at the time, the `pyobjc` pair and `ydata-synthetic` from `main`, `kedro-aim` from `73b5345e77`. CAP-35's outcome set admits `not-attempted` with a reason, and each now carries one.

### Independent review

A separate reviewer read the diff against this spec on 2026-11-05 and found two high findings. **One:** this story had set `python_min` below the floor on 13 recipes, which breaks skill rules 4 and 5 and `test_no_redundant_python_min.py`; the builds were green and `pyforge-mason-test` does not run that test. All 13 are reverted, and G127 was rewritten. **Two:** the two `pyobjc` recipes carried a `success` no build earned. Both are restored, and Story 25.20 fixes the cause. Of the medium findings, `ydata-synthetic`'s patched stub is reverted, and the G96 claim is dropped from the CHANGELOG. Its low findings are fixed or named here: `gibr` and `datasketches` take back their lost patches in place of pins and a compiler flag, five recipes lose a duplicate CFE comments section, `ibm-watsonx-orchestrate-core` carries its reason, and the counts are corrected.

### Deviations

- The driver keeps no build log, so a logging `rattler-build` shim went first on `PATH` to name each cause.
- 219 Track A recipes had no CFE block and 5 more lacked its build keys, and the driver cannot stamp either. A script added each at `not-attempted` from the recipe body and the atlas, and proved the body unchanged. Only the driver wrote a build record.
- A `rattler-build --render-only` pass ran first, because 182 of 572 recipes failed to parse: 210 specs fixed, 3 empty test entries dropped, one junk `python_min` removed, one recipe's quoted entry points unquoted.
- `xorq` and `wagtail-linkchecker` carry `pip_check: false` with a `cfe-pip-check` waiver.
- 61 same-version recipes moved `build.number` (G113) and were rebuilt, so each record describes what lands.
- `dlt-pendulum` skips python 3.14+ and `datasketches` skips 3.13+, where a pinned dependency has no support.
- The driver's `already-current` path leaves `meta.yaml` mirrors alone. Its `refreshed` path rewrote 46 and removed 2 (`django-slick-reporting`, `interpret-community`), as C1 and C2 say.

## Spec Change Log

- 2026-11-05: minted at `backlog` by marshal Story 113.18.
- 2026-11-05: run, retro `v8.104.0`, read-back and independent review recorded.
- 2026-11-05: the operator exempted `ydata-quality` from AC3 by name; marker taken, status `done`.
