---
title: "25.2: Track B refreshes the co-maintained recipes and keeps every other maintainer's work"
type: 'feature'
created: '2026-09-29'
status: 'backlog'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - docs/specs/feedstock-refresh.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - docs/how-to/feedstock-platform-expansion.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Track B of the feedstock refresh campaign (`docs/specs/feedstock-refresh.md`, § *Track B*) covers every
conda-forge feedstock that `rxm7706` **co-maintains**: `rxm7706` is on the maintainer list, and so is someone else. It
was scoped on 2026-06-19 from the atlas: 232 co-maintained feedstocks, 190 with a local recipe (62 v1, 128 v0) and 42
without, and among the 190 roughly 143 behind. It never started. Its extra rule is the one the sole-maintainer track did
not need: preserve every other maintainer's work. A regeneration that emits only `rxm7706` as maintainer, or
"modernizes" away an intentional pin, damages a feedstock someone else also owns.

The operator ruled on 2026-09-29 that `docs/specs/` retires (`spec-one-chain-per-station:CAP-11`) and that this
unfinished campaign joins Mason's chain.

**Approach:** run Track B's waves through `conda-forge-expert`, with its Wave A discovery first.
- Re-count the co-maintained set live from the atlas (maintainer `rxm7706` and more than one distinct maintainer).
- Resolve the directory-to-conda-name mapping for the recipes without a local mirror, and snapshot each feedstock's
  deployed `recipe-maintainers` list.
- Bucket: v1-refresh, v0-migration (C1 keep `meta.yaml` / C2 remove it), gh-numbering, compiled-platform and
  no-local-recipe (pull the deployed feedstock recipe as a new mirror).
- Regenerate with diff-apply, re-merge the full deployed maintainer list, fix grayskull regressions only, and build
  locally.
- Commit per bucket through this story's PR.

Ledger key: `25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / L / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57); AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in
  the `retro(cfe):` commit).
- CFE G53 (re-merge co-maintainers) and G96 (a bump's dependency authority is the feedstock).
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Sibling: Story 25.1 (Track A, sole-maintainer) is disjoint by construction and independent.

## Acceptance Criteria

- Given the atlas refreshed within 3 days When the story starts Then the story spec records the live co-maintained
  count, the mapping split for recipes without a local mirror (mapping artifact vs genuinely missing) and the per-bucket
  counts, before any recipe changes
- Given each co-maintained recipe in scope When the story closes Then its `recipe.yaml` is at the feedstock's published
  version (or confirmed not-behind), with the current CFE `cfe-*` block at the bottom
- Given each processed recipe When its `extra.recipe-maintainers` is compared with the deployed feedstock's Then the
  local list is a superset; the story spec records the audit (G53)
- Given a change that would override a deliberate maintainer choice (an intentional pin, a platform exclusion, a custom
  build script) When the recipe is regenerated Then the choice is kept, and the proposed change is noted in the bottom
  CFE comments block with a `cfe-forge-recipe-updates-needed` token
- Given each genuinely missing feedstock When the no-local-recipe bucket runs Then `recipes/<name>/` mirrors the
  deployed recipe at the same bar as the others
- Given each recipe When `validate_recipe`, `optimize_recipe` and `conda-smithy recipe-lint --conda-forge` run Then none
  reports an error (STD-002 is expected for C1), and `check_dependencies` finds no missing dependency
- Given each recipe When it is built locally on linux-64 into its own `--output-dir` Then it builds green, or its
  `cfe-local-build-*` fields honestly record `build-clean-test-blocked` (G95) or `not-attempted` with the reason
- Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a CFE `CHANGELOG.md`
  semver entry and its version carriers
- Given `pixi run --frozen -e pyforge-mason pyforge-mason-test` When it runs Then it passes (no Mason code changes)

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1). Read `docs/specs/feedstock-refresh.md` § *Track B* for
   its waves, coordination rules 1 to 5 and landmines 1 to 13. Where the file and the skill differ, the skill wins, and
   the story records the difference.
2. Wave A, discovery:
   - Refresh the atlas if it is older than 3 days.
   - Compute the co-maintained set, then resolve the mapping for recipes without a local mirror (`lookup_feedstock`,
     the atlas `conda_name`).
   - Live-verify each behind candidate (the GitHub-tag-numbering guard), and snapshot each deployed maintainer list.
   - Record the counts in this spec's § *Run results*, then stop for the operator to confirm the scope. Continue after
     that confirmation.
3. Work the buckets in batches of at most 5, with at most 4 regen-or-build agents at once. Per recipe:
   - regenerate or update at the published version, and re-merge the full deployed maintainer list;
   - fix regressions only; when unsure whether a choice is deliberate, treat it as deliberate;
   - run the gates in order: `validate`, `lint-optimize`, `check_dependencies`, `scan-vulnerabilities`, CI-parity lint;
   - build into `build_artifacts/<name>` (G52), and stamp `cfe-local-build-*` from the real outcome.
4. Review every diff, then commit per bucket (`recipes: …`, never a subject starting `Story 25.2:`).
5. Run the maintainer-list audit over every processed recipe and record it in § *Run results*.
6. Close with the Rule-2 retro in its own commit, subject `retro(cfe): v<x.y.z> — …`. Bump MINOR for a new gotcha,
   PATCH otherwise.
7. Reconcile every Spec `spec-surface-check` names: memlog first, then `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement. Where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.
- Keep `cfe-*` metadata in the local recipe (it is stripped only if a PR is ever asked for; G62).

**Never:**
- Do not open a feedstock, staged-recipes or upstream PR, and never self-merge on a co-maintained feedstock. Submission
  is a separate, operator-asked step (coordination rule 4).
- Do not drop a co-maintainer from any `recipe-maintainers` list.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not touch a sole-maintainer recipe: that set is Story 25.1's.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | behind v1 recipe, 3 maintainers deployed | refreshed; all 3 maintainers kept; build green | — |
| maintainer clobber | the regen emits only `rxm7706` | the deployed list is re-merged before the recipe is left | landmine 10 |
| deliberate pin | an upper pin with a maintainer's comment | kept; the proposed change parked in the CFE comments block | coordination rule 2 |
| mapping artifact | a "missing" recipe exists under another directory name | counted as present, not re-created | landmine 11 |
| genuinely missing | no local mirror anywhere | deployed recipe pulled into `recipes/<name>/` and brought to the bar | Wave F |
| test env pollution | a dep solve fails for a package that is on conda-forge | rebuild isolated before recording a block | G52, landmine 13 |
| now sole | a co-maintained feedstock lost its other maintainers | moves to Story 25.1's scope; noted in the run results | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-29 (evening) — Proposed: the feedstock refresh
campaign joins Mason's chain*.
Ledger key: `25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: recipe-build` (a recipe build ships no runtime capability behind a flag).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code, so the suite must stay green).

**Manual checks:**
- For each recipe in scope: `pixi run -e local-recipes validate recipes/<name>` and
  `pixi run -e local-recipes lint-optimize recipes/<name>` report no errors, and
  `pixi run -e local-recipes recipe-build recipes/<name>` exits 0 on linux-64 (or the recorded block is justified).
- `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/<name>` — no lint (G65).
- § *Run results* in this spec carries the live counts, the per-bucket results, the maintainer-list audit and every
  recipe left blocked.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert` — exactly one `retro(cfe):` subject, and
  that commit carries `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0 after the scoped stamps.

## Run results

Not started. Wave A writes the live counts here first.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate); the operator reviews the branch before
  landing it as `Merge pyforge-mason/25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work into main`.
