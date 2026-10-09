---
title: "25.1: Track A's Wave H refreshes the sole-maintainer recipes the first waves missed"
type: 'feature'
created: '2026-09-29'
status: 'in-progress'
baseline_revision: '70142b6f71afc760d8935d0f7c4b26a00182b249'
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

**Problem:** Track A of the feedstock refresh campaign (`docs/specs/feedstock-refresh.md`, § *Track A*) brings every
local recipe behind a **sole-maintainer** conda-forge feedstock (`rxm7706` the only maintainer) to the feedstock's
published version. Waves B to F shipped on 2026-06-21 for the 252 recipes then behind (`1fe1848b43`, `363537dd43`).
Those waves were scoped to *behind* recipes only. A recipe at the right version but still in `meta.yaml` is not
submission-ready, and a sole feedstock with no local recipe has no mirror at all. The same day the file was reopened for
**Wave H**: 179 recipes (155 version-current `meta.yaml`-only, 24 missing), counted by a live working-tree scan on
2026-06-21. Run 3 finished three of them (`amundsen-common`, `amundsen-metadata`, `amundsen-search`), uncommitted, and
paused at a weekly usage limit. Since then the July punch-list and bump waves have changed many recipes, so the counts
are stale.

The operator ruled on 2026-09-29 that `docs/specs/` retires (`spec-one-chain-per-station:CAP-11`) and that this
unfinished campaign joins Mason's chain.

**Approach:** run Wave H through `conda-forge-expert`, with the legacy file's Wave A re-baseline first.
- Re-count the sole-maintainer scope live from the atlas.
- Bucket each recipe: H1 v0-to-v1 migration (C1 keep `meta.yaml` when the feedstock is still v0, C2 delete it when the
  feedstock is already v1), H2 create-missing (after resolving the directory-to-conda-name mapping), plus any recipe
  that has fallen behind again since June (v1-refresh).
- Regenerate each recipe with diff-apply, fold in platform expansion only where the recipe is compiled, and build it
  locally.
- Commit per bucket through this story's PR.

Ledger key: `25-1-track-a-s-wave-h-refreshes-the-sole-maintainer-recipes-the-first-waves-missed`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / L / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57); AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in
  the `retro(cfe):` commit).
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Sibling: Story 25.2 (Track B, co-maintained) is disjoint by construction and independent.

## Acceptance Criteria

- Given the atlas refreshed within 3 days When the story starts Then the story spec records the live sole-maintainer
  count, the Wave H remainder and its per-bucket split (H1 C1, H1 C2, H2 create-missing, v1-refresh, false positives
  dropped), before any recipe changes
- Given each recipe in the live scope When the story closes Then its `recipe.yaml` is at the feedstock's published
  version (or confirmed not-behind), with the current CFE `cfe-*` block at the bottom
- Given a C1 recipe (feedstock still v0) When it is migrated Then `meta.yaml` stays beside the new `recipe.yaml`; given
  a C2 recipe (feedstock already v1) Then the local `meta.yaml` is removed
- Given each recipe When `validate_recipe`, `optimize_recipe` and `conda-smithy recipe-lint --conda-forge` run Then none
  reports an error (STD-002 is expected for C1), and `check_dependencies` finds no missing dependency
- Given each recipe When it is built locally on linux-64 into its own `--output-dir` Then it builds green, or its
  `cfe-local-build-*` fields honestly record `build-clean-test-blocked` (G95) or `not-attempted` with the reason
- Given a noarch recipe When it is regenerated Then no platform expansion is added; given a compiled one Then its matrix
  widens to osx-arm64 and linux-aarch64 per `docs/how-to/feedstock-platform-expansion.md`
- Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a CFE `CHANGELOG.md`
  semver entry and its version carriers
- Given `pixi run --frozen -e pyforge-mason pyforge-mason-test` When it runs Then it passes (no Mason code changes)

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1). Read `docs/specs/feedstock-refresh.md` § *Track A* for
   its waves, parameters and landmines 1 to 9. Where the file and the skill differ (the `cfe-*` block version, the
   Python floor), the skill wins, and the story records the difference.
2. Wave A, re-baseline:
   - Refresh the atlas if it is older than 3 days.
   - Recompute the sole-maintainer set and the version delta, then live-verify each candidate against its feedstock and
     PyPI (the GitHub-tag-numbering guard, landmine 1).
   - Subtract the recipes already done, including Run 3's three if they are in the tree.
   - Record the counts in this spec's § *Run results*, then stop for the operator to confirm the scope. Continue after
     that confirmation.
3. Work the buckets in batches of at most 5, with at most 4 regen-or-build agents at once (landmine 5). Per recipe:
   - regenerate or update at the published version, and modernize grayskull regressions;
   - run the gates in order: `validate`, `lint-optimize`, `check_dependencies`, `scan-vulnerabilities`, CI-parity lint;
   - build into `build_artifacts/<name>` (G52: no shared output dir), and stamp `cfe-local-build-*` from the real
     outcome.
4. Review every diff, then commit per bucket (`recipes: …`, never a subject starting `Story 25.1:`).
5. Close with the Rule-2 retro in its own commit, subject `retro(cfe): v<x.y.z> — …`. Bump MINOR for a new gotcha,
   PATCH otherwise.
6. Reconcile every Spec `spec-surface-check` names: memlog first, then `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement. Where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.
- Keep `cfe-*` metadata in the local recipe (it is stripped only if a PR is ever asked for; G62).

**Never:**
- Do not open a feedstock, staged-recipes or upstream PR, and do not push a feedstock branch (no explicit ask; a green
  local build ends each recipe).
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not touch a co-maintained recipe: that set is Story 25.2's.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path, C2 | feedstock v1, local `meta.yaml` only | `recipe.yaml` authored, `meta.yaml` removed, build green | — |
| C1 | feedstock still v0 | `recipe.yaml` beside `meta.yaml`; `cfe-forge-recipe-updates-needed: [meta-yaml-to-recipe-yaml]` | STD-002 expected |
| tag numbering | feedstock tag ≠ PyPI version | re-map, or confirm not-behind; no blind bump | landmine 1 |
| mapping artifact | a "missing" recipe exists under another directory name | counted as present, not re-created | resolve via `lookup_feedstock` first |
| test env pollution | a dep solve fails for a package that is on conda-forge | rebuild isolated before recording a block | G52 |
| generator KeyError | `'releases'` from the version-pinned path | use the latest-version path when it equals the target | landmine 6 |
| now co-maintained | a sole feedstock gained a maintainer since June | moves to Story 25.2's scope; noted in the run results | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-29 (evening) — Proposed: the feedstock refresh
campaign joins Mason's chain*.
Ledger key: `25-1-track-a-s-wave-h-refreshes-the-sole-maintainer-recipes-the-first-waves-missed`.
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
- § *Run results* in this spec carries the live counts, the per-bucket results and every recipe left blocked.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert` — exactly one `retro(cfe):` subject, and
  that commit carries `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0 after the scoped stamps.

## Run results

**Wave A (re-baseline) — 2026-10-09.** Script: `.cursor/wave_h_rebaseline.py`. Artifacts:
`.cursor/wave_h_baseline.json`, `.cursor/wave_h_baseline.md`. **Stop here for operator
scope confirmation** before any recipe edits (Task 2 gate).

| Metric | Count |
|--------|------:|
| Sole-maintainer feedstocks (cf_atlas) | 584 |
| **Wave H remainder** (H1 C1 + H1 C2 + H2 + v1-refresh) | **33** |
| H1 C1 (v0 feedstock, meta-only, version-current) | 0 |
| H1 C2 (v1 feedstock, meta-only, version-current) | 0 |
| H2 create-missing | 0 |
| v1-refresh (local behind `latest_conda_version`) | 33 |
| False positives dropped | 2 |
| Already v1-current (out of Wave H scope) | 549 |

**Atlas:** shared `cf_atlas.db` at primary checkout, built **2026-09-18** (~20.5 days old;
story gate is 3 days). Full `bootstrap-data` / `build-cf-atlas` (~30–45 min) was **not** run
this session; published versions may lag live conda-forge. Refresh atlas (or `atlas-phase`
B/H/K) before recipe work.

**Methodology:** sole-maintainer query on `package_maintainers` ⋈ `maintainers` (rxm7706 only);
local `recipes/` scan for `recipe.yaml` / `meta.yaml` and version compare via
`packaging.version`; case-insensitive dir match; `pixitainer-docker` → `pixitainer` and
`Docs2Static` / `Flake8-pyproject` / `Django-Enterprise-Maintenance-Suite` mapping artifacts
count as present, not H2. GH-numbering suspect (`html-to-markdown`) dropped to false positives.
Archived `vllm-nccl-cu12` dropped. Run 3 pilots (`amundsen-common`, `amundsen-metadata`,
`amundsen-search`) are in **already v1-current**, not subtracted from remainder.

**Context vs June 2026:** legacy Wave H expected ~179 (155 meta-only + 24 missing); the tree
after Waves B–F and later bumps leaves **no version-current meta-only sole recipes** and **no
genuine missing dirs** after mapping — remainder is mostly **re-behind** (33) since the stale
atlas / upstream releases.

**v1-refresh sample (first 10 by conda_name):** ag-ui-langgraph, ag-ui-protocol, copilotkit,
customersatisfactionmetrics, ddgs, … (full list in JSON).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate); the operator reviews the branch before
  landing it as `Merge pyforge-mason/25-1-track-a-s-wave-h-refreshes-the-sole-maintainer-recipes-the-first-waves-missed into main`.
