---
title: 'Deck facts refreshes every marked surface, not just the poster'
type: 'feature'
created: '2026-09-14'
status: 'done'
baseline_revision: ~
review_loop_iteration: 0
followup_review_recommended: false
context: ['spec-deck-family-lockstep/SPEC.md']
warnings: []
deferred: []
declared_low_risk: false
verdict_mode: advisory
---

## Recovery note (2026-09-17)

This is the original pre-implementation intent-contract for Story 21.3, recovered
from an abandoned `bmad-loop` run's loop-home worktree (`~/.bmad-loops/pyforge-herald`)
after the story had already landed and merged -- drafted 2026-09-14, never promoted to
this tracked location. The story is `done`; some detail below (e.g. file paths) reflects
the plan as drafted, not necessarily the final implementation, which may have evolved
during dev/review. For the actual landing record, see `spec-deck-family-lockstep/.memlog.md`'s
2026-09-14/15 entries.

<intent-contract>

## Intent

**Problem:** `deck-facts --refresh` in Epic 20 only updates the poster. The Infographic head, Infographic Deck, executive summary and Marp sources carry marked facts but are not refreshed together.

**Approach:** Extend `deck_facts.py --refresh` to walk every marked surface — poster, head, Infographic Deck, exec summary, Marp sources — so one ledger change updates all surfaces atomically.

## Boundaries & Constraints

**Always:**
- All five surfaces refreshed in one command
- Same ledger source of truth
- Per-surface mismatch reporting
- Idempotent — second run changes nothing

**Never:**
- Hand-editing marked facts after automated refresh
- Partial refreshes

## Tasks & Acceptance

**Execution:**
- Extend `deck_facts.py --refresh` to iterate all five surfaces
- Implement `--check` to report per-surface mismatch counts
- Integration test: update one fact, run refresh on one deck, verify all five surfaces updated

**Acceptance Criteria:**
- `deck_facts --refresh` walks poster, head, deck, summary, marp
- `deck_facts --check` reports mismatch count per surface
- Running refresh twice produces no changes on second run
- All marked facts in output match current `facts.yaml`
- Part of CAP-2

</intent-contract>
