---
title: "Addendum: pyforge-scribe PRD"
created: 2026-07-25
updated: 2026-07-25
---

# Addendum: pyforge-scribe PRD

Technical-how, options-considered, and depth that belongs to the architecture phase rather than the PRD's product narrative. Referenced from `prd.md` FR-7.

## Write-boundary detail (FR-7)

The legacy `claude-team-memory` spec's FR-7 forbade the promotion skill from writing anywhere outside `.claude/memory/`. Scribe is now a real package, so the boundary needs one more line to stay precise:

**Scribe MAY write to:**
- `.claude/memory/**` (team memory — the whole point of Wave 1).
- Its own package source tree (wherever `pyforge.scribe` lives as a pixi workspace member — exact path TBD at architecture phase, likely `src/pyforge_scribe/` or `apps/pyforge-scribe/` following this repo's existing package-layout convention).
- Its own compiled-graph artifact store (Wave 2) — location and format TBD at architecture phase (§8 Open Question 1 of the PRD).
- User-local memory (`~/.claude/projects/<encoded-path>/memory/`), but **only** the specific pointer-stub rewrite on a promoted entry (FR-5) — never any other file there.

**Scribe MUST NOT write to** (inherited from legacy FR-7, restated): `.claude/skills/` (any skill other than its own, if Wave 1 ships as a skill-shaped implementation), `.claude/scripts/`, `.claude/agents/`, `.mcp.json`, `recipes/`, `_bmad/`, `_bmad-output/` outside its own project directory, and root `CLAUDE.md` (human-driven edit per FR-7's note).

## Options considered for Wave 1 implementation shape

Three shapes were weighed for how Wave 1 (Capture & Promotion) actually ships, given the D-1 supersession decision (Scribe is a real package, but Wave 1's *logic* doesn't need to be over-engineered):

1. **Pure skill, no CLI yet** (closest to the legacy spec as literally written) — fastest to ship, but creates a discontinuity when Wave 2 introduces the `scribe` CLI (users would have two different invocation styles across waves).
2. **Thin CLI wrapper around skill-shaped logic** (recommended direction, not mandated by this PRD) — `scribe capture` exists as a real CLI entry point from day one, but its Wave 1 implementation internally reuses the proposal-then-confirm / team-voice-rewrite logic almost verbatim from the legacy spec's skill design. This keeps FR-14's "CLI is the public contract" true from the start without requiring Wave 2's full graph-compile engine to exist yet.
3. **Full package from day one, including a premature storage-engine commitment** — rejected; front-loads Wave 2's harder open question (graph storage engine) onto Wave 1 unnecessarily.

Option 2 is the addendum's recommendation to the architecture phase, not a PRD-level commitment (PRD FR-14 fixes the contract, not the internal implementation sequencing).

## Sizing / duration note

No effort estimate is given in this PRD. Per this repo's CLAUDE.md rule ("BMAD must re-verify spec cost/size/duration claims at intake"), any duration estimate for Wave 1/Wave 2 should be produced at epics/stories time against this PRD's actual FR count (15 FRs across 4 features), not inferred here.

## Legacy spec cross-reference table

For implementers diffing this PRD against `docs/specs/claude-team-memory.md` directly:

| Legacy story | Legacy FR(s) | This PRD |
|---|---|---|
| Story 1 (scaffold `.claude/memory/`) | FR-1, FR-8 | FR-1, FR-8 (§4.1) |
| Story 2 (skill scaffold) | — | FR-14 (§4.4), reshaped per D-1 |
| Story 3 (relevance test + voice rules) | FR-4 | FR-4 (§4.1) |
| Story 4 (workflow body) | FR-3, FR-6 | FR-3, FR-6 (§4.1) |
| Story 5 (`CLAUDE.md` wiring) | — | §4.1 Notes (human-driven, FR-7 boundary) |
| Story 6 (seed promotion) | — | D-3 (§9), UJ-4 |
| Story 7 (pointer stub) | FR-5 | FR-5 (§4.1) |
| Story 8 (README) | — | carried forward implicitly; not a numbered FR in either doc |
| Story 9 (`CLAUDE.md` de-dup, Q3) | — | §4.1 Notes, Open Question 6 |
| Story 10 (smoke test) | — | not restated as an FR; test-plan concern for epics/stories phase |
| — (net new) | — | FR-2 (index size), FR-9–13 (graph compile/recall, Wave 2), FR-15 (pixi membership) |
