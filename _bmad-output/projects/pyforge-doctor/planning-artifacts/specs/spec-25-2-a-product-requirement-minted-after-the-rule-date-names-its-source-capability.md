---
title: '25.2: A product requirement minted after the rule date names its source capability'
type: 'feature'
created: '2026-09-16'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Two requirement namespaces (1,626 FR- vs 3,161 CAP- citations) with no rule joining them; a PRD can grow a requirement no Spec ever contracted.

**Approach:** A detector parses each station PRD, collects FR-n / NFR-n ids, subtracts a per-station baseline of the pre-rule population, and requires a `← CAP-m` citation on the same line or first body line for every new id, resolving CAP-m against the station's Spec (any open Spec folder under the station before its fold). Baseline regenerates only at a station's fold PR.

## Boundaries & Constraints

**Always:**
- Baseline FRs are never findings.
- fr-without-cap FAIL for a new FR with no CAP citation; fr-cap-unresolved FAIL for a citation to a CAP that does not exist.
- Before a station folds, resolution accepts any open Spec folder under that station.
- Registered in detectors-ci; conformance test zero FAIL at the merge SHA.

**Never:**
- Do not backfill citations into pre-rule FRs (that happens in each fold's PRD re-derive).
- Do not accept a CAP citation from another station's Spec.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new FR, no citation | FR-88 with no ← CAP | fr-without-cap FAIL | fail |
| new FR, valid citation | FR-88 ← CAP-12 (exists) | no finding | none |
| new FR, dangling citation | FR-88 ← pyforge-marshal:CAP-99 (declared by no open Spec) | fr-cap-unresolved FAIL | fail |
| pre-rule FR | in fr-baseline.json | no finding | none |
| pre-fold station | CAP in a non-station open Spec folder | resolves | none |

</intent-contract>

## Binding

Parent Spec capability: `spec-one-chain-per-station CAP-5`.
Standard: `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`.
Surface: doctor sources/prd.py (or board.py) gather_fr_without_cap, sources registration + dispatcher, pixi.toml fr-without-cap-check, scripts/detectors.py, docs/governance/fr-baseline.json, doctor tests.
Ledger key: `25-2-a-product-requirement-minted-after-the-rule-date-names-its-source-capability`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-25-2-a-product-requirement-minted-after-the-rule-date-names-its-source-capability.md`.
