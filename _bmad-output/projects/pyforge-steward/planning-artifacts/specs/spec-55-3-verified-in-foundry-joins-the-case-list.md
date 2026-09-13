---
title: 'verified-in-foundry joins the case list'
type: 'docs'
created: '2026-09-13'
status: 'backlog'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `verified-in-foundry` can be claimed from Frame
preflight. That is not A/B behavior.

**Approach:** Join the claim to a 54.1 case-list id. Missing id is
HARD.

## Boundaries & Constraints

**Always:**
- Case-list id is the join key.

**Never:**
- Never accept Frame schema-only as verification.

</intent-contract>

## Acceptance Criteria

1. Claim without a case-list id is HARD.
2. Claim with a listed id is not HARD for this reason.
3. 54.1 list is the named surface (even if still in progress).
