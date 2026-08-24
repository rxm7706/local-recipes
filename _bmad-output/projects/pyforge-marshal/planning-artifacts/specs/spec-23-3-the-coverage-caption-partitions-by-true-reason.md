---
title: The coverage caption partitions by true reason
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: de1853603d
---

<intent-contract>

## Intent

**Problem:** Velocity coverage captions mislabel hand-driven stories — e.g. "predates instrumentation" when promoted specs carry revision fields (FR-194 CAP-3; spec-dashboard-velocity-captures-hand-driven-work).

**Approach:** In `docs/dashboard/generate.py` + `index.html`, partition coverage caption by true absence class: journal-measured / wall-clock-derived / spec-without-revision-fields / no-spec-at-all. Never claim "predates instrumentation" for a story whose spec carries `baseline_revision`/`final_revision`. Deps: 23.1 done; 23.2 done (#714). Completes Epic 23.

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
- Surface: `docs/dashboard/generate.py`, `docs/dashboard/index.html`
- Tests: caption partitions; no false "predates" for revision-bearing specs

## Verification

- Dashboard generate + render tests green
- Fixture: hand-driven line shows correct class counts in caption
