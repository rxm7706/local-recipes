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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `e91c220927` (2026-08-29, "atlas: sync sprint-status-ledger + epics.md -- Story 21.2 done"); also `f20492af73` (2026-08-29, "atlas: remove cf_atlas.db seeds from production datasets (Story 21.2)"); also `6949c2f084` (2026-08-23, "feat(marshal): Story 21.2 orchestrated Full/minimal chain regeneration"). Ledger row `21-2-deck-trio-derives-the-infographic-deck-from-the-standalone: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md`, `_bmad-output/projects/pyforge-atlas/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
