---
spec: pptx-deck-generation
status: ready
owner-dream: docs/dreams/pptx-deck-generation.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/pptx-deck-generation.md
open_questions:
  - "The repo's own .pptx template: derive one from the six-act deck framework's visual system, or adopt an operator-supplied .potx — decide at 15.1."
---

# SPEC — A PowerPoint-native deck pipeline (editable .pptx)

## Why
Both trigger halves fired: Marp's .pptx export is PROVEN non-editable
(2026-08-22 inspection — background-image slides, zero text runs), and the
operator NAMED the audience — the 21-station deck program delivered to
stakeholders who edit slides. This is a second, parallel pipeline for the
one artifact the HTML/Marp pipeline structurally cannot produce; it shares
no code with the bridge.

## Capabilities
- **CAP-1 — template-parse-then-fill (→ 15.1).** Parse the `.potx`/`.pptx`
  template once into a machine-readable `spec.json` contract; the agent
  writes `content_plan.json`; mechanical placeholder filling — raw OOXML
  never hand-written. Pattern from the sibling org's most mature blueprint
  (5/6 epics complete there; pattern only, unlicensed). *Success:* an
  existing station deck's content renders to a .pptx whose every text run
  is genuinely editable in PowerPoint.
- **CAP-2 — custom shapes + real autofit (→ 15.2, downstream).** Owned by
  `spec-pptx-custom-shapes` — cards/metric boxes/tables/section labels
  beyond template placeholders, Pillow real-font-measured autofit.

## Constraints
Coexists with, never replaces, the HTML/Marp pipeline (different audiences);
no sibling prose/code verbatim; the six-act framework remains the content
grammar; template fidelity over cleverness (a stakeholder's edits must
survive round-trips).

## Non-goals
Porting the bridge pipeline; PDF/PNG QA (deck-visual-qa's chain); WF brand
specifics.

## Success signal
A station deck ships as an editable .pptx a stakeholder modifies and sends
back — text runs intact, no OOXML surgery anywhere in the flow.
