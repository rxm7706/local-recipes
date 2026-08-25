---
title: The coverage caption partitions by true reason
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: a782d2fb3f
final_revision: e47efc11e19c5b53f04d673b8a15d9e9902ab0dd
---

<intent-contract>

## Intent

**Problem:** Velocity coverage captions mislabel hand-driven stories — e.g. "predates instrumentation" when promoted specs carry revision fields (FR-194 CAP-3; spec-dashboard-velocity-captures-hand-driven-work).

**Approach:** In `pyforge.doctor.sources.fleet_scan` + `index.html`, partition coverage caption by true absence class: journal-measured / wall-clock-derived / spec-without-revision-fields / no-spec-at-all. Never claim "predates instrumentation" for a story whose spec carries `baseline_revision`/`final_revision`. Deps: 23.1 done; 23.2 done (#714). Completes Epic 23.

## Acceptance Criteria

- Caption names the four absence classes when a line contains hand-driven stories.
- No "predates instrumentation" for stories with resolvable revision fields.
- Classes align with 23.1/23.2 metric classes (journal vs wall-clock vs absent).
- Does not regress warden/atlas curated timing byte-identity from 23.2.

## Boundaries & Constraints

**Never:** Fabricate a class. Never blend classes into one bucket. Finalize marshal ledger only. maintenance label (docs/dashboard).

</intent-contract>

## Code Map

- Parent: `spec-dashboard-velocity-captures-hand-driven-work/SPEC.md` (CAP-3)
- Surface: `pyforge.doctor.sources.fleet_scan`, `docs/dashboard/index.html`
- Tests: caption partitions; no false "predates" for revision-bearing specs

## Verification

- Dashboard generate + render tests green
- Fixture: hand-driven line shows correct class counts in caption

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/716
Merge: e47efc11e19c5b53f04d673b8a15d9e9902ab0dd
Merge policy: admin merge — GitHub Actions billing blocks CI; local tests green before merge.
Summary: CAP-3 coverage caption partitions velocity.sub by true absence class (journal-measured / wall-clock-derived / spec-without-revision-fields / no-spec-at-all); never "predates instrumentation" for revision-bearing specs. Epic 23 complete.
Files:
- pyforge.doctor.sources.fleet_scan — partition_timing_coverage, _velocity_coverage_sub_caption, _story_spec_path
- docs/dashboard/data.js — regenerated captions
- .claude/skills/conda-forge-expert/tests/meta/test_dashboard_scan_timing_wall_clock.py — CAP-3 tests
Verification:
- pytest test_dashboard_scan_timing_wall_clock.py + test_dashboard_renders.py — 23 passed
- warden timing+velocity byte-identical; atlas timing byte-identical
