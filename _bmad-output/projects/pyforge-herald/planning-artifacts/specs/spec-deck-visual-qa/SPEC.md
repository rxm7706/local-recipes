---
spec: deck-visual-qa
status: ready
owner-dream: docs/dreams/deck-visual-qa.md
surface:
  - src/shared/packages/pyforge-herald/
  - presentations/<topic>/ (built decks the gates run against; worked example presentations/agentic-sdlc/)
sources:
  - ../../../../../../docs/dreams/deck-visual-qa.md
open_questions: []
  # ANSWERED 2026-09-09 (both, decided in shipped code — batch row `herald-OQs`):
  # OQ-1 entrypoint placement -> the Epic-6 CLI dispatcher won; `herald deck qa <slug>
  #   [--repo-root]` at cli.py:331-341 / :764-765 / :982-995. No per-deck `scripts/` step.
  # OQ-2 serve mode -> against `file://`; a throwaway loopback static server
  #   (deck_qa.py:143-152). Both are now Constraints below.
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/deck-visual-qa.md` is listed in `sources:` for
> narrative rationale this contract intentionally omits.

# Herald's deck pipeline has no gate that proves a deck LOOKS right

## Why

A recorded gap to close, not a speculative one. This repo's own accumulated feedback already
names it verbatim — "Visual output needs a screenshot — render gates prove the page RUNS, never
that it LOOKS right" (auto-memory `feedback_visual_output_needs_a_screenshot.md`) — and the
owner Dream's Realization log independently confirms it: checked directly against
`docs/specs/presentation-deck.md`, no `check_xml`/`overflow`/`visual_qa`-shaped step exists
anywhere in that spec, making this the strongest-evidenced of its three-dream batch. The deck
workflow's own verify checklist is entirely run-shaped — serves at :5173, extracts with no lost
sections, keyboard nav works, `dist/` opens as `file://` — nothing ever looks at pixels. Every
deck this repo ships is therefore "proven" only to render without a JS exception.

The Dream carves out a visual-QA half that is independent of whether the sibling `.pptx`
pipeline ([[pptx-deck-generation]]) is ever built: Herald's EXISTING HTML/React deck engine
already exposes everything needed — the current slide index is mirrored to the URL hash
(`#/12`), so every slide is deep-linkable and reload-stable, and `manifest.json` enumerates the
slides. Capacity and placement are clear: every numbered story in Herald's tracked
sprint-status ledger is `done` (only optional per-epic retrospectives remain), and none of the
project's 13 epics covers deck QA (Epics 2–3 sync decks with Claude Design; they never judge
rendering) — this is a NEW epic at decomposition time.

## Capabilities

- **CAP-1**
  - **intent:** A headless-render-to-PNG step callable after any deck build: drive the deck
    engine's existing per-slide `#/<n>` URL-hash routes with headless Chromium
    (playwright-python, already pinned in the pixi envs per `docs/reference/library-llms-full.md`
    — no new dependency), screenshot every slide `manifest.json` names at the native 1920×1080
    frame, and emit one PNG per slide plus a contact sheet — an artifact a human or LLM reviewer
    actually looks at instead of trusting "the build didn't crash."
  - **success:** Run against the worked-example deck (`presentations/agentic-sdlc/`, 45 slides,
    PR #50), it emits exactly one PNG per manifest entry (named by slide index/id) plus one
    contact sheet, and a reviewer can spot a visually broken slide from the sheet alone. A slide
    that renders badly still yields its PNG — the run reports, it never aborts on ugliness.
- **CAP-2**
  - **intent:** A format-agnostic unedited-placeholder scan reframed for Herald's own
    convention: flag slides shipping with unfilled image slots, catching BOTH spellings —
    `<image-slot placeholder="…">` in prototype/fragment sources AND the dashed `.image-slot`
    placeholder `<div>` the extractor converts them to (`presentation-deck.md` § extraction).
    Explicitly NOT the source org's PowerPoint-specific "Click to add"/Lorem-ipsum regex.
  - **success:** Run against `presentations/agentic-sdlc/` today, it flags exactly slide 40
    ("In action"), whose three `<image-slot>` panels are documented in `presentation-deck.md`'s
    own placeholder table as deliberately left for real screenshots — a live true positive. A
    deck with every slot filled reports clean.
- **CAP-3**
  - **intent:** Both gates emit into one machine-readable report keyed by gate id (gate →
    status → per-slide findings → paths to reviewer-facing artifacts), designed so the three
    parked `.pptx`-contingent gates — `check_xml` OOXML ordering, `check_typst_safety`,
    `audit_overflow` — can register as new gate ids later without reworking the report shape,
    the entrypoint, or any consumer.
  - **success:** Adding a stub third gate id requires no change to the report schema or to the
    two v1 gates' output; the report round-trips (parse it back, address each gate's findings
    by id).

## Constraints

- **Always:** report-only — the QA step never mutates deck sources and never rebuilds; a human
  or agent fixes (carried from the Dream's source scope unchanged).
- **Always:** runs against Herald's EXISTING HTML/React pipeline; zero dependency on
  [[pptx-deck-generation]] or [[pptx-custom-shapes]]. The three format-specific gates inherit
  those sibling Dreams' preconditions and are out of scope here — this spec only reserves their
  slot in the CAP-3 report interface.
- **Always:** headless-only default (headless Chromium → PNG); no AppleScript/COM native-app
  render backends.
- **Always:** no new headless-browser dependency — playwright-python is already catalogued in
  the pixi envs; consult `library-llms-full.md` before proposing anything beyond it.
- **Always:** the gate's entrypoint is the existing Epic-6 CLI dispatcher, not a per-deck
  build step — `herald deck qa <slug> [--repo-root]` (decided 2026-09-09 against the
  `scripts/` alternative; shipped at `cli.py:331-341`, `:764-765`, `:982-995`). A per-deck
  pipeline step would fork the gate per deck and re-open the CAP-3 report contract.
- **Always:** the headless render is driven over a real HTTP origin — a throwaway loopback
  static server bound on `127.0.0.1:0` — never `file://` (decided 2026-09-09; shipped at
  `deck_qa.py:143-152`, slides driven at `http://127.0.0.1:{port}/#/{index+1}`,
  `deck_qa.py:341`). Reason, recorded inline in the code: the deck is a Vite bundle with
  dynamically-imported JS chunks and Chromium blocks cross-origin fetch/module-import under
  `file://`. This does not weaken `presentation-deck.md`'s own offline-`file://` verify gate;
  it says the QA render may not rely on it.

## Non-goals

- **Not** an automated fix-and-rebuild loop — reports only.
- **Not** a WCAG 2.1 AA accessibility audit.
- **Not** cross-platform rendering parity claims — the headless-Chromium PNG is the review
  artifact, never a fidelity guarantee across browsers, OSes, or native apps.
- **Not** a pixel-diff visual-regression baseline system — the PNGs feed a reviewer's judgment
  (human or LLM), not an automated pass/fail on pixels.
- **Not** the three `.pptx`-contingent gates themselves — they stay parked with their sibling
  Dreams until those pipelines exist.

## Success signal

Today, finishing a deck means passing `presentation-deck.md`'s run-shaped checklist and
trusting the result looks right — the exact failure mode the repo's memory already recorded.
After this ships, one command against `presentations/agentic-sdlc/` yields 45 PNGs, a contact
sheet, and a gate-keyed report whose placeholder scan flags slide 40's three unfilled
`<image-slot>` panels and nothing else — and every future deck build can attach "here is what
each slide LOOKS like" evidence, closing the "render gates prove the page RUNS, never that it
LOOKS right" gap for the whole pipeline.

**Realization status (2026-09-09): built, not in effect.** Epic 14 shipped all three gates
(14.1/14.2/14.3 `done`; `deck_qa.py`, 665 lines) and nothing calls them — no pixi task
(`pixi.toml` names `deck_qa` only in a playwright dependency comment, line 2352), no CI job
(`grep -rn "deck qa" .github/workflows/` is empty), and `docs/specs/presentation-deck.md` — the
workflow every deck build follows — still carries zero reference to the gate, so its verify
checklist remains purely run-shaped, which is exactly the gap this Spec exists to close. No run
artifact exists anywhere: `render_gate` writes `.herald/deck-qa/<slug>/render/`
(`deck_qa.py:117`, `:245-250`) and `.herald/` is not in the tree. Vessel: herald Epic 19 Story
19.3 (steward Epic 49 carries the index row).
