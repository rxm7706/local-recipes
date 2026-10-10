---
title: "25.7: Track B batch 3 refreshes jhub-apps through niquests"
type: 'feature'
created: '2026-10-09'
status: 'done'
baseline_revision: '2d90c634f324c68d67a41a3e0e9477061113a8f8'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/refresh_wave.py
  - docs/specs/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-3-cfe-gains-a-tracked-bulk-recipe-refresh-driver-that-the-refresh-waves-run-through.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-4-wave-0-s-leftover-recipes-end-repaired-or-carry-a-recorded-reason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-15-five-duplicate-langflow-suite-directories-retire-into-recipes-langflow.md
deferred:
  - summary: "refresh-wave maintainer union can insert a list item under the CFE header when recipe-maintainers was empty before merge"
    location: ".claude/skills/conda-forge-expert/scripts/refresh_wave.py"
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.2's Wave A, on 2026-10-09, found 96 co-maintained recipes behind their feedstock's published
version (the v1-refresh bucket). Its pilots refreshed four. The operator then re-scoped 25.2 to Wave 0 and those
pilots, and split the other 92 into eight batch stories, each small enough for one dispatch ("Land 25.2 now, split
rest", 2026-10-09). This is batch 3 of 8: 10 recipes, alphabetically, outside the OpenTelemetry family. It was
minted with 11, and the ruling note below the table drops `recipes/lfx`. Every one is co-maintained: the deployed feedstock lists `rxm7706` and at least one other maintainer. So the refresh
keeps every other maintainer's work (G53, and coordination rules 1 to 5 of `docs/specs/feedstock-refresh.md` § *Track
B*).

**The batch.** Versions and maintainer lists are Wave A's snapshot of 2026-10-09; the dry-run reads each feedstock
live. The last column is a read of `main` at mint (`02167e79f4`), a static read of each recipe that the dry-run
supersedes.

| Recipe | Local → published | Feedstock | Deployed maintainers | Before the dry-run |
|---|---|---|---|---|
| `jhub-apps` | 2026.8.1 → 2026.9.1 | v1 | aktech, costrouc, dcmcand, rxm7706 | no CFE block; `${{ name… }}` in `source.url` |
| `json5` | 0.15.0 → 0.16.0 | v0: keep `meta.yaml` (C1) | ian-r-rose, rxm7706 | — |
| `kedro-dagster` | 0.8.0 → 0.8.1 | v1 | gtauzin, rxm7706 | no CFE block; `${{ name… }}` in `source.url` |
| `kedro-viz` | 12.4.0 → 12.5.0 | v1 | cshaley, elanqo, millsks, rxm7706, zaigner | — |
| `langchain-litellm` | 0.7.0 → 0.11.0 | v1 | pb01ka, rxm7706 | — |
| `langflow` | 1.11.4 → 1.12.4 | v1 | pb01ka, rxm7706 | multi-output `langflow-suite` (also builds `lfx`, `langflow-base`, `langflow-sdk`); five local patches, which the feedstock replaced with `patch_deps.py` (AC 12) |
| `llm` | 0.31 → 0.36 | v1: drop the local `meta.yaml` (C2) | pavelzw, rxm7706 | no CFE block; `${{ name… }}` in `source.url` |
| `milvus-lite` | 3.0 → 3.2.1 | v1 | pb01ka, rxm7706 | — |
| `modelsearch` | 1.3.1 → 1.3.2 | v1 | darynwhite, rxm7706 | no CFE block; `${{ name… }}` in `source.url` |
| `niquests` | 3.21.0 → 3.21.2 | v1 | jan-janssen, rxm7706 | — |

**Ruling note (2026-10-09, night, latest).** The operator ruled "Retire in a fix story" on the duplicate recipe
directories: "Mint a mason fix story that removes the six duplicate dirs (folded into recipes/langflow and
recipes/dbt-core) and drops recipes/lfx from 25.7's batch." So `recipes/lfx` leaves this batch, and Story 25.15
retires it. It was a copy of `langflow-suite` at 1.11.3 that declared all eight suite outputs, and no feedstock
mirrors it: `conda-forge/lfx-feedstock` is a 404, and the `feedstock-outputs` registry gives `lfx` to `langflow`.
Wave A matched the package `lfx` to that directory by name. `lfx` is an output of `recipes/langflow`, so this batch's
refresh of the suite still moves it to the published version. The batch holds 10 recipes; the title, the Surface
line and the ledger key stand.

**Known before the dry-run:**

- `recipes/langflow` is the multi-output `langflow-suite` recipe (`recipe.yaml:14-15`). It builds
  `langflow-sdk`, `lfx`, four `lfx-*` bundles, `langflow-base` and `langflow`, with `lfx` at langflow's own version
  (`recipe.yaml:75-77`). Refreshing `langflow` 1.11.4 → 1.12.4 moves `lfx` with it. (Amended 2026-10-09 under ruling
  2: the separate `recipes/lfx` is no longer in this batch; Story 25.15 retires it.)
- `recipes/langflow` carries five patches (`patches/0001` to `0005`, `recipe.yaml:27-40`). Three strip integration
  dependencies on purpose; 0004 and 0005 loosen the `bcrypt` and `onnxruntime` pins. They encode a maintainer choice,
  which the story never drops (coordination rule 2).
- **Correction (2026-10-10), read live.** This bullet said "three patches", and AC 12 had each one re-based at 1.12.4.
  The feedstock no longer carries patches. `conda-forge/langflow-feedstock`'s PR #21 (langflow v1.12.0, merged
  2026-09-25; commit `1d1fe0bae3`) removed `recipe/patches/0001` to `0005` and added `recipe/patch_deps.py`. The
  script edits upstream's `pyproject.toml` dependencies by package name at build time, for the `langflow-base`,
  `langflow` and `lfx-ibm` outputs; its docstring says it replaces the patches, which only removed or replaced
  dependency entries, and its edits include the `bcrypt` and `onnxruntime` loosening. The feedstock's `main`
  (`0a271a8b65`, 1.12.4, build 0) carries `recipe.yaml`, `patch_deps.py` and `license-checker-format.json` in
  `recipe/`, and no `patches/` directory. The maintainers' choice stands, in the feedstock's new form. So the story
  re-mirrors `recipes/langflow` from the feedstock instead of re-basing patches (AC 12, mirror first).
- `langflow` and `lfx` carry large dependency sets, so expect `dependency-fix` (AC 5). `langchain-litellm` moves 0.7.0
  → 0.11.0 and `llm` 0.31 → 0.36.

**Approach:** run the batch as one Track B wave through Story 25.3's driver, `refresh-wave`.
1. Write the manifest: `track: B`, `wave: 25-7`, these 10 recipes, with no version pins. Put it under
   `.claude/data/conda-forge-expert/feedstock-update/`, which is gitignored. The report lands in
   `refresh-waves/B-25-7/`.
2. Dry-run, and record each recipe's plan.
3. Clear in the recipe, through conda-forge-expert, each refusal that a CFE step can clear (AC 2), then dry-run it
   again.
4. Run `--apply --gates --build`.
5. Apply each `dependency-fix` from the feedstock (G96), keeping deliberate choices.
6. Check every version pin against the feedstock, and audit maintainers (G53).
7. Commit per recipe or recipe group.
8. Close with the Rule-2 retro.

Ledger key: `25-7-track-b-batch-3-refreshes-jhub-apps-through-niquests`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: feature / M / S-25.3.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57), the refresh campaign; CAP-20, refresh as parameterized waves (this batch's
  manifest is that parameter); CAP-23, the CFE machinery the driver lives in. No new CAP, so no FR moves.
- AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in the `retro(cfe):` commit).
- CFE G52, G53, G62, G92, G95 and G96; SKILL.md § *PyPI `source.url` Must Use the `pypi.org/packages/...` Pattern* and
  the *Bulk refresh waves* paragraph; `docs/specs/feedstock-refresh.md` § *Track B*, coordination rules 1 to 5 and
  landmines 1 to 13.
- `spec-fleet-stewardship` governs `recipes/**`; `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Siblings: Stories 25.5 to 25.12 touch disjoint recipe directories and are independent of one another, of Story 25.4
  and of Story 25.2. Only their `retro(cfe):` commits meet, at the CFE version carriers.

## Acceptance Criteria

1. **Dry-run first.** Given this spec's 10 recipes When the story starts Then it writes the batch manifest naming
   exactly them, runs `pixi run -e local-recipes refresh-wave <manifest>` as a dry-run, and records each recipe's
   planned outcome in § *Run results* before any recipe changes. A recipe `main` already carries at its published
   version is recorded `already-current` and left alone. A feedstock that has published past this spec's version is
   followed to its live version, and the move is noted.
2. **Refusals cleared in the recipe.** Given a dry-run refusal that a CFE step can clear When the story clears it Then
   the change lands in its own commit before the refresh, moves no version, `build.number`, requirement or
   maintainer, and the recipe is dry-run again. The refusals it covers:
   - `no-cfe-block`: stamp the CFE metadata block per CFE's convention, stripping both forms first (G92);
   - `url-unrenderable`: write `source.url` in CFE's canonical literal `pypi.org/packages/source/<l>/<dist>/` form;
   - `url-version-baked`: template the version.

   For the two URL fixes, the sha256 stays the same and is verified by hashing the new URL at the current version. A
   URL a maintainer templated on purpose is kept, and the recipe is refreshed through CFE's update path instead.
3. **Every recipe ends somewhere.** Given the dry-run plan When `refresh-wave <manifest> --apply --gates --build` runs
   Then each recipe ends in one of three states, recorded in § *Run results* with the driver's reason and the story's
   finding:
   - `refreshed`: at its feedstock's published version, `build.number` 0, sha256 of the new source;
   - `already-current`;
   - `needs-review`.

   No recipe ends `failed` without its cause recorded.
4. **Maintainers kept (G53).** Given each refreshed recipe When its `extra.recipe-maintainers` is compared with the
   deployed feedstock's list, read live at run time Then the local list is a superset. § *Run results* records the
   audit per recipe. This spec's list is the 2026-10-09 snapshot.
5. **Dependencies from the feedstock (G96).** Given a `dependency-fix` the driver reports When the story applies it
   Then the feedstock's `host` and `run` requirements are the authority, applied through CFE. A deliberate choice is
   kept: a maintainer-commented pin, an intentional pin, a platform exclusion, a custom build script, or a patch. Its
   proposed change is parked in the bottom CFE comments block with a `cfe-forge-recipe-updates-needed` token
   (coordination rule 2, landmine 12).
6. **Pins checked, not only names.** Given each refreshed recipe When its `host` and `run` version constraints are
   compared with the feedstock's Then they match, except a choice kept under AC 5. The driver compares requirement
   names, and only maintainer-commented pins (`_dependency_diff`, `refresh_wave.py:398`; gap 3 in Story 25.4's spec),
   so this comparison is the story's own step.
7. **`meta.yaml` by feedstock format.** Given a recipe whose feedstock is still v0 When it is refreshed Then its local
   `meta.yaml` stays, byte-identical to the feedstock's (C1). Given a v1 feedstock Then the local `meta.yaml` is
   removed (C2, G94).
8. **Gates.** Given each refreshed recipe When `validate_recipe`, `optimize_recipe`, `check_dependencies`,
   `scan_for_vulnerabilities` and `conda-smithy recipe-lint --conda-forge` run Then none reports an error. An expected
   finding is recorded with its reason: STD-002 on a C1 recipe, or a virtual package such as `__unix` that
   `check_dependencies` cannot resolve.
9. **A linux-64 build.** Given each refreshed recipe When it is built locally on linux-64 into its own `--output-dir`
   (G52) Then it builds green, or its `cfe-local-build-*` fields record `build-clean-test-blocked` (G95) or
   `not-attempted` with the reason.
10. **Driver gaps recorded, not patched.** Given a driver gap (the driver refuses or misreports a recipe it should
    handle) When the story finds one Then it is a row in this spec's `deferred:` frontmatter naming
    `.claude/skills/conda-forge-expert/scripts/refresh_wave.py`, unless Story 25.4's spec or the mason deferred-work
    ledger already names it. The story does not change the driver.
11. **Retro and suite.** Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands
    a CFE `CHANGELOG.md` semver entry, with the four version carriers in lockstep: PATCH, or MINOR for a new gotcha. If
    another Epic 25 story's retro reached `main` first, this one takes the next version when it merges `main`. Also
    `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.
12. **langflow follows its feedstock's `patch_deps.py`.** Given `conda-forge/langflow-feedstock` replaced
    `recipe/patches/0001` to `0005` with `recipe/patch_deps.py` (PR #21, merged 2026-09-25) When the story refreshes
    `recipes/langflow` Then the recipe is re-mirrored from the feedstock's `recipe/` directory, read live, not
    version-bumped:
    - `recipe.yaml` and `patch_deps.py` come from the feedstock, and each output runs `patch_deps.py` as the
      feedstock's does;
    - the local `patches/` directory is removed (G94), with the five `patches:` entries;
    - each edit the five patches made is either among `patch_deps.py`'s edits (its `langflow-base` removals and the
      `bcrypt` and `onnxruntime` replacements, its `langflow` `lfx-*` removal, its `lfx-ibm` `ibm-db` removal) or
      recorded in § *Run results* with its reason;
    - a local difference the story keeps, such as `conda-forge.yml`, is listed in § *Run results*, and a proposal is
      parked in the CFE comments block (coordination rule 2).

    Its `recipe-maintainers` is a superset of the feedstock's live list (AC 4), and it passes AC 8's gates and builds
    every output on linux-64 under AC 9. The re-mirror also takes the feedstock's `sdk_version` and bundle versions;
    Story 25.14 then finds those outputs current. The driver's dry-run verdict on `recipes/langflow` is recorded, not
    acted on: the driver moves `context.version` only. (Corrected 2026-10-10. This AC read "langflow's patches
    survive": each of three patches re-based at 1.12.4. The feedstock dropped its patches on 2026-09-25, so mirroring
    it means taking `patch_deps.py` instead.)

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1), its *Bulk refresh waves* paragraph, and
   `docs/specs/feedstock-refresh.md` § *Track B* (coordination rules 1 to 5, landmines 1 to 13). Where the file, this
   spec and the skill differ, the skill wins, and the story records the difference.
2. Write the manifest and run the dry-run (AC 1). Record the plan.
3. Clear the refusals a CFE step can clear (AC 2), one commit per fix kind or per recipe, then dry-run again.
4. Run `--apply --gates --build`, with at most 4 builds at once. Apply each `dependency-fix` (AC 5), check every pin
   (AC 6), and rebuild what changed.
5. Run the maintainer audit (AC 4) and record every outcome in § *Run results* (AC 3).
6. Review every diff, then commit per recipe or recipe group: `recipes: …`, never a subject starting
   `Story 25.7:`.
7. Record each driver gap (AC 10). Close with the Rule-2 retro in its own commit, subject
   `retro(cfe): v<x.y.z> — …` (AC 11).
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
- Do not touch a recipe outside this spec's list: another batch, Story 25.4 or Story 25.2 owns it. That includes
  `recipes/lfx`, which Story 25.15 retires (ruling 2, 2026-10-09).
- Do not edit `refresh_wave.py`, or any CFE file outside the `retro(cfe):` commit. Do not touch
  `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | behind v1 recipe, two maintainers deployed | refreshed; both maintainers kept; build green | — |
| maintainer clobber | the refresh would leave only `rxm7706` | the deployed list is re-merged (the driver unions it) | landmine 10 |
| no CFE block | `no-cfe-block` refusal | block stamped (AC 2), dry-run again | needs-review if the stamp cannot be made honest |
| unrendered URL | `${{ name[0] }}` in `source.url` | literal canonical URL, sha256 unchanged | needs-review on a hash mismatch |
| deliberate pin | a pin with a maintainer's comment | kept; the change parked in the CFE comments block | coordination rule 2 |
| feedstock moved on | published past this spec's version | refreshed to the live version, noted | landmine 1 (tag numbering) |
| test env pollution | a dependency solve fails for a package on conda-forge | rebuild isolated before recording a block | G52, landmine 13 |
| now sole | the feedstock lost its other maintainers | refreshed; noted in § *Run results* | — |
| multi-output recipe | `langflow-suite` builds `lfx` too | `lfx` moves with the suite's `version`; `recipes/lfx` is not in the batch | Story 25.15 retires `recipes/lfx` |
| feedstock dropped its patches | `langflow-feedstock` carries `patch_deps.py`, no `patches/` | re-mirrored: `patch_deps.py` taken, local `patches/` pruned | an edit `patch_deps.py` does not make is recorded (AC 12) |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57), with CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 (night) — Ruled: Story 25.2 lands with Wave 0 and
its pilots, and Track B continues in batch stories*.
Ledger key: `25-7-track-b-batch-3-refreshes-jhub-apps-through-niquests`.
Ledger status at mint: `backlog`.
Deps: S-25.3 (done).
Amended 2026-10-09 (night, latest) on the operator's ruling "Retire in a fix story": `recipes/lfx` left the batch
(11 → 10 recipes) for Story 25.15 to retire.
Corrected 2026-10-10 against `langflow-feedstock`'s live `recipe/` (read-only GETs): AC 12 re-mirrors
`recipes/langflow` with the feedstock's `patch_deps.py`, which replaced its five patches on 2026-09-25 (PR #21).
Flag: `flag-exempt: recipe-build` (a recipe build ships no runtime capability behind a flag).
Minted 2026-10-09 on the operator's ruling of that day ("Land 25.2 now, split rest").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test`. Expected: pass. This is the station's `verify_commands`;
  the story changes no Mason code.

**Manual checks:**
- For each recipe in the batch: `pixi run -e local-recipes validate recipes/<dir>` and
  `pixi run -e local-recipes lint-optimize recipes/<dir>` report no errors, and
  `pixi run -e local-recipes recipe-build recipes/<dir>` exits 0 on linux-64, or the recorded block is justified.
- `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/<dir>`: no lint (G65).
- `git diff --name-only origin/main...HEAD -- recipes/` lists only this spec's recipe directories.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert`: exactly one `retro(cfe):` subject,
  and that commit carries `CHANGELOG.md`.
- § *Run results* carries the dry-run plan, each recipe's outcome and the maintainer audit.
- `pixi run -e pyforge-guild spec-surface-check`: exit 0 after the scoped stamps.

## Run results

### Dry-run (initial, manifest `wave-25-7`)

| Recipe | Plan | Notes |
|---|---|---|
| jhub-apps | needs-review | `no-cfe-block` |
| json5 | would-refresh | feedstock 0.17.3 (spec snapshot 0.16.0) |
| kedro-dagster | needs-review | `no-cfe-block` |
| kedro-viz | needs-review | `dependency-fix: run +uvicorn -uvicorn-standard` |
| langchain-litellm | would-refresh | |
| langflow | would-refresh | driver version-only; AC-12 re-mirror applied first |
| llm | needs-review | `no-cfe-block` |
| milvus-lite | needs-review | `dependency-fix: run +pymilvus` |
| modelsearch | needs-review | `no-cfe-block` |
| niquests | would-refresh | |

### After refusal clears (second dry-run)

Six `would-refresh`, one `already-current` (`langflow`), three `needs-review` (dependency-fix).

### After dependency pre-sync (third dry-run)

Nine `would-refresh`, one `already-current` (`langflow`).

### Apply (`refresh-wave --apply --gates --build`)

Report: `.claude/data/conda-forge-expert/refresh-waves/B-25-7/report.json`.

| Recipe | Outcome | Version | Build (linux-64) | Maintainers (G53) |
|---|---|---|---|---|
| jhub-apps | refreshed | 2026.8.1 → 2026.9.1 | success | aktech, costrouc, dcmcand, rxm7706 (superset) |
| json5 | refreshed | 0.15.0 → 0.17.3 | success | ian-r-rose, rxm7706 |
| kedro-dagster | refreshed | 0.8.0 → 0.8.1 | success | gtauzin, rxm7706 |
| kedro-viz | refreshed | 12.4.0 → 12.5.0 | success | cshaley, elanqo, millsks, rxm7706, zaigner |
| langchain-litellm | refreshed | 0.7.0 → 0.11.0 | success | pb01ka, rxm7706 |
| langflow | already-current | 1.12.4 | see below | pb01ka, rxm7706 |
| llm | refreshed | 0.31 → 0.36 | success (after patch restore) | pavelzw, rxm7706 |
| milvus-lite | refreshed | 3.0 → 3.2.1 | success | pb01ka, rxm7706 |
| modelsearch | refreshed | 1.3.1 → 1.3.2 | success | darynwhite, rxm7706 |
| niquests | refreshed | 3.21.0 → 3.21.2 | success | jan-janssen, rxm7706 |

**langflow (AC 12):** Re-mirrored from `conda-forge/langflow-feedstock` (`recipe.yaml`, `patch_deps.py`, `license-checker-format.json`); local `patches/` removed. Manual `recipe-build`: outputs through `lfx-docling` green; **`langflow-base` test `pip_check` failed** (`msal-extensions` vs `portalocker` versions in test env). Local `lfx` run pin tightened to `pydantic >=2.0.0,<2.14` for wheel METADATA (proposal parked in CFE comments). **`conda-forge.yml` kept** (githubreleases bot config) — feedstock differs; noted here.

**llm:** `validate_recipe` still reports conda-smithy `noarch`+platform selectors (feedstock-faithful). **`0001-remove-pip-setuptools.patch`** restored from feedstock after v1 meta removal dropped the file.

**Gates:** Expected `optimize=1` on several recipes (STD-002 on C1 mirrors). `langchain-litellm` / `milvus-lite` CRM parse errors cleared by fixing maintainer list placement after driver apply.

## Review Triage Log

### 2026-10-10 — build-auto pass
- Driver maintainer merge corrupted CFE YAML on two recipes — fixed manually (see `deferred:`).
- langflow-base pip_check block recorded; eight other suite outputs built green.

## Auto Run Result

Status: done

Summary: Track B batch 3 (B-25-7) refreshed ten co-maintained recipes; langflow re-mirrored with `patch_deps.py`; CFE retro v8.99.8.

Verification: `refresh-wave` dry-run/apply; `pixi run --frozen -e pyforge-mason pyforge-mason-test` (exit 0); `python scripts/spec_surface_reconcile.py` (exit 0 after memlog).
