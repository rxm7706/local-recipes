---
title: "25.22: The in-scope recipes take back what the identity mirror dropped"
type: 'fix'
created: '2026-11-05'
status: 'done'
baseline_revision: '6d52ea19c3'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: recipe-build
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
deferred:
  - id: identity-mirror-out-of-scope-patch-files
    summary: "Outside CAP-35's scope, 249 recipes name a patch file that is not on disk, counted by parsing each recipe's source.patches with templated paths skipped, grpc-cpp among them (recipe at 1.83.0, patches from 1.74.1), so they cannot build locally; and 7 recipes keep patch files their recipe.yaml never names: ansi2html, cassandra-driver, dbus-python, grpc-cpp, pymupdf, python-magic and salt. The campaign builds none of them. Mirror each patch directory from its feedstock when a story needs that recipe."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-22-the-in-scope-recipes-take-back-what-the-identity-mirror-dropped.md:73
    severity: low
  - id: identity-mirror-moved-recipes-backwards
    summary: "The identity mirror moved 17 of 949 comparable recipes to an older version, 11 of them in CAP-35's scope, because each sat ahead of its feedstock. CAP-35 holds a recipe at the published version, so most stand. The one that broke something is reactpy: an operator-directed local-only 2.0.0b13 became 1.1.0, so reactpy-django 6.0.0b1, which pins reactpy >=2.0.0b13 and whose success record dates from 2026-07-14, can no longer solve. Restore the v2 chain or retire reactpy-django."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-22-the-in-scope-recipes-take-back-what-the-identity-mirror-dropped.md:73
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Commit `20b2f459fa` mirrored recipes from their feedstocks and lost things. Story 25.19 found `dataprofiler`, `gibr`
and `datasketches` without their `source.patches`, and `DW-mason-25-19-3` named four more recipes with patch files nothing uses.

**Approach:** Compare each recipe with the commit before the mirror and with its live feedstock. Restore what the feedstock
lists and no note explains, delete a patch file with no use and say why, and rebuild through `refresh-wave`.

Ledger key: `25-22-the-in-scope-recipes-take-back-what-the-identity-mirror-dropped`. Type / Effort / Deps: fix / S / Story 25.21.

### Living CAP citations

- **CAP-35** — the feedstock refresh campaign; its recipes carry their feedstock's pins (G96). This story closes `DW-mason-25-19-3`.

## Acceptance Criteria

- **AC1 — The scan.** The story records what the mirror dropped, by class, with counts, in scope and out.
- **AC2 — The dependencies.** Each in-scope dependency the feedstock lists, that the recipe lacks and that no note explains is restored at the feedstock's spec, at the same version, with `build.number` bumped (G113).
- **AC3 — The patch files.** No in-scope recipe has an unnamed patch file without a recorded reason, and each file `DW-mason-25-19-3` names is reconnected or deleted with its reason.
- **AC4 — The records.** Each changed recipe's `cfe-local-build-*` record is written by a `refresh-wave` build.
- **AC5 — The retro.** A `retro(cfe):` commit carries a CFE `CHANGELOG.md` entry, and `pixi run --frozen -e pyforge-mason pyforge-mason-test` exits 0.

## Boundaries & Constraints

- Recipes only: no CFE script change.
- `dataprofiler`, `gibr` and `datasketches` were fixed by Story 25.19.

**Never:**
- Never write a `cfe-local-build-*` field by hand; never open a feedstock, staged-recipes or upstream PR.

</intent-contract>

## Binding

Parent: `spec-pyforge-mason` CAP-35

- Closes: `DW-mason-25-19-3`.
- Epic: Epic 25.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).

## Run record (2026-11-05)

### AC1: the scan

Against `20b2f459fa~1`, which held 4,119 recipes, and against each live feedstock:

| Class | Found | In scope | Disposition |
|---|---|---|---|
| Patch named before the mirror, not now | 9 recipes | 4 | see below |
| Dependency or constraint the feedstock lists, the recipe lacks, no note explains, same version | 18 on 8 recipes | 18 on 8 | restored |
| Patch file `recipe.yaml` never names | 11 recipes | 2 (`reactpy`, `StringZilla`) | see below |
| Patch file `recipe.yaml` names, not on disk, by parsing `source.patches` | 249 recipes | 0 | deferred |
| Version older than before the mirror | 17 of 949 recipes | 11 | deferred; CAP-35 holds the published version |
| Note names a patch the body does not | 5 recipes | 5 | history; each recipe built |

The in-scope patch findings: `tree-sitter-php` records since Story 25.17 that its patch no longer applies, `langflow` moved to `patch_deps.py`, and `db-gpt` renamed its patches. `pgjdbc`, `smartsheet-python-sdk`, `office2pdf` and `langflow`'s notes describe patches of earlier versions, and all four built in Story 25.19. `reactpy` is below.

The dependency scan parsed `host` and `run`, and a hit counts only if the feedstock lists the name and the recipe's body has it nowhere. So 7 of the 21 raw hits fell away: six sit under a selector the parser skips, and `django-celery-beat`'s `tzdata` has been `python-tzdata` since Story 25.19. The first scan read `run_constraints` as `run` and skipped `run_constrained`; review caught both, and a sweep of the in-scope feedstocks found no other same-version miss of that kind. The scan compares names, so a spec that differs under the same name (`click` against `click >=4.0`) is not in it; that stays G96's gap (`DW-mason-25-17`).

### AC2: the dependencies

| Recipe | Restored | Record before | Record now |
|---|---|---|---|
| `clickclick` | host `six`, `flake8`; run `pyyaml >=3.11`, replacing the C library `yaml` | G95 | `success` |
| `contextvars` | run `immutables >=0.9` | G95 | `success` |
| `sqlalchemy-dremio` | run `pyarrow-all >=20.0.0,<20.1.0`, replacing `pyarrow ~=20.0.0` | G95 | `success` |
| `django-ai-assistant` | `run_constraints` on `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`; the `<4.0` python ceiling | `success` | `success` |
| `pdfplumber` | host `setuptools-scm` | `success` | `success` |
| `pip-audit` | run `html5lib >=1.1`, `toml >=0.10` | `success` | `success` |
| `pydeck` | host `jinja2`, `jupyter`; `run_constraints` on `ipykernel`, `ipywidgets`, `traitlets` | `success` | `success` |
| `weasyprint` | run `pango >=1.44.0`, `glib` | `success` | `success` |

Three recipes moved from G95 to `success`, so the lost dependency was what blocked them. Each spec is the feedstock's, in the feedstock's section, and each recipe's `build.number` moved by one.

### AC3: the patch files

- `StringZilla` (Track A): file kept. Its `recipe.yaml` comments the patch out, exactly as the feedstock's `meta.yaml` does, and the recipe builds without it. Its CFE comments now say so.
- `reactpy` (Track A): file kept, reason recorded in its CFE comments. The patch belongs to the operator-directed local-only 2.0.0b13 recipe, which the mirror replaced with the feedstock's 1.1.0. `reactpy-django` 6.0.0b1's `success` record dates from 2026-07-14, before the mirror, and its `reactpy >=2.0.0b13` no longer solves. Whether v2 returns is the operator's call (deferred).
- `apache-airflow-providers-google` (outside scope): patch deleted. Nothing named it, and the feedstock, now at 22.8.0, carries no patch; the recipe stays at 22.3.0.
- `conda` (outside scope): patch and the stale `meta.yaml` that named it deleted. The feedstock is v1, now at 26.9.4 with no patch, and the recipe is 26.7.0, so C2 drops the `meta.yaml`. The recipe has no CFE block, so the reason lives here.
- `grpc-cpp` (outside scope): left, and deferred with its class. `recipe.yaml` is at 1.83.0 and names patches of that release, while the directory holds 1.74.1's. Deleting three files would leave it as broken as it is.

### AC4: the records

`refresh-wave --apply --gates --build --rebuild --force` ran the 8 recipes in `A-W22-deps` and `B-W22-deps`, on Story 25.21's driver, and `A-W22-review` and `B-W22-review` rebuilt `django-ai-assistant` and `pydeck` after review. Each ended `already-current` with `render: ok` and build `success`, and both runs exited 0, with each build's log in `logs/`. A first pass was discarded by Story 25.21's reviewer (see that story's record), so these are the second builds. `optimize_recipe` exits 1 on `clickclick`, `contextvars`, `pdfplumber`, `pip-audit` and `pydeck`, as it did before. `reactpy`, `apache-airflow-providers-google`, `StringZilla` and `conda` changed no body line, so their records stand.

### Independent review

A separate reviewer found one high, three medium and five low items. The high: `django-ai-assistant` took the three `langchain-*` packages as hard `run` deps, where the feedstock has `run_constraints`, because the scan's parser read that section as `run`. Fixed and rebuilt. Medium: `pydeck`'s `run_constrained` and host `jinja2` were missed; this story's first text claimed `reactpy-django` still solves on a stale record, and its first draft deleted a patch the operator's local-only chain owns; the 227 count was a regex's. All corrected above. Low: the dated comments named Story 25.19, the conda and airflow feedstock versions were stale, and `StringZilla`'s reason sat only here.

## Spec Change Log

- 2026-11-05: minted from `DW-mason-25-19-3` at the operator's "Do this task here".
- 2026-11-05: run and retro `v8.105.0` recorded; status `done`.
- 2026-11-05: review applied.
