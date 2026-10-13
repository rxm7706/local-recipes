---
title: '99.7: The hand-disabled workflows are retired or parked, and the convention is documented'
type: 'chore'
created: '2026-10-13'
status: 'ready-for-dev'
baseline_revision: '233e07909b5f7e89e49744cdeb642cdc0985b177'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md
  - docs/governance/ci-surfaces.yaml
  - .github/workflows/staged-recipes-linter.yml
  - .github/workflows/linter_issue_comment.yml
  - .github/workflows/reusable-staged-recipes-linter.yml
  - .github/workflows/reusable-staged-recipes-linter-selftest.yml
  - docs/map.yaml
  - AGENTS.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Six workflows have been `disabled_manually` in the GitHub UI since 2026-08-24 12:06–12:07 with no
recorded reason (`test-all`, `kedro-viz-publish`, `staged-recipes-linter`, `linter_issue_comment`,
`reusable-staged-recipes-linter`, `reusable-staged-recipes-linter-selftest`). The pause convention is documented
nowhere a reader looks, and tracked docs still cite the deleted `ACTIONS_ENABLED` variable as current state.

**Approach:**

- **Retire the linter family (ruling Q4).** Delete the four staged-recipes-linter workflow files and the files under
  `.github/workflows/scripts/` that only they use (grep every caller before deleting; keep anything another workflow,
  pixi task or test references). Each gets a `retired` row with `retired_on: <landing date>` and the reason
  "staged-recipes linting retired; local-recipes is not a staged-recipes fork". The environment.yaml sync check that
  `linter.py` carried moves nowhere: `steward provision --verify` (FR-15) and Story 100.3's reconcile own it; the
  story notes that in its spec change log after checking no CI lane relied on it.
- **Park the other two.** `test-all` and `kedro-viz-publish` get `paused-manually` rows with the operator's recorded
  reason (the Spec's open question; until the operator answers, `reason: not recorded (asked 2026-10-12)`) and
  `review_by: 2026-11-01` (ruling Q8).
- **How-to.** `docs/how-to/pause-ci.md`, registered in `docs/map.yaml`: the registry, the switch convention and the
  grandfathered names, `steward ci status|vars|pause|resume`, the `--yes` and merge-gate rules, the dispatch
  carve-out, the canary, the preflight banner and `--ignore-ci-pauses`.
- **Pointer.** `AGENTS.md` § *Running and verifying* gains one line naming the how-to and `steward ci status`
  (scribe's parity meta-test and `governance-currency` stay green).
- **`ACTIONS_ENABLED`.** No tracked doc outside a dated log entry cites it as current state; each live citation is
  struck or rewritten in place.

Ledger key: `99-7-the-hand-disabled-workflows-are-retired-or-parked-and-the-convention-is-documented`.
Type / Effort / Deps: chore / S / S-99.1, S-99.4.

### Living CAP citations

- **`spec-pyforge-steward` CAP-166** (FR-39): the hygiene retirements, the parks, the how-to.
- **`spec-pyforge-scribe` CAP-27**: one `AGENTS.md` pointer, no duplicated rule.
- **Flag:** none (a chore, spec-feature-flag-governance Q1).
- **Origin.** The 2026-10-12 Dream entry; rulings Q4 and Q8.

## Acceptance Criteria

- **AC1 — Retired.** The four linter workflow files and their sole-use scripts are gone; each has a `retired` row;
  `grep -rn` finds no remaining caller of a deleted file.
- **AC2 — Parked.** `test-all` and `kedro-viz-publish` have `paused-manually` rows with a `reason` and `review_by`
  2026-11-01; `python scripts/ci_surface_gates.py --check` exits 0.
- **AC3 — Documented.** `docs/how-to/pause-ci.md` exists and is in `docs/map.yaml`; `docs-map-render-test` and
  `docs-gen-test` pass; `AGENTS.md` gains exactly one line; `governance-currency` and the parity meta-test pass.
- **AC4 — `ACTIONS_ENABLED`.** `grep -rn ACTIONS_ENABLED --include='*.md' --include='*.yml' --include='*.toml' .`
  matches only dated log entries.
- **AC5 — Live check (operator, after landing).** `python scripts/ci_surface_gates.py --check --live` exits 0: the
  retired files are gone from GitHub's workflow list or listed as deleted, and the two parked workflows match their
  rows.

## Boundaries & Constraints

- Workflows are not re-enabled or disabled through the UI or `gh` by this story; the operator does that, if at all.
- No recipe-build workflow is rebuilt (mason's call); `test-linux`, `test-macos` and `test-windows` stay.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| a script under `.github/workflows/scripts/` that a pixi task also runs | kept; its row unchanged |
| a doc that cites `ACTIONS_ENABLED` inside a dated Realization-log entry | left as history |
| the operator answers the open question before dispatch | that reason replaces the placeholder |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (FR-39), minted 2026-10-12.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-12 (ci pause control plane) entry.
- Epic: Epic 99, Stories 99.1–99.7.
- Ledger key: `99-7-the-hand-disabled-workflows-are-retired-or-parked-and-the-convention-is-documented`.
- Ledger status at mint: `backlog`.
- Deps: S-99.1, S-99.4. `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"`.
- Specced 2026-10-13 from the epic's text ahead of its dependencies' landing.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild ci-surface-gates-check` — expected: exit 0 (AC2).
- `pixi run --frozen -e pyforge-guild docs-map-render-test` and `pixi run --frozen -e pyforge-guild docs-gen-test` — expected: pass (AC3).
- `pixi run --frozen -e pyforge-guild governance-currency` — expected: exit 0 (AC3).
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the parity meta-test; start `scribe-pg-up` first).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-13: specced from Epic 99's Story 99.7 text ahead of its dependencies' landing so the steward chain runs
  unattended (operator direction 2026-10-13).
