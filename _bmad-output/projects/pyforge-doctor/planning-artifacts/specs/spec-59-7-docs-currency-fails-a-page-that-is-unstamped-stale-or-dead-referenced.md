---
title: '59.7: docs-currency fails a page that is unstamped, stale or dead-referenced'
type: 'fix'
created: '2026-11-17'
status: 'done'
story: 59-7-docs-currency-fails-a-page-that-is-unstamped-stale-or-dead-referenced
spec: spec-pyforge-doctor
difficulty: 'heavy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/**'
  - 'src/shared/packages/pyforge-doctor/tests/meta/**'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md'
  - 'pixi.toml'
  - 'docs/reference/detectors.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/MAP.md
  - docs/_STYLE_GUIDE.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The detector's skip is the hole the whole audit fell through, and warn-first never became fail.

**Approach:** Tests first on fixture trees, then the source. Keep every fail-open path as it is (CAP-62 posture, AD-15). The exemption is declared on the page, never listed in the detector.

Ledger key: `59-7-docs-currency-fails-a-page-that-is-unstamped-stale-or-dead-referenced`.
Type / Effort / Deps: fix / M / S-59.2, S-59.3.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-84** — documentation currency; amended 2026-11-17: every authored page is stamped or declares its detector, the currency classes fail, the workflow inventory is generated, package-level pages fold into the quadrants.

## Boundaries & Constraints

**Always:**
- Check every command, path, flag, count and link in a page against the tree before its stamp moves; keep `sources:` narrow (the file a page restates, not a hub file).
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never hand-edit a generated page, the generated section of `docs/MAP.md`, a compiled station skill, a `SPEC.md` or `sprint-status-ledger.yaml`.
- Never run a bare `spec_surface_check.py --write-baseline`; Story 59.8 stamps each governing Spec scoped, once, last.
- Never move a station's code, CLI or capability to make a page true: fix the page.

## Acceptance Criteria

**Given** `docs-currency` returns without a finding when a page has no `verified:`, and every class it reports is WARN although the capability promotes each to fail once green
**When** the source gains the class `docs-currency-authored-unstamped`, reads `checked_by:` as the one page-declared exemption (the task name must resolve in `pixi.toml`), and reports map-render, generated-stale, authored-stale and authored-unstamped as FAIL
**Then** on fixture trees: an unstamped authored page fails; a resolving `checked_by:` yields no finding and an unresolvable one fails; a moved source, a missing source path and a dead backticked reference each fail; a source touched on the `verified:` date passes; an unreadable `map.yaml` still yields one WARN and no FAIL
**And** `contract.md` names the new check code and input; the oracle meta-test and the public-contract meta-test exit 0; the change lands on a tree the source already reads green (Stories 59.2 and 59.3 first)

- **AC1 — The source's package-half tests and doctor's two contract meta-tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py src/shared/packages/pyforge-doctor/tests/meta/test_package_half_is_the_oracle.py -q -p no:cacheprovider
  ```

- **AC2 — The live tree reads green with only the OK row.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild docs-currency-check
  ```

- **AC3 — Both halves of doctor's suite pass.** Expected: exit 0 each.

  ```bash
  pixi run --frozen -e pyforge-doctor pyforge-doctor-test && pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test
  ```

- **AC4 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-59-7-*.md)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (amended 2026-11-17); FR-17 ← CAP-84.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-17 (the full documentation refresh) entry; operator ruling of 2026-11-17.
- Epic: Epic 59, minted with this story.
- Ledger key: `59-7-docs-currency-fails-a-page-that-is-unstamped-stale-or-dead-referenced` (`backlog`).
- Deps: S-59.2, S-59.3.
- Surface: `marshal-policy.toml` `[epic_surfaces]."59"`.
- Minted 2026-11-17 in the chain commit of the integration branch `docs-full-refresh-2026-11-17`, the first commit of the branch.

## Notes

- One integration branch and one PR carry Stories 59.1 to 59.8 (operator ruling 2026-11-17). Stories 59.1 to 59.6 run in parallel on disjoint files; 59.7 lands on a tree its source already reads green; 59.8 runs last.
- Measured at main `33c96fd0bb`: 57 authored pages, 19 stamped, 17 of those stale, 38 unstamped; 6 generated; 7 pointers.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-17: minted from the station Dream's 2026-11-17 entry (the full documentation refresh) and the operator's ruling of 2026-11-17.
