---
spec: pptx-custom-shapes
status: ready
owner-dream: docs/dreams/pptx-custom-shapes.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/pptx-custom-shapes.md
---

# SPEC — Programmatic shapes + real-font autofit for the .pptx pipeline

## Why
Unparked with its parent (operator audience decision, 2026-08-22): dense
slides need cards/metric boxes/tables/section labels no template
placeholder anticipates, plus autofit from REAL font metrics — never
hand-written OOXML, never guessed text sizing.

## Capabilities
- **CAP-1 — the shape API + autofit engine (→ 15.2).**
  `add_card`/`add_metric_box`/`add_table`/`add_section_label`-shaped calls
  rendering into the 15.1 pipeline's decks; autofit via Pillow `ImageFont`
  measurement (wrap, shrink, orphan rebalancing — already a transitive
  dependency, no new class); color/font mapping from the repo's own
  template, not any external brand. *Success:* a metric-dense slide renders
  with no overflow and no manual size fiddling; the shapes are editable
  objects in PowerPoint.

## Constraints
Strictly downstream of 15.1's pipeline (Deps enforced); sibling Pillow
pattern only, no verbatim import.

## Non-goals
A general drawing library; chart rendering (native chart XML is its own
future question).

## Success signal
The densest six-act appendix slide ships as editable objects that fit —
measured, not guessed.

**Realization status (2026-09-09): built, unexercised.** Story 15.2 shipped
`add_card` / `add_metric_box` / `add_table` / `add_section_label` plus
`fit_text`'s Pillow `ImageFont` autofit inside `pptx_pipeline.py`, reached from
`content_plan.json`'s optional `"shapes"` list. No dense slide has ever been run
through it — no `content_plan.json` exists anywhere in the tree — so the signal
above is unexercised. Vessel: herald Epic 19 Story 19.4, the same real-deck
render that exercises this Spec's parent.

## Assumptions
- DW-FU-15-1-2 (`_resolve_layout` picks the first match on duplicate layout
  names) is unreachable with the stock template's 11 distinct layout names and
  becomes live only when a branded `.potx` lands.
