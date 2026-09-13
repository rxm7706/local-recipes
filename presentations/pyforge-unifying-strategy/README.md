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
  Unifying Strategy Deck.dc.html                       28-slide narrative deck prototype (six acts)
  PyForge Unifying Strategy - Executive Summary.dc.html  one-page 1920×1080 exec summary
  PyForge Unifying Strategy - Infographic.dc.html        ★ the trio head — 19-section one-pager, 3 inline-SVG diagrams
  PyForge Unifying Strategy - Infographic Deck.dc.html   the same story re-laid as 27 slides
  PyForge Unifying Strategy Infographic standalone.html  same body as ★, no x-dc wrapper, styles in <head>
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
