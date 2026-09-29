---
title: '21.11: One deck proves the Design loop end to end'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every push this far has been repo→Design, so the bridge's editing half is unexercised on current content and no rebuilt deck carries a Design-side improvement.

**Approach:** One deck is opened in Claude Design, visually improved there by a human, and pulled back byte-exact (`render_preview` → curl → strip the `data-omelette-injected` harness and the blank line the serve layer inserts after `<head>`).

## Boundaries & Constraints

**Always:**
- git holds the improved bytes; the read-back is byte-identical.
- The README records the etag and the date.
- `deck-facts <slug> --check` still reports 0 `mismatch` (the visual pass must not break a mark).
- The pull is the closing act: no Design-side edit is complete until git holds it.

**Never:**
- Never treat a Design-side edit as complete if git does not hold the bytes.
- Never break a marked fact in the visual pass.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| human visual pass | one deck opened in Design | pulled bytes in git; README etag+date; 0 mismatch | pull is the close |
| mark breakage | visual edit moves a marked fact | `--check` reports mismatch — fail | visual pass must not break marks |

</intent-contract>

## Binding

Parent Spec capability: `spec-deck-family-lockstep` CAP-5.
Surface: one deck's `project/` artifacts, its `README.md` ledger, `docs/specs/presentation-deck.md` (§ *The MCP bridge* — the worked pull).
Deps: S-21.4.
Ledger key: `21-11-one-deck-proves-the-design-loop-end-to-end`.
Minted 2026-09-18 from `epics.md` (Intent + ACs only) so the filename matches CHAIN-STANDARD §5 (`spec-` + ledger key).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `b8016a87e7` (2026-09-13, "herald: pull pyforge-unifying-strategy's Design-side visual pass (Story 21.11)"); also `2bb7bc58f5` (2026-09-10, "Wire capability-effect beside story-status-check (Story 21.11)."). Ledger row `21-11-one-deck-proves-the-design-loop-end-to-end: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/deck-inventory.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-lockstep/.memlog.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml`, `presentations/pyforge-unifying-strategy/README.md`, `presentations/pyforge-unifying-strategy/project/PyForge Story.dc.html`, `presentations/pyforge-unifying-strategy/project/PyForge Unifying Strategy - Executive Summary.dc.html`, `presentations/pyforge-unifying-strategy/project/PyForge Unifying Strategy - Infographic Deck.dc.html`, `presentations/pyforge-unifying-strategy/project/PyForge Unifying Strategy - Infographic.dc.html`, `presentations/pyforge-unifying-strategy/project/PyForge Unifying Strategy Infographic standalone.html`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
