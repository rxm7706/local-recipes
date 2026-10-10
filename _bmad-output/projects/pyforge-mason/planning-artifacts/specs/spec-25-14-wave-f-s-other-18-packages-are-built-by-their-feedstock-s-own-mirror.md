---
title: "25.14: Wave F's other 18 packages are built by their feedstock's own mirror"
type: 'feature'
created: '2026-10-09'
status: 'done'
baseline_revision: '086436de5eb3bc317eb778a542786c613c491e45'
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
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-4-wave-0-s-leftover-recipes-end-repaired-or-carry-a-recorded-reason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-7-track-b-batch-3-refreshes-jhub-apps-through-niquests.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-13-wave-f-mirrors-the-two-co-maintained-feedstocks-that-have-no-local-recipe.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-15-five-duplicate-langflow-suite-directories-retire-into-recipes-langflow.md
deferred:
  - summary: "Map co-maintained packages to feedstocks via atlas packages.feedstock_name (Wave A step A3), never by recipes/<name>/ directory name alone."
    location: docs/specs/feedstock-refresh.md
  - id: refresh-wave-suite-context-version-only
    summary: "refresh-wave moves context.version only (refresh_recipe compares lv/tv from context.version); G72 suites keep sdk_version and bundle context pins behind unless hand-synced or re-mirrored."
    location: .claude/skills/conda-forge-expert/scripts/refresh_wave.py:701
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.2's Wave A, on 2026-10-09, put 20 co-maintained packages in the no-local-recipe bucket. The
operator answered Track B Q2 (`<create_missing>`) the same night: "create them". Story 25.13 mirrors the two that are
feedstocks of their own (`dbt-snowflake`, `zxing-cpp-python`). The other 18 are not feedstocks. They are outputs of two
multi-output feedstocks, and both already have their local mirror:

| Feedstock (registry owner) | Local mirror | Wave F packages | Published at mint | Local at mint |
|---|---|---|---|---|
| `db-gpt` | `recipes/db-gpt` (recipe `dbgpt-split`, 16 outputs) | `dbgpt`, `dbgpt-acc-auto`, `dbgpt-acc-flash-attn`, `dbgpt-agent`, `dbgpt-app`, `dbgpt-cli`, `dbgpt-client`, `dbgpt-code`, `dbgpt-ext`, `dbgpt-ext-chromadb`, `dbgpt-ext-rag`, `dbgpt-framework`, `dbgpt-proxy-openai`, `dbgpt-proxy-tongyi`, `dbgpt-sandbox`, `dbgpt-serve` | 0.8.2, build 2 | 0.8.2, build 2 |
| `langflow` | `recipes/langflow` (recipe `langflow-suite`, 8 outputs) | `langflow-base`, `langflow-sdk` | 1.12.4 and 0.4.0 | 1.11.4 and 0.3.3 |

Deployed maintainers, both feedstocks: `rxm7706`, `pb01ka`.

Wave A matched each package to a directory by name (`resolve_local_dir` in Story 25.2's uncommitted
`.cursor/track_b_wave_a.py`), so it found no directory called `dbgpt-app` and counted the package missing. Track B's
own plan says to resolve that mapping first (Wave A step A3, landmine 11), and Story 25.1's I/O matrix already counted
such a package "present, not re-created". The same name-matching misread four more of `recipes/langflow`'s outputs. It
matched `lfx-arxiv`, `lfx-docling`, `lfx-duckduckgo` and `lfx-ibm` to four directories of the same names, read each
one's first `version:` line (langflow's 1.11.3), and bucketed them `v1-ahead` of their published 0.1.5, 0.1.7, 0.1.5
and 0.2.5. In `recipes/langflow` they are really 0.1.2, 0.1.3, 0.1.2 and 0.1.2: behind. No story covers them, so this
story does.

**Why no `recipes/<output>/` directory (the duplicate-output investigation at mint).** The ruling's default reading
would give each of the 18 its own standalone mirror. The mint read what that breaks, and found:
- *No repo check refuses a second recipe declaring the same package name.* `refresh_wave.py:240` refuses only a
  duplicate manifest entry. `test_recipe_yaml_parse_audit.py` checks duplicate keys within one file. The fork's
  staged-recipes linter (`.github/workflows/scripts/linter.py:126-176`) matches the recipe name or
  `extra.feedstock-name` against conda-forge feedstocks and bioconda only. `test-linux.yml` builds each changed recipe
  in its own job. `main` already proves it. Six directories each declare all eight `langflow-suite` outputs:
  `recipes/langflow` at 1.11.4, and `recipes/lfx`, `lfx-arxiv`, `lfx-docling`, `lfx-duckduckgo` and `lfx-ibm` at
  1.11.3. Two more both build `dbt-core` 1.12.2: `recipes/dbt` and `recipes/dbt-core`. The detectors stay green.
- *What a duplicate does break is the mirror itself.* No conda-forge feedstock exists under any of the 18 names, nor
  under `lfx` or the four bundles (`gh api repos/conda-forge/<name>-feedstock` returns 404 for all 23, 2026-10-09).
  conda-forge's `feedstock-outputs` registry gives all 16 `dbgpt-*` names to `db-gpt`, and `langflow-base`,
  `langflow-sdk`, `lfx` and the four `lfx-*` bundles to `langflow`. So a standalone `recipes/dbgpt-app` would mirror no feedstock. That breaks SKILL.md § *Local-mirror
  fidelity* ("New recipes with no feedstock yet … nothing to mirror") and `spec-fleet-stewardship` CAP-1
  (`recipes/<feedstock>/`). It could never be submitted, because the registry lets one feedstock claim each output
  name. It would also shadow the multi-output build in the local channel, which `recipe-build` shares and
  re-injects into every later build (`.claude/scripts/conda-forge-expert/native-build.sh:81,120`; the G52 class). And it drifts: the five `lfx*` copies
  already sit one version behind `recipes/langflow`.
- *Option (a), dropping the 18 outputs from `recipes/db-gpt` and `recipes/langflow` in favour of standalone recipes,
  loses more.* Each feedstock builds its outputs from one source tarball and one patch set; splitting them breaks both
  mirrors' fidelity, and reverses G72, the fold that put `langflow-sdk` into the suite.

So this story takes option (b): each of the 18 is built by its feedstock's own mirror at its published version, and
no directory is created. If the operator meant 20 directories, see § *Open questions*. (Resolved 2026-10-09: the
operator confirmed option (b), "Yes, inside the mirrors"; open question 1.)

**What the mirrors need, read at mint:**
- `recipes/db-gpt` is current and faithful. Outside `extra:` it matches `db-gpt-feedstock`'s `recipe.yaml` but for one
  comment's placement, and its three patch files carry the feedstock's names. Its CFE block is stale. It still reads
  `cfe-on-conda-forge-status: pending-approval-on-conda-forge` and `cfe-on-conda-forge-feedstock: none`, although
  staged-recipes #33883 merged on 2026-07-16 and created the feedstock. Its `cfe-forge-recipe-updates-needed` names a
  loosening the feedstock already took (feedstock PR #6, merged 2026-09-03). Its header comment says "8 outputs",
  "v0.8.1" and "pb01ka only — consume, not co-maintain", yet `extra.recipe-maintainers` lists both maintainers.
- `recipes/langflow` is Story 25.7's to refresh to 1.12.4, and this story depends on it. `refresh-wave` moves
  `context.version` only (`refresh_wave.py:701-752`). A G72 suite carries a separate context version for each
  independently versioned output: `sdk_version`, and the four bundle versions `duckduckgo_version`, `arxiv_version`,
  `ibm_version` and `docling_version`. So 25.7's driver run can leave `langflow-sdk` and the bundles behind (driver
  gap 5). The feedstock's context at mint reads `version` 1.12.4, `sdk_version` 0.4.0, and bundle versions 0.1.5,
  0.1.5, 0.2.5 and 0.1.7.

**Approach:**
1. Read both feedstocks live, and the registry entry of each of the 22 package names (AC 1).
2. `recipes/db-gpt`: confirm fidelity (AC 3), bring its CFE metadata current with no recipe change (AC 4), audit
   maintainers (AC 6), and run `refresh-wave` over it as a one-recipe wave to record `already-current`.
3. `recipes/langflow`, after Story 25.7: bring every output to the feedstock's own version (AC 5), then run the gates
   and rebuild (AC 7).
4. Record the corrected mapping, and every other directory that declares one of the 22 names (ACs 8 and 9). Close
   Wave F's deferral. File driver gap 5 (AC 10). Close with the Rule-2 retro (AC 12).

Ledger key: `25-14-wave-f-s-other-18-packages-are-built-by-their-feedstock-s-own-mirror`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: feature / M / S-25.7, S-25.13, S-25.15.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57), the refresh campaign; CAP-20, the recurring campaigns; CAP-23, the CFE machinery
  the driver lives in. No new CAP, so no FR moves.
- AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in the `retro(cfe):` commit).
- CFE G52, G53, G72, G92, G95 and G96; SKILL.md § *Local-mirror fidelity* and § *Bulk refresh waves*;
  `docs/specs/feedstock-refresh.md` § *Track B* (Wave A step A3, Wave F, coordination rules 1 to 5, landmines 1 to 13).
- `spec-fleet-stewardship` CAP-1 governs `recipes/**`; `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Siblings: Story 25.7 refreshes `recipes/langflow` first; its batch no longer holds `recipes/lfx` (ruling 2,
  2026-10-09). Story 25.15 retires the five `lfx*` copies first. Story 25.13 mirrors the other two Wave F feedstocks.
  Story 25.4's spec holds driver gaps 1 to 4.

## Acceptance Criteria

1. **Read live first.** Given `db-gpt-feedstock` and `langflow-feedstock` When the story starts Then it records in
   § *Run results*, before any file changes: each feedstock's published version and build number, its context
   versions, its outputs, its deployed `extra.recipe-maintainers` and the files in its `recipe/` directory; and, for
   each of the 22 names (the 18 and the four `lfx-*` bundles), its `feedstock-outputs` registry entry. A name whose
   entry no longer names `db-gpt` or `langflow` alone is `needs-review` with that entry recorded. A feedstock that has
   published past this spec's versions is followed, and the move is noted.
2. **No directory per output.** Given the 18 When the story closes Then it has created no `recipes/<output>/`
   directory for any of them, and each is declared by its feedstock's mirror, `recipes/db-gpt` or `recipes/langflow`,
   whose `extra.feedstock-name` names that feedstock.
3. **`recipes/db-gpt` stays a faithful mirror.** Given `recipes/db-gpt` and `db-gpt-feedstock`'s `recipe/` When they
   are compared Then everything outside `extra:` and comments matches, and every patch file is byte-identical to the
   feedstock's. Each of the 16 outputs is at the feedstock's `version` and build number, so the one-recipe
   `refresh-wave` dry-run reports it `already-current`. A difference is resolved toward the feedstock, or recorded as a
   deliberate choice in the CFE comments block.
4. **`recipes/db-gpt`'s CFE metadata tells the truth.** Given its stale CFE block When the story updates it Then it
   reads `cfe-on-conda-forge-status: confirmed-on-conda-forge` and
   `cfe-on-conda-forge-feedstock: https://github.com/conda-forge/db-gpt-feedstock`, and
   `cfe-forge-recipe-updates-needed` drops what the feedstock already took. The header comment states the 16 outputs,
   the version and both maintainers, and keeps its dated history as history. No version, build number, requirement,
   patch or maintainer changes, and the block keeps one header and one `cfe-conda-name` (G92).
5. **Every `langflow-suite` output at the feedstock's own version.** Given `recipes/langflow` after Story 25.7 When
   each output is compared with `langflow-feedstock`'s context Then `langflow-base` and `langflow` are at `version`,
   `langflow-sdk` at `sdk_version`, and `lfx-duckduckgo`, `lfx-arxiv`, `lfx-ibm` and `lfx-docling` at their own context
   versions. At mint those were 1.12.4, 0.4.0, 0.1.5, 0.1.5, 0.2.5 and 0.1.7. A version Story 25.7 left behind moves
   through CFE, with each output's requirements checked against the feedstock's (G96), and Story 25.7's three patches
   still apply.
6. **Maintainers kept (G53).** Given both mirrors When each one's `extra.recipe-maintainers` is compared with its
   deployed feedstock's list, read live at run time Then the local list is a superset. § *Run results* records the
   audit.
7. **Gates and a build where the recipe changed.** Given a mirror whose recipe changed outside its CFE block and
   comments When `validate_recipe`, `optimize_recipe`, `check_dependencies`, `scan_for_vulnerabilities` and
   `conda-smithy recipe-lint --conda-forge` run Then none reports an error, an expected finding is recorded with its
   reason, and every output builds green on linux-64 into an isolated `--output-dir` (G52). Otherwise the
   `cfe-local-build-*` fields record `build-clean-test-blocked` (G95) or `not-attempted` with the reason. A mirror
   whose change stays inside its CFE block and comments is not rebuilt, and its existing `cfe-local-build-*` record
   stands, as § *Run results* notes.
8. **One declarer per name.** Given the 22 names When every `recipes/*/recipe.yaml` and `meta.yaml` is parsed for
   `package.name` and each `outputs[].package.name` Then each name is declared by its feedstock's mirror alone, and
   § *Run results* records the parse and its result. At mint the five `lfx*` copies also declared the eight
   `langflow-suite` outputs. Story 25.15 retires them first (ruling 2, 2026-10-09; this story's Deps), so the story
   expects no other declarer. A directory that still declares one of the 22 names is listed with its version, and
   left for the operator; this story removes none.
9. **The corrected mapping, and Wave F's deferral closed.** Given Wave A's 20 no-local-recipe names and the four
   bundles it bucketed `v1-ahead` When the story closes Then § *Run results* carries one row per name: package,
   owning feedstock, mirror directory, local version and published version. Story 25.13's two rows come from its run
   results. If the mason deferred-work ledger carries the row ingested from Story 25.2's deferral "Twenty
   genuinely-missing local mirrors", that row is closed, naming Stories 25.13 and 25.14. The mapping rule is a row in
   this spec's `deferred:` frontmatter naming `docs/specs/feedstock-refresh.md` (Wave A step A3), which has no tracked
   tool: map a package to its feedstock through the atlas's `packages.feedstock_name`, never by directory name.
10. **Driver gaps recorded, not patched.** Given driver gap 5 (`refresh-wave` moves `context.version` only, so a
    suite's per-output context versions stay behind) and any other gap the story finds When the story closes Then each
    is a row in this spec's `deferred:` frontmatter naming
    `.claude/skills/conda-forge-expert/scripts/refresh_wave.py` with path:line evidence, unless Story 25.4's spec or
    the mason deferred-work ledger already names it. The story does not change the driver.
11. **Nothing leaves the local repo.** Given the story's whole run When it closes Then no `git push`, `gh pr create`,
    `gh repo fork` or `gh api` write reached anything outside `rxm7706/local-recipes`; no issue or comment was opened;
    no `mason recipe submit` or `mason package ship` and no CFE `submit_pr` or `prepare_submission_branch` ran.
12. **Retro and suite.** Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands
    a CFE `CHANGELOG.md` semver entry, with the four version carriers in lockstep: PATCH, or MINOR for a new gotcha
    (candidates: a multi-output feedstock's outputs are not missing mirrors; a suite's per-output versions need their
    own refresh). If another Epic 25 story's retro reached `main` first, this one takes the next version when it merges
    `main`. Also `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1): § *Local-mirror fidelity*, § *Bulk refresh waves*,
   G52, G53, G72 and G92; and `docs/specs/feedstock-refresh.md` § *Track B*. Where the file, this spec and the skill
   differ, the skill wins, and the story records the difference.
2. Confirm Stories 25.7, 25.13 and 25.15 are `done`, and read both feedstocks and the 22 registry entries live (AC 1).
3. `recipes/db-gpt`: compare it with the feedstock (AC 3), run a one-recipe `refresh-wave` dry-run (manifest `track: B`,
   `wave: 25-14`, `name: db-gpt`, `feedstock: db-gpt`, under the gitignored `feedstock-update/` directory), update the
   CFE block (AC 4) and audit maintainers (AC 6).
4. `recipes/langflow`: bring every output to the feedstock's version (AC 5), audit maintainers (AC 6), then run the
   gates and the isolated build (AC 7), at most 4 builds at once.
5. Run the package-name parse (AC 8), write the mapping table, and close the ledger row (AC 9). File the gaps (ACs 9
   and 10).
6. Review every diff, then commit per recipe: `recipes: …`, never a subject starting `Story 25.14:`.
7. Close with the Rule-2 retro in its own commit, subject `retro(cfe): v<x.y.z> — …` (AC 12).
8. Reconcile every Spec `spec-surface-check` names: memlog first, then `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement. Where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.
- Keep `cfe-*` metadata in the local recipe. It is stripped only if a PR is ever asked for (G62).
- Read feedstocks and the `feedstock-outputs` registry only: raw files, or `gh api` GETs.

**Never:**
- Nothing reaches conda-forge, a feedstock or staged-recipes. No `git push`, `gh pr create`, `gh repo fork` or
  `gh api` write outside `rxm7706/local-recipes`; no issue or comment; no `mason recipe submit` or
  `mason package ship`; no CFE `submit_pr` or `prepare_submission_branch`.
- Do not create a `recipes/<output>/` directory for any of the 22 names, and do not remove or empty any recipe
  directory. Story 25.15 retires the five `lfx*` copies, and keeps `recipes/dbt` (open question 2, resolved).
- Do not drop a co-maintainer from any `recipe-maintainers` list, and never self-merge on a co-maintained feedstock.
- Do not touch a recipe directory other than `recipes/db-gpt/` and `recipes/langflow/`; touch `recipes/langflow/` only
  after Story 25.7 is `done`.
- Do not edit `refresh_wave.py`, or any CFE file outside the `retro(cfe):` commit. Do not touch
  `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| output already current | `recipes/db-gpt` at the feedstock's 0.8.2 | `already-current`; CFE block corrected only; no rebuild | — |
| output behind in a suite | `langflow-sdk` at 0.3.3 after Story 25.7 | `sdk_version` moved to the feedstock's; rebuilt | needs-review if a patch no longer applies |
| registry moved | a name's `feedstock-outputs` entry names another feedstock | recorded; that name `needs-review` | AC 1 |
| duplicate declarer | a directory other than the mirror declares one of the 22 names | listed with its version; left in place | AC 8; Story 25.15 retires the `lfx*` copies first |
| maintainer clobber | a mirror would carry fewer handles than its feedstock | the deployed list re-merged | G53, landmine 10 |
| test env pollution | a dependency solve fails for a package on conda-forge | rebuild isolated before recording a block | G52, landmine 13 |
| dependency left | 25.7, 25.13 or 25.15 not `done` | stop; the story does not start | Deps |

## Open questions

1. **Did "create them" mean 20 standalone directories?** This story reads the ruling as Track B Q2 itself frames it:
   create a mirror for each feedstock with none, after Wave A step A3 prunes the mapping artifacts. The Dream's
   2026-10-09 (night) entry had already noted that Wave F "may be two recipes, not 20". *Recommended:* no new
   directory for the 18 (option (b), above). *Alternative:* author 18 single-output recipes anyway, either beside the
   multi-output mirrors (each mirrors no feedstock, cannot be submitted, and shadows its twin in the local channel) or
   instead of their outputs (option (a): both mirrors stop matching their feedstocks). Either alternative re-scopes
   this story before it starts.
   **Resolved 2026-10-09 (night, latest), operator ruling 1, "Yes, inside the mirrors":** keep Story 25.13 (the two
   new recipes) and this story (the 18 outputs at their published versions inside `recipes/db-gpt` and
   `recipes/langflow`). No standalone directory. This story stands as written.
2. **Retire the duplicate recipe directories?** `recipes/lfx`, `recipes/lfx-arxiv`, `recipes/lfx-docling`,
   `recipes/lfx-duckduckgo` and `recipes/lfx-ibm` each re-declare all eight `langflow-suite` outputs, a version behind
   `recipes/langflow`. `recipes/dbt` builds the same `dbt-core` 1.12.2 as `recipes/dbt-core`. They are why Wave A
   bucketed the four bundles `v1-ahead` and the conda name `dbt` against `dbt-core`. Story 25.7 currently refreshes
   `recipes/lfx`. *Recommended:* retire the duplicates in a fix story of their own once the operator agrees; the git
   history keeps them. *Alternative:* keep them, and accept the drift and the local-channel shadowing. This story changes
   none of them either way.
   **Resolved 2026-10-09 (night, latest), operator ruling 2, "Retire in a fix story":** "Mint a mason fix story that
   removes the six duplicate dirs (folded into recipes/langflow and recipes/dbt-core) and drops recipes/lfx from 25.7's
   batch." Story 25.15 is that fix, and this story depends on it. Its mint verified ownership first. The five `lfx*`
   copies mirror no feedstock and retire. `recipes/dbt` is kept: it is the `recipes/<feedstock>/` mirror of
   `conda-forge/dbt-feedstock`, so Story 25.15's open question 1 returns the `recipes/dbt`/`recipes/dbt-core` pair to
   the operator. Story 25.7's batch dropped `recipes/lfx`.

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57), with CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 (night, later) — Ruled: Wave F creates the
missing mirrors, and the 18 outputs stay in their feedstock's mirror*.
Ledger key: `25-14-wave-f-s-other-18-packages-are-built-by-their-feedstock-s-own-mirror`.
Ledger status at mint: `backlog`.
Deps: S-25.7, S-25.13, S-25.15.
Amended 2026-10-09 (night, latest) on the operator's rulings "Yes, inside the mirrors" and "Retire in a fix story":
both open questions resolved, and S-25.15 added, because this story moves the `lfx-*` bundles that the five
`lfx*` copies also declared.
Flag: `flag-exempt: recipe-build` (a recipe build ships no runtime capability behind a flag).
Minted 2026-10-09 on the operator's answer to Track B Q2 ("create them").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test`. Expected: pass. This is the station's `verify_commands`;
  the story changes no Mason code.

**Manual checks:**
- `pixi run -e local-recipes validate recipes/<dir>` and `pixi run -e local-recipes lint-optimize recipes/<dir>` report
  no errors for `recipes/db-gpt` and `recipes/langflow`; a linux-64 `rattler-build build --recipe
  recipes/<dir>/recipe.yaml --output-dir <isolated dir>` exits 0 for each mirror the story changed outside its CFE
  block, or the recorded block is justified.
- `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/<dir>`: no lint (G65).
- `git diff --name-only origin/main...HEAD -- recipes/` lists only `recipes/db-gpt/` and `recipes/langflow/`.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert`: exactly one `retro(cfe):` subject,
  and that commit carries `CHANGELOG.md`.
- § *Run results* carries the live read, the registry entries, the 24-row mapping table, the duplicate declarers and
  the maintainer audit.
- `pixi run -e pyforge-guild spec-surface-check`: exit 0 after the scoped stamps.

## Run results

### Live read (2026-10-10, before edits)

| Feedstock | Published | Build | Context versions | `recipe/` files | Deployed maintainers |
|---|---|---|---|---|
| `db-gpt-feedstock` @ `76343d18` | 0.8.2 | 2 | `version` 0.8.2 | `recipe.yaml`, `patches/` (3) | rxm7706, pb01ka |
| `langflow-feedstock` | 1.12.4 | 0 | `version` 1.12.4; `sdk_version` 0.4.0; bundles 0.1.5 / 0.1.5 / 0.2.5 / 0.1.7 | `recipe.yaml`, `patch_deps.py`, `license-checker-format.json` | rxm7706, pb01ka |

Registry (`conda-forge/feedstock-outputs`, sharded `outputs/` tree): all 16 `dbgpt-*` names → `db-gpt`; `langflow-base`, `langflow-sdk`, `lfx`, and the four `lfx-*` bundles → `langflow`. No name mapped to a different feedstock alone (`needs-review` none).

### `recipes/db-gpt`

- Fidelity: recipe body outside `extra:` matches feedstock except patch-list comment order (aligned to feedstock); three patch files byte-identical to feedstock `recipe/patches/`.
- `refresh-wave` dry-run manifest `B/25-14`: **already-current** at 0.8.2.
- CFE block updated to `confirmed-on-conda-forge` + feedstock URL; stale forge-update row dropped; header comment now states 16 outputs and both maintainers.
- Maintainers: local list equals deployed (superset trivial).

### `recipes/langflow` (post Story 25.7)

- Context and per-output version pins match feedstock; Story 25.7 re-mirror + build record stands.
- **No recipe edit in this story** — existing `cfe-local-build-*` on `recipes/langflow` unchanged (AC 7).

### Package-name parse (22 names + `langflow` suite output)

- **Duplicate declarers:** none (Story 25.15 retired the five `lfx*` copies).
- Each of the 22 names is declared only by `recipes/db-gpt` or `recipes/langflow`.

### Wave F mapping (24 rows: 18 Wave A “missing” + 4 bundles mis-bucketed + 2 from Story 25.13)

| Package | Owning feedstock | Mirror | Local version | Published |
|---|---|---|---|---|
| dbgpt … dbgpt-serve (16 rows) | db-gpt | recipes/db-gpt | 0.8.2 | 0.8.2 |
| langflow-base | langflow | recipes/langflow | 1.12.4 | 1.12.4 |
| langflow-sdk | langflow | recipes/langflow | 0.4.0 | 0.4.0 |
| lfx-duckduckgo, lfx-arxiv, lfx-ibm, lfx-docling | langflow | recipes/langflow | 0.1.5 / 0.1.5 / 0.2.5 / 0.1.7 | same |
| dbt-snowflake, zxing-cpp-python | own feedstocks | recipes/dbt-snowflake, recipes/zxing-cpp-python | per Story 25.13 run results | per 25.13 |

### Deferred-work ledger

- Closed **DW-mason-25-2** (“Twenty genuinely-missing local mirrors…”) — Wave F completed by Stories **25.13** and **25.14**.

## Review Triage Log

### 2026-10-10 — Review pass

- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none)

## Auto Run Result

Status: done

Summary: Wave F outputs inside feedstock mirrors; db-gpt CFE corrected; langflow unchanged after 25.7; retro(cfe) v8.99.9; `pyforge-mason-test` and `spec_surface_reconcile.py` green.
