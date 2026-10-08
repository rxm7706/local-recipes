---
title: '62.3: Consumers cite on rows only'
type: 'feature'
created: '2026-09-16'
status: 'done'
baseline_revision: 'ca4cc7f7d1c8f8e8e8e8e8e8e8e8e8e8e8e8e8e8'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md'
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A station can mint a stealth metric.

**Approach:** Citing off, archived, or an unknown id is a refuse. Hub Outcome Guards are not implemented here — they read later.

## Boundaries & Constraints

**Always:**
- Citing off, archived, or unknown id is a refuse.

**Never:**
- Do not implement Hub Outcome Guards here.
- Do not invent weights.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| cite off | known id, state off | refuse | refuse |
| cite unknown | id not in catalog | refuse | refuse |
| cite on | known id, state on | allowed | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/league_measure.py` — stdlib-only reader for `measure-catalog.md`; `validate_measure_cite()` is the refuse path Herald / Atlas / Marshal / Doctor import (same seam as `cutover_root` / `flags`).
- `src/shared/packages/pyforge-core/tests/unit/test_league_measure.py` — matrix rows for off / archived / unknown; live repo asserts eight `on` rows.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md` — authoritative id → `State` table (read-only for this story).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-core/src/pyforge/core/league_measure.py` — add catalog parser + `validate_measure_cite` refuse semantics — cross-station callers must not duplicate the table.
- `src/shared/packages/pyforge-core/tests/unit/test_league_measure.py` — cover every I/O matrix row plus live eight-measure catalog — regression guard for CAP-3.

**Acceptance Criteria:**
- Given a known id whose catalog `State` is `off`, when `validate_measure_cite` runs, then `allowed` is false and the reason names a non-`on` state.
- Given an id absent from the catalog, when `validate_measure_cite` runs, then `allowed` is false with reason `unknown measure id`.
- Given a known id whose catalog `State` is `on`, when `validate_measure_cite` runs against the live repo, then `allowed` is true.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (new module + matrix tests).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station `verify_commands`; MRS-GATE-010 binding).

## Binding

Parent Spec capability: `spec-build-league-scorecard CAP-3`.
Surface: a refuse path Herald / Atlas / Marshal / Doctor can call..
Ledger key: `62-3-consumers-cite-on-rows-only`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-62-3-consumers-cite-on-rows-only.md`.

## Auto Run Result

Status: done

**Summary:** Added `pyforge.core.league_measure.validate_measure_cite` — the shared refuse path that reads the published companion catalog and allows cites only when a row's `State` is `on`.

**Verification performed:**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — exit 0 (2290 passed).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0 (2057 passed, 5 skipped).
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile on `spec-pyforge-core` and `spec-pyforge-steward`.

**Follow-up review recommendation:** false
