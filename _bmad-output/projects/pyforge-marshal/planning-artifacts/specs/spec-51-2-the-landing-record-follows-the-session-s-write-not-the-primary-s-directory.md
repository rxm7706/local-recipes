---
title: '51.2: The landing record follows the session''s write, not the primary''s directory'
type: 'fix'
created: '2026-09-19'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** bmad-build-auto wrote 50.4's Review Triage Log, Auto Run Result, `followup_review_recommended: true` and one deferral to `<worktree>/_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-50-4-…md` (tracked spec as `context:`), flipped only `status:` on the tracked copy, and finalize's scan of the primary's Tier-3 dir found nothing — promoted by hand (#1488), DW-FU-50-4 ingested by hand; the same landing's `dispatch-land` projection read `pr_number: null, marshal_native: false` for a refusal that happened after PR #1487 was opened

**Approach:** finalize's promotion scan reads the worktree's Tier-3 dir as a discovery source beside the primary's, and the REFUSED result carries the PR facts already known at :317

## Boundaries & Constraints

**Always:**
- the 50.4 fixture's tracked spec carries `## Auto Run Result` and its `deferred:` item reaches `deferred_work_intake.py` with no hand step; a post-open refusal journals `pr_number` and `marshal_native`
- the primary-directory promotion path is byte-identical (existing fixtures), and a worktree with no twin promotes nothing (silence is not a finding)

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-250`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` (accepts the worktree beside `slug`/`key`), `.../dispatch_land.py` (spawns finalize with the worktree; the two REFUSED `DispatchLandingResult` constructors keep `pr_number` / `marshal_native`), `.../cli/deploy.py::_scan_promotions` / `_discover_candidates` (a second Tier-3 source: the dispatch worktree's `implementation-artifacts/`, read before teardown), tests.
Ledger key: `51-2-the-landing-record-follows-the-session-s-write-not-the-primary-s-directory`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-2-the-landing-record-follows-the-session-s-write-not-the-primary-s-directory.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.2 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
