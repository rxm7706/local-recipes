---
title: 'The Infographic head derives from the standalone'
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

This is the original pre-implementation intent-contract for Story 21.1, recovered
from an abandoned `bmad-loop` run's loop-home worktree (`~/.bmad-loops/pyforge-herald`)
after the story had already landed and merged -- drafted 2026-09-14, never promoted to
this tracked location. The story is `done`; some detail below (e.g. file paths) reflects
the plan as drafted, not necessarily the final implementation, which may have evolved
during dev/review. For the actual landing record, see `spec-deck-family-lockstep/.memlog.md`'s
2026-09-14/15 entries.

<intent-contract>

## Intent

**Problem:** The Infographic head and the standalone prototype can diverge, requiring manual re-authoring to keep them in sync. The head's body is identical to the standalone's by definition, so the divergence is removable by transform rather than by discipline.

**Approach:** `deck_trio.py` implements a transformation verb that derives a deck's Infographic head (`.dc.html` with `x-dc` wrapper, styles in the helmet) from a current standalone prototype. The three (head, deck, standalone) can no longer disagree because the head is mechanically derived.

## Boundaries & Constraints

**Always:**
- Head is derived, never hand-authored
- Output is wrapped in `.dc.html` with `x-dc` class
- Styles are embedded (helmet-level CSS)
- Transform is idempotent — running twice produces byte-identical output
- File placement: `presentations/<slug>/src/infographic-head.dc.html`

**Never:**
- Hand-editing the derived head
- Split the derivation from the standalone sync

## Tasks & Acceptance

**Execution:**
- Implement `deck_trio.py --head <slug>` verb
- Accepts deck slug, produces `.dc.html` file
- Run on one shipped deck, verify body matches standalone modulo wrapper/styles
- Idempotent test: run twice, verify byte-identical output

**Acceptance Criteria:**
- `deck_trio.py` has `--head` verb
- Verb produces `.dc.html` with correct wrapper and embedded styles
- Output content matches standalone's `<body>` exactly
- File renders without error in browser
- Running twice produces byte-identical output
- Part 1 of CAP-1 (21-2 is part 2, the Infographic Deck)

</intent-contract>
