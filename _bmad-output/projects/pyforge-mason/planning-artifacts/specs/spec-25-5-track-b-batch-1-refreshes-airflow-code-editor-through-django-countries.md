---
title: "25.5: Track B batch 1 refreshes airflow-code-editor through django-countries"
type: 'feature'
created: '2026-10-09'
status: 'done'
followup_review_recommended: false
baseline_revision: 'f05de4bab8500a64631f84d8a9a0dc6bce064295'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/refresh_wave.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-3-cfe-gains-a-tracked-bulk-recipe-refresh-driver-that-the-refresh-waves-run-through.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-4-wave-0-s-leftover-recipes-end-repaired-or-carry-a-recorded-reason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-15-five-duplicate-langflow-suite-directories-retire-into-recipes-langflow.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-16-three-dbt-adapter-recipes-are-re-mirrored-from-their-own-feedstocks.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.2's Wave A, on 2026-10-09, found 96 co-maintained recipes behind their feedstock's published
version (the v1-refresh bucket). Its pilots refreshed four. The operator then re-scoped 25.2 to Wave 0 and those
pilots, and split the other 92 into eight batch stories, each small enough for one dispatch ("Land 25.2 now, split
rest", 2026-10-09). This is batch 1 of 8: the first twelve recipes, alphabetically, outside the OpenTelemetry family.
The ruling note below the table moves `dbt-bigquery` out and re-points `dbt-core` to `recipes/dbt`, so the batch holds
11. Every one is co-maintained: the deployed feedstock lists `rxm7706` and at least one other maintainer. So the
refresh keeps every other maintainer's work (G53, and coordination rules 1 to 5 of `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md` §
*Track B*).

**The batch.** Versions and maintainer lists are Wave A's snapshot of 2026-10-09; the dry-run reads each feedstock
live. The last column is a read of `main` at mint (`02167e79f4`), a static read of each recipe that the dry-run
supersedes.

| Recipe | Local → published | Feedstock | Deployed maintainers | Before the dry-run |
|---|---|---|---|---|
| `airflow-code-editor` | 8.3.0 → 8.3.1 | v1 | rxm7706, xylar | `${{ name… }}` in `source.url`; 25.2's B1 dry-run: `url-unrenderable` |
| `avro` | 1.12.1 → 1.12.2 | v0: keep `meta.yaml` (C1) | mariusvniekerk, rxm7706 | `${{ name… }}` in `source.url`; 25.2's B1 dry-run: `url-unrenderable` |
| `azure-monitor-opentelemetry-exporter` | 1.0.0b56 → 1.0.0b58 | v0: keep `meta.yaml` (C1) | conda-forge/opentelemetry-api, rxm7706 | no CFE block; `${{ name… }}` in `source.url`; 25.2's B1 dry-run: `no-cfe-block` |
| `azure-storage-file-share` | 12.26.0 → 12.27.0 | v0: keep `meta.yaml` (C1) | davidbrochart, rxm7706 | no CFE block; `${{ name… }}` in `source.url`; 25.2's B1 dry-run: `no-cfe-block` |
| `billiard` | 4.2.4 → 4.3.1 | v0: keep `meta.yaml` (C1) | kwilcox, rxm7706 | no CFE block; 25.2's B2 dry-run: `no-cfe-block` (deferred from B2) |
| `cachetools` | 7.1.7 → 7.2.1 | v0: keep `meta.yaml` (C1) | maartenbreddels, marcelotrevisani, rxm7706 | 25.2's B2 dry-run: `dependency-fix: host -setuptools-scm` (deferred from B2) |
| `dbt` (builds `dbt-core`) | 1.12.2 → 1.12.5 | v1 (`dbt-feedstock`); no local `meta.yaml` since 2026-08-20 | drewbanin, jthandy, maresb, rxm7706, thewchan, zaneselvans | `${{ name… }}` in `source.url`; CFE block names `dbt-feedstock`; its patch file restored by Story 25.15; a `License.md` the feedstock's `recipe/` lacks |
| `django-allauth` | 65.19.1 → 65.19.7 | v0: keep `meta.yaml` (C1) | cshaley, jacksund, rxm7706, sannykr | — |
| `django-anymail` | 15.1 → 15.2 | v0: keep `meta.yaml` (C1) | cshaley, elanqo, millsks, rxm7706, zaigner | `${{ name… }}` in `source.url` |
| `django-bootstrap5` | 26.2 → 26.3 | v1 | rxm7706, swainn | — |
| `django-countries` | 9.0.0 → 9.1.0 | v0: keep `meta.yaml` (C1) | mxr-conda, rxm7706 | no CFE block; `${{ name… }}` in `source.url` |

**Ruling note (2026-10-10).** Two operator rulings of 2026-10-09, on Story 25.15's open questions, change two rows:
- "Retire recipes/dbt-core": "Keep recipes/dbt as the dbt-feedstock mirror, retire recipes/dbt-core, and re-point batch
  25.5's dbt-core row to recipes/dbt. Added to Story 25.15." The `dbt-core` row now names `recipes/dbt`, the
  `recipes/<feedstock>/` mirror of `conda-forge/dbt-feedstock`, and the manifest entry is `name: dbt`. The old entry
  could not have run: an entry's `feedstock` defaults to its `name` (`refresh_wave.py:231`), and
  `conda-forge/dbt-core-feedstock` is a 404. Story 25.15 retires `recipes/dbt-core` and restores `recipes/dbt`'s
  missing patch file, so this story now depends on it, and its refresh starts from a recipe that builds.
- "Fix in a story": "Mint a mason fix story that re-mirrors the three adapter recipes from
  dbt-bigquery/postgres/redshift-feedstock (dbt-bigquery-feedstock is now v1 at 1.12.1), and correct batch 25.5's
  table." The `dbt-bigquery` row was wrong twice. Its feedstock moved to v1 on 2026-09-19 (PR #58, `aa7005a714`;
  1.12.1, build 1), so "v0: keep `meta.yaml` (C1)" no longer held. And `recipes/dbt-bigquery/recipe.yaml` is a copy of
  `dbt-core`'s recipe, so a version refresh would have moved the wrong package. Story 25.16 re-mirrors it, with
  `dbt-postgres` and `dbt-redshift`, so it leaves this batch.

The batch holds 11 recipes; the title and the ledger key stand.

**Known before the dry-run:**

Six of these 11 already went through the driver in Story 25.2's dry-runs (waves `B1` and `B2`; their
reports are gitignored in the 25.2 worktree) and ended `needs-review`:
- `airflow-code-editor` and `avro`: `url-unrenderable`. Both URLs read
  `https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/…` with `name` in `context`. The driver renders only a
  bare `${{ var }}` (gap 1 in Story 25.4's spec). CFE's canonical form, a literal path, clears it (AC 2).
- `azure-monitor-opentelemetry-exporter`, `azure-storage-file-share` and `billiard`: `no-cfe-block`.
- `cachetools`: `dependency-fix: host -setuptools-scm`. The feedstock's `host` no longer lists `setuptools-scm`
  (G96, AC 5).

`billiard` and `cachetools` are the two recipes deferred from 25.2's wave B2 (AC 12). `billiard` is not
`noarch: python`. `dbt-feedstock` is v1, and `recipes/dbt` dropped its local `meta.yaml` on 2026-08-20 (C2). Its
`License.md` is not in the feedstock's `recipe/`, so the refresh prunes it (G94). (Amended 2026-10-10: this line named
`recipes/dbt-core`, whose `meta.yaml` the refresh would have dropped.)

**Approach:** run the batch as one Track B wave through Story 25.3's driver, `refresh-wave`.
1. Write the manifest: `track: B`, `wave: 25-5`, these 11 recipes, with no version pins. Put it under
   `.claude/data/conda-forge-expert/feedstock-update/`, which is gitignored. The report lands in
   `refresh-waves/B-25-5/`.
2. Dry-run, and record each recipe's plan.
3. Clear in the recipe, through conda-forge-expert, each refusal that a CFE step can clear (AC 2), then dry-run it
   again.
4. Run `--apply --gates --build`.
5. Apply each `dependency-fix` from the feedstock (G96), keeping deliberate choices.
6. Check every version pin against the feedstock, and audit maintainers (G53).
7. Commit per recipe or recipe group.
8. Close with the Rule-2 retro.

Ledger key: `25-5-track-b-batch-1-refreshes-airflow-code-editor-through-django-countries`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: feature / M / S-25.3, S-25.15.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57), the refresh campaign; CAP-20, refresh as parameterized waves (this batch's
  manifest is that parameter); CAP-23, the CFE machinery the driver lives in. No new CAP, so no FR moves.
- AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in the `retro(cfe):` commit).
- CFE G52, G53, G62, G92, G95 and G96; SKILL.md § *PyPI `source.url` Must Use the `pypi.org/packages/...` Pattern* and
  the *Bulk refresh waves* paragraph; `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md` § *Track B*, coordination rules 1 to 5 and
  landmines 1 to 13.
- `spec-fleet-stewardship` governs `recipes/**`; `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Siblings: Stories 25.5 to 25.12 touch disjoint recipe directories and are independent of one another, of Story 25.4
  and of Story 25.2. Only their `retro(cfe):` commits meet, at the CFE version carriers. This story also runs after
  Story 25.15, which writes `recipes/dbt` first (ruling note). Story 25.16 owns `recipes/dbt-bigquery`.

## Acceptance Criteria

1. **Dry-run first.** Given this spec's 11 recipes When the story starts Then it writes the batch manifest naming
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
12. **Deferred from B2.** Given `billiard` and `cachetools`, deferred from Story 25.2's wave B2 When this story closes
    Then each is `refreshed`, or `needs-review` with a reason deeper than B2's (`no-cfe-block`; `dependency-fix: host
    -setuptools-scm`): what the story tried and why it did not clear. If the mason deferred-work ledger carries the
    row ingested from 25.2's B2 deferral, it is closed with this story as its resolution.

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1), its *Bulk refresh waves* paragraph, and
   `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md` § *Track B* (coordination rules 1 to 5, landmines 1 to 13). Where the file, this
   spec and the skill differ, the skill wins, and the story records the difference.
2. Write the manifest and run the dry-run (AC 1). Record the plan.
3. Clear the refusals a CFE step can clear (AC 2), one commit per fix kind or per recipe, then dry-run again.
4. Run `--apply --gates --build`, with at most 4 builds at once. Apply each `dependency-fix` (AC 5), check every pin
   (AC 6), and rebuild what changed.
5. Run the maintainer audit (AC 4) and record every outcome in § *Run results* (AC 3).
6. Review every diff, then commit per recipe or recipe group: `recipes: …`, never a subject starting
   `Story 25.5:`.
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
  `recipes/dbt-core`, which Story 25.15 retires, and `recipes/dbt-bigquery`, `recipes/dbt-postgres` and
  `recipes/dbt-redshift`, which Story 25.16 re-mirrors (rulings of 2026-10-09).
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
| deferred from B2 | `billiard` with no CFE block | block stamped (AC 2), then refreshed | needs-review with a deeper reason (AC 12) |
| dropped host dep | `cachetools`: feedstock `host` lost `setuptools-scm` | applied from the feedstock (G96) | kept and parked if a maintainer comment marks it deliberate |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57), with CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 (night) — Ruled: Story 25.2 lands with Wave 0 and
its pilots, and Track B continues in batch stories*.
Ledger key: `25-5-track-b-batch-1-refreshes-airflow-code-editor-through-django-countries`.
Ledger status at mint: `backlog`.
Deps: S-25.3 (done), S-25.15.
Amended 2026-10-10 on the operator's rulings of 2026-10-09, "Retire recipes/dbt-core" and "Fix in a story": the
`dbt-core` row re-pointed to `recipes/dbt`, `dbt-bigquery` moved to Story 25.16 (12 → 11 recipes), and S-25.15 added.
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

### Dry-run (initial, manifest `wave-25-5`)

| Recipe | Plan | Notes |
|---|---|---|
| airflow-code-editor | needs-review | `url-unrenderable` |
| avro | needs-review | `url-unrenderable` |
| azure-monitor-opentelemetry-exporter | needs-review | `no-cfe-block` |
| azure-storage-file-share | needs-review | `no-cfe-block` |
| billiard | needs-review | `no-cfe-block` |
| cachetools | needs-review | `dependency-fix: host -setuptools-scm` |
| dbt | needs-review | `no-feedstock` (manifest used `dbt-feedstock`; lookup name is `dbt`) |
| django-allauth | needs-review | `dependency-fix: host -setuptools-scm` |
| django-anymail | needs-review | `url-unrenderable` |
| django-bootstrap5 | needs-review | `dependency-fix: run pin django` |
| django-countries | needs-review | `no-cfe-block` |

### After refusal clears (second dry-run)

All eleven: `would-refresh`.

### Apply (`refresh-wave --apply --gates --build`)

Report: `.claude/data/conda-forge-expert/refresh-waves/B-25-5/report.json` (gitignored).

| Recipe | Outcome | Version | Build (linux-64) | Maintainers (G53) |
|---|---|---|---|---|
| airflow-code-editor | refreshed | 8.3.0 → 8.3.1 | success | rxm7706, xylar (superset) |
| avro | refreshed | 1.12.1 → 1.12.2 | success after `python_min.*` host fix | mariusvniekerk, rxm7706 |
| azure-monitor-opentelemetry-exporter | refreshed | 1.0.0b56 → 1.0.0b58 | success after run-pin sync | rxm7706, conda-forge/opentelemetry-api |
| azure-storage-file-share | refreshed | 12.26.0 → 12.27.0 | success after `python_min.*` host fix | davidbrochart, rxm7706 |
| billiard | refreshed | 4.2.4 → 4.3.1 | success | kwilcox, rxm7706 |
| cachetools | refreshed | 7.1.7 → 7.2.1 | success | maartenbreddels, marcelotrevisani, rxm7706 |
| dbt | refreshed | 1.12.2 → 1.12.5 | success; patch restored; `License.md` pruned | drewbanin, jthandy, maresb, rxm7706, thewchan, zaneselvans |
| django-allauth | refreshed | 65.19.1 → 65.19.7 | success | cshaley, jacksund, rxm7706, sannykr |
| django-anymail | refreshed | 15.1 → 15.2 | success after `python_min.*` host fix | cshaley, elanqo, millsks, rxm7706, zaigner |
| django-bootstrap5 | refreshed | 26.2 → 26.3 | success | rxm7706, swainn |
| django-countries | refreshed | 9.0.0 → 9.1.0 | success after `python_min.*` host fix | mxr-conda, rxm7706 |

Gates: `validate=0` on all; `optimize=1` on C1 mirrors (STD-002 expected); `billiard` `check-deps=1` (`cross-python_${{ target_platform }}` placeholder — recorded, not a recipe defect).

### Deferred from B2 (AC 12)

- `billiard`: refreshed (was `no-cfe-block` in 25.2 B2 dry-run).
- `cachetools`: refreshed after host `setuptools-scm` removed per feedstock (was `dependency-fix` in B2).

## Review Triage Log

### 2026-10-10 — Review pass
- verdicts: 8 findings — high 1, medium 2, low 0, false 3, maybe-false 2
- findings:
  - `[high]` `[patch]` Five recipes kept `cfe-local-build-status: failed` after post-refresh manual fixes and green rebuilds — updated stamps to `success` on avro, azure-monitor-opentelemetry-exporter, azure-storage-file-share, django-anymail, django-countries.
  - `[medium]` `[patch]` Stale `version-update-to-*` tokens on cachetools and django-allauth after refresh — removed obsolete version tokens, kept `meta-yaml-to-recipe-yaml`.
  - `[medium]` `[reject]` WIP checkpoint commits use `wip: 25.5` subjects instead of `recipes:` per Tasks — acceptable for auto-checkpoints; squash/reword optional at PR time.
  - `[false]` `[reject]` avro `meta.yaml` duplicate commented deps — byte-identical to deployed feedstock (verified via `conda-forge/avro-feedstock`).
  - `[false]` `[reject]` C1 meta `files.pythonhosted.org` vs v1 `pypi.org` URL — feedstock-faithful C1 mirror; v1 `recipe.yaml` uses canonical PyPI path by policy.
  - `[false]` `[reject]` Driver gaps not in `deferred:` frontmatter — already tracked on Story 25.4 spec; AC 10 defers duplicate rows.
  - `[maybe-false]` `[defer]` SKILL.md bulk-refresh paragraph not expanded with 25.5 lessons — CHANGELOG carries retro; PATCH without new gotcha id is intentional.
  - `[maybe-false]` `[defer]` Manifest `wave-25-5.yaml` gitignored — report under `.claude/data/conda-forge-expert/refresh-waves/B-25-5/` documents apply.

## Auto Run Result

Status: done

Summary: Track B batch 1 refreshed eleven co-maintained recipes through `refresh-wave` B-25-5 with pre-refresh refusal clears, post-refresh host/pin fixes, eleven green linux-64 builds, and CFE retro v8.99.3.

Verification: `refresh-wave` dry-run/apply; per-recipe `recipe-build`; `pixi run --frozen -e pyforge-mason pyforge-mason-test` (exit 0); `python scripts/spec_surface_reconcile.py` (exit 0); `pixi run -e pyforge-guild spec-surface-check` (exit 0).

Follow-up review recommended: false
