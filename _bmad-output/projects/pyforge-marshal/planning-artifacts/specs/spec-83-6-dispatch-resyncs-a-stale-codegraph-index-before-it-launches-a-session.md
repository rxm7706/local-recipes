---
title: '83.6: Dispatch resyncs a stale codegraph index before it launches a session'
type: 'fix'
created: '2026-10-02'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Dispatch shells `steward session check` (Story 63.4) and folds a non-ok verdict into the WARN MRS-DISP-049. The codegraph index goes stale every time the primary checkout pulls `main`, so every dispatch after a landing warned `codegraph-index: stale` on 2026-10-02 until `marshal seed kit --apply` resynced it by hand.

**Approach:** When the only non-ok rows are the codegraph index (and the kit row that reports it), prelaunch runs the kit's incremental codegraph resync within the kit's own ceiling and re-checks; a resync that fails or times out leaves today's warning, and nothing here blocks a launch.

Ledger key: `83-6-dispatch-resyncs-a-stale-codegraph-index-before-it-launches-a-session`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 63.4 (`spec-pyforge-steward` CAP-5) and the token-economy kit (Story 28.3). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the session check reports only codegraph-index stale When prelaunch runs Then it resyncs, re-checks and launches with no MRS-DISP-049
- Given the resync fails or times out When prelaunch runs Then it warns MRS-DISP-049 and launches
- Given another non-ok row When prelaunch runs Then it warns as today
- Given the resync removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where the shipped behaviour lives, and pin it with a test that fails without the fix.

**Never:** Never block a launch on the resync. Do not resync when the index is fresh.

</intent-contract>

## Binding

Parent: Story 63.4 (`spec-pyforge-steward` CAP-5) and the token-economy kit (Story 28.3).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 (night) entry.
Ledger key: `83-6-dispatch-resyncs-a-stale-codegraph-index-before-it-launches-a-session`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 at the operator's request to chain the defects found landing Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
