<!-- RECOVERED 2026-08-04 Tier 3 (epics.md-derived Intent + ACs). Promote to full spec after initial stories land. -->
---
title: "Story 10-1: Restore atlas dependency completeness"
type: "feature"
created: "2026-07-27"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-04"
---

## Intent
Ensure all 31/31 shipped story specs are promoted to tracked planning-artifacts/specs; audit tooling that flagged 'missing' specs.

## Acceptance Criteria

- All 32 original specs (2 originals + 30 epics.md regenerated) are in planning-artifacts/specs
- Epic 10 stories 10-1..10-6 have spec files
- Dashboard gap-count reflects reality (not nested SPEC.md dirs miscounted as story specs)

## Notes
This spec was recovered from epics.md after Epic 10 was added (2026-07-27) post-atlas's initial 2026-07-25 reconciliation. Promote to full narrative spec + ACs matrix once implementation begins.