# PyForge Unifying Strategy — deck family

Herald-station presentation family for the **pyforge-unifying-strategy** chain
(*PyForge Unifying Strategy — The Canopy & 8-Station Hub-and-Spoke Enterprise
Architecture*). Steward's chain; display brand **The Canopy** on the slides,
slug `pyforge-unifying-strategy` in paths, per the display-brand-vs-slug rule
in `docs/specs/presentation-deck.md`.

**Content grounding** (all facts derived, none recalled):

- `docs/dreams/pyforge-unifying-strategy.md` — the Dream + decision trail
  (Grounding, the 2026-08-24 rulings, the Realization log).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/`
  — SPEC.md (CAP-1..19 with live proofs), `stack.md`, `convergence.md`,
  `console-parity-inventory.md`, `resilience-invariants.md`,
  `architecture-diagrams.md`; plus the brief and PRD bundles dated 2026-08-24.

## The artifact family

```
project/
  Unifying Strategy Deck.dc.html                       28-slide narrative deck prototype (six acts) — UNTOUCHED by the 2026-09-13 pull below
  PyForge Unifying Strategy - Executive Summary.dc.html  one-page 1920×1080 exec summary
  PyForge Unifying Strategy - Infographic.dc.html        ★ the trio head — 23-section one-pager, 3 inline-SVG diagrams
  PyForge Unifying Strategy - Infographic Deck.dc.html   the same story re-laid as slides
  PyForge Unifying Strategy Infographic standalone.html  same body as ★, no x-dc wrapper, styles in <head>
  PyForge Story.dc.html                                  narrative <doc-page> write-up of the Dream (Grounding 2026-08-30 · Epic 40 red-team 2026-09-02) — NOT part of the five-file family contract above; added 2026-09-13 alongside the Design-side pull, no facts.yaml coverage, no deck-facts/deck-export surface
src/marp/
  pyforge-unifying-strategy-deck-2026-08-26.md
  pyforge-unifying-strategy-executive-summary-2026-08-26.md
  pyforge-unifying-strategy-infographic-2026-08-26.md
  pyforge-unifying-strategy-infographic-standalone-2026-08-26.html   (generated — marp)
src/pptx/
  pyforge-unifying-strategy-deck-2026-08-26.pptx                     (generated — marp --pptx)
  pyforge-unifying-strategy_infographic_deck-2026-08-26.pptx         (generated — marp --pptx)
```

Regenerate the derived exports (never hand-edit them):

```bash
pixi run -e local-recipes deck-export pyforge-unifying-strategy
```

Visual system: **Modernist** (Archivo / Archivo Expanded; light `#f3f2f2`,
ink `#201e1d`, red `#ec3013`), matching the other pyforge persona decks. The
form/density exemplar is `presentations/pyforge-warden/project/"Warden
Infographic standalone.html"`; the six-act arc follows the canonical deck
framework. Design-system tokens are inlined in each `.dc.html` helmet so every
file renders from disk (Google Fonts online, system fallback offline).

**Deliberately not included:** the React/Vite interactive deck engine
(`src/deck/`, `scripts/extract-slides.mjs`, `dist/`). The family filename
contract does not require it; the prototype honors the `<section
data-label/data-speaker-notes>` extraction contract, so wiring the engine
later is a mechanical copy from `presentations/pyforge-warden/` plus
`npm run extract`.

## Ledger — 2026-09-13 facts re-derived (Story 20.12)

Facts-only re-derivation of the standalone poster (`spec-deck-family-currency` CAP-3, the
poster half of Story 20.12). This poster is the family's **structure, acts and length
reference**, so its arc, section order, diagrams and length are unchanged: every count,
version, status and date it prints is now a `data-fact` mark resolving to a row in
`facts.yaml`, re-derived at tree `6a49e9f223`. `deck-facts pyforge-unifying-strategy --check`
→ `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 9 unshown; facts 36/36`.

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Unifying Strategy Infographic standalone.html` | 132,338 B · 21 sections · 6 acts · 9 SVG · 4 grid-rendered tables (0 `<table>`) · facts 36/36 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) into the deck's own Design project `1e4020bc-7f7f-43b2-9219-0904d4863df6` (created and seeded the same day) · Design etag `1789307803346747` · 132,337 B on both sides · read back via `render_preview` → curl → harness strip: **byte-identical** to git` | rendered 2026-09-13, page 13,790 px; head + Infographic Deck: standalone ahead (lockstep slice pending) |

Floors (standard): act bands exactly six ✓ · numbered sections ≥ 18 (21) ✓ · inline SVG ≥ 3 (9) ✓ ·
bytes ≥ 90,000 ✓ · tables ≥ 3 — four **grid-rendered** equivalents (the 19-capability grid §05, the
thirteen-directive grid §12, the five-tier matrix §17, the which-surface-when grid §19); no `<table>`
element, which the standard allows ✓ · cast cards — this is a chain poster, not a station poster, so
the cast is the eight-station hero strip plus the hub-and-spoke topology, each station with role and
surface ✓ · facts all resolved ✓ · headless full-page PNG at 1240 px reviewed by eye in ~2500 px tiles
(`.herald/deck-qa/pyforge-unifying-strategy/`, gitignored) ✓ · offline apart from the Google Fonts
`<link>` ✓.

**Stale literals replaced with the ledger's current value:** masthead status
(`CAP-1..18 closed 2026-08-26 · CAP-19 live` → `Spec ready · CAP-1..19 · Dream specified`),
the capability-count chip and the Scope cell (`spec_capabilities`), the Owner cell (now carries
`steward_stories_done_total`, this chain's ledger proxy), and the Host cell (`Py 3.12` → `Py 3.14`,
the fixed floor in `stack.md`).

**Rewritten as prose because no ledger row exists for them** (never guessed, per the
derive-never-declare constraint): `40/40` (meta strip and the §17 heading), `1/8` (§01 stat),
the dated closeout claims (`closed 2026-08-26`, `Minted 2026-08-26`, `Live proof · CRC 2026-08-26`,
`OQ ruling · 2026-08-26`, `declared 2026-08-26`), the §15 timeline's own date chips (those entries
are archived out of the living Realization log, so they are re-labelled `Day one … Day four` and the
lede now cites the log's live `dream_log_*` rows instead), the MCP protocol revisions
(`2025-03-26 → 2026-07-28` → "the March 2025 revision through the July 2026 one"), the tier ids
`01/02`, and the third-party pins `mcp 2.0.0`, `liquibase 5.0.4+`, `cachebox`/`6.2.5`,
`vizro-ai 0.4.2` and `Django >=5.2.17,<6`. `poster_last_commit_date` is deliberately not printed.

**Design project:** created by the operator as **"PyForge Unifying Strategy deck"**
(`1e4020bc-7f7f-43b2-9219-0904d4863df6`, bound to Modernist
`fbc1d6c8-b35f-4df6-9044-a64d2675427b`) and seeded with the family. The push, read-back and the
canonical `## Design project` registry section are the operator's half of Story 20.12 and are not
written here.

## Ledger — 2026-09-13 (later) — Design-side visual pass pulled, Story 21.11

`spec-deck-family-lockstep` Story 21.11 ("one deck proves the Design loop end to end") worked
against this deck. A human visually improved the ★ head, the Executive Summary and the
Infographic Deck directly in Claude Design (not in this project — in a second, ad-hoc project
`13f845b0-4387-4a51-b1d4-304be61449a3` "PyForge Unifying Strategy" that predates and duplicates
this one, missing the Modernist `_ds/` binding, `deck-stage.js` and the `reference/` exemplar this
project carries). Operator decision: **this project (`1e4020bc`) stays canonical**; the improved
content was pulled from `13f845b0` and landed here instead of rebinding the registry.

Pulled via `render_preview` → curl the serve URL → strip the injected `data-omelette-injected`
harness (a prior pass at this recipe left one spurious blank line after `<head>`; fixed to
collapse the full injected-block gap, not just the first newline pair — verified byte-identical
read-back before and after the fix).

Design etag on all three of the Infographic/Executive-Summary/Infographic-Deck pushes:
`1789351538239239`; standalone's own etag after the marks-fix re-push: `1789352363599851`.

- `PyForge Unifying Strategy - Infographic.dc.html`: 129,936 B → **236,872 B**. ★ head's own body
  is no longer the standalone's body (Epic 21's own invariant) — the human's edit grew the head
  independently and neither `deck-trio` (Story 21.1/21.2) nor its reverse exists yet to reconcile
  them mechanically. Masthead rebranded **"Foundry Platform"** (was "The Canopy") — this README's
  own display-brand line above still says The Canopy; not changed here, an operator call.
- `PyForge Unifying Strategy - Executive Summary.dc.html`: 6,248 B → 6,478 B.
- `PyForge Unifying Strategy - Infographic Deck.dc.html`: 101,309 B → 121,107 B (landed from the
  Design-side file named `... v2.dc.html`; `v2` dropped on landing, this family doesn't version
  filenames).
- `PyForge Unifying Strategy Infographic standalone.html`: 132,337 B → **236,761 B**, mechanically
  derived from the new head (unwrap `<x-dc>`, move `<style>` into `<head>`, drop the
  `data-dc-script` marker and `support.js` tag) since `13f845b0` had no standalone file at all —
  the reverse of the normal head-from-standalone direction, done by hand per Story 21.11's own
  scope (proving the pull loop, not the trio-lockstep tooling). 23 sections, 7 act bands, 3 inline
  SVGs. Round-trip verified byte-identical against git twice (before and after the marks pass
  below).
- `PyForge Story.dc.html` (16,771 B, new): pulled alongside per operator decision; see the family
  table above.

**Marks pass** (operator-requested, real editorial work — not a rewrite of Epic 21's own
mark-derivation tooling): the fresh standalone regressed `deck-facts --check` from 0 unmarked/36
facts to **24 unmarked/facts 4/28**. Went through all 24 by hand, following this deck's own
already-established house style for exactly this situation (Django "5.2" not "5.2.17", cachebox
"6.2 line" not "6.2.5", liquibase "5.0 point release" not "5.0.4", vizro-ai "0.4 release" not
"0.4.2" — all already in the pre-pull content):

- 13 third-party version floors in the new §6 Integration Surface tool matrix, truncated
  `x.y.z` → `x.y` (Wagtail, mcp, Liquibase, DuckDB, Vizro, vizro-mcp, cocoindex, graphifyy,
  Langflow, DB-GPT, markitdown) plus two narrative mentions (`mcp` SDK, `vizro-ai`).
- The MCP protocol revision span rewritten `2025-03-26 → 2026-07-28` → "March 2025" / "July 2026",
  reusing this exact phrase from elsewhere in the same content.
- Three narrative dates dropped (no relative-day narrative to relabel to, unlike the archived
  closeout dates): "declared complete 2026-08-26" → "declared complete across all eight stations";
  the fastmcp-migration date; the live-escalation date.
- Nine bare fractions (`N/5` readiness scores ×8, `40/40 · 20/40` tiers) rewritten `/` → `of`, an
  alternate literal form already used throughout `facts.yaml`'s own `shown_as` lists — no
  information lost.

`deck-facts --check` now reports **3 unmarked**, each verified against its cited live source
before being left alone (none guessed, none invented): `SPEC.md`'s AD-1 datastores exception really
is dated 2026-09-11 (×2 mentions); `stack.md`'s own `updated:` stamp really is 2026-08-26; the
dossier filename and the token-economy catalog citation really do carry 2026-08-30. None has a
facts.yaml row — same "no ledger row exists" category this README already documents below for the
pre-pull content, just newly surfaced by the rebrand. Turning them into tracked facts means
extending `deck_facts.py`'s shared derivation code (used by all 15 decks); left as a follow-up, not
done here. The 11 `drifted` / 32 `unshown` findings are ordinary fleet-progress drift since this
deck's own last `--refresh`, unrelated to this pull.

**Not done this pass:** `Unifying Strategy Deck.dc.html` (untouched, no Design-side edit existed
for it); reconciling the head/standalone divergence properly (needs Story 21.1/21.2's `deck-trio`);
extending `--check`/`--refresh` to walk the head, Infographic Deck and exec summary too (Story
21.3); the display-brand line above (still "The Canopy") against the pulled content's own
"Foundry Platform" masthead.

## Design project (the bridge's far end)
Prototype lives in Claude Design project **"PyForge Unifying Strategy deck"** (`1e4020bc-7f7f-43b2-9219-0904d4863df6`):
https://claude.ai/design/p/1e4020bc-7f7f-43b2-9219-0904d4863df6?file=Unifying%20Strategy%20Deck.dc.html
