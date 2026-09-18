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
