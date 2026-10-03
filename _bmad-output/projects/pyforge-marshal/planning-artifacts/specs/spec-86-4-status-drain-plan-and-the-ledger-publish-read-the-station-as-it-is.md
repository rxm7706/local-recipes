---
title: "86.4: Status, the drain plan and the ledger publish read the station as it is"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Three reporting and publish gaps the operator ruled to fix: `marshal status` warns MRS-STATUS-010 for a failed patch of the story the home is re-driving right now; `factory drain --plan` reports a serial station busy with a live session as would_dispatch; and a ledger publish rejected because origin/main moved (non-fast-forward) is never retried, so a merged landing reads refused (MRS-DISP-051 then MRS-DISP-020).

**Approach:** Skip the MRS-STATUS-010 WARN for the row's current story (keep it listed); read live sessions in `plan_station_cycle`'s serial branch and report would_dispatch false with an in-flight note; retry `commit_paths_onto_remote_tip` up to 3 times on a non-fast-forward (re-fetch, rebuild, re-push) and note it on CAP-277.

Ledger key: `86-4-status-drain-plan-and-the-ledger-publish-read-the-station-as-it-is`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The capabilities that shipped each behaviour (see each row); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a failed patch for the current story When status renders Then no MRS-STATUS-010 for it and the patch is still listed
- Given a serial station with a live session When drain --plan runs Then would_dispatch is false with an in-flight note, no refusal
- Given a publish rejected once as non-fast-forward When finalize runs Then it re-fetches, rebuilds, pushes and the landing reads landed
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-4-14-8`, `DW-marshal-65-1-2`, `DW-marshal-68-1-2` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Bound the retry (3) and journal each attempt. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never force-push.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-FU-4-14-8` — cli/status.py skips the MRS-STATUS-010 WARN for a failed patch whose story_key equals the row's current_story; the patch stays listed in failed_patches. Add a unit test.
- `DW-marshal-65-1-2` — plan_station_cycle's serial branch (parallel_cap <= 1) reads live dispatch sessions (station_in_flight_conflict / _live_dispatch_story_keys) and, when busy, reports would_dispatch false with an in-flight note (no refusal, no exit-code change); add a drain-plan test.
- `DW-marshal-68-1-2` — commit_paths_onto_remote_tip retries a non-fast-forward rejection up to 3 times (re-fetch, rebuild the commit, re-push) before raising; record it on CAP-277 and add a unit test with a fake that rejects once.

## Binding

Parent: The capabilities that shipped each behaviour (see each row)
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `86-4-status-drain-plan-and-the-ledger-publish-read-the-station-as-it-is`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
