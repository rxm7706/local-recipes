---
title: '60.3: Ship backends — conda channel default'
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

**Problem:** An air-gapped host cannot install without github.com.

**Approach:** The default ship path is a pixi/conda index package on that channel. Object storage and git bundle / tarball are switchable extras.

## Boundaries & Constraints

**Always:**
- Default ship path is the conda/pixi channel index package.

**Never:**
- Do not make github.com required for the default install.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| air-gap install | no github.com | conda/pixi channel path works | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-self-hosted-bmad-marketplace CAP-3`.
Surface: a noarch catalog-index recipe under recipes/; the existing SelfExplainML / Artifactory channel path..
Ledger key: `60-3-ship-backends-conda-channel-default`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-60-3-ship-backends-conda-channel-default.md`.
