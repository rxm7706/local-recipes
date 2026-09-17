---
title: 'The Infographic Deck derives from the standalone'
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

This is the original pre-implementation intent-contract for Story 21.2, recovered
from an abandoned `bmad-loop` run's loop-home worktree (`~/.bmad-loops/pyforge-herald`)
after the story had already landed and merged -- drafted 2026-09-14, never promoted to
this tracked location. The story is `done`; some detail below (e.g. file paths) reflects
the plan as drafted, not necessarily the final implementation, which may have evolved
during dev/review. For the actual landing record, see `spec-deck-family-lockstep/.memlog.md`'s
2026-09-14/15 entries.

<intent-contract>

## Intent

**Problem:** The Infographic Deck is hand-authored to match the standalone, and they drift. Keeping them in sync requires manual discipline and rework.

**Approach:** `deck_trio.py --deck <slug>` derives a 1920×1080 slide deck from the standalone's sections, one slide per numbered section. The transform is mechanical and idempotent.

## Boundaries & Constraints

**Always:**
- Deck is derived, never hand-authored
- One slide per standalone section
- 1920×1080 aspect ratio
- Marp markdown format
- Output renders without layout errors
- File placement: `presentations/<slug>/src/marp/infographic-deck.md`

**Never:**
- Hand-editing the derived deck
- Changing the section count without updating the standalone

## Tasks & Acceptance

**Execution:**
- Implement `deck_trio.py --deck <slug>` verb
- Produces Marp markdown with one slide per section
- Run on one shipped deck, verify section count matches standalone
- Integration test: Marp renders without error

**Acceptance Criteria:**
- `deck_trio.py --deck` verb exists and accepts deck slug
- Output has one slide per standalone section
- Slides render as 1920×1080 in Marp viewer
- Running twice produces byte-identical output
- Part 2 of CAP-1 (21-1 is part 1, the Infographic head)

</intent-contract>
