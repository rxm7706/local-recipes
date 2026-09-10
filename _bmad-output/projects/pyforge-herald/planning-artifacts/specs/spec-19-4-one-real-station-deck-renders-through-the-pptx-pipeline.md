---
title: 'One real station deck renders through the pptx pipeline'
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The pptx pipeline (`pptx_pipeline.py`, 1057 lines) ships `extract_spec` /
`fill_template` and a shape API (`add_card` / `add_metric_box` / `add_table` /
`add_section_label` + Pillow `fit_text` autofit) behind `herald deck pptx-spec` / `pptx-fill`
(`cli.py:342-386`, all of Epic 15's stories 15.1/15.2 `done`), but has never rendered a real
station deck. Every `.pptx` under `presentations/*/src/pptx/` is a dated Marp export from
2026-07/08 — background-image slides with zero text runs, the exact inadequacy Epic 15 was built
to fix — and no `content_plan.json` exists anywhere in the tree.

**Approach:** Author one station deck's content as a real `content_plan.json` and fill it through
the existing pipeline against the committed interim template
(`templates/pyforge-deck-template.pptx`), producing a `.pptx` with genuinely editable text runs.
At least one dense slide must exercise the shape API — not just a plain template-fill path — to
prove the pipeline's shape-fitting capability, not merely its text substitution. The pipeline
code itself (`pptx_pipeline.py`) is unchanged; this story exercises the pipeline that already
ships, it does not add one.

## Boundaries & Constraints

**Always:**
- The deck follows the canonical six-act framework, with the Warden standalone deck as the shape
  exemplar.
- At least one dense slide exercises the shape API (`add_card` / `add_metric_box` / `add_table` /
  `add_section_label` + Pillow `fit_text` autofit).
- The output `.pptx` is the pipeline's own output (via `extract_spec` / `fill_template`), not a
  Marp export.
- Fill against the committed interim template (`templates/pyforge-deck-template.pptx`).

**Never:**
- `pptx_pipeline.py` is not changed — this story adds no pipeline.
- A PyForge-branded `.potx` stays deferred work reachable by a `--template` flag — not built, and
  not a blocker for this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Baseline (today) | every `.pptx` under `presentations/*/src/pptx/` is a Marp export (2026-07/08); no `content_plan.json` exists | the gap this story closes | — |
| `content_plan.json` authored and filled | a real `content_plan.json` for one station deck, filled via `herald deck pptx-fill` against `templates/pyforge-deck-template.pptx` | resulting `.pptx` opens with real, editable text runs — not background-image slides | — |
| Dense slide via shape API | a slide with content no placeholder anticipates | rendered via `add_card` / `add_metric_box` / `add_table` / `add_section_label` with Pillow `fit_text` autofit | — |
| Provenance check | inspect the output file | the file is the pipeline's own output, not a Marp export | — |
| Template choice | no PyForge-branded `.potx` exists | the interim `templates/pyforge-deck-template.pptx` is used; a `.potx` is deferred behind a future `--template` flag | not a blocker for this story |

</intent-contract>

## Code Map

- a first real `content_plan.json` — new (none exists anywhere in the tree today)
- `src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_pipeline.py` — unchanged (read-only
  reference; this story adds no pipeline)
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py:342-386` — existing
  `herald deck pptx-spec` / `pptx-fill` wiring (read-only reference)
- `presentations/<station>/src/pptx/` — output location for the new deck
- `templates/pyforge-deck-template.pptx` — the committed interim template filled against
- `docs/specs/presentation-deck.md` — the pptx step, if it earns one

## Tasks & Acceptance

**Execution:**
- feature: author one station deck's content as a real `content_plan.json`
- feature: fill it through the existing pipeline (`herald deck pptx-fill`) against
  `templates/pyforge-deck-template.pptx`
- feature: ensure at least one dense slide exercises the shape API
- docs: add a pptx step to `presentation-deck.md`, if it earns one

**Acceptance Criteria:**
- Given `pptx_pipeline.py` (1057 lines) ships `extract_spec` / `fill_template` and the shape API
  (`add_card` / `add_metric_box` / `add_table` / `add_section_label` + Pillow `fit_text` autofit)
  behind `herald deck pptx-spec` / `pptx-fill` (`cli.py:342-386`), while every `.pptx` under
  `presentations/*/src/pptx/` is a dated Marp export from 2026-07/08 and no `content_plan.json`
  exists — when one station deck is authored as a `content_plan.json` and filled through the
  pipeline against the committed interim template (`templates/pyforge-deck-template.pptx`), then
  the resulting `.pptx` opens with real, editable text runs (not background-image slides), at
  least one dense slide exercises the shape API, and the file is the pipeline's output rather
  than a Marp export.
- And the deck follows the canonical six-act framework with the Warden standalone deck as the
  shape exemplar; a PyForge-branded `.potx` stays deferred work reachable by a `--template` flag,
  not a blocker for this story.

## Spec Change Log

## Review Triage Log
