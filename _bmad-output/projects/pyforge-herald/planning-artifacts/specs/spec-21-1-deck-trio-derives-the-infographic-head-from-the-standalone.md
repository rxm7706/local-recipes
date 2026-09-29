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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `1113e6eceb` (2026-09-17, "herald: recover Epic 21 story specs 21.1-21.4 from a stale loop home"); also `a6bccc1b1c` (2026-09-10, "Reconcile DEFERRED_SPECS against live Spec statuses (Story 21.1)"); also `19090c81ca` (2026-08-29, "atlas: sync sprint-status-ledger -- Story 21.1 done"). Ledger row `21-1-deck-trio-derives-the-infographic-head-from-the-standalone: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-1-deck-trio-derives-the-infographic-head-from-the-standalone.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-2-deck-trio-derives-the-infographic-deck-from-the-standalone.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-3-deck-facts-refreshes-every-marked-surface-not-just-the-poster.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-4-the-ten-decks-trios-re-derived-refreshed-and-pushed.md`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
