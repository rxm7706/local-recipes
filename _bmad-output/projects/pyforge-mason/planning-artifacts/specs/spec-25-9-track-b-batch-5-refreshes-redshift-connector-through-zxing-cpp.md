---
title: "25.9: Track B batch 5 refreshes redshift_connector through zxing-cpp"
type: 'feature'
created: '2026-10-09'
status: 'done'
baseline_revision: '378590c8772520d3d414250c75fd8c0c9fbcf177'
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
deferred:
  - location: .claude/skills/conda-forge-expert/scripts/refresh_wave.py
    reason: maintainer union can insert `- <name>` inside the `#### CFE metadata` header (StringZilla, vlmrun B-25-9; same as Stories 25.7–25.8) — CRM parse failure until moved under `recipe-maintainers`
  - location: .claude/skills/conda-forge-expert/scripts/refresh_wave.py
    reason: tree-sitter-swift deliberate `${{ tag }}` URL reports `url-version-baked` (gap 4); refresh through hand `update_recipe`, not driver bump
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.2's Wave A, on 2026-10-09, found 96 co-maintained recipes behind their feedstock's published
version (the v1-refresh bucket). Its pilots refreshed four. The operator then re-scoped 25.2 to Wave 0 and those
pilots, and split the other 92 into eight batch stories, each small enough for one dispatch ("Land 25.2 now, split
rest", 2026-10-09). This is batch 5 of 8: 11 recipes, the last eleven, alphabetically, outside the OpenTelemetry
family. Every one is co-maintained: the deployed feedstock lists `rxm7706` and at least one other maintainer. So the
refresh keeps every other maintainer's work (G53, and coordination rules 1 to 5 of `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md` §
*Track B*).

**The batch.** Versions and maintainer lists are Wave A's snapshot of 2026-10-09; the dry-run reads each feedstock
live. The last column is a read of `main` at mint (`02167e79f4`), a static read of each recipe that the dry-run
supersedes.

| Recipe | Local → published | Feedstock | Deployed maintainers | Before the dry-run |
|---|---|---|---|---|
| `redshift_connector` | 2.1.15 → 2.1.17 | v1: drop the local `meta.yaml` (C2) | Brooke-white, bsharifi, personal-naveenkumar, rxm7706, vahid110 | — |
| `robocorp-workitems` | 1.5.0 → 1.5.1 | v0: keep `meta.yaml` (C1) | rxm7706, zaigner | no CFE block; `${{ name… }}` in `source.url` |
| `selectolax` | 0.4.11 → 0.4.13 | v0: keep `meta.yaml` (C1) | rxm7706, soapy1 | — |
| `sentry-sdk` | 2.68.0 → 2.71.0 | v0: keep `meta.yaml` (C1) | alippai, dgasmith, djsutherland, rxm7706 | — |
| `stringzilla` | 4.6.3 → 5.2.0 | v0: keep `meta.yaml` (C1) | mukhery, rxm7706 | directory `recipes/StringZilla` |
| `tox` | 4.60.0 → 4.64.9 | v1 | bollwyvl, cshaley, kalefranz, rxm7706, sannykr | — |
| `tree-sitter-php` | 0.24.2 → 0.25.1 | v1 | killua156, mgorny, rxm7706 | no CFE block |
| `tree-sitter-swift` | 0.7.3 → 0.7.4 | v1 | killua156, mgorny, rxm7706 | no CFE block; URL templated through `context.tag` on purpose (`url-version-baked`, gap 4) |
| `vlmrun` | 0.6.3 → 0.9.0 | v1 | pb01ka, rxm7706 | — |
| `wagtail` | 7.4.2 → 8.0 | v1 | darynwhite, rxm7706 | — |
| `zxing-cpp` | 2.3.0 → 3.1.1 | v1 | carlodri, rxm7706 | `${{ name… }}` in `source.url` |

**Known before the dry-run:**

- `stringzilla` lives in `recipes/StringZilla/`. Its manifest entry is `name: StringZilla` with
  `feedstock: stringzilla`. It moves 4.6.3 → 5.2.0.
- `wagtail` 7.4.2 → 8.0 and `zxing-cpp` 2.3.0 → 3.1.1 are major moves, so expect `dependency-fix` (AC 5). For
  `zxing-cpp` the move is a change of identity, not only of version (the last bullet, AC 13).
- `recipes/tree-sitter-swift` templates its URL through `context.tag`, which is `${{ version }}-with-generated-files`
  on purpose (`recipe.yaml:6-12`): that tag carries the generated parser, so the build needs no node toolchain. The
  driver refuses it as `url-version-baked` (gap 4 in Story 25.4's spec). Keep the URL, and refresh it through CFE's
  version-and-sha256 path instead (AC 12).
- `tree-sitter-php` has no CFE block. Both tree-sitter recipes are abi3 builds; G5 applies if a source changes.
- **`zxing-cpp`'s feedstock changed identity (found at the Wave F mint, 2026-10-09, night).**
  `conda-forge/zxing-cpp-feedstock` was repurposed on 2026-09-08 by its PR #10 (merged `44fc37f4b5`). It used to build
  the Python bindings from the PyPI sdist. It now builds the C++ library from the GitHub tag `v${{ version }}`, with
  `build.sh`, `build.bat`, cmake and ninja, a `run_exports` pin and `package_contents` tests, and it lists `TomNysWF`
  beside `carlodri` and `rxm7706`. The bindings moved to `zxing-cpp-python-feedstock`. `recipes/zxing-cpp` still holds
  the old bindings recipe at 2.3.0, and Wave A's maintainer snapshot above predates the move. Bumping that recipe to
  3.1.1 would build bindings under the library's name, so this story re-mirrors it instead (AC 13). The bindings get
  their own mirror, `recipes/zxing-cpp-python`, in Story 25.13.

**Approach:** run the batch as one Track B wave through Story 25.3's driver, `refresh-wave`.
1. Write the manifest: `track: B`, `wave: 25-9`, these 11 recipes, with no version pins. Put it under
   `.claude/data/conda-forge-expert/feedstock-update/`, which is gitignored. The report lands in
   `refresh-waves/B-25-9/`.
2. Dry-run, and record each recipe's plan.
3. Clear in the recipe, through conda-forge-expert, each refusal that a CFE step can clear (AC 2), then dry-run it
   again.
4. Run `--apply --gates --build`.
5. Apply each `dependency-fix` from the feedstock (G96), keeping deliberate choices.
6. Check every version pin against the feedstock, and audit maintainers (G53).
7. Commit per recipe or recipe group.
8. Close with the Rule-2 retro.

Ledger key: `25-9-track-b-batch-5-refreshes-redshift-connector-through-zxing-cpp`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: feature / M / S-25.3.

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
  and of Story 25.2. Only their `retro(cfe):` commits meet, at the CFE version carriers.

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
12. **A deliberate URL stays.** Given `tree-sitter-swift`'s `${{ tag }}` URL When the story refreshes it Then the URL
    and its `context.tag` comment are unchanged; the version and sha256 move through CFE's update path
    (`update_recipe`); and the recipe still builds from the `-with-generated-files` tag.
13. **`zxing-cpp` follows its repurposed feedstock.** Given `conda-forge/zxing-cpp-feedstock` now builds the C++
    library (PR #10, merged 2026-09-08) When the story handles `recipes/zxing-cpp` Then the recipe is re-mirrored from
    the feedstock's `recipe/` directory (`recipe.yaml`, `build.sh`, `build.bat`, `LICENSE` and `test/`), not
    version-bumped. The PyPI bindings recipe it held is replaced. The CFE block names the new identity: a GitHub
    upstream, the feedstock's URL and `cfe-on-conda-forge-status: confirmed-on-conda-forge`. Its `recipe-maintainers`
    is a superset of the feedstock's live list (G53), `TomNysWF` included. It passes AC 8's gates and builds on
    linux-64 under AC 9, with the feedstock's `package_contents` and CMake test passing. The driver's dry-run verdict
    on it is recorded, not acted on. The bindings' mirror, `recipes/zxing-cpp-python`, is Story 25.13's; this story
    does not create it.

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
   `Story 25.9:`.
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
- Do not touch a recipe outside this spec's list: another batch, Story 25.4 or Story 25.2 owns it.
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
| directory differs from name | `recipes/StringZilla` for `stringzilla` | manifest `name: StringZilla`, `feedstock: stringzilla` | — |
| deliberate URL template | `tree-sitter-swift`'s `${{ tag }}` | kept; refreshed through `update_recipe` | needs-review if the tag scheme is gone upstream |
| feedstock changed identity | `zxing-cpp-feedstock` now builds the C++ library | re-mirrored from the feedstock (AC 13), not version-bumped | needs-review if the library build or its tests fail |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57), with CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 (night) — Ruled: Story 25.2 lands with Wave 0 and
its pilots, and Track B continues in batch stories*.
Ledger key: `25-9-track-b-batch-5-refreshes-redshift-connector-through-zxing-cpp`.
Ledger status at mint: `backlog`.
Deps: S-25.3 (done).
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

### Dry-run (initial, manifest `wave-25-9`)

| Recipe | Plan | Notes |
|---|---|---|
| redshift_connector | would-refresh | v1 meta would-remove |
| robocorp-workitems | needs-review | `no-cfe-block` |
| selectolax | would-refresh | |
| sentry-sdk | would-refresh | |
| StringZilla | would-refresh | maintainer add pb01ka |
| tox | needs-review | `dependency-fix` |
| tree-sitter-php | needs-review | `no-cfe-block` |
| tree-sitter-swift | needs-review | `no-cfe-block` (then `url-version-baked` after CFE stamp) |
| vlmrun | needs-review | `dependency-fix` |
| wagtail | needs-review | `dependency-fix` |
| zxing-cpp | needs-review | `url-unrenderable` (old PyPI bindings recipe) |

Report: `.claude/data/conda-forge-expert/refresh-waves/B-25-9/report.json`.

### After refusal clears + G96 pre-sync (dry-run 2)

Ten `would-refresh`; **tree-sitter-swift** still `url-version-baked`; **zxing-cpp** `already-current` after AC-13 re-mirror.

### Apply (`refresh-wave --apply --gates --build`)

| Recipe | Outcome | Version | Build (linux-64) | Maintainers (G53) |
|---|---|---|---|---|
| redshift_connector | refreshed | 2.1.15 → 2.1.17 | success | Brooke-white, bsharifi, personal-naveenkumar, rxm7706, vahid110 (superset) |
| robocorp-workitems | refreshed | 1.5.0 → 1.5.1 | success (post host python pin) | rxm7706, zaigner |
| selectolax | refreshed | 0.4.11 → 0.4.13 | success | rxm7706, soapy1 |
| sentry-sdk | refreshed | 2.68.0 → 2.71.0 | success | alippai, dgasmith, djsutherland, rxm7706 |
| StringZilla | refreshed | 4.6.3 → 5.2.0 | build-clean-test-blocked (script `import cli`) | mukhery, pb01ka, rxm7706 |
| tox | refreshed | 4.60.0 → 4.64.10 | success | bollwyvl, cshaley, kalefranz, rxm7706, sannykr |
| tree-sitter-php | refreshed | 0.24.2 → 0.25.1 | success | killua156, mgorny, rxm7706 |
| tree-sitter-swift | refreshed (hand) | 0.7.3 → 0.7.4 | success | killua156, mgorny, rxm7706 |
| vlmrun | refreshed | 0.6.3 → 0.9.0 | success (upstream-exact pip_check pins) | pb01ka, rxm7706 |
| wagtail | refreshed | 7.4.2 → 8.0 | success (post G96 run sync) | darynwhite, rxm7706 |
| zxing-cpp | re-mirrored (hand) | 2.3.0 bindings → 3.1.1 C++ lib | success | carlodri, rxm7706, TomNysWF |

**Gates:** Expected `optimize=1` on several C1 v0 mirrors (STD-002). **selectolax** `check-deps=1` (virtual/cross-python placeholder pattern).

## Review Triage Log

### 2026-10-10 — build-auto pass

- Self-review against AC: all eleven recipes at feedstock versions or documented block; zxing-cpp C++ re-mirror; tree-sitter-swift tag URL preserved (AC 12).
- Driver maintainer-merge corruption on StringZilla and vlmrun — fixed manually; deferred rows cite `refresh_wave.py`.

## Auto Run Result

Status: done

Summary: Track B batch 5 (B-25-9) refreshed eleven co-maintained recipes; driver-refreshed nine plus hand-finish on tree-sitter-swift and zxing-cpp re-mirror; CFE retro v8.99.11.

Verification: `refresh-wave` dry-run/apply; `pixi run --frozen -e pyforge-mason pyforge-mason-test` (exit 0); `python scripts/spec_surface_reconcile.py` (exit 0 after memlogs on spec-fleet-stewardship, spec-pyforge-mason, spec-packaging-factory).
