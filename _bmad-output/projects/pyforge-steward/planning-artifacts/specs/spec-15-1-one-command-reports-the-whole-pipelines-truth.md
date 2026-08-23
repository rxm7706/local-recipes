---
title: One command reports the whole pipeline's truth
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 48ec846f71
---

<intent-contract>

## Intent

**Problem:** The 13 bmad-suite packages have no single truth report across upstream / recipe / channel / installed / wired stages (spec-bmad-suite-channel-product CAP-1); operators still reconstruct the 2026-08-22 research matrix by hand.

**Approach:** Add a steward duty that, for the 13 suite packages, reports upstream latest (npm AND GitHub per package class), recipe version, channel version, installed version, and wired-or-not — drift named per stage, each probe fail-open — consuming existing probes (npm/GitHub queries, recipe.yaml parse, api.anaconda.org listing, pixi list, `.claude/skills` census). Run against the 2026-08-22 baseline reproduces the research matrix.

## Acceptance Criteria

- One command covers all 13 suite packages.
- Per package reports: upstream latest (npm and/or GitHub by class), recipe version, channel version, installed version, wired-or-not.
- Drift named per stage; each probe fail-open (never abort the whole report on one probe fail).
- Fixture or recorded baseline reproduces the 2026-08-22 research matrix shape.

## Boundaries & Constraints

**Never:** Implement 15.2 autotick advance or later CAP stories. Never `scripts/bmad-switch`. Steward 12-7 remains skipped. Finalize steward ledger only.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/` — new suite-truth duty
- CLI verb under steward
- Existing probes: npm/GitHub, recipe.yaml, anaconda.org, pixi list, skills census
- Unit tests with fail-open fixtures

## Verification

- `pixi run --frozen -e pyforge-steward pytest …` green
- Fail-open probe fixture; baseline matrix shape covered
- CI: detectors, linter, package tests
