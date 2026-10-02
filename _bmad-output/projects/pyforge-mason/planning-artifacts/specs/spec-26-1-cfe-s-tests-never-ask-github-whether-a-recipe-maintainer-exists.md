---
title: "26.1: CFE's tests never ask GitHub whether a recipe maintainer exists"
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/tests/conftest.py
  - .claude/skills/conda-forge-expert/tests/integration/test_workflow_npm.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CFE's `validate_recipe` runs conda-smithy's linter, and the linter's maintainer check
(`conda_smithy.lint_recipe._maintainer_exists`, and `_team_exists` for a `org/team` maintainer) asks github.com whether
each maintainer exists. With `GH_TOKEN` unset it asks unauthenticated (an HTTP `HEAD` of the user's profile page). The
`cfe-regression-net` lane sets no token, so its verdict depends on how GitHub answers an unauthenticated request from a
CI runner: on 2026-10-02 one PR failed the lane twice, in a different test of `tests/integration/test_workflow_npm.py`
each time (`Recipe maintainer "rxm7706" does not exist`), and passed on a re-run. The same request from a workstation
returns 200.

**Approach:** a fixture in CFE's `tests/conftest.py` replaces both lookups with a local answer for every test not
marked `network`, so no CFE test asks GitHub. A regression test proves the stub is in force by failing if a lookup
reaches the network. CFE's runtime lint is unchanged.

Ledger key: `26-1-cfe-s-tests-never-ask-github-whether-a-recipe-maintainer-exists`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-34 (FR-56): CFE's tests give the same verdict in any environment (Story 24.1 made the
  host-gate tests hermetic). A defect of the same class, so no new CAP; a `fix` needs no flag.

## Acceptance Criteria

- Given no GH_TOKEN and no network route to github.com When the CFE suite runs Then every test that lints a recipe passes
- Given the stub in force When a test calls the maintainer or team lookup Then no request leaves the process
- Given a test marked `network` When it runs Then it keeps conda-smithy's real lookup
- Given the stub removed When the regression test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Go through `conda-forge-expert` (Rule 1). Land code, tests, `CHANGELOG.md` entry and version carriers in
one `retro(cfe):` commit (Rule 2).

**Never:** Do not change CFE's runtime lint or `validate_recipe`. Do not set a token in the workflow as the fix. Do not
touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `recipes/**`.

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-34 (FR-56).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-02 — Proposed: CFE's tests never ask GitHub whether
a recipe maintainer exists*.
Ledger key: `26-1-cfe-s-tests-never-ask-github-whether-a-recipe-maintainer-exists`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code).

**Manual checks:**
- `pixi run --frozen -e local-recipes test-ci` (the `cfe-regression-net` command) with `GH_TOKEN` unset and github.com
  unreachable — expected: pass.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No review has run yet.
