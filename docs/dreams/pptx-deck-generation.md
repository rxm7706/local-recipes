---
title: A second, PowerPoint-native deck pipeline, if this repo ever needs editable
  .pptx output
type: dream
owner: herald
status: archived
archived-reason: absorbed
---
> **Consolidated into [[pyforge-herald]]** on 2026-09-17 (one-chain-per-station herald fold; folded from `pptx-deck-generation`).
# A second, PowerPoint-native deck pipeline, if this repo ever needs editable .pptx output

## The Dream

The source dream's template-parse-then-fill pattern — parse a `.potx`/`.pptx` template once into
a machine-readable `spec.json` contract, let an agent write a `content_plan.json`, mechanically
fill placeholders without touching OOXML by hand — solves a real, well-documented problem for
audiences that need an EDITABLE PowerPoint file, not a browser deck. This repo already has a deck
pipeline, but it produces a genuinely different artifact: Herald's own bridge (`bridge.py`,
`deck_pipeline.py`) round-trips through Claude Design's MCP tools to a React+Vite HTML slide deck
(`docs/specs/presentation-deck.md`'s own workflow), never a `.pptx` file. This Dream is not a port
of that pipeline — it shares no code with it — it is a SECOND, parallel capability for the one
thing the HTML pipeline structurally cannot produce: a file PowerPoint itself can open and edit.

## What it looks like when real

Left thin — no scoped feature, because no PyForge audience has been identified that needs an
editable `.pptx` specifically, as opposed to the browser deck the existing pipeline already
produces:

- IF a real audience need for editable `.pptx` output emerges (an external presentation to
  reviewers who expect PowerPoint, not a URL), the source dream's template-parse-then-fill
  discipline — `spec.json` as the machine-readable contract, `content_plan.json` as the agent's
  own content mapping, mechanical placeholder filling never touching raw OOXML by hand — is a
  sound, well-proven pattern to build against, given the source dream's own maturity (its own
  Realization log shows 5 of 6 epics complete, the most implementation-ready blueprint of any
  dream in this whole batch).
- This Dream and Herald's existing HTML deck pipeline would coexist, not compete — different
  output formats for different audiences, sharing only the top-level "generate a deck" concept,
  not any code.

## What is real

Herald's own deck pipeline already produces a real `.pptx` file, shipped, not merely planned:
`docs/specs/presentation-deck.md`'s `deck-export` step writes a dated PowerPoint export to
`src/pptx/<slug>-YYYY-MM-DD.pptx`, derived from the deck's Marp narrative — confirmed by reading
the spec directly (§ the artifact dependency tree names the exact path and derivation). This
substantially narrows this Dream's actual premise: it is NOT "nothing produces `.pptx` here,"
it's "the existing `.pptx` is a Marp-markdown-to-slides conversion, not a template-positioned fill
the way the source dream's `python-pptx`-based approach guarantees." Whether that distinction
matters — whether Marp's own PPTX fidelity (shape/text positioning, WF-brand-equivalent layout
precision) is good enough for whatever audience would consume it — is unverified and is the real
open question this Dream should resolve before any code, not "build a second pipeline because
none exists."

## Constraints

- **Not a fork or reimplementation of Herald's existing deck pipeline.** Different artifact
  format's underlying mechanism (`python-pptx` template-fill vs. Marp markdown-conversion),
  deliberately separate code paths if both end up existing.
- **Verify Marp's existing `.pptx` output is actually insufficient before building this.** See
  "What is real" — a real `.pptx` already ships; this Dream is only justified if that export's
  fidelity is concretely inadequate for a named audience, not by default.

## Non-goals

- **Not a replacement for the HTML/React deck pipeline** — that pipeline's own strengths (live
  URL, keyboard nav, presenter view) are not this Dream's concern.
- **Not multi-brand support** — carried from the source's own v1 scope (WF-branding-only)
  unchanged; if built, this repo has no equivalent brand template to target yet either.

## Full feature audit against `deck-generation-pipeline`

| Source feature | Disposition | Why |
|---|---|---|
| Template parse → `spec.json` contract | **Pattern retained, no target template** | Sound design; no PyForge-branded `.potx` template exists to parse yet. |
| `content_plan.json` → mechanical fill | **Pattern retained** | Same reasoning — the mechanism is sound, no current trigger to build it. |
| Slide cloning between presentations (images/charts) | **Omitted, no target** | No current multi-deck rebranding need identified. |
| `[Content_Types].xml`/`docProps/app.xml` patching | **Implementation detail, deferred** | Not a scoping decision — carried forward as a "when built" concern. |
| 21 WF slide layouts (16:9, WF Sans) | **Omitted, WF-specific** | No PyForge-branded template exists; this repo's own template, if ever built, would need its own layout set. |

## Kinships

[[pyforge-herald]] (the actual owner — decks are Herald's domain in real PyForge, corrected from
the source's own `owner: scribe` label; scribe's real current scope is team-memory
capture/compile/promote/recall, unrelated) · [[pptx-custom-shapes]] and
[[deck-visual-qa]] (the two sibling dreams from the same source batch, extending and validating
this one respectively — captured together, same ownership correction applies to both)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Ownership corrected from the source's own `owner: scribe` label: checked directly and found
  decks are Herald's domain in this repo (`deck_pipeline.py`, `bridge.py` exist there), while
  scribe's actual current scope (`capture.py`/`compile.py`/`promote.py`/`recall.py`) is team-memory,
  unrelated to decks. First draft understated the overlap — re-checked `presentation-deck.md`
  directly and found Herald's `deck-export` step already ships a real, dated `.pptx` per deck
  (`src/pptx/<slug>-YYYY-MM-DD.pptx`, Marp-derived). Corrected the premise from "nothing produces
  `.pptx` here" to the narrower, real open question: whether Marp's conversion fidelity is
  actually inadequate for some named audience — unverified, and the thing to check before any
  code, not assumed.
- **2026-09-09 (fleet readiness pass — built, unexercised)** — Epic 15 is `done` (15.1
  template-parse-then-fill, 15.2 shapes + autofit); `pptx_pipeline.py` (1057 lines) ships
  both CAPs, with `herald deck pptx-spec` / `herald deck pptx-fill` on the CLI
  (`cli.py:342-386`, dispatched `:766-769`), and the interim template is committed and
  git-tracked at `src/pyforge/herald/templates/pyforge-deck-template.pptx`. § *What is
  real* above is superseded: it still frames this as an unanswered "is Marp good enough"
  question, which 2026-08-22 answered (Marp's export is background-image slides with zero
  text runs). The Spec's one open question is **closed this date** — 15.1 answered it with
  a third option neither branch named, python-pptx's own bundled Office theme adopted
  verbatim and regenerated by `scripts/generate_default_template.py`, because a hand-derived
  `.potx` needs custom slide *layouts* python-pptx cannot author without forbidden raw-OOXML
  surgery and an operator-supplied `.potx` needs a human who was not present. A branded
  `.potx` remains owed and is a `--template` flag, not a code change. **Status held at
  `specified`**: no station deck has been rendered through the pipeline — no
  `content_plan.json` exists anywhere in the tree, and every `.pptx` under
  `presentations/*/src/pptx/` is a dated Marp export from 2026-07/08. Vessel: herald Epic 19
  Story 19.4 (render one real station deck), per the fleet-readiness decision batch
  2026-09-09 row C6.
