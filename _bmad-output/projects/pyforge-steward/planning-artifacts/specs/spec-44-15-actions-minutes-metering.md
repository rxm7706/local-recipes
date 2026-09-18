---
title: '44.15: Actions-minutes metering'
type: 'feature'
created: '2026-09-18'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `steward budget check` to meter the account's GitHub Actions minutes against the plan's included minutes and my declared ceiling

**Approach:** the foundry dispatch, Marshal's drains and the rebuild harness read a real budget instead of discovering the ceiling by being refused.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-44-15-actions-minutes-metering.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `44-15-actions-minutes-metering` off `blocked` (operator confirmation required).
- Do not dispatch outward Foundry/archive/conda-forge work without operator confirmation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| a `user`-scoped GitHub credential held in `steward keys` (never in the manifest or `.steward/budget.yaml`) and a ceiling declared by `steward budget set` **Whe… | `steward budget check` runs **Then** it reads the account's Actions billing API, reports included, used and remaining m… | it reads the account's Actions billing API, reports included, used and remaining minutes with the private-repo multipliers applied, and returns a real under/over verdict — `EXIT_BUDGET_NOT_CONFIGURED… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the meta invariant `test_no_cost_integration_sdk_imported_in_budget` is amended for this one source (the GitHub billing API; still no cloud-cost SDK), and every other spend source keeps reporting the… | n/a |
| And-clause from epics.md | when the story lands | `steward budget check --json` is consumable by the 44.3 confirmation, by Marshal's foundry drains and by the 44.14 harness as their ceiling, and a refused runner ("payments have failed" / spending li… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `fnd:CAP-10`.
Surface: named on the story in epics.md
Ledger key: `44-15-actions-minutes-metering`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-44-15-actions-minutes-metering.md`.

## Epic excerpt

As a platform operator,
I want `steward budget check` to meter the account's GitHub Actions minutes against the plan's included minutes and my declared ceiling,
So that the foundry dispatch, Marshal's drains and the rebuild harness read a real budget instead of discovering the ceiling by being refused.

**Type:** feature • **Effort:** M • **Deps:** none • **FR/AD:** fnd:CAP-10 • fnd:AD-14, fnd:AD-23 • steward Epic 4 (4.1–4.3, the honest stub) • `feedback_gh_actions_api_gotchas`
**Given** a `user`-scoped GitHub credential held in `steward keys` (never in the manifest or `.steward/budget.yaml`) and a ceiling declared by `steward budget set` **When** `steward budget check` runs **Then** it reads the account's Actions billing API, reports included, used and remaining minutes with the private-repo multipliers applied, and returns a real under/over verdict — `EXIT_BUDGET_NOT_CONFIGURED` only when no metering source is configured
**And** the meta invariant `test_no_cost_integration_sdk_imported_in_budget` is amended for this one source (the GitHub billing API; still no cloud-cost SDK), and every other spend source keeps reporting the honest stub
**And** `steward budget check --json` is consumable by the 44.3 confirmation, by Marshal's foundry drains and by the 44.14 harness as their ceiling, and a refused runner ("payments have failed" / spending limit) is reported as a finding, never as a cheap green

