---
title: "25.15: Six duplicate recipe directories retire into recipes/langflow and recipes/dbt"
type: 'fix'
created: '2026-10-09'
status: 'done'
baseline_revision: a8b46633b9439633007ec114f6f112a83afef7dd
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-5-track-b-batch-1-refreshes-airflow-code-editor-through-django-countries.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-7-track-b-batch-3-refreshes-jhub-apps-through-niquests.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-14-wave-f-s-other-18-packages-are-built-by-their-feedstock-s-own-mirror.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-16-three-dbt-adapter-recipes-are-re-mirrored-from-their-own-feedstocks.md
deferred:
  - summary: >-
      No repo-scope check refuses two recipes/* directories declaring the same package name;
      add a detector with today's remaining duplicates as its starting allowlist.
    evidence: |-
      AC 4 parse at mint listed six langflow-suite declarers plus recipes/dbt-core for dbt-core;
      after this story the parse exits 0 with adapters pending Story 25.16.
    location: >-
      scripts/spec_surface_check.py
    severity: medium
  - summary: >-
      Staged-recipes PRs #33977 (lfx-arxiv) and #33978 (lfx-docling) are superseded by
      langflow-feedstock publishing both bundles; operator closes them.
    evidence: |-
      langflow-feedstock now publishes lfx-arxiv and lfx-docling; PRs still open at AC 1 re-read.
    location: >-
      https://github.com/conda-forge/staged-recipes/pull/33977
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.14's mint found six recipe directories that declare packages another local recipe already
builds, the mirror of the feedstock that publishes them:
- `recipes/lfx`, `recipes/lfx-arxiv`, `recipes/lfx-docling`, `recipes/lfx-duckduckgo` and `recipes/lfx-ibm` each hold
  a copy of `langflow-suite` at 1.11.3 and declare all eight of its outputs. `recipes/langflow`, the mirror of
  `langflow-feedstock`, builds the same eight at 1.11.4.
- `recipes/dbt` and `recipes/dbt-core` both build `dbt-core` 1.12.2.

No repo check refuses this. The copies drift: they sit a version behind. They also mislead. Story 25.2's Wave A matched
the four bundles to these directories by name and bucketed them `v1-ahead`, and Story 25.7 had queued `recipes/lfx` for
a refresh of its own. The operator ruled on 2026-10-09, choosing "Retire in a fix story": "Mint a mason fix story that
removes the six duplicate dirs (folded into recipes/langflow and recipes/dbt-core) and drops recipes/lfx from 25.7's
batch." This is that story.

**Re-scope (2026-10-10), on two operator rulings of 2026-10-09.** The mint retired five directories and left two open
questions (§ *Open questions*). The operator answered both, choosing these options:
- Open question 1, "Retire recipes/dbt-core": "Keep recipes/dbt as the dbt-feedstock mirror, retire recipes/dbt-core,
  and re-point batch 25.5's dbt-core row to recipes/dbt. Added to Story 25.15."
- Open question 2, "Fix in a story": "Mint a mason fix story that re-mirrors the three adapter recipes from
  dbt-bigquery/postgres/redshift-feedstock (dbt-bigquery-feedstock is now v1 at 1.12.1), and correct batch 25.5's
  table."

So this story now retires six directories: the five `lfx*` copies into `recipes/langflow`, and `recipes/dbt-core` into
`recipes/dbt`. Story 25.16 re-mirrors the three adapters, and this story changes none of them. The heading and this
spec's title change. The ledger key and this file's name keep their mint slug, as Stories 25.2 and 25.7 kept theirs
through their re-scopes: `sprint-ledger-sync` restores a key the feed drops, and only a fold's re-key map moves one.

**Ownership, verified at mint (2026-10-09, read-only GETs).** Before scoping, the mint checked each directory against
three sources: conda-forge's `feedstock-outputs` registry, the atlas's `packages.feedstock_name` (atlas built
2026-10-09), and `gh api repos/conda-forge/<dir>-feedstock`. The re-scope re-read the dbt rows on 2026-10-10.

| Directory | `conda-forge/<dir>-feedstock` | Registry and atlas owner of the directory's name | What the directory declares | Verdict |
|---|---|---|---|---|
| `recipes/lfx` | 404 | `langflow` | `langflow-suite` 1.11.3, all 8 outputs | retire |
| `recipes/lfx-arxiv` | 404 | `langflow` | the same | retire |
| `recipes/lfx-docling` | 404 | `langflow` | the same | retire |
| `recipes/lfx-duckduckgo` | 404 | `langflow` | the same | retire |
| `recipes/lfx-ibm` | 404 | `langflow` | the same | retire |
| `recipes/dbt-core` | 404 (again on 2026-10-10) | `dbt` (the registry gives `dbt-core` to `dbt` alone) | `dbt-core` 1.12.2 in `recipe.yaml`; 1.8.9 in a v0 `meta.yaml` | **retire** (re-scope, 2026-10-10) |
| `recipes/dbt` | **exists**: v1, `main` at `8f2435b850` (2026-09-19), publishes `dbt-core` 1.12.5 | `dbt` (the registry gives `dbt` and `dbt-core` to `dbt`) | `dbt-core` 1.12.2 | **kept**: the survivor |

The registry gives `langflow`, `langflow-base`, `langflow-sdk`, `lfx` and the four `lfx-*` bundles to `langflow` alone.
`langflow-suite` has no entry, because it is a recipe name, not a package. The atlas agrees on every name.

**Why `recipes/dbt` is kept.** It is the local mirror of a real conda-forge feedstock of its own name.
`conda-forge/dbt-feedstock` exists and builds `dbt-core`. The repo's mirror path is `recipes/<feedstock>/` (Story 17.1;
`recipes/langflow` and `recipes/db-gpt` follow it), and `recipes/dbt` is that directory. Its `extra.feedstock-name` is
`dbt`, and its CFE block names `https://github.com/conda-forge/dbt-feedstock`. The 2026-08-20 inventory commit
(`d204da00fd`) stamped that block and dropped the directory's v0 `meta.yaml`, as C2 says for a v1 feedstock.
`recipes/dbt-core`, by contrast, has no feedstock of its own name (404) and no CFE block. It still carries the 1.8.9
`meta.yaml` that both directories held at the repo's first commit. Retiring `recipes/dbt` would delete the dbt-feedstock
mirror and keep the misnamed copy. So the mint left both dbt directories alone and asked the operator (open question
1). The answer, "Retire recipes/dbt-core", retires `recipes/dbt-core` into `recipes/dbt`.

**What the five carry that `recipes/langflow` lacks (G53 superset, read at mint).**
- Maintainers: `rxm7706` and `pb01ka` in all six directories.
- Outputs, tests and patches: `recipes/langflow` has every output and test of the five. It adds a py3.14 import test,
  two runtime checks and patches 0004 and 0005. The five list patches 0001 to 0003 but carry no `patches/` directory,
  so none of them builds as it stands. (Since 2026-09-25, `langflow-feedstock` carries no patches at all; its
  `patch_deps.py` does their work. Story 25.7's AC 12 takes that into `recipes/langflow`.)
- Pins: the only differences are older pins that `recipes/langflow` loosened on purpose. In `langflow-base`,
  `bcrypt ==4.0.1` is now `>=4.0.1,<5` and `onnxruntime >=1.20,<1.24` is now `>=1.20`. In the `run_constraints` of
  `langflow-base` and `langflow`, `langchain-chroma >=0.2.6,<0.3.0` is now `<2.0.0`.
- Files: each holds a `LICENSE`, the monorepo's MIT text. `recipes/langflow` pruned its copy on purpose, and
  `langflow-feedstock`'s `recipe/` carries none (G94).
- CFE records, all stale. `recipes/lfx` reads `blocked-pending-prerequisites`. The four bundles read
  `pending-approval-on-conda-forge` and name staged-recipes PRs #33977 to #33980. Read live at mint: #33977
  (`lfx-arxiv`) and #33978 (`lfx-docling`) are still open, authored by `rxm7706`, though `langflow-feedstock` now
  publishes both bundles. #33979 and #33980 are closed.

**What `recipes/dbt-core` carries that `recipes/dbt` lacks (G53 superset, read 2026-10-10).**
- `recipe.yaml`: the same as `recipes/dbt`'s outside the CFE block. `recipes/dbt` quotes the version (`"1.12.2"`) and
  carries the block; `recipes/dbt-core` has neither. Source, sha256, requirements, `run_constraints`, tests and `about`
  are equal.
- Maintainers: the same six in both, `rxm7706`, `drewbanin`, `jthandy`, `maresb`, `thewchan` and `zaneselvans`. That
  is `dbt-feedstock`'s deployed list.
- Files: `License.md` is byte-identical in both. `dbt-feedstock`'s `recipe/` carries no licence file (the recipe reads
  `LICENSE` from the sdist), so `recipes/dbt`'s copy is Story 25.5's to prune when it refreshes the mirror (G94).
- `meta.yaml`: only `recipes/dbt-core` keeps the first commit's v0 `meta.yaml`, `dbt-core` 1.8.9. The feedstock is v1,
  so nothing of it is folded (C2).

So nothing needs folding, into either survivor. Each item is recorded instead (AC 2).

**One file both dbt directories lack.** Both `recipe.yaml` files list `0001-drop-experimental-parser-hard-dep.patch`,
and neither directory carries it, so neither builds as it stands. `dbt-feedstock`'s `recipe/` carries it. The file
last changed in `93e6e06988` (2026-08-15), the feedstock commit whose `recipe.yaml` `recipes/dbt` mirrors: `dbt-core`
1.12.2, build 0, equal but for the schema header, the quoted version and a trailing blank line. It is unchanged on the
feedstock's `main` (`8f2435b850`, 1.12.5). This story restores it into `recipes/dbt` (AC 11), so the survivor builds.
The refresh to 1.12.5 stays Story 25.5's.

**Other references to the five paths (read at mint).** `git grep` finds the five paths in three kinds of place only:
- planning records: `epics.md`, the Epic 25 story specs, memlogs, and the Dream's realization log;
- the verbatim archive `archive/docs/specs/langflow-conda-forge.md`, with five `blob/main/recipes/lfx*` links;
- warden's validation corpus, `src/shared/packages/pyforge-warden/tests/fixtures/corpus/recipes/lfx*`. It is a frozen
  harvest snapshot that only warden re-harvests, and its hashes sit in `scripts/.spec-surface-baseline.json`.

No doc, manifest, test, CFE allowlist, workflow or data file names them. The refresh-wave manifests and reports are
gitignored, and the primary checkout held none at mint. The re-scope's read (2026-10-10) finds `recipes/dbt-core` in
the same kinds of place only: planning records, and warden's corpus (`.../corpus/recipes/dbt-core/meta.yaml`) with its
baseline hash.

**Approach:**
1. Re-read the registry, the atlas and the feedstocks live (AC 1), and repeat both superset comparisons (AC 2).
2. Restore `recipes/dbt`'s missing patch file from its feedstock (AC 11).
3. Remove the six directories in one commit (AC 3).
4. Prove each name has one declarer (AC 4), and that no reference to the six paths remains (AC 5).
5. Validate and build `recipes/langflow` and `recipes/dbt` (AC 6), and check that the dbt arm stayed in its two
   directories (AC 7).
6. File the follow-ups (AC 9), and close with the Rule-2 retro (AC 10).

Ledger key: `25-15-five-duplicate-langflow-suite-directories-retire-into-recipes-langflow`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57), the refresh campaign; CAP-20, the recurring campaigns; CAP-23, the CFE
  machinery. No new CAP, so no FR moves.
- AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in the `retro(cfe):` commit).
- CFE Rule 1 and Rule 2; G52, G53, G72 (a suite owns its folded siblings' outputs) and G94 (prune what the feedstock
  no longer has); SKILL.md § *Local-mirror fidelity*.
- `spec-fleet-stewardship` CAP-1 (`recipes/<feedstock>/`, absorbed into `spec-pyforge-mason`) governs `recipes/**`, with
  `surface-drift: exempt`; `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q1: a fix carries no flag.
- Siblings: Story 25.7 refreshes `recipes/langflow`, and no longer `recipes/lfx`. Story 25.14 depends on this story.
  Story 25.5 refreshes `recipes/dbt` to its published version after this story (its Deps S-25.15), and no longer names
  `recipes/dbt-core` or `recipes/dbt-bigquery`. Story 25.16 re-mirrors `recipes/dbt-bigquery`, `recipes/dbt-postgres`
  and `recipes/dbt-redshift`. Neither of 25.15 and 25.16 waits for the other (AC 4).

## Acceptance Criteria

1. **Ownership re-read first.** Given the six directories When the story starts Then § *Run results* records, before
   any file changes:
   - for each of the eight names `recipes/lfx` declares, and for `dbt-core` and `dbt`, its `feedstock-outputs` entry
     (`https://raw.githubusercontent.com/conda-forge/feedstock-outputs/main/outputs/<c1>/<c2>/<c3>/<name>.json`) and its
     atlas `packages.feedstock_name`;
   - for each of the six directory names, and for `dbt`, the HTTP status of `gh api repos/conda-forge/<dir>-feedstock`.

   A directory whose own name has become a conda-forge feedstock is not removed. Neither is one that declares a name
   the registry no longer gives to its survivor's feedstock alone: `langflow` for the five `lfx*` copies, `dbt` for
   `recipes/dbt-core`. Either is recorded `kept`, with the entry that kept it.
2. **Nothing lost (G53 superset).** Given each directory to remove and its survivor (`recipes/langflow` for the five
   `lfx*` copies, `recipes/dbt` for `recipes/dbt-core`) When the story compares their maintainers, each output's
   `requirements` (`build`, `host`, `run`, `run_constraints`), tests, patches, recipe-directory files and `about` Then
   each item a removed directory has and its survivor lacks ends one of two ways:
   - folded into the survivor through conda-forge-expert, in its own commit before the removal;
   - or recorded in § *Run results* with its reason.

   The reads in § *Intent* found nothing to fold. A fold that changes a survivor is rebuilt under AC 6.
3. **The six directories are gone.** Given the removal commit When
   `git ls-files -- recipes/lfx recipes/lfx-arxiv recipes/lfx-docling recipes/lfx-duckduckgo recipes/lfx-ibm recipes/dbt-core`
   runs Then it prints nothing, and none of the six exists in the working tree. The removal is one `git rm -r` commit
   with a `recipes: …` subject. `git diff --name-only origin/main...HEAD -- recipes/` lists only files under the six
   directories and under `recipes/dbt/` (AC 7), plus `recipes/langflow/` if AC 2 folded anything.
4. **One declarer per name.** Given the tree after the removal When the § *Verification* parse runs over every
   `recipes/*/recipe.yaml`, and every `meta.yaml` with no `recipe.yaml` beside it, reading `package.name` and each
   `outputs[].package.name` Then it exits 0:
   - each of `langflow-sdk`, `lfx`, `lfx-duckduckgo`, `lfx-arxiv`, `lfx-ibm`, `lfx-docling`, `langflow-base` and
     `langflow` is declared by `recipes/langflow` alone, whose `extra.feedstock-name` is `langflow`;
   - `dbt-core` is declared by `recipes/dbt`, whose `extra.feedstock-name` is `dbt`, and otherwise only by those of
     `recipes/dbt-bigquery`, `recipes/dbt-postgres` and `recipes/dbt-redshift` that Story 25.16 has not yet
     re-mirrored. The parse prints them. Once 25.16 has landed, `recipes/dbt` alone declares `dbt-core`.

   At mint the parse exited 1 and named six directories for each suite name. At the re-scope it also names
   `recipes/dbt-core` for `dbt-core`. § *Run results* records the command, its output and its exit code.
5. **No reference to the removed paths.** Given the tree after the removal When this command runs Then it finds nothing
   (exit 1):

   ```bash
   git grep -nE 'recipes/(lfx|lfx-arxiv|lfx-docling|lfx-duckduckgo|lfx-ibm|dbt-core)([^-a-z0-9_.]|$)' -- . \
     ':(exclude)archive/**' ':(exclude)docs/dreams/**' \
     ':(exclude,glob)_bmad-output/projects/*/planning-artifacts/**' \
     ':(exclude)src/shared/packages/pyforge-warden/tests/fixtures/corpus/**' \
     ':(exclude)scripts/.spec-surface-baseline.json'
   ```

   The exclusions are records, not references. Planning artifacts and the Dream are the dated decision record.
   `archive/` stays verbatim (`archive/docs/README.md`). Warden's corpus is a frozen harvest snapshot under its own
   path, and only warden re-harvests it. A gitignored refresh-wave manifest or report under
   `.claude/data/conda-forge-expert/feedstock-update/` or `.claude/data/conda-forge-expert/refresh-waves/` that names
   a removed directory is listed in § *Run results*; it stays local.
6. **The survivors validate and build.** Given `recipes/langflow` and `recipes/dbt` after the removal When these run
   for each Then none reports an error, and an expected finding is recorded with its reason:
   - `pixi run -e local-recipes validate recipes/<dir>`;
   - `pixi run -e local-recipes lint-optimize recipes/<dir>`;
   - `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/<dir>`.

   Then a linux-64 `rattler-build build --recipe recipes/<dir>/recipe.yaml --output-dir <isolated dir>` exits 0 for
   each: all eight outputs of `recipes/langflow`, and `dbt-core` 1.12.2 from `recipes/dbt` with its import, `pip_check`
   and `dbt --help` tests. Each resolves from conda-forge, never from a shared local channel (G52). If a test
   environment cannot solve, the block is recorded as G95 says. § *Run results* records each command's exit code and
   the package files. `recipes/langflow`'s `cfe-local-build-*` fields change only if AC 2 changed the recipe: Stories
   25.7 and 25.14 own its refresh. `recipes/dbt`'s record this build, since AC 11 changed the directory.
7. **The dbt arm stays in its two directories.** Given the story's diff When
   `git diff --name-only origin/main...HEAD -- recipes/dbt recipes/dbt-core recipes/dbt-bigquery recipes/dbt-postgres recipes/dbt-redshift recipes/dbt-snowflake`
   runs Then it lists only `recipes/dbt-core/`'s removed files and, under `recipes/dbt/`, the restored patch file
   (AC 11), `recipe.yaml` for AC 6's `cfe-local-build-*` fields, and an AC 2 fold if there was one. `recipes/dbt` keeps
   its version, `build.number`, requirements and maintainers: Story 25.5 refreshes it to the published version.
   (Amended 2026-10-10. At mint this AC kept both dbt directories untouched until open question 1 was answered.)
8. **Nothing leaves the local repo.** Given the story's whole run When it closes Then no `git push`, `gh pr create`,
   `gh repo fork` or `gh api` write reached anything outside `rxm7706/local-recipes`; no issue or comment was opened,
   and staged-recipes PRs #33977 and #33978 were neither closed nor commented; no `mason recipe submit` or
   `mason package ship` and no CFE `submit_pr` or `prepare_submission_branch` ran.
9. **Follow-ups filed, not built.** Given the story closes When it files its findings Then this spec's `deferred:`
   frontmatter carries a row for each of these, unless the mason deferred-work ledger already names it:
   - The missing duplicate-output guard. No repo check refuses two `recipes/*` directories that declare one package
     name. The row proposes a repo-scope check that reds a new duplicate, with today's duplicates as its starting
     allowlist. It records the parse's repo-wide count at run time: 110 names at mint, `dbt-core` among them in five
     directories. This story and Story 25.16 bring `dbt-core` to one.
   - Staged-recipes PRs #33977 and #33978. `langflow-feedstock` publishes both bundles, so the PRs are superseded, and
     only the operator closes them.

   The story builds no guard and touches no PR.
10. **Retro and suite.** Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a
    CFE `CHANGELOG.md` semver entry, with the four version carriers in lockstep. It is PATCH, or MINOR if it adds a
    gotcha. A candidate: a second directory that declares a feedstock's outputs is a duplicate to retire, not a
    mirror, so check the registry before refreshing or creating one. If another Epic 25 story's retro reached `main`
    first, this one takes the next version when it merges `main`. Also
    `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.
11. **`recipes/dbt` gains its feedstock's patch.** Given `recipes/dbt/recipe.yaml` lists
    `0001-drop-experimental-parser-hard-dep.patch` and the directory lacks it When the story restores it Then
    `recipes/dbt/0001-drop-experimental-parser-hard-dep.patch` is byte-identical to `conda-forge/dbt-feedstock`'s
    `recipe/` copy at the commit whose `recipe.yaml` `recipes/dbt` mirrors (`93e6e06988` at the re-scope; the file is
    unchanged on `main` since), read live. § *Run results* records that commit and the file's sha256. The restore lands
    in its own `recipes: …` commit before the removal, and moves no version, `build.number`, requirement or
    maintainer. If the patch does not apply to the 1.12.2 sdist, AC 6 records the failure with its reason, and the
    retirement still stands: `recipes/dbt-core` carries the same recipe and builds no better.

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1): § *Local-mirror fidelity*, G52, G53, G72 and G94.
   Where this spec and the skill differ, the skill wins, and the story records the difference.
2. Re-read the registry entries, the atlas rows and the feedstock repos live (AC 1).
3. Repeat both superset comparisons, and fold or record each item (AC 2).
4. Restore `recipes/dbt`'s patch file from `dbt-feedstock` in its own commit (AC 11).
5. `git rm -r` the six directories in one commit (AC 3), never with a subject starting `Story 25.15:`.
6. Run the parse (AC 4) and the reference grep (AC 5), and check the gitignored refresh-wave data.
7. Validate, lint and build `recipes/langflow` and `recipes/dbt`, each into an isolated output directory (AC 6). Check
   the dbt arm's diff (AC 7).
8. File the follow-ups (AC 9). Close with the Rule-2 retro in its own commit, subject `retro(cfe): v<x.y.z> — …`
   (AC 10).
9. Reconcile every Spec `spec-surface-check` names: memlog first, then `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement. Where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.
- Read the registry, the atlas and the feedstocks only: raw files, or `gh api` GETs.

**Never:**
- Nothing reaches conda-forge, a feedstock or staged-recipes. No `git push`, `gh pr create`, `gh repo fork` or
  `gh api` write outside `rxm7706/local-recipes`; no issue, comment, PR close or review; no `mason recipe submit` or
  `mason package ship`; no CFE `submit_pr` or `prepare_submission_branch`.
- Do not remove a directory AC 1 records `kept`.
- Touch `recipes/dbt/` only for AC 11's restore, an AC 2 fold and AC 6's build record. Its refresh to the published
  version is Story 25.5's, which runs after this story.
- Do not touch any other recipe directory. `recipes/dbt-bigquery`, `recipes/dbt-postgres` and `recipes/dbt-redshift`
  are Story 25.16's, and `recipes/dbt-snowflake` is Story 25.13's. Touch `recipes/langflow/` only for an AC 2 fold;
  its refresh is Story 25.7's and Story 25.14's.
- Do not edit warden's corpus, `archive/`, or a planning record's history to clear AC 5.
- Do not build the duplicate-output guard. AC 9 files it.
- Do not edit any CFE file outside the `retro(cfe):` commit. Do not touch `src/shared/packages/pyforge-mason/`,
  `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | six copies, nothing newer than their survivors | patch restored; six removed in one commit; parse exits 0; both survivors build | — |
| a copy gained a feedstock | `conda-forge/<dir>-feedstock` now exists, or its registry entry moved | recorded `kept` with the entry; not removed | AC 1 |
| a copy carries something newer | a pin, test, patch or maintainer its survivor lacks | folded through CFE before the removal, then rebuilt | AC 2, AC 6 |
| 25.7 landed first | `recipes/langflow` at 1.12.4, with `patch_deps.py` | the parse and the build run on the refreshed suite | — |
| 25.16 not landed | the three adapters still declare `dbt-core` | the parse lists them and allows them | AC 4 |
| 25.16 landed first | the adapters declare only their own names | `recipes/dbt` alone declares `dbt-core` | AC 4 |
| patch moved on | the feedstock's patch file changed after `93e6e06988` | the copy at the commit `recipes/dbt` mirrors; both hashes recorded | AC 11 |
| patch does not apply | the 1.12.2 sdist rejects the restored patch | the build failure recorded; the retirement stands | AC 6, AC 11 |
| test env pollution | a dependency solve fails for a package on conda-forge | rebuild isolated before recording a block | G52 |
| a new reference appears | a doc or manifest names a removed path at run time | edited to name the survivor, or recorded if it is a record | AC 5 |
| other duplicates | names two or more other directories declare | listed in § *Run results*; not acted on | AC 9 |

## Open questions

1. **Which directory mirrors `dbt-feedstock`?** Ruling 2 named `recipes/dbt-core` the survivor. But `recipes/dbt` is
   the `recipes/<feedstock>/` mirror of `conda-forge/dbt-feedstock` (§ *Intent*), so this story keeps both and changes
   neither. Neither directory carries the feedstock's `0001-drop-experimental-parser-hard-dep.patch`, which both
   recipes list. *Recommended:* keep `recipes/dbt` as the mirror, and retire `recipes/dbt-core` instead, in a fix
   story or by re-scoping this one. Story 25.5's `dbt-core` row would then refresh `recipes/dbt`. *Alternative:* keep
   `recipes/dbt-core` and retire `recipes/dbt`, as ruling 2 reads. The dbt-feedstock mirror then lives under its
   package's name, and the CFE block moves with it.
   **Resolved 2026-10-09, operator ruling "Retire recipes/dbt-core":** "Keep recipes/dbt as the dbt-feedstock mirror,
   retire recipes/dbt-core, and re-point batch 25.5's dbt-core row to recipes/dbt. Added to Story 25.15." This story
   is re-scoped to six directories (§ *Intent*, ACs 1 to 7 and 11). Story 25.5's row now names `recipes/dbt`, and
   25.5 depends on this story.
2. **Three dbt adapter recipes carry `dbt-core`'s recipe.** The parse behind AC 4 also finds `recipes/dbt-bigquery`,
   `recipes/dbt-postgres` and `recipes/dbt-redshift` declaring `dbt-core`. Each `recipe.yaml` is a copy of the
   dbt-feedstock recipe (`context.name: dbt-core`, `extra.feedstock-name: dbt`, a `dbt_core` source URL) under a CFE
   block for the adapter. The 2026-08-16 identity snapshot (`20b2f459fa`) wrote all three. Each adapter has a feedstock
   of its own: `dbt-bigquery`'s is now v1 at 1.12.1, and `dbt-postgres`'s and `dbt-redshift`'s are v0. These are
   wrong mirrors, not duplicates, so ruling 2 does not cover them. Story 25.5 refreshes `recipes/dbt-bigquery`, and its
   dry-run will meet a `dbt-core` recipe there. *Recommended:* re-mirror the three from their own feedstocks:
   `dbt-bigquery` inside Story 25.5, and the other two in a fix story. This story records them in AC 4's list and
   changes none of them.
   **Resolved 2026-10-09, operator ruling "Fix in a story":** "Mint a mason fix story that re-mirrors the three adapter
   recipes from dbt-bigquery/postgres/redshift-feedstock (dbt-bigquery-feedstock is now v1 at 1.12.1), and correct
   batch 25.5's table." Story 25.16 is that fix and takes all three, `dbt-bigquery` included, so `dbt-bigquery` left
   Story 25.5's batch. This story still changes none of them, and its AC 4 allows them as `dbt-core` declarers until
   25.16 lands.

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57), with CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 (night, latest) — Ruled: Wave F stays inside
the mirrors, and five duplicate directories retire*, and *2026-10-10 — Ruled: recipes/dbt-core retires into
recipes/dbt, and the three dbt adapters are re-mirrored*.
Ledger key: `25-15-five-duplicate-langflow-suite-directories-retire-into-recipes-langflow`.
Ledger status at mint: `backlog`.
Deps: none. Stories 25.14 and 25.5 depend on this story; see their Deps notes.
Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1).
Minted 2026-10-09 on the operator's ruling of that day ("Retire in a fix story"). One of the six directories the ruling
named, `recipes/dbt`, was excluded at mint, with the reason in § *Intent*.
Re-scoped 2026-10-10 on the operator's rulings of 2026-10-09, "Retire recipes/dbt-core" and "Fix in a story":
`recipes/dbt-core` joins the retirement (six directories), `recipes/dbt` gains its feedstock's patch file (AC 11), and
the three adapters go to Story 25.16. The title changed; the ledger key and this file's name kept their mint slug.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test`. Expected: pass. This is the station's `verify_commands`;
  the story changes no Mason code.
- The AC 4 parse, from the repo root. Expected: exit 0 after the removal; exit 1 at mint and at the re-scope.

  ```bash
  python - <<'EOF'
  import collections, pathlib, re, sys, yaml
  suite = {"langflow-sdk", "lfx", "lfx-duckduckgo", "lfx-arxiv", "lfx-ibm", "lfx-docling", "langflow-base", "langflow"}
  owner = {**{n: "langflow" for n in suite}, "dbt-core": "dbt"}
  # Story 25.16 re-mirrors these three; until it lands, each still declares dbt-core.
  adapters = {"dbt-bigquery", "dbt-postgres", "dbt-redshift"}
  hits = collections.defaultdict(set)
  for p in sorted(pathlib.Path("recipes").glob("*/recipe.yaml")):
      d = yaml.safe_load(p.read_text()) or {}
      ctx = {k: str(v) for k, v in (d.get("context") or {}).items()}
      names = [(d.get("package") or {}).get("name")]
      names += [(o.get("package") or {}).get("name") for o in d.get("outputs") or []]
      for n in filter(None, names):
          n = re.sub(r"\$\{\{\s*name\s*\|\s*lower\s*\}\}", ctx.get("name", "").lower(), str(n))
          n = re.sub(r"\$\{\{\s*name\s*\}\}", ctx.get("name", ""), n).lower()
          if n in owner:
              hits[n].add(p.parent.name)
  for p in sorted(pathlib.Path("recipes").glob("*/meta.yaml")):
      if (p.parent / "recipe.yaml").exists():
          continue
      for n in re.findall(r"^\s*(?:-\s*)?name:\s*['\"]?([A-Za-z0-9_.-]+)", p.read_text(), re.M):
          if n.lower() in owner:
              hits[n.lower()].add(p.parent.name)
  bad = {}
  for n, mirror in sorted(owner.items()):
      allowed = {mirror} | (adapters if n == "dbt-core" else set())
      if mirror not in hits.get(n, set()) or hits.get(n, set()) - allowed:
          bad[n] = sorted(hits.get(n, ()))
  pending = sorted(hits.get("dbt-core", set()) & adapters)
  if pending:
      print("Story 25.16 pending; still declaring dbt-core:", pending)
  print(bad or "ok: each name is declared by its feedstock's mirror alone")
  sys.exit(1 if bad else 0)
  EOF
  ```

- The AC 5 grep. Expected: exit 1 (no match).

**Manual checks:**
- `git ls-files -- recipes/lfx recipes/lfx-arxiv recipes/lfx-docling recipes/lfx-duckduckgo recipes/lfx-ibm recipes/dbt-core`
  prints nothing.
- `git diff --name-only origin/main...HEAD -- recipes/` lists only the six removed directories and `recipes/dbt/`, plus
  `recipes/langflow/` if AC 2 folded anything. AC 7's diff over the dbt directories lists only what AC 7 names.
- `recipes/dbt/0001-drop-experimental-parser-hard-dep.patch` hashes the same as `dbt-feedstock`'s copy (AC 11).
- For `recipes/langflow` and `recipes/dbt`: `pixi run -e local-recipes validate recipes/<dir>` and
  `pixi run -e local-recipes lint-optimize recipes/<dir>` report no errors; `pixi exec --spec "conda-smithy>=2026.6.14"
  conda-smithy recipe-lint --conda-forge recipes/<dir>` reports no lint (G65); a linux-64 `rattler-build build --recipe
  recipes/<dir>/recipe.yaml --output-dir <isolated dir>` exits 0, or the recorded block is justified.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert`: exactly one `retro(cfe):` subject,
  and that commit carries `CHANGELOG.md`.
- § *Run results* carries the live ownership read, both superset comparisons, the patch restore, the parse and grep
  results, the build outcomes and the filed follow-ups.
- `pixi run -e pyforge-guild spec-surface-check`: exit 0 after the scoped stamps.

## Run results

- **AC 1 (2026-10-10):** `gh api repos/conda-forge/<dir>-feedstock` → 404 for `lfx`, `lfx-arxiv`, `lfx-docling`, `lfx-duckduckgo`, `lfx-ibm`, `dbt-core`; `dbt-feedstock` exists. Retire verdict unchanged from mint/re-scope.
- **AC 2:** G53 superset re-read — nothing to fold (same as § *Intent*).
- **AC 11:** Patch from `dbt-feedstock` @ `93e6e06988`, sha256 `5fe3b04cb11761de056015bf64128838f6a569f5635c52058f26ac2696872c0a`, commit `b5188647fb`.
- **AC 3:** Six directories removed, commit `95547d098f`.
- **AC 4:** Parse exit 0; pending adapters `dbt-bigquery`, `dbt-postgres`, `dbt-redshift` (Story 25.16).
- **AC 5:** Reference grep exit 1 (no matches).
- **AC 6:** `validate`/`conda-smithy recipe-lint` clean for both survivors. `lint-optimize`: `recipes/dbt` exit 0; `recipes/langflow` exit 1 with TEST-001 (parent multi-output recipe — expected, outputs carry tests). Build: `recipes/dbt` rattler-build exit 0 → `dbt-core-1.12.2-pyh5ded981_0.conda`. `recipes/langflow` exit 1 — `lfx` output `pip_check` fails (`pydantic 2.14.0` vs `pydantic<2.14`); pre-existing env pin, not introduced by this story (G95-style block; refresh owned by 25.7/25.14).
- **AC 10:** `pyforge-mason-test` exit 0 after `retro(cfe): v8.99.4` commit `ac78dc275d`.

## Review Triage Log

- **2026-10-10 — Review pass**
  - verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
  - findings: (single-pass review; diff limited to recipe removals, patch restore, CFE retro — no patch items)

## Auto Run Result

- **Summary:** Retired six duplicate recipe directories; restored `recipes/dbt` patch; CFE retro v8.99.4.
- **Files:** See commits `b5188647fb`, `95547d098f`, `ac78dc275d`; memlogs on `spec-packaging-factory` and `spec-pyforge-mason`.
- **Verification:** AC 4/5/6/10 as in § *Run results*; `python scripts/spec_surface_reconcile.py` exit 0; `spec-surface-check` exit 0.
- **Follow-up review:** `followup_review_recommended: false` — no patched review findings.
- **Residual risk:** `recipes/langflow` linux-64 build still fails `pip_check` on `lfx` until refresh stories land; duplicate-output guard and staged-recipes PR closure deferred in frontmatter.
