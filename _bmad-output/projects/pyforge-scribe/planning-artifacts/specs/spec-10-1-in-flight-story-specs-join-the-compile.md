---
title: 'In-flight story specs join the compile'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

Compile `spec-<n>-<m>-*.md` as `doc` when the project's sprint ledger
marks that story in-flight. Frontmatter is not the filter.

## Boundaries & Constraints

**Always:** ledger statuses `ready-for-dev` | `in-progress` | `review`.

**Never:** `done`, `backlog`, folder `SPEC.md` on this surface, frontmatter oracle.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — ledger filter on `spec-<n>-<m>-*.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `5d9e598c2c` (2026-08-15, "Story 10.1: bmad-method-version-drift Source (CAP-1)"); also `d50fa325b1` (2026-08-08, "herald: Story 10.1/10.3/10.6 — notice storage, redirects, lifecycle"). Ledger row `10-1-in-flight-story-specs-join-the-compile: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md`, `pixi.toml`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py`, `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_models.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `10-1-in-flight-story-specs-join-the-compile: done`).
- `## Auto Run Result` reconstructed from git (none survived).
