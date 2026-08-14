---
title: A deck is proven to look right, not merely to render without crashing
type: dream
owner: herald
status: specified
---

# A deck is proven to look right, not merely to render without crashing

## The Dream

Every deck this repo produces — Herald's existing HTML/React pipeline today, and a possible
`.pptx` pipeline ([[pptx-deck-generation]]) tomorrow — passes some render check before being
called done, but "renders without a JS exception" and "looks right" are different claims, and
today's tooling only proves the first. This is not a hypothetical gap: it is a standing,
already-recorded piece of feedback in this repo's own memory — "Visual output needs a
screenshot — render gates prove the page RUNS, never that it LOOKS right." The source dream's
`visual_qa` concept (render every slide to PNG for review, opt-in native-app backends) is a direct
answer to a problem this repo has already been told it has, independent of whether a `.pptx`
pipeline ever exists.

## What it looks like when real

Splits cleanly into two pieces with different dependencies:

- **Visual rendering QA (PNG-per-slide, for review)** — applies to Herald's EXISTING HTML/React
  deck pipeline today, no `.pptx` pipeline required. This is the piece that actually closes the
  documented "render gates prove RUNS, never LOOKS right" gap — a headless-render-to-PNG step
  callable after any deck build, HTML or `.pptx` alike, giving a human or an LLM reviewer
  something to look at instead of trusting "the build didn't crash."
- **Structural/format-specific gates** (`check_xml`'s OOXML element-ordering validation,
  `check_typst_safety`'s Typst-PDF-renderer crash-pattern detection, `audit_overflow`'s
  text-capacity estimation) — these are `.pptx`/OOXML-specific and inherit
  [[pptx-deck-generation]]'s own open question about whether that pipeline is ever built at all.
- **`check_placeholders`** (regex scan for unedited "Click to add"/Lorem ipsum) — format-agnostic
  in principle; Herald's HTML pipeline already has its own `<image-slot>` placeholder convention
  (`presentation-deck.md`), so a similar unedited-placeholder scan could apply there too, though
  this repo's placeholder shape differs from the source's PowerPoint-specific one.

## What is real

Herald's existing deck pipeline (`docs/specs/presentation-deck.md`) has NO dedicated
visual/structural QA gate today — checked directly, no `check_xml`/`overflow`/`visual_qa`-shaped
step exists anywhere in that spec. The gap this Dream's visual-QA half would close is real and
already named in this repo's own accumulated feedback, not speculative.

## Constraints

- **The visual-QA half does not require [[pptx-deck-generation]] to exist** — it should be scoped
  and potentially built against Herald's EXISTING HTML pipeline first, independent of that other
  Dream's own open question.
- **The structural/format-specific gates DO require a `.pptx` pipeline** — OOXML-element-ordering
  and Typst-crash-pattern checks have no meaning without `.pptx`/Typst artifacts to check.

## Non-goals

- **Not an automated fix-and-rebuild loop** — the QA pipeline reports; a human or agent fixes,
  carried from the source dream's own scope unchanged.
- **Not full WCAG 2.1 AA accessibility audit** — carried unchanged.
- **Not cross-platform rendering parity guarantees** — carried unchanged.

## Full feature audit against `deck-quality-assurance`

| Source feature | Disposition | Why |
|---|---|---|
| `visual_qa` (render every slide to PNG for review) | **Included, independent of `.pptx`** | The one piece with a real, already-documented local gap to close — applies to Herald's existing HTML pipeline today. |
| `check_xml` (OOXML element-ordering/choice-group validation) | **Contingent on [[pptx-deck-generation]]** | Meaningless without `.pptx`/OOXML artifacts. |
| `check_typst_safety` (Typst-PDF-renderer crash patterns) | **Contingent on [[pptx-deck-generation]]** | This repo's own pipeline doesn't use Typst for PDF export (see `presentation-deck.md`'s own export chain); relevant only if a future `.pptx`-adjacent pipeline introduces a Typst step. |
| `audit_overflow` (80%-capacity text estimation, autofit-aware) | **Contingent on [[pptx-custom-shapes]]** | Needs that Dream's own autofit engine to have an "AUTOFIT_OK/UNREADABLE" classification to audit against. |
| `check_placeholders` (unedited "Click to add"/Lorem ipsum scan) | **Reframed, format-agnostic in principle** | Herald's HTML pipeline has its own `<image-slot>` placeholder convention already; a similar unedited-content scan could apply there, though the exact regex/shape differs from PowerPoint's. |
| PowerPoint AppleScript/COM native-app render backends | **Omitted, platform-specific** | Opt-in native rendering is a nice-to-have this Dream doesn't need to commit to; a headless PDF/PNG path (PyMuPDF/`pdftoppm`, already the source's own default) is sufficient. |

## Kinships

[[pyforge-herald]] (the estate — the visual-QA half applies to Herald's EXISTING deck pipeline
directly) · [[pptx-deck-generation]] and [[pptx-custom-shapes]] (the two sibling Dreams whose
format-specific gates this one's structural half depends on)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit,
  alongside its two sibling deck dreams. Unlike those two, found this one splits into an
  independently-valuable half: `visual_qa`'s PNG-per-slide rendering directly answers an
  already-recorded piece of this repo's own feedback ("render gates prove RUNS, never LOOKS
  right"), applicable to Herald's existing HTML pipeline with no dependency on whether a `.pptx`
  pipeline is ever built — the strongest-evidenced of the three deck dreams in this batch as a
  result.
- **2026-08-14** — Spec authored (spec-deck-visual-qa, pyforge-herald) by the 2026-08-14 dream-backlog audit: the visual-QA half only (PNG-per-slide headless render + <image-slot> placeholder scan against the existing HTML pipeline); the three .pptx-contingent gates stay parked with their sibling dreams.
