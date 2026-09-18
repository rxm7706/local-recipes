---
title: '44.2: The red-team document fixes'
type: 'docs'
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

**Problem:** R-23, R-24 and R-25 landed and the two stale Python-floor pins corrected

**Approach:** the documents the cutover copies into the lasting repo state what the shipped code does.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-44-2-the-red-team-document-fixes.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `44-2-the-red-team-document-fixes` off `blocked` (operator confirmation required).
- Do not dispatch outward Foundry/archive/conda-forge work without operator confirmation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| the Dream, compose files and research **When** the edits land **Then** `readOnlyRootFilesystem` and the Windows / free-threading claims match the shipped Conta… | the edits land **Then** `readOnlyRootFilesystem` and the Windows / free-threading claims match the shipped Containerfil… | `readOnlyRootFilesystem` and the Windows / free-threading claims match the shipped Containerfile and `pixi.toml` platforms, Keycloak is pinned once at `26.4.0`, the "zero domain models" constraint re… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the three ledger entries are resolved | n/a |

</intent-contract>

## Binding

Parent Spec capability: `Spec Constraints`.
Surface: named on the story in epics.md
Ledger key: `44-2-the-red-team-document-fixes`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-44-2-the-red-team-document-fixes.md`.

## Epic excerpt

As a platform operator,
I want R-23, R-24 and R-25 landed and the two stale Python-floor pins corrected,
So that the documents the cutover copies into the lasting repo state what the shipped code does.

**Type:** docs • **Effort:** S • **Deps:** none • **FR/AD:** Spec Constraints • red-team X-6 / D-5 / S-6 / T-9 • `DW-RT-2026-09-02-7/-8/-9`
**Given** the Dream, compose files and research **When** the edits land **Then** `readOnlyRootFilesystem` and the Windows / free-threading claims match the shipped Containerfile and `pixi.toml` platforms, Keycloak is pinned once at `26.4.0`, the "zero domain models" constraint reads "no station-domain models on `django-<station>`", and `stack.md` / `convergence.md` no longer pin Python `3.12.*`
**And** the three ledger entries are resolved

