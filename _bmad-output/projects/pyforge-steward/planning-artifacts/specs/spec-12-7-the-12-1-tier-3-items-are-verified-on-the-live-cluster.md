---
title: '12.7: The 12.1 Tier-3 items are verified on the live cluster'
type: 'verification'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `helm install` of core + OCP overlay on the running cluster **Then** the four honestly-unverified items are proven — Route admission, SCC enforcement, PVC binding, official postgres/redis images under an SCC-assigned arbitrary UID (contingency ladder: dataMountPath/UID seams → RH images → bitnami, whichever was needed gets recorded) — plus the fresh-install migration-window observation; failures…

**Approach:** the four honestly-unverified items are proven — Route admission, SCC enforcement, PVC binding, official postgres/redis images under an SCC-assigned arbitrary UID (contingency ladder: dataMountPath/UID seams → RH images → bitnami, whichever was needed gets recorded) — plus the fresh-install migration-window observation; failures land as findings, never silent notes.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-12-7-the-12-1-tier-3-items-are-verified-on-the-live-cluster.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| `helm install` of core + OCP overlay on the running cluster **Then** the four honestly-unverified items are proven — Route admission, SCC enforcement, PVC bind… | as in epics.md | the four honestly-unverified items are proven — Route admission, SCC enforcement, PVC binding, official postgres/redis images under an SCC-assigned arbitrary UID (contingency ladder: dataMountPath/UI… | fail loud; never silent skip |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: attended run + a dated verification record in the 12.1 spec's orbit
Ledger key: `12-7-the-12-1-tier-3-items-are-verified-on-the-live-cluster`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-12-7-the-12-1-tier-3-items-are-verified-on-the-live-cluster.md`.

## Epic excerpt

**Type:** verification • **Effort:** M • **Deps:** S-12.4, S-12.5, S-12.6 • **FR/AD:** spec-local-ocp-hybrid-environment CAP-4
**Surface:** attended run + a dated verification record in the 12.1 spec's orbit
**Given** `helm install` of core + OCP overlay on the running cluster **Then** the four
honestly-unverified items are proven — Route admission, SCC enforcement, PVC binding,
official postgres/redis images under an SCC-assigned arbitrary UID (contingency ladder:
dataMountPath/UID seams → RH images → bitnami, whichever was needed gets recorded) —
plus the fresh-install migration-window observation; failures land as findings, never
silent notes.

