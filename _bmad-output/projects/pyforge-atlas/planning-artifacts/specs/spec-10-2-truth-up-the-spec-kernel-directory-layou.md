<!-- RECOVERED 2026-08-04 Tier 3 (epics.md-derived Intent + ACs). Promote to full spec after initial stories land. -->
---
title: "Story 10-2: Truth-up the spec-kernel directory layout"
type: "feature"
created: "2026-07-27"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-04"
---

## Intent
Separate and document the distinction between per-story spec files (flat spec-<id>-*.md) and feature-level spec kernels (spec-<name>/SPEC.md), fix dashboard counting bug.

## Acceptance Criteria

- Nested SPEC.md dirs are excluded from 'tracked story specs' count
- Dashboard properly counts only flat spec-*.md files
- README.md in planning-artifacts/specs documents the distinction

## Notes
This spec was recovered from epics.md after Epic 10 was added (2026-07-27) post-atlas's initial 2026-07-25 reconciliation. Promote to full narrative spec + ACs matrix once implementation begins.