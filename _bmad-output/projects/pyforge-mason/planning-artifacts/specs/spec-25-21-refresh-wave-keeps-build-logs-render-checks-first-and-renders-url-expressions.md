---
title: "25.21: refresh-wave keeps build logs, render-checks first and renders URL expressions"
type: 'fix'
created: '2026-11-05'
status: 'done'
baseline_revision: '6d52ea19c3'
review_loop_iteration: 1
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
- No recipe changes. The 67 in-scope recipes that fail to render today are reported, not fixed here.

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

## Run record (2026-11-05)

### AC1 and AC2: logs and the pre-check

A live run on scratch copies, with real rattler-build and real feedstock lookups, gave:

| Recipe | Flags | Outcome | Evidence |
|---|---|---|---|
| `airflow-provider-xlsx` | `--render-check`, dry run | `needs-review` | `render-failed: …Invalid match spec 'python 3.11'`; `logs/airflow-provider-xlsx.render.log`; no recipe written |
| `kthread` | `--apply --build --rebuild` | `already-current`, build `success` | `logs/kthread.log`, 29 KB |
| `django-mptt`, given an expression URL | `--apply --build` | `refreshed` 0.21.0 to 0.21.1, build `success` | downloaded `django_mptt-0.21.1.tar.gz`; the sha agrees with the feedstock's |

Of the 880 in-scope recipes, 67 fail the pre-check today, all in Track B. This story reports them and fixes none.

### AC3: the URL decision

The driver renders. 445 of the 880 in-scope recipes carry a URL expression, and Story 25.19 rewrote 25 by script to refresh them, so the hand step recurs. The recipe keeps its form, so nothing reviews a rewrite, and the driver's feedstock sha check catches a wrong render.

Evidence: over the 880 in-scope recipes, the helper's URL equals rattler-build's own on all 810 that rattler-build renders with a URL; 67 fail to render and 3 give no JSON. The independent review widened that to every `recipes/*/recipe.yaml`: 5,826 of 5,832 first-source URLs match, and the 6 differences lie outside CAP-35's scope.

`recipe_editor`, which the driver and `calculate_hash` share, renders in jinja2's immutable sandbox, because recipe text comes from feedstocks. `jinja2` is a declared dependency of the `local-recipes` feature.

### AC4: the tests

The 12 tests that exercise new behaviour failed before the code, and 129 pass after it. 16 mutants of the new guards were each killed on a scratch copy with a green baseline.

### Independent review

A separate reviewer found 3 medium and 3 low items. Fixed: a wrapped cause lost its tail on every real failure tried; a timeout or a missing `rattler-build` stuck as a terminal `needs-review`, and now ends `failed`, which a rerun retries; four mutants survived, and each now has a test; an expression that raises fails closed; a passing render clears the old `.render.log`. Accepted: a context key named `self` is not hidden, and no recipe has one; `--render-check` ends an unrenderable `already-current` recipe with no feedstock lookup; `tree-sitter-swift`, which reaches its version only through a context chain, still reports `url-version-baked`. `pixi.toml`'s task description does not list driver flags, `--rebuild` included, so it stays as it is.

The reviewer also ran `git checkout -- recipes` in this worktree, against its read-only brief, and discarded Story 25.22's uncommitted work. Nothing was lost beyond a rebuild. Commit before you start a reviewer in the same worktree.

## Spec Change Log

- 2026-11-05: minted from `DW-mason-25-19-2` at the operator's "Do this task here".
- 2026-11-05: run, review and retro `v8.105.0` recorded; status `done`.
