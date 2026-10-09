---
title: "22.4: vc loses its sentinel key once rattler-build can emit its vc14 track feature"
type: 'fix'
created: '2026-10-09'
status: 'blocked'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-22-1-the-twelve-recipes-carrying-conda-recipe-manager-s-sentinel-key-are-repaired.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `recipes/vc/recipe.yaml` is one of the twelve files the 2026-08-16 bulk crm conversion (`20b2f459fa`) left
with a `<conda_recipe_manager.types.SentinelType object at 0x…>` mapping key. The key sits in the activation output's
`tests[0]` (`outputs[5].tests[0]`). There, `meta.yaml` wraps three `# [win]` clang checks and a `clang` test requirement
in `{% if vsyear | int >= 2022 %}`.

Story 22.1's dispatch run (2026-10-09) ported the whole file to v1, and the port renders on win-64. The independent
review of the 22.1 landing (2026-10-09; evidence in the session scratchpad `review-221/`: `vc-win.err`, `vc-main.yaml`,
`st/`, `mj/`, `vc_repack.py`) found that it does not say what `meta.yaml` says:

- **Track features.** `meta.yaml` gives the `vc`, `vs<year>_<platform>` and `vs_<platform>` outputs
  `track_features: [vc{{ vc_major }}]` (`vc14`), one feature the three share, so the solver de-prioritises them
  together. rattler-build 0.76.1 rejects `build.track_features`. The port used `build.variant.down_prioritize_variant:
  1`, which writes a per-package `track_features: <name>-p-0` (a test output built with it carries `st-out-p-0`), not
  `vc14`.
- **Variant matrix.** The feedstock's `recipe/conda_build_config.yaml` zips five entries: VS 2026 win-64 and win-arm64,
  VS 2022 win-64 and win-arm64, VS 2019 win-64 (`vcver`, `vsyear`, `vsver`, `runtime_version`, `update_version`,
  `cl_version`, `uuid`, `sha256`, `cross_target_platform`). The port hardcoded the first entry in `context`, so it
  renders VS 2026 win-64 only.
- **Recipe files.** The feedstock's `recipe/` also holds `vc_repack.py`, `activate.bat`, `LICENSE.TXT` and
  `conda_build_config.yaml`; the mirror has only `meta.yaml` (G94).
- **Staging inheritance.** The port's outputs inherit the `vc-extract` staging output and call
  `python …/vc_repack.py`, but an inheriting output does not get the staging build environment: its script sees only
  its own build requirements, so `python` is `command not found` (status 127) unless the output declares it.
- **String-vs-int comparison.** The port compared the string `vsver` with an integer. minijinja answers `true` for
  `"9" >= 17` as well as for `"18" >= 17`, so a VS 2019 entry (`vsver` 16) would take the VS 2022+ branch. Every
  comparison needs `| int`.

Operator ruling, 2026-10-09 (the second that day): Story 22.1 lands for ten recipes, and `vc` moves to this story.
22.1 restored `recipes/vc/` to `main`'s copy, sentinel included. 22.1's corpus check
(`test_no_crm_sentinel_keys_in_recipe_yaml`) allowlists exactly that leak, `recipes/vc/recipe.yaml` at
`outputs[5].tests[0]`, naming this story. The draft port is kept in branch history:
`git show 2ebf09ea75:recipes/vc/recipe.yaml`.

**Approach:**

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1), G121 in particular.
2. Re-read the live feedstock (`conda-forge/vc-feedstock`): if it moved to v1, mirror its `recipe/` verbatim (G94) and
   skip step 3.
3. Copy the feedstock's `vc_repack.py`, `activate.bat`, `LICENSE.TXT` and `conda_build_config.yaml` into `recipes/vc/`.
   Port `meta.yaml` against them:
   - read the variant values from `conda_build_config.yaml`, not `context`;
   - emit `track_features: [vc14]` on the three outputs that carry it;
   - declare `python` (and whatever else the script calls) on each output that runs `vc_repack.py`;
   - convert every `vsver` / `vsyear` / `update_version` comparison with `| int`;
   - keep `meta.yaml`'s comments where they map (G93: never at column 0).
4. Gates: render-only on win-64 with `recipes/vc/conda_build_config.yaml` as a variant config, rendering at least one
   output for each of the five entries; `validate_recipe`; the CI-parity lint on a copy without `meta.yaml`. No build:
   vc is Windows-only.
5. In the story's `retro(cfe):` commit, remove the `vc` allowlist entry from the corpus check and bump CFE (PATCH
   unless the retro adds guidance).

Ledger key: `22-4-vc-loses-its-sentinel-key-once-rattler-build-can-emit-its-vc14-track-feature`.
Ledger status: `blocked` (minted blocked by the second 2026-10-09 split; the operator flips it).
Type / Effort / Deps: fix / M / S-22.1.

### Blocking condition

rattler-build 0.76.1 (the newest release on 2026-10-09) cannot emit a named, shared track feature:
`build.track_features` is rejected, and `build.variant.down_prioritize_variant` writes `<name>-p-<n>`. The story
unblocks when a rattler-build release can emit `track_features: [vc14]` on an output. Asking rattler-build for the
feature (an issue or PR) is outward work and waits for operator confirmation.

### Living CAP citations

- `spec-pyforge-mason` CAP-32 (FR-54); AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in
  the `retro(cfe):` commit).
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Split from Story 22.1 (second operator ruling, 2026-10-09). CFE G121 records the converter leak and the traps listed
  above (staging build environment, `track_features`, minijinja string-vs-int).

## Acceptance Criteria

- Given `recipes/` When `grep -rl 'object at 0x' recipes/ --include=recipe.yaml` runs Then it does not list `recipes/vc/recipe.yaml`
- Given `recipes/vc/recipe.yaml` When `rattler-build build --render-only --target-platform win-64` runs with `.ci_support/win64.yaml`, the local pinning and `recipes/vc/conda_build_config.yaml` Then it exits 0 and renders at least one output for each of the five `conda_build_config.yaml` entries, none hardcoded in `context`
- Given the rendered `vc`, `vs<year>_<platform>` and `vs_<platform>` outputs When their `track_features` are read Then each carries `vc14`, and no output carries a `<name>-p-<n>` feature
- Given each output whose script calls `python` When its requirements are read Then it declares `python` itself
- Given each `vsver`, `vsyear` or `update_version` comparison When it is read Then it converts with `| int`
- Given `recipes/vc/` When it is listed Then it holds the feedstock's `vc_repack.py`, `activate.bat`, `LICENSE.TXT` and `conda_build_config.yaml`, and `meta.yaml`
- Given the file When `validate_recipe` and `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge` run on a copy without `meta.yaml` Then neither reports an error
- Given the activation output's test When it is compared with `meta.yaml` Then it runs the same clang checks under the same `vsyear | int >= 2022` condition, with the same test requirement
- Given the story's `retro(cfe):` commit When `pixi run -e local-recipes test` runs Then `test_no_crm_sentinel_keys_in_recipe_yaml` passes with no `vc` allowlist entry
- Given the story closes When the Rule-2 retro runs Then its `retro(cfe):` commit carries a CFE `CHANGELOG.md` semver entry and its version carriers

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement; where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Keep `meta.yaml` in the directory, and point every render, test and lint at `recipe.yaml`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not flip this story's ledger key out of `blocked`; the operator does.
- Do not build vc (Windows-only).
- Do not approximate the shared feature with `down_prioritize_variant`.
- Do not open a feedstock, staged-recipes, upstream or rattler-build PR or issue without an explicit ask.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-32 (FR-54).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 (later) — Ruled: Story 22.1 lands for ten recipes,
and vc waits for a named track feature*.
Ledger key: `22-4-vc-loses-its-sentinel-key-once-rattler-build-can-emit-its-vc14-track-feature`.
Ledger status at mint: `blocked`.
Deps: S-22.1.
Flag: `flag-exempt: recipe-build` (a recipe repair ships no runtime capability behind a flag).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code).

**Manual checks:**
- `grep -rl 'object at 0x' recipes/ --include=recipe.yaml` — expected: no `recipes/vc/recipe.yaml`.
- `pixi run -e local-recipes rattler-build build --render-only --recipe recipes/vc/recipe.yaml --variant-config .ci_support/win64.yaml --variant-config .pixi/envs/local-recipes/conda_build_config.yaml --variant-config recipes/vc/conda_build_config.yaml --target-platform win-64`
  — expected: exit 0, outputs for all five variant entries, `track_features: vc14` on `vc`, `vs<year>_<platform>` and
  `vs_<platform>`.
- `pixi run -e local-recipes validate recipes/vc` and the CI-parity lint on a copy without `meta.yaml` — expected: no
  error.
- `pixi run -e local-recipes test` — expected: pass, with no `vc` allowlist entry.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Spec Change Log

- 2026-10-09: Minted blocked from the operator's second ruling that day, which split `vc` out of Story 22.1. The 22.1
  review's evidence: the draft port's `variant.down_prioritize_variant` in place of `track_features: [vc14]`, a
  `context` holding one of five variant entries, four feedstock recipe files missing, outputs calling `python` without
  declaring it, and an unconverted string-vs-int `vsver` comparison (Story 22.1's `deferred:` entry, now pointing here).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
