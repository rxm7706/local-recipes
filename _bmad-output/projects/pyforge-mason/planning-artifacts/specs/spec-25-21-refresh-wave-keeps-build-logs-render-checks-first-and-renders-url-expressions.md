---
title: "25.21: refresh-wave keeps build logs, render-checks first and renders URL expressions"
type: 'fix'
created: '2026-11-05'
status: 'in-progress'
baseline_revision: '6d52ea19c3'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: recipe-build
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/refresh_wave.py
  - .claude/skills/conda-forge-expert/scripts/recipe_editor.py
  - .claude/skills/conda-forge-expert/tests/unit/test_refresh_wave.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.19 had to supply three things by hand. `refresh-wave` discards each build's output, so a logging
`rattler-build` shim on `PATH` named the causes. It has no render step, so a scripted pass found 182 of 572 recipes that
failed to parse. And it reports `url-unrenderable` for a URL expression, so 25 recipes needed a scripted rewrite.

**Approach:** Write each build's output to `logs/<name>.log` in the report directory. Add `--render-check`, which runs
`rattler-build build --render-only` on each recipe, in a dry run too, and which `--build` implies: a recipe that fails ends
`needs-review` with its error and spends no gate or build. Render a source URL's `${{ … }}` expressions through one helper in
`recipe_editor`, which the driver and `calculate_hash` share.

Ledger key: `25-21-refresh-wave-keeps-build-logs-render-checks-first-and-renders-url-expressions`. Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **CAP-35** — the feedstock refresh campaign, whose waves this driver runs. This story closes `DW-mason-25-19-2`.

## Acceptance Criteria

- **AC1 — The log.** Every build `refresh-wave` runs writes its output, ANSI-stripped, to `logs/<name>.log` in the report directory, and the report row names it in `build.log`. A log write that fails is a note and never fails the recipe.
- **AC2 — The pre-check.** `--render-check` runs `rattler-build build --render-only` with the build's own variant configs on each recipe, with or without `--apply`, and writes no recipe. `--build` under `--apply` implies it for each recipe it would build, before the first write. A recipe that fails ends `needs-review` with `render-failed: <error>`, unedited, keeps its log at `logs/<name>.render.log`, and runs no gate and no build. `--repair` refuses `--render-check`.
- **AC3 — The URL.** A source URL's expressions render from `context`, through one helper the driver and `calculate_hash` share, including a context value that names another. An expression that cannot render still reports `url-unrenderable`, and `calculate_hash` refuses it before any download. The rendered URL equals rattler-build's own on every in-scope recipe where rattler-build renders one.
- **AC4 — The tests.** `tests/unit/test_refresh_wave.py` and the editor's tests cover each, and each new test fails with its fix reverted.
- **AC5 — The retro.** The change lands in a `retro(cfe):` commit with its `CHANGELOG.md` entry, the skill says what the driver now does, `DW-mason-25-19-2` closes, and `pixi run --frozen -e pyforge-mason pyforge-mason-test` exits 0.

## Boundaries & Constraints

- A CFE script change, so the full chain (operator ruling 2026-09-29).
- A fix: no new CAP, no flag (`spec-feature-flag-governance` Q1).
- No recipe changes. The 65 in-scope recipes that fail to render today are reported, not fixed here.

**Never:**
- Never rewrite a recipe's source URL: the driver renders it, and the recipe stays as it is.
- Never add a status to the `cfe-local-build-status` vocabulary.
- Never write a `cfe-local-build-*` field by hand.

</intent-contract>

## Binding

Parent: `spec-pyforge-mason` CAP-35

- Closes: `DW-mason-25-19-2`.
- Epic: Epic 25.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).
- `pytest .claude/skills/conda-forge-expert/tests/unit/test_refresh_wave.py` in the `local-recipes` env — expected: pass.

## Spec Change Log

- 2026-11-05: minted from `DW-mason-25-19-2` at the operator's "Do this task here".
