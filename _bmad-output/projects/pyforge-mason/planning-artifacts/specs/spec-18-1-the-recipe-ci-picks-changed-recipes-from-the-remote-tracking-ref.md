---
title: "18.1: The recipe CI picks changed recipes from the remote-tracking ref"
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the four recipe build workflows (`.github/workflows/test-{all,linux,macos,windows}.yml`) choose which recipes a pull request builds with `git diff --name-only origin/${{ github.base_ref }}...HEAD -- 'recipes/*'`. Their checkout fetches tags (`fetch-depth: 0`), and git resolves a short name to `refs/tags/<n>` before `refs/remotes/<n>`, so a pushed tag named `origin/main` would empty the changed-recipe set. The branch is dormant today: no recipe workflow runs on `pull_request` (`test-all.yml` is `workflow_dispatch` only; `test-{linux,macos,windows}.yml` are `workflow_call` + `workflow_dispatch`, called only by `test-all`), so this hardens it for when a trigger returns. Found by doctor Story 32.1 (`DW-mason-recipe-ci-short-base-ref-2026-09-27`).

**Approach:** all four diff from `refs/remotes/origin/${{ github.base_ref }}...HEAD`. The regression test is `pyforge-core:CAP-10`'s workflow scan (marshal Story 63.1, same change), which covers these four; no second test. `.github/` is outside the CFE surface (`scripts/mason_cfe_surface_check.py`), so no CFE retro is owed.

Ledger key: `18-1-the-recipe-ci-picks-changed-recipes-from-the-remote-tracking-ref`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-28; `pyforge-core:CAP-10` (the workflow scan); `coverage-gate-independence:CAP-4`.

## Acceptance Criteria

- Given a pull request touching `recipes/<name>/` When a recipe workflow picks what to build Then it diffs `refs/remotes/origin/${{ github.base_ref }}...HEAD`
- Given the workflow scan (marshal Story 63.1) When it runs Then all four workflows pass it
- Given a manual `workflow_dispatch` with a `recipes` input When a recipe workflow runs Then its path is unchanged

## Boundaries & Constraints

**Always:** the change is the diff base only.

**Never:** touch a recipe, the CFE surface or the manual `recipes` input path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| pull request | `base_ref=main` | diff from `refs/remotes/origin/main` | a missing ref fails as before |
| pushed tag `origin/main` | PR checkout with tags | the remote-tracking ref's recipe set | — |
| `workflow_dispatch` | `recipes` input | unchanged | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-28.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-27 (night) — Proposed: the recipe CI picks changed recipes from the remote-tracking ref*.
Deferred-work: closes `DW-mason-recipe-ci-short-base-ref-2026-09-27`.
Ledger key: `18-1-the-recipe-ci-picks-changed-recipes-from-the-remote-tracking-ref`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the workflow scan).

## Review Triage Log

- **Review 1 (2026-09-27, independent agent) — FAIL (on 70.1), then fixed:**
  - [fixed] LOW: the failure scenario cannot occur today -- no recipe workflow runs on `pull_request`, so the branch
    is dormant; the Dream, CAP-28 (memlog amendment, then its rendered line), the epic and this spec now call it
    hardening.
