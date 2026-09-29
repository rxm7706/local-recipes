---
title: "Story 10-1: Restore atlas dependency completeness"
type: "feature"
created: "2026-07-27"
status: done
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-04"
---

<!-- RECOVERED 2026-08-04 Tier 3 (epics.md-derived Intent + ACs). Promote to full spec after initial stories land. -->

## Intent
Ensure all 31/31 shipped story specs are promoted to tracked planning-artifacts/specs; audit tooling that flagged 'missing' specs.

## Acceptance Criteria

- All 32 original specs (2 originals + 30 epics.md regenerated) are in planning-artifacts/specs
- Epic 10 stories 10-1..10-6 have spec files
- Dashboard gap-count reflects reality (not nested SPEC.md dirs miscounted as story specs)

## Notes
This spec was recovered from epics.md after Epic 10 was added (2026-07-27) post-atlas's initial 2026-07-25 reconciliation. Promote to full narrative spec + ACs matrix once implementation begins.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `5d9e598c2c` (2026-08-15, "Story 10.1: bmad-method-version-drift Source (CAP-1)"); also `d50fa325b1` (2026-08-08, "herald: Story 10.1/10.3/10.6 — notice storage, redirects, lifecycle"). Ledger row `10-1-restore-atlas-dependency-completeness-so-the-suite-can-collect: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md`, `pixi.toml`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py`, `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_models.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `10-1-restore-atlas-dependency-completeness-so-the-suite-can-collect: done`).
- `## Auto Run Result` reconstructed from git (none survived).
