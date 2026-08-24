---
title: Wall-clock fallback derivation from promoted-spec revision fields
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 89a2e90376
---

<intent-contract>

## Intent

**Problem:** Dashboard velocity derives active compute only from bmad-loop journals, so hand-driven stories show nothing even when promoted specs carry `baseline_revision`/`final_revision` (FR-194 CAP-1; spec-dashboard-velocity-captures-hand-driven-work).

**Approach:** In `docs/dashboard/generate.py` (`scan_timing`), for `done` stories with resolvable revision fields and zero closed journal sessions, derive wall-clock duration offline from local git commit timestamps. Choose one bound in-story (final−baseline vs first-commit-in-range) and state what is measured in the caption — never an unqualified "duration". Re-runs refresh derived values (`derived: true`). No resolvable signal → stay absent (never fabricate). Deps: none. Do not implement CAP-2 blending separation (23.2) or CAP-3 caption partitions (23.3) beyond what CAP-1 derivation needs.

## Acceptance Criteria

- Done story with resolvable baseline/final revisions and no journal sessions gets wall-clock from local git timestamps only.
- Doctor 8.1–8.4 (or equivalent fixtures) carry timing marks after generate.
- Re-run refreshes derived values; never freezes stale derived numbers.
- Story with no resolvable signal stays absent from the chart.
- Caption/field names the bound measured (not unqualified "duration").
- Does not implement Stories 23.2–23.3 beyond derivation plumbing.

## Boundaries & Constraints

**Never:** Fabricate timing. Never blend wall-clock into active-compute series as if they were the same class (leave full separation to 23.2 if not already implied). Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-dashboard-velocity-captures-hand-driven-work/SPEC.md` (CAP-1)
- Surface: `docs/dashboard/generate.py` (`scan_timing`)
- Tests: revision-field derivation; absent when unresolvable; refresh on re-run

## Verification

- `docs/dashboard/generate.py --source git` (or project test harness) shows wall-clock for revision-bearing hand-driven stories
- Related dashboard/generate tests green
