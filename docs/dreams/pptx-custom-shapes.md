---
title: Programmatic OOXML shapes for information-dense slides, if the .pptx pipeline
  ever exists
type: dream
owner: herald
status: archived
archived-reason: absorbed
---
> **Consolidated into [[pyforge-herald]]** on 2026-09-17 (one-chain-per-station herald fold; folded from `pptx-custom-shapes`).
# Programmatic OOXML shapes for information-dense slides, if the .pptx pipeline ever exists

## The Dream

Cards, metric boxes, tables, and section labels with no template placeholder to fill — plus a
real text-autofit engine using actual font measurement, not a guess — so an agent never
hand-writes OOXML fill/font XML for slide content a template didn't anticipate. This capability
is meaningless without [[pptx-deck-generation]]'s own template-parse-then-fill pipeline existing
first: there is no "open canvas layout" to place custom shapes on without a `.pptx` template
pipeline to place them inside. Strictly downstream of that Dream, not independent of it.

## What it looks like when real

Not scoped independently — see [[pptx-deck-generation]]'s own "What it looks like when real."
IF that Dream is ever built (contingent on Marp's existing `.pptx` export proving genuinely
inadequate, per its own open question), this capability would be its natural extension for
content a template placeholder can't express: `add_card`/`add_metric_box`/`add_table`/
`add_section_label`-shaped calls, an autofit engine using real font metrics (this repo already
depends on Pillow transitively in several environments, so `ImageFont`-based measurement is not a
new dependency class), and WF-brand-specific color/font mapping replaced with whatever this
repo's own `.pptx` template (if one is ever built) actually uses.

## What is real

Nothing — this Dream has no independent existence from [[pptx-deck-generation]], which itself has
no independent existence from a verified, named audience need for editable `.pptx` output beyond
what Herald's existing Marp export already produces.

## Constraints

- **Does not exist without [[pptx-deck-generation]] existing first.** This is not a standalone
  capability — building it before the base template-fill pipeline would have nothing to attach to.

## Non-goals

- **Not chart or SmartArt creation** — carried from the source's own v1 scope unchanged.
- **Not dynamic data binding** — static content only, carried unchanged.

## Full feature audit against `custom-branded-elements`

| Source feature | Disposition | Why |
|---|---|---|
| `add_card`/`add_metric_box`/`add_table`/`add_section_label` shape API | **Pattern retained, contingent** | Sound design; contingent entirely on [[pptx-deck-generation]] existing. |
| Text autofit engine (Pillow-based real font measurement) | **Pattern retained, contingent** | Same — genuinely useful IF the base pipeline exists; Pillow itself is not a new dependency class for this repo. |
| WF brand color-to-scheme-slot mapping | **Omitted, WF-specific** | No PyForge-branded template exists to map colors for. |
| Theme font refs (`+mj-lt`/`+mn-lt`) | **Implementation detail, deferred** | Not a scoping decision — carried forward as a "when built" concern. |

## Kinships

[[pptx-deck-generation]] (the base Dream this one is strictly downstream of — not a peer, a
dependent) · [[deck-visual-qa]] (the sibling Dream that would validate this one's output, same
source batch)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit,
  alongside its two sibling deck dreams. Deliberately framed as non-independent from
  [[pptx-deck-generation]] rather than duplicating that Dream's own "is a `.pptx` pipeline even
  needed" open question here — one open question, named once, inherited by both dependents.
- **2026-09-09 (fleet readiness pass — built, unexercised)** — § *What is real* ("Nothing —
  this Dream has no independent existence…") is superseded: Story 15.2 shipped
  `add_card` / `add_metric_box` / `add_table` / `add_section_label` plus `fit_text`'s Pillow
  `ImageFont` autofit inside `pptx_pipeline.py`, reached from `content_plan.json`'s optional
  `"shapes"` list. Unexercised — no dense slide has been run through it, because no
  `content_plan.json` exists anywhere in the tree, so the "densest six-act appendix slide"
  signal has never been executed. **Status held at `specified`.** Vessel: herald Epic 19
  Story 19.4 — the same real-deck render that exercises its parent
  [[pptx-deck-generation]] — per the fleet-readiness decision batch 2026-09-09 row C6.
