---
title: '60.1: The catalog config names backends and sources'
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

**Problem:** Listings have no estate home and no named source.

**Approach:** Git is the edit store and backends/sources are declared in config. A new backend or source is a plugin, not a rewrite. Creating a new GitHub catalog repo needs operator confirm at this story.

## Boundaries & Constraints

**Always:**
- Backends and sources are declared in config.
- A new backend or source is a plugin, not a rewrite.

**Never:**
- Do not mint a new GitHub catalog repo without operator confirm.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new source | add a declared source | plugin slot, no rewrite | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-self-hosted-bmad-marketplace CAP-1`.
Surface: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-self-hosted-bmad-marketplace/backends-and-sources.md; a config the installer and Claude/Codex extraKnownMarketplaces can point at..
Ledger key: `60-1-the-catalog-config-names-backends-and-sources`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-60-1-the-catalog-config-names-backends-and-sources.md`.
