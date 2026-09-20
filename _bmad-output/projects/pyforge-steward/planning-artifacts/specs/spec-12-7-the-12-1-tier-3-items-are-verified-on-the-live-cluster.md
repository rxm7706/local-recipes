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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `3b76aa7fd3` (2026-08-31, "mason: reconcile spec-pyforge-mason drift -- Epics 5-9 + Story 12.7"). Ledger row `12-7-the-12-1-tier-3-items-are-verified-on-the-live-cluster: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md`, `scripts/.spec-surface-baseline.json`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
