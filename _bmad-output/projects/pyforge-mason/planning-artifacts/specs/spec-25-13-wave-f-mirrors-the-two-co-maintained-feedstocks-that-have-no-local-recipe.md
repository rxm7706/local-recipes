---
title: "25.13: Wave F mirrors the two co-maintained feedstocks that have no local recipe"
type: 'feature'
created: '2026-10-09'
status: 'in-progress'
baseline_revision: f05de4bab8500a64631f84d8a9a0dc6bce064295
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - docs/specs/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-9-track-b-batch-5-refreshes-redshift-connector-through-zxing-cpp.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-14-wave-f-s-other-18-packages-are-built-by-their-feedstock-s-own-mirror.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.2's Wave A, on 2026-10-09, put 20 co-maintained packages in the no-local-recipe bucket
(`genuinely_missing_names` in its baseline). That is Track B's Wave F, which `docs/specs/feedstock-refresh.md` Q2
(`<create_missing>`) governed. The operator answered Q2 on 2026-10-09: "create them". A mint-time read of the 20
against the atlas's `packages.feedstock_name` and conda-forge's `feedstock-outputs` registry finds four feedstocks, not
20:
- 18 are outputs of two multi-output feedstocks that already have a local mirror: the 16 `dbgpt-*` of
  `db-gpt-feedstock` (`recipes/db-gpt`) and `langflow-base` and `langflow-sdk` of `langflow-feedstock`
  (`recipes/langflow`). Wave A matched packages to directories by name, so it missed them (Track B landmine 11).
  Story 25.14 takes them, and creates no directory for them.
- **Two are feedstocks of their own with no local recipe in any directory: `dbt-snowflake` and `zxing-cpp-python`.**
  This story mirrors them. Both are co-maintained: each deployed recipe lists `rxm7706` and at least one other
  maintainer, so the mirror keeps every other maintainer's work (G53, and coordination rules 1 to 5 of
  `docs/specs/feedstock-refresh.md` § *Track B*).

**The two.** A live read at mint (2026-10-09, raw GETs and `gh api` GETs only) of each feedstock's `main`:

| Feedstock | Published | Recipe | Deployed maintainers | `recipe/` files | Read at mint |
|---|---|---|---|---|---|
| `conda-forge/dbt-snowflake-feedstock` | 1.12.1, build 1 | v1, `noarch: python`, rattler-build | rxm7706, maresb, thewchan | `recipe.yaml` | `source.url` templated through `${{ name[0] }}` and `${{ name \| replace('-', '_') }}`; `context.name`; a `certifi <2025.4.26` run pin |
| `conda-forge/zxing-cpp-python-feedstock` | 3.1.1, build 2 | v1, compiled (C, C++, scikit-build-core, nanobind), rattler-build | rxm7706, carlodri | `recipe.yaml` | `source.url` on `files.pythonhosted.org/packages/source/z/zxing-cpp/`; imports `zxingcpp`; `conda_build.error_overlinking: true` in its `conda-forge.yml` |

**Known before the run:**

- No `recipes/*/recipe.yaml` or `meta.yaml` on `main` declares a package named `dbt-snowflake` or `zxing-cpp-python`
  (grep at mint). conda-forge's `feedstock-outputs` registry assigns `dbt-snowflake` to both `dbt` and
  `dbt-snowflake`; the `dbt` entry is history, since `dbt-feedstock`'s recipe today builds only `dbt-core`.
- `zxing-cpp-python` is new because conda-forge moved the Python bindings. Until 2026-09-08 `zxing-cpp-feedstock`
  built them under the name `zxing-cpp`. Its PR #10 (merged `44fc37f4b5`) repurposed it to the C++ library, and the
  bindings moved to `zxing-cpp-python-feedstock`. `recipes/zxing-cpp` still holds the old bindings recipe at 2.3.0.
  That directory is Story 25.9's, which now re-mirrors it from the repurposed feedstock (25.9's AC 13). This story
  does not touch it. Until 25.9 lands, two local recipes build the `zxingcpp` module under two package names; nothing
  in `recipes/` depends on either.
- `dbt-snowflake`'s run requirements (`dbt-core`, `dbt-adapters`, `dbt-common`) have local recipes, and Story 25.5
  refreshes `dbt-core`. Its build resolves them from conda-forge into an isolated output directory (G52, landmine 13),
  never from a shared local channel.
- `refresh-wave` refuses a missing directory (`blocked`): the CFE skill keeps create-missing a manual step (SKILL.md
  § *Bulk refresh waves*). This story uses CFE's feedstock tools, not the driver.

**Approach:** mirror first, through conda-forge-expert, one feedstock at a time.
1. Read each feedstock live (AC 1): `lookup_feedstock`, `get_feedstock_context` (open and recent issues are planning
   input, never auto-applied), and its `recipe/` directory by raw GET.
2. Copy the feedstock's `recipe/` directory into `recipes/<feedstock>/` (AC 2). Both feedstocks are v1, so there is no
   `meta.yaml` (C2).
3. Bring it to the CFE bar without overriding a maintainer's choice: canonical `source.url` (AC 3), maintainers
   re-merged (AC 4), the CFE metadata and comments blocks (AC 5).
4. Run the gates (AC 6) and a linux-64 build into an isolated output directory (AC 7).
5. Check that no other recipe declares either name (AC 8). Commit per recipe. Close with the Rule-2 retro (AC 10).

Ledger key: `25-13-wave-f-mirrors-the-two-co-maintained-feedstocks-that-have-no-local-recipe`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57), the refresh campaign: Track B "authors a local mirror where none exists";
  CAP-20, the recurring campaigns; CAP-23, the CFE machinery. No new CAP, so no FR moves.
- AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in the `retro(cfe):` commit).
- CFE G52, G53, G92, G95 and G96; SKILL.md § *Local-mirror fidelity*, § *PyPI `source.url` Must Use the
  `pypi.org/packages/...` Pattern* and step 1b (*Feedstock-aware enrichment*); `docs/specs/feedstock-refresh.md`
  § *Track B* Wave F, coordination rules 1 to 5 and landmines 1 to 13.
- `spec-fleet-stewardship` CAP-1 (the local mirror is the source of truth, `recipes/<feedstock>/`) governs
  `recipes/**`; `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Siblings: Story 25.14 (Deps S-25.13) takes Wave F's other 18 packages and closes Wave F's deferral. Story 25.9 owns
  `recipes/zxing-cpp`. Only the `retro(cfe):` commits of Epic 25's stories meet, at the CFE version carriers.

## Acceptance Criteria

1. **Read live first.** Given the two feedstocks When the story starts Then it reads each one live and records in
   § *Run results*, before any file is written: the published version and build number, the recipe format, the
   deployed `extra.recipe-maintainers`, and every file in the feedstock's `recipe/` directory. A feedstock that has
   published past this spec's version is followed to its live version, and the move is noted. A name that has gained
   a local recipe in any directory by then (by `package.name` or an `outputs[].package.name`) is recorded and not
   created twice.
2. **Mirror first.** Given each feedstock's `recipe/` directory When the story creates `recipes/<feedstock>/` Then
   every file comes from the feedstock, there is no `meta.yaml` (both feedstocks are v1; C2), and the recipe is not
   regenerated by grayskull (`generate_recipe_from_pypi` is never run into `recipes/`). Its only differences from the
   feedstock are those ACs 3 to 5 make, plus grayskull-regression modernization that coordination rule 2 allows. Each
   difference is listed in § *Run results*. A deliberate maintainer choice is kept, such as `dbt-snowflake`'s
   `certifi <2025.4.26` pin and `zxing-cpp-python`'s build backend; a change the story would propose to one is parked
   in the bottom CFE comments block with a `cfe-forge-recipe-updates-needed` token (landmine 12).
3. **Canonical source URL, same bytes.** Given `zxing-cpp-python`'s `files.pythonhosted.org/packages/source/...` URL
   and `dbt-snowflake`'s templated one When each is written Then `source.url` takes CFE's canonical literal form,
   `https://pypi.org/packages/source/<l>/<dist>/<file>-${{ version }}.tar.gz`, with only `${{ version }}`
   interpolated. The sha256 equals the feedstock's, verified by hashing the new URL. The difference from the feedstock
   is parked in the CFE comments block with a `cfe-forge-recipe-updates-needed` token.
4. **Maintainers kept (G53).** Given each new recipe When its `extra.recipe-maintainers` is compared with the deployed
   feedstock's list, read live at run time Then the local list is a superset and includes `rxm7706`. § *Run results*
   records the audit. This spec's lists are the 2026-10-09 read.
5. **CFE metadata, once.** Given each new recipe When the story stamps its CFE block Then it carries the full `cfe-*`
   identity block, including `cfe-conda-name`, `cfe-upstream-registry: pypi`, `cfe-upstream-name`,
   `cfe-on-conda-forge-status: confirmed-on-conda-forge`, `cfe-on-conda-forge-feedstock` (the feedstock URL) and the
   `cfe-local-build-*` fields, with exactly one `#### CFE metadata` header and one `cfe-conda-name` (G92). The bottom
   comments block names the feedstock commit the mirror was taken from.
6. **Gates.** Given each new recipe When `validate_recipe`, `optimize_recipe`, `check_dependencies`,
   `scan_for_vulnerabilities` and `conda-smithy recipe-lint --conda-forge` run Then none reports an error. An expected
   finding is recorded with its reason, such as the fork-only hint that a feedstock of the same name exists.
7. **A linux-64 build, isolated.** Given each new recipe When it is built locally on linux-64 into its own
   `--output-dir` (G52) Then it builds green, with `zxing-cpp-python`'s `zxingcpp` import and `pip_check` passing, or
   its `cfe-local-build-*` fields record `build-clean-test-blocked` (G95) or `not-attempted` with the reason.
   `dbt-snowflake`'s test environment resolves `dbt-core`, `dbt-adapters` and `dbt-common` from conda-forge, never from
   a shared local channel.
8. **One recipe per package name.** Given the two new directories When the story closes Then a parse of every
   `recipes/*/recipe.yaml` and `meta.yaml` (`package.name` and each `outputs[].package.name`) finds `dbt-snowflake`
   and `zxing-cpp-python` each declared by exactly one directory, its own mirror. The story records the parse command
   and its result in § *Run results*.
9. **Nothing leaves the local repo.** Given the story's whole run When it closes Then no `git push`, `gh pr create`,
   `gh repo fork` or `gh api` write reached anything outside `rxm7706/local-recipes`; no issue or comment was opened;
   no `mason recipe submit` or `mason package ship` and no CFE `submit_pr` or `prepare_submission_branch` ran.
10. **Retro and suite.** Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands
    a CFE `CHANGELOG.md` semver entry, with the four version carriers in lockstep: PATCH, or MINOR for a new gotcha
    (a candidate: a feedstock repurposed to a new identity, as `zxing-cpp` was, which a version-only refresh misses).
    If another Epic 25 story's retro reached `main` first, this one takes the next version when it merges `main`. Also
    `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1): § *Local-mirror fidelity*, step 1b, § *PyPI
   `source.url` Must Use the `pypi.org/packages/...` Pattern*, G52, G53 and G92; and `docs/specs/feedstock-refresh.md`
   § *Track B* (Wave F, coordination rules 1 to 5, landmines 1 to 13). Where the file, this spec and the skill differ,
   the skill wins, and the story records the difference.
2. Read both feedstocks live and record them (AC 1).
3. For each feedstock: copy its `recipe/` directory into `recipes/<feedstock>/` (AC 2); write the canonical
   `source.url` and verify the sha256 (AC 3); run `enrich_from_feedstock` and audit maintainers (AC 4); stamp the CFE
   block (AC 5).
4. Run the gates (AC 6) and the isolated linux-64 build (AC 7), at most 4 builds at once.
5. Run the package-name parse (AC 8) and record every outcome in § *Run results*.
6. Review every diff, then commit per recipe: `recipes: …`, never a subject starting `Story 25.13:`.
7. Close with the Rule-2 retro in its own commit, subject `retro(cfe): v<x.y.z> — …` (AC 10).
8. Reconcile every Spec `spec-surface-check` names: memlog first, then `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement. Where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.
- Keep `cfe-*` metadata in the local recipe. It is stripped only if a PR is ever asked for (G62).
- Read feedstocks only: raw files, or `gh api` GETs.

**Never:**
- Nothing reaches conda-forge, a feedstock or staged-recipes. No `git push`, `gh pr create`, `gh repo fork` or
  `gh api` write outside `rxm7706/local-recipes`; no issue or comment; no `mason recipe submit` or
  `mason package ship`; no CFE `submit_pr` or `prepare_submission_branch`.
- Do not drop a co-maintainer from any `recipe-maintainers` list, and never self-merge on a co-maintained feedstock.
- Do not touch a recipe directory other than `recipes/dbt-snowflake/` and `recipes/zxing-cpp-python/`. In particular,
  `recipes/zxing-cpp` is Story 25.9's, `recipes/dbt` (which builds `dbt-core`) is Story 25.5's, `recipes/dbt-core`
  is Story 25.15's to retire, `recipes/dbt-bigquery`, `recipes/dbt-postgres` and `recipes/dbt-redshift` are Story
  25.16's, and `recipes/db-gpt` and `recipes/langflow` are Story 25.14's. (Amended 2026-10-10 on the operator's
  rulings of 2026-10-09; this line named `recipes/dbt-core` as Story 25.5's.)
- Do not create a directory for any of Wave F's other 18 packages (Story 25.14).
- Do not edit `refresh_wave.py`, or any CFE file outside the `retro(cfe):` commit. Do not touch
  `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | v1 feedstock, two or three maintainers | mirrored; every maintainer kept; build green | — |
| feedstock moved on | published past this spec's version | mirrored at the live version, noted | landmine 1 (tag numbering) |
| name appeared locally | a directory now declares the package | recorded; not created twice | AC 1, AC 8 |
| URL form | `files.pythonhosted.org/packages/source/...` or a templated path | canonical literal URL, sha256 unchanged | needs-review on a hash mismatch |
| deliberate pin | `certifi <2025.4.26` | kept; any proposal parked in the CFE comments block | coordination rule 2 |
| licence differs | `enrich_from_feedstock` aborts on a licence mismatch | stop for that recipe, record the abort reason | never pick a side silently |
| test env pollution | a dependency solve fails for a package on conda-forge | rebuild isolated before recording a block | G52, landmine 13 |
| bindings under two names | `recipes/zxing-cpp` (25.9's) still builds `zxingcpp` | recorded; not touched here | Story 25.9 AC 13 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57), with CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 (night, later) — Ruled: Wave F creates the
missing mirrors, and the 18 outputs stay in their feedstock's mirror*.
Ledger key: `25-13-wave-f-mirrors-the-two-co-maintained-feedstocks-that-have-no-local-recipe`.
Ledger status at mint: `backlog`.
Deps: none.
Flag: `flag-exempt: recipe-build` (a recipe build ships no runtime capability behind a flag).
Minted 2026-10-09 on the operator's answer to Track B Q2 ("create them").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test`. Expected: pass. This is the station's `verify_commands`;
  the story changes no Mason code.

**Manual checks:**
- For each of `recipes/dbt-snowflake` and `recipes/zxing-cpp-python`: `pixi run -e local-recipes validate
  recipes/<dir>` and `pixi run -e local-recipes lint-optimize recipes/<dir>` report no errors, and a linux-64
  `rattler-build build --recipe recipes/<dir>/recipe.yaml --output-dir <isolated dir>` exits 0, or the recorded block
  is justified.
- `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/<dir>`: no lint (G65).
- `git diff --name-only origin/main...HEAD -- recipes/` lists only `recipes/dbt-snowflake/` and
  `recipes/zxing-cpp-python/`.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert`: exactly one `retro(cfe):` subject,
  and that commit carries `CHANGELOG.md`.
- § *Run results* carries the live read, each difference from the feedstock, the maintainer audit, the build outcome
  and the package-name parse.
- `pixi run -e pyforge-guild spec-surface-check`: exit 0 after the scoped stamps.

## Run results

- Not run yet.

## Review Triage Log

- No review has run yet.
