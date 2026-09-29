---
title: "Story 10-2: Truth-up the spec-kernel directory layout"
type: "feature"
created: "2026-07-27"
status: done
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-04"
---

<!-- RECOVERED 2026-08-04 Tier 3 (epics.md-derived Intent + ACs). Promote to full spec after initial stories land. -->

## Intent
Separate and document the distinction between per-story spec files (flat spec-<id>-*.md) and feature-level spec kernels (spec-<name>/SPEC.md), fix dashboard counting bug.

## Acceptance Criteria

- Nested SPEC.md dirs are excluded from 'tracked story specs' count
- Dashboard properly counts only flat spec-*.md files
- README.md in planning-artifacts/specs documents the distinction

## Notes
This spec was recovered from epics.md after Epic 10 was added (2026-07-27) post-atlas's initial 2026-07-25 reconciliation. Promote to full narrative spec + ACs matrix once implementation begins.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `a8577c09f4` (2026-08-21, "doctor: split CAP-8 out of Epic 11; fix stale Story 10.2 text"); also `f1a3c28ba8` (2026-08-15, "doctor: correct 4 false-done ledger entries; resolve Story 10.2's CAP-2 data source"); also `3fbf29750a` (2026-08-08, "herald: Story 10.2/10.4 — notice authoring workflow & CLI"). Ledger row `10-2-truth-up-the-spec-kernel-and-its-companions: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-resolution-sweep/SPEC.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `10-2-truth-up-the-spec-kernel-and-its-companions: done`).
- `## Auto Run Result` reconstructed from git (none survived).
