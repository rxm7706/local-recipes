---
title: Wall-clock is never blended with active-compute
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 5999f70a35
---

<intent-contract>

## Intent

**Problem:** Wall-clock fallback (23.1) must not appear as active agent-compute on the velocity chart — readers need to tell metric classes apart from chart/caption alone (FR-194 CAP-2).

**Approach:** In `docs/dashboard/generate.py` + `index.html`, keep wall-clock-derived stories out of the active-compute bar series (or mark with a distinct class/series). Caption/legend makes the class readable without inspecting raw data. Preserve warden/atlas curated numbers byte-identical. Deps: 23.1 done (PR #711). Do not implement CAP-3 caption partitions (23.3) beyond what CAP-2 needs for class labeling.

## Acceptance Criteria

- No wall-clock number is rendered as if it were active agent-compute.
- Reader can tell each story's metric class from chart/caption alone.
- Warden/atlas curated timing values are byte-identical before and after.
- Does not implement Story 23.3 full absence-class partitioning (beyond class labels CAP-2 needs).

## Boundaries & Constraints

**Never:** Mix wall-clock into the active-compute bar series without a distinct class. Finalize marshal ledger only. maintenance label (docs/dashboard).

</intent-contract>

## Code Map

- Parent: `spec-dashboard-velocity-captures-hand-driven-work/SPEC.md` (CAP-2)
- Surface: `docs/dashboard/generate.py`, `docs/dashboard/index.html`
- Tests: blend refusal; curated byte-identity; chart class visibility

## Verification

- Dashboard generate + render tests green
- Visual/data assertion: wall-clock stories not in active-compute bars
