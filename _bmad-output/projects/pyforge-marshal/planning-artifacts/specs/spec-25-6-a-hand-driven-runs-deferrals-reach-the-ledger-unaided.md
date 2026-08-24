---
title: A hand-driven run's deferrals reach the ledger unaided
type: feature
created: '2026-08-24'
status: ready
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: 954216325a
---

<intent-contract>

## Intent

**Problem:** Hand-driven `bmad-build-auto` runs can record deferrals in spec frontmatter, but the deferred-work pipeline does not ingest them — only loop runs are bridged via bmad-loop's `_harvest_spec_deferrals` (FR-611 CAP-6; spec-bmad-611-era-alignment; closes DW-BL011-2).

**Approach:** Extend `scripts/deferred_work_*.py` / `scripts/deferred_work_check.py` intake seam to read spec-frontmatter `deferred:` lists (doctor DW-14-1-1 canary shape, 2026-08-22) into the tracked ledger without human relay. Honor both sources: loop-harvested + hand-driven frontmatter. Deps: none. Does not implement CAP-7 (Story 25.7).

## Acceptance Criteria

- Fixture spec with frontmatter `deferred:` (DW-14-1-1 shape) ingested into tracked ledger by pipeline.
- Loop-run deferrals still honored via existing bmad-loop bridge — no regression.
- `deferred_work_check.py` (or successor gate) detects missing hand-driven intake.
- DW-BL011-2 closes in deferred-work ledger or equivalent.

## Boundaries & Constraints

**Never:** Duplicate bmad-loop harvest logic for loop runs. Finalize marshal ledger only. **maintenance label** if changes outside `recipes/` (scripts/ expected).

</intent-contract>

## Code Map

- Parent: `spec-bmad-611-era-alignment/SPEC.md` (CAP-6)
- Surfaces: `scripts/deferred_work_*.py`, `scripts/deferred_work_check.py`
- Canary: doctor DW-14-1-1 frontmatter shape (2026-08-22)

## Verification

- Fixture-driven intake test
- `deferred_work_check.py` green on live repo
