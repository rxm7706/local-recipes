---
title: '59.6: Shape hygiene — roster, S-N.N, commits, status comments'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Four STATIONS lists disagree and 19 Dreams comment on status:.

**Approach:** One roster of eight exists (LONG paths/packages/envs, SHORT owner: / Source / prose). A trailing # on Dream status: is a finding. Commit subjects are Capitalized sentences with no trailing period, except type(scope): under recipes/ and the CFE changelog.

## Boundaries & Constraints

**Always:**
- One roster of eight with LONG and SHORT forms.
- Trailing # on Dream status: is a finding.
- S-N.N stays prose-only.

**Never:**
- Do not invent a second roster.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| status comment | Dream status: ready # leftover | detector finding | finding |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-7`.
Surface: docs/governance/guild-roster.json; Dream files under docs/dreams/; commit-subject convention (hook or detector). S-N.N stays prose-only..
Ledger key: `59-6-shape-hygiene-roster-s-n-n-commits-status-comments`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-6-shape-hygiene-roster-s-n-n-commits-status-comments.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

