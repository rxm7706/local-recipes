---
title: 'The ten decks' trios re-derived, refreshed and pushed'
type: 'feature'
created: '2026-09-14'
status: 'in-review'
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

This is the original pre-implementation intent-contract for Story 21.4, recovered
from an abandoned `bmad-loop` run's loop-home worktree (`~/.bmad-loops/pyforge-herald`)
after most of the story had already landed -- drafted 2026-09-14, never promoted to
this tracked location. Story status is `in-review`, not `done`: the push+read-back leg
completed for all ten decks (PRs #1394-#1404), but four of them (atlas/herald/marshal/
unifying-strategy) remain head-only pending DW-4, a pre-existing, out-of-scope
poster-vocabulary gap. Some detail below (e.g. file paths) reflects the plan as
drafted, not necessarily the final implementation. For the actual landing record, see
`spec-deck-family-lockstep/.memlog.md`'s 2026-09-16/17 entries.

<intent-contract>

## Intent

**Problem:** Epic 20 left ten PyForge decks behind — their Infographic heads/decks are standalone ahead, marked surfaces are stale, exports are dated 2026-07/08.

**Approach:** Apply trio derivation (21-1, 21-2), fact refresh (21-3), and export regeneration to all ten PyForge decks in `presentations/pyforge-*/`. Ensure all derived files are stamped with the rebuild date.

## Boundaries & Constraints

**Always:**
- All ten PyForge decks in one cohesive effort
- Current facts ledger drives all refreshes
- Derived files dated rebuild day
- One PR per deck or consolidated PR

**Never:**
- Hand-fixing the decks
- Splitting across multiple story arcs

## Tasks & Acceptance

**Execution:**
- Create batch script/command to apply trio derivation to all ten
- Apply fact refresh to all ten
- Regenerate all exports
- Update README files with current stamps
- Verify `herald deck status` shows all ten at 0 mismatch

**Acceptance Criteria:**
- All ten PyForge decks have current heads and decks
- All marked surfaces synchronized
- All PPTX and Marp exports regenerated and dated
- `herald deck status` reports all ten at 0 mismatch
- Aggregation story applying 21-1, 21-2, 21-3 to full set

</intent-contract>
