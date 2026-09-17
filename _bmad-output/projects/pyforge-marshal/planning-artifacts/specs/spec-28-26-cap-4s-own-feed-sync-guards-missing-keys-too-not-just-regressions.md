---
title: "CAP-4's own feed-sync guards missing keys too, not just regressions"
type: 'fix'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - scripts/promote_sprint_status.py
warnings: []
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `cli/land.py`'s `_promote_sprint_ledger` (marshal's CAP-4 fully-autonomous auto-land path) refuses a Tier-3-feed-to-tracked-twin promotion only when `promote_sprint_status.regressions()` reports a key moving OUT of a protected state (`done`). It never checks for a twin key the feed drops entirely while that key was never in a protected state (e.g. a still-`backlog` story). Story 48.1 (pyforge-steward) fixed this exact class of bug in `promote_sprint_status.py`'s own standalone `main()` CLI, but that fix lives only in `main()` — `cli/land.py` never routes through it. Live incident 2026-09-10: CAP-4 auto-landed warden's Story 12.1, then its own feed-sync step silently dropped Epic 12's five still-backlog stories (plus the epic/retrospective rows) from the tracked ledger, because warden's Tier-3 feed had never learned Epic 12 exists. Restored by hand (PR #1117).

**Approach:** Add the same "any twin-only key" check `promote_sprint_status.main()` already has, as a small pure helper (`_land_feed_sync_refusal`) `_promote_sprint_ledger` calls alongside `regressions()`. Refuse (WARN-named, same shape as the existing regression refusal) rather than silently writing a working ledger missing that key.

## Boundaries & Constraints

**Always:** Keep the existing `regressions()`-based refusal (a key moving out of `done`) working unchanged — this is additive, not a replacement. Keep the refusal WARN-named via the existing `Finding`/`_MRS_LAND_011` mechanism, never a hard crash — CAP-4's auto-land must degrade to "nothing promoted" on refusal, not fail the whole land.

**Never:** Touch `promote_sprint_status.py`'s own `main()`/`--repair-feed` logic (Story 48.1's scope, already correct). Refuse a promotion where the incoming feed is a superset of (or equal to) the twin — only missing keys should refuse, not new ones appearing.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| SUPERSET_FEED | Incoming feed has every twin key plus new ones | Promotion proceeds normally | No refusal |
| DROPPED_DONE_KEY | Twin has a `done` key absent from incoming | Refused, labeled "un-finish" (unchanged existing behavior) | WARN finding |
| DROPPED_BACKLOG_KEY | Twin has a `backlog`-status key absent from incoming (the live-incident case) | Refused, labeled "drop" | WARN finding |
| NO_CHANGE | Incoming feed identical to twin | Promotion proceeds (working == fresh_ledger, feed_synced False) | No refusal |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` — new `_land_feed_sync_refusal(promote_mod, existing, incoming) -> tuple[str, str] | None` helper; `_promote_sprint_ledger`'s feed-sync branch calls it instead of inlining the `regressions()`-only check
- `src/shared/packages/pyforge-marshal/tests/unit/test_land.py` — 3 new tests for `_land_feed_sync_refusal` (superset-is-safe, dropped-done, dropped-backlog matching the live incident)

## Tasks & Acceptance

**Execution:**
- `cli/land.py` — extract `_land_feed_sync_refusal`, call it from `_promote_sprint_ledger` — fix
- `tests/unit/test_land.py` — 3 focused unit tests against a fake `promote_mod` — test

**Acceptance Criteria:**
- Given a twin with a still-backlog key absent from the incoming feed, when `_promote_sprint_ledger` runs its feed-sync step, then the promotion is refused with a WARN finding naming the dropped key
- Given an incoming feed that is a strict superset of the twin, when the feed-sync step runs, then the promotion proceeds normally
- Given a twin `done` key absent from incoming, when the feed-sync step runs, then the existing "un-finish" refusal behavior is unchanged

## Spec Change Log

## Review Triage Log

## Auto Run Result

Status: done

**Summary:** `_promote_sprint_ledger`'s feed-sync step now refuses on ANY twin-only key missing from the incoming Tier-3 feed, not just one moving out of `done`. Closes the gap Story 48.1 didn't reach (its own scope was `promote_sprint_status.py`'s `main()` only).

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` — new `_land_feed_sync_refusal` helper, wired into `_promote_sprint_ledger`
- `src/shared/packages/pyforge-marshal/tests/unit/test_land.py` — 3 new tests
- `spec-28-26-…md` — story contract
- `sprint-status-ledger.yaml` — 28-26 → done

**Review:** Implementation verified directly against the spec's own I/O matrix; no separate review-loop pass for this single-file fix.

**Verification:** `pytest test_land.py -k feed_sync_refusal` → 3 passed. Full `pyforge-marshal-test` → 7694 passed.

**Residual risks:** None identified — purely additive refusal check, same WARN-and-skip degrade path the existing regression check already uses.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_land.py -k feed_sync_refusal -q` — expected: 3 passed
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all pass
