---
title: "25.19: The recipes that still record a failed build get their own build"
type: 'fix'
created: '2026-11-05'
status: 'done'
baseline_revision: '836a2ee286'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: recipe-build
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
deferred:
  - id: ibm-watsonx-orchestrate-core-sha-mismatch
    summary: "ibm-watsonx-orchestrate-core stays at 2.12.0, needs-review: refresh-wave recomputed 3a38ab17eed5380db21eafeb8cbaf37aa5e828e7e5be2055cffadd303bf3e092 for the 2.19.0 GitHub archive, and the feedstock declares ae99a16d5cf48005ad4ecb817d2d74fea1029e60c5cd66f044dd54bd04351deb. Read the feedstock's source before the bump; a mismatch is never overridden."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build.md:84
    severity: low
  - id: refresh-wave-driver-gaps-track-a
    summary: "refresh_wave gaps from the first tracked Track A run: _TEST_BLOCK_RE misses rattler-build's own wording, so a clean build with an unsolvable test environment stamps failed, not build-clean-test-blocked; no build log is kept; there is no render-only pre-check; a skip over every variant stamps success with 0 outputs; a ${{ name[0] }} URL is unrenderable. Each is a CFE script change and takes its own Story."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build.md:84
    severity: medium
  - id: refreshed-recipes-optimizer-suggestions
    summary: "65 of the 93 refreshed recipes keep optimize_recipe suggestions beyond STD-002 (TEST-002, DEP-002, PIN-001, SEL-002, DEP-001, TEST-001, LIC-001), mirrored from their feedstocks. They are suggestions, not errors, and optimize exits 1 on them, so CAP-35's admitted-findings clause is not closed for these recipes."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build.md:84
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
- **AC3 — The clause.** `grep -l 'cfe-local-build-status: failed'` over the `recipe.yaml` of every recipe in either track's scope matches none (grep exits 1).
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

The operator ruled "Run all 615": 586 Track A recipes and the 29 Track B `failed` records. Five Track B `not-attempted` records with no reason in their CFE comments joined later, because CAP-35 forbids them. The driver ran from `main`'s scripts with `CFE_RECIPES_ROOT` at this worktree, in 24 report directories under `.claude/data/conda-forge-expert/refresh-waves/` (`*-W19-*`). Reports are gitignored and stay on the operator's machine.

| End state | Recipes |
|---|---|
| `success`, each record written by a build | 617 |
| `not-attempted`, host-blocked, with the reason in the CFE comments | 2 (`uiautomation`, `java-access-bridge-wrapper`) |
| `needs-review`: sha256 mismatch against the feedstock at 2.19.0 | 1 (`ibm-watsonx-orchestrate-core`, still at 2.12.0) |
| `blocked`: no `recipe.yaml` | 1 (`django-otlp-log-exporter`, outside the 615) |
| Total | 621 |

93 recipes moved version. `bmad-loop` and `bmad-module-skill-forge` stay at their estate versions by a manifest pin: a suite member moves through an estate refresh. The last run of every recipe that ended `success` exited 0.

The first pass over the 573 Track A recipes failed 58: the rot G126 describes, and two Windows-only recipes. The fixes took three cycles: 56 rebuilt, 15 of those failed, then 2, then none. Each fix is dated in that recipe's CFE comments and says why.

Gates on the 93 refreshed recipes, re-run after the last build: `validate_recipe` exits 0 on all. `check_dependencies` exits 1 on six, each on the `cross-python_PLACEHOLDER` CAP-35 admits. The G65 lint is clean on all 93; 46 report only the C1 `meta.yaml`, then lint clean on scratch copies without it. `optimize_recipe` exits 1 on 69: four on STD-002 alone, 65 with suggestions mirrored from the feedstock, which the `deferred:` entry names. Over all 621, the vulnerability scan exits non-zero on eight (`collate-sqllineage`, `feathr`, `gibr`, `langsmith-mcp-server`, `openmetadata-sqllineage`, `synthetic-data`, `ydata-quality`, `ydata-synthetic`). The scanner reports OSV advisories against their pinned dependencies; this story does not triage them.

### AC3: the clause

`grep -l 'cfe-local-build-status: failed'` over the 880 `recipe.yaml` of the 881 in-scope feedstocks exits 1 with no match. The 437 `failed` records still in `recipes/` are outside both tracks. This story does not touch them.

### AC4: the marker

CAP-35 takes its dated marker for the `grep` clause over both tracks and for Track A's run, at the atlas snapshot above. Track B's version clause stays at its own snapshot, 2026-11-01 (Story 25.18). 46 co-maintained feedstocks have moved on since then, which CAP-35 says does not reopen it, and `DW-mason-25-18` already carries the campaign's view of them. Track B's 107 recipes with no CFE block record no build, so the `grep` cannot see them; the marker claims nothing about them.

### G124 read-back and corrections

Every row of every report was read back against its recipe's record. Two rows differ, on purpose:

| Recipe | Report row | Record | Why |
|---|---|---|---|
| `java-access-bridge-wrapper` | `failed`, `2026-11-05T19:20:16Z`, `A-W19-2` | `not-attempted` | `__win` in `run`; a linux-64 test environment cannot solve it |
| `uiautomation` | `failed`, `2026-11-05T20:22:47Z`, `A-W19-3` | `not-attempted` | `comtypes` has no linux build, as the recipe's own note says |

Both recipes recorded `not-attempted` before this wave, and the wave's Linux run could not build either. Their uncommitted stamps were the only change in each file, so `git checkout HEAD` restored them: no value was written by hand. CAP-35's outcome set admits `not-attempted` with a host-blocked reason. `java-access-bridge-wrapper` gained that reason in its CFE comments.

### Deviations

- The driver keeps no build log, so a logging `rattler-build` shim went first on `PATH` to name each cause.
- 224 Track A recipes had no CFE block, and the driver cannot stamp one. A script added each block at `not-attempted` from the recipe body and the atlas, and proved the body unchanged. Only the driver wrote a build record.
- A `rattler-build --render-only` pass ran first, because 182 of 572 recipes failed to parse: 210 specs fixed, 3 empty test entries dropped, one junk `python_min` removed, one recipe's quoted entry points unquoted.
- This story set `python_min` below the 3.11 floor on 13 recipes, because upstream or a pin stops there (G127): `ydata-quality` at 3.7 and `skope-rules` at 3.9, the rest at 3.10.
- `xorq` and `wagtail-linkchecker` carry `pip_check: false` with a `cfe-pip-check` waiver.
- `ydata-synthetic` moved to 2.0.1 because PyPI no longer serves 2.0.0. 2.0.1 is a deprecation stub that cannot be imported, so a source patch adds its missing import. It also pins `tensorflow-cpu 2.15.*`, and `easydict` stays unpinned because conda-forge has no 1.10.
- 72 same-version recipes moved `build.number` (G113) and were rebuilt, so each record describes what lands.
- `dlt-pendulum` skips python 3.14+ and `datasketches` skips 3.13+, where a pinned dependency has no support.
- `meta.yaml` mirrors stay as they are; the driver's `--rebuild` path does not touch them, a known gap.

## Spec Change Log

- 2026-11-05: minted at `backlog` by marshal Story 113.18.
- 2026-11-05: run, retro `v8.104.0` and read-back recorded; status `done`.
