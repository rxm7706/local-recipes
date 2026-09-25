---
title: '59.3: The Charter carries the BMAD cross-walk and pitched stays optional'
type: 'docs'
created: '2026-09-16'
status: 'in-progress'
baseline_revision: '9bdabafaa0966bf6d2ae78b0888c4e913f6418de'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Hub has a Charter walk and BMAD's daily nouns do not.

**Approach:** The Charter maps Epic / Story / Sprint / PRD / Retrospective (never join) and records Spec shipped != story done != Dream realized. pitched remains declared and optional; no Dream is backfilled.

## Boundaries & Constraints

**Always:**
- Charter maps Epic, Story, Sprint, PRD, Retrospective.
- Spec shipped, story done, and Dream realized stay three different facts.
- pitched stays declared and optional.

**Never:**
- Do not join those BMAD nouns into one row.
- Do not backfill pitched onto existing Dreams.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dream without pitched | frontmatter lacks pitched | unchanged; pitched optional | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-3`.
Surface: docs/dreams/pyforge-charter.md; docs/governance/guild-roster.json..
Ledger key: `59-3-the-charter-carries-the-bmad-cross-walk-and-pitched-stays-optional`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-3-the-charter-carries-the-bmad-cross-walk-and-pitched-stays-optional.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

