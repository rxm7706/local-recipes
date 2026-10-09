---
title: "22.3: ctng-compilers loses its sentinel key once rattler-build renders its output graph"
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

**Problem:** `recipes/ctng-compilers/recipe.yaml` is the twelfth of the files the 2026-08-16 bulk crm conversion
(`20b2f459fa`) left with a `<conda_recipe_manager.types.SentinelType object at 0x…>` mapping key. The key sits in the
`gxx_impl` output's `tests[0]`, where `meta.yaml` wraps the tzdb checks in
`{% if cross_target_cxx_stdlib == "libstdcxx" %}`, nesting `{% if target_platform == cross_target_platform %}`.

Story 22.1's dispatch run (2026-10-09) repaired the key and the defects the render found beside it:

- the test became two nested `if:` blocks in the element's own `script:`, in `meta.yaml`'s order;
- the output-level `run_exports` moved under `requirements`;
- `context` gained the values the render asked for.

The file then parses and passes `validate_recipe`. `rattler-build build --render-only` 0.76.1 with
`.ci_support/linux64.yaml` plus the local pinning still exits 1 with `Cycle detected in recipe outputs` across the gcc
stack. rattler-build #2531 (a false cycle from `pin_subpackage` in `run_constraints`) closed on 2026-07-03 with PR #2537,
and 0.76.1 (2026-09-14) carries that fix, so this is a case it did not cover.

Operator ruling, 2026-10-09: Story 22.1 lands without `ctng-compilers`, which moves to this story. A second ruling the
same day also moved `vc` out, to Story 22.4, so 22.1 lands ten recipes. 22.1 restored the file to `main`'s copy,
sentinel included. 22.1's corpus check (`test_no_crm_sentinel_keys_in_recipe_yaml`) allowlists exactly one leak here,
`recipes/ctng-compilers/recipe.yaml` at `outputs[6].tests[0]`, naming this story; a second leak in the file still reds. The draft repair is kept in branch history: `git show 0dc82240c5:recipes/ctng-compilers/recipe.yaml`.

**Approach:**

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1).
2. Re-read the live feedstock (`conda-forge/ctng-compilers-feedstock`): if it moved to v1, mirror its `recipe.yaml`
   verbatim (G94) and skip step 3.
3. Re-apply the draft repair on the current file and render. If the cycle persists on the newest rattler-build, try a
   feedstock-faithful variant set: the feedstock's own `conda_build_config.yaml` in place of the generic `linux64`
   config.
4. Gates: render-only on linux-64 with at least one output rendered, `validate_recipe`, and the CI-parity lint on a copy
   without `meta.yaml`. No build: ctng-compilers is heavyweight.
5. In the story's `retro(cfe):` commit, remove the `ctng-compilers` allowlist entry from the corpus check and bump CFE
   (PATCH unless the retro adds guidance).

Ledger key: `22-3-ctng-compilers-loses-its-sentinel-key-once-rattler-build-renders-its-output-graph`.
Ledger status: `blocked` (minted blocked by the 2026-10-09 split; the operator flips it).
Type / Effort / Deps: fix / M / S-22.1.

### Blocking condition

`rattler-build build --render-only` (0.76.1, the newest release on 2026-10-09) reports `Cycle detected in recipe
outputs` for the repaired file. The story unblocks when either:

- a rattler-build release renders the repaired file, or
- a feedstock-faithful variant set renders it on the current release.

Reporting the cycle upstream (a rattler-build issue) is outward work and waits for operator confirmation.

### Living CAP citations

- `spec-pyforge-mason` CAP-32 (FR-54); AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in
  the `retro(cfe):` commit).
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Split from Story 22.1 (operator ruling 2026-10-09). CFE G121 records the converter leak.

## Acceptance Criteria

- Given `recipes/` When `grep -rl 'object at 0x' recipes/ --include=recipe.yaml` runs Then it does not list `recipes/ctng-compilers/recipe.yaml`
- Given `recipes/ctng-compilers/recipe.yaml` When `rattler-build build --render-only` runs with `.ci_support/linux64.yaml` and the local pinning (or the feedstock-faithful variant set) Then it exits 0 with at least one output rendered, not skipped
- Given the file When `validate_recipe` and `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge` run on a copy without `meta.yaml` Then neither reports an error
- Given the repaired `gxx_impl` test When it is compared with `meta.yaml` Then it runs the same commands under the same conditions, in the same order
- Given the recipe directory When it is listed Then `meta.yaml` is still there
- Given the story's `retro(cfe):` commit When `pixi run -e local-recipes test` runs Then `test_no_crm_sentinel_keys_in_recipe_yaml` passes with no `ctng-compilers` allowlist entry
- Given the story closes When the Rule-2 retro runs Then its `retro(cfe):` commit carries a CFE `CHANGELOG.md` semver entry and its version carriers

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement; where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Keep `meta.yaml` in the directory, and point every render, test and lint at `recipe.yaml`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not flip this story's ledger key out of `blocked`; the operator does.
- Do not build ctng-compilers (heavyweight).
- Do not open a feedstock, staged-recipes, upstream or rattler-build PR or issue without an explicit ask.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-32 (FR-54).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 — Ruled: Story 22.1 lands for eleven recipes, and
ctng-compilers waits for rattler-build*.
Ledger key: `22-3-ctng-compilers-loses-its-sentinel-key-once-rattler-build-renders-its-output-graph`.
Ledger status at mint: `blocked`.
Deps: S-22.1.
Flag: `flag-exempt: recipe-build` (a recipe repair ships no runtime capability behind a flag).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code).

**Manual checks:**
- `grep -rl 'object at 0x' recipes/ --include=recipe.yaml` — expected: no `recipes/ctng-compilers/recipe.yaml`.
- `pixi run -e local-recipes rattler-build build --render-only --recipe recipes/ctng-compilers/recipe.yaml --variant-config .ci_support/linux64.yaml --variant-config .pixi/envs/local-recipes/conda_build_config.yaml`
  — expected: exit 0 with at least one rendered output.
- `pixi run -e local-recipes validate recipes/ctng-compilers` and the CI-parity lint on a copy without `meta.yaml` —
  expected: no error.
- `pixi run -e local-recipes test` — expected: pass, with no `ctng-compilers` allowlist entry.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Spec Change Log

- 2026-10-09: Minted blocked from the operator's ruling that split `ctng-compilers` out of Story 22.1. The 22.1 run's
  render evidence: `Cycle detected in recipe outputs` on rattler-build 0.76.1 after the sentinel and output-level
  `run_exports` repairs (Story 22.1's `deferred:` entry, now pointing here).
- 2026-10-09: Corrected after the second independent review of the 22.1 landing. The text assumed the other eleven
  recipes were fixed and that this story empties the allowlist. A second ruling moved `vc` to Story 22.4, so the
  allowlist holds two entries, keyed by file and location. The ACs, Approach step 5 and Verification now say this
  story removes the `ctng-compilers` entry and the grep no longer lists `recipes/ctng-compilers/recipe.yaml`.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
