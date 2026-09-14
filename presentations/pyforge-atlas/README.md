# PyForge-Atlas deck (`pyforge.atlas`)

A self-contained React + Vite slide deck for **PyForge-Atlas** — the conda-forge
intelligence layer being migrated from a hand-rolled ~10,000-LOC orchestrator to
declarative **Kedro + Dagster + DuckDB** dataflow, with a Boring Semantic Layer,
a Vizro / Vizro-AI read surface, and MCP / A2A agent interfaces. Built with the
reusable **Design-to-Deck** workflow (`docs/specs/presentation-deck.md`); the
deck **engine** (`src/deck/*`) and glue are copied verbatim from
`presentations/pyforge-warden/`, so only the **prototype** and the **generated**
`src/slides/fragments/` + `manifest.json` are PyForge-Atlas-specific.

The slide content lives in the Claude Design prototype at
`project/PyForge Atlas.dc.html`; the fragments and manifest are generated from
it by `npm run extract` and are already committed here (21 slides, 5 acts).

## Quick start

```
npm install
npm approve-scripts esbuild && npm rebuild esbuild   # npm 11+ blocks esbuild's install script
npm run extract    # prototype -> src/slides/fragments/*.html + manifest.json
npm run dev        # review at localhost:5173
npm run build      # static, offline-safe dist/
```

`extract` is plain Node (no esbuild) and runs without the approve-scripts step.
`dev`/`build` need it once per clone; commit the `allowScripts` entry + lockfile.

## Bringing in / updating the deck

1. **Author the deck in Claude Design** at **1920×1080**, following the
   *prototype contract* in `docs/specs/presentation-deck.md`: each slide is one
   `<section>` carrying `data-label="…"`, `data-speaker-notes="…"`, and
   `style="background:#HEX; …"` (first `#hex` = slide background); inline styles;
   footers `PYFORGE-ATLAS · <TAG>` left, `NN / TT` right. Each slide's inner is a
   full-frame root `<div>` (the extractor keeps only the section inner, rendered
   into a padding-less `1920×1080` frame).
2. **Export the handoff `.dc.html`** and drop it in **`project/`**, named
   **`PyForge Atlas.dc.html`** (or rename `SRC` at the top of
   `scripts/extract-slides.mjs` to match your filename — spaces are fine).
3. **Extract → build:** `npm run extract` (→ 21 fragments + manifest),
   then `npm run dev` to review or `npm run build` for `dist/`.
4. **(Optional) exports:** keep a Marp `.marp.md` mirror in `src/marp/` and a
   dated PowerPoint `src/pptx/pyforge-atlas-YYYY-MM-DD.pptx`.

## Keymap

| Key | Action |
|---|---|
| `→` · `Space` · `PgDn` | Next slide |
| `←` · `PgUp` | Previous |
| `Home` · `End` | First / last |
| `O` | Overview grid |
| `S` | Presenter view (notes + timer) |
| `F` | Fullscreen |
| `?` | Keyboard cheat-sheet |
| `Esc` | Back to the deck |

The current slide mirrors to the URL hash (`#/12`) — every slide is
deep-linkable and reload-stable.

## How it's structured

- **`src/deck/*`, `src/slides/index.js`, `vite.config.js`, `src/main.jsx`,
  `src/App.jsx`, `src/index.css`, `.gitignore`** — the topic-agnostic engine +
  glue, copied **verbatim** from `pyforge-warden`. Keep byte-identical across
  decks; any engine fix lands in every copy in the same change.
- **`index.html`** — per-deck title/description + the Archivo Google-Fonts link.
- **`scripts/extract-slides.mjs`** — topic-agnostic extractor; only its `SRC`
  (prototype filename) and `BANNER_MAP` are per-deck (`BANNER_MAP = {}` here —
  the prototype references no remote images, so `dist/` is fully offline bar
  Google Fonts).
- **`project/`** — the design handoff (`PyForge Atlas.dc.html` + its
  `deck-stage.js` / `support.js` design-time runtime).
- **`src/slides/fragments/` + `manifest.json`** — **generated** by `extract`;
  never hand-edit (they're overwritten). Content lives in the prototype.

## Act structure (21 slides)

Cover · **Act I** From monolith to DAG (problem · before/after · seven pipelines)
· **Act II** Node-shaped & agent-maintainable (add phase 24 · what it buys ·
verify-first gate) · **Act III** An agent workforce builds it (who runs it ·
graduated autonomy · eight waves · which surface) · **Act IV** New signals
(Basilisk / velocity / readiness · open questions) · **Act V** The read surface
inverts (five surfaces · the PyForge family) · closing statement.

Design brand **Atlas** on the slides; distribution slug `pyforge-atlas` in paths.
Palette is Modernist — light `#f3f2f2`, dark `#201e1d`, red `#ec3013` / `#c22a10`
— matching the `pyforge-warden` deck so the two sit next to each other.

## Design project (the bridge's far end)
Prototype lives in Claude Design project **"PyForge Atlas deck"** (`2acb0575-9997-442b-bb0e-6207d78f6648`):
https://claude.ai/design/p/2acb0575-9997-442b-bb0e-6207d78f6648?file=PyForge%20Atlas.dc.html

### Provenance

Created and seeded 2026-07-24 — the deck predates the bridge pilot, so it had no Design
project until then. Bound to the Modernist design system.

### Artifact map + sync ledger (2026-07-24, disk → Design seed)

- `PyForge Atlas.dc.html` (75448, `1784892835897059`) — **byte-identical to
  disk** ✓ (uploaded via DesignSync `localPath`, no context relay)
- `support.js` (66404, `1784890273511358`) — server-written current runtime,
  matches disk byte count
- `deck-stage.js` (133230, `1784890278864518`) — server-side copy from the
  genesis project (byte count matches disk)
- `PyForge Atlas - Executive Summary.dc.html` (7656) +
  `src/marp/pyforge-atlas-{deck,executive-summary,infographic}-2026-07-24.md`
  — batch etag `1784893549439075`

Disk-side only (stay git-side): `src/pptx/*.pptx`, the infographic standalone,
the built React deck. Convention: Design project name ↔ this folder.

## Ledger — 2026-09-13 standard rebuild (Story 20.3)

Rebuilt repo-side to `infographic-standard.md` (spec-deck-family-currency CAP-1/CAP-3) from
`facts.yaml` re-derived at tree `b5fe5e46fc` (`pixi run -e local-recipes deck-facts pyforge-atlas`).
Every count, version, status and date on the poster is a `data-fact` mark resolving to a ledger
row; `deck-facts pyforge-atlas --check` → `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced,
1 unshown; facts 77/77` (the one unshown row is `poster_last_commit_date`, left off on purpose —
it goes stale on the very commit that lands the poster).

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Atlas Infographic standalone.html` | 132,410 B · 23 `<section` (22 numbered + creed) · 6 acts · 4 SVG · 8 tables · facts 77/77 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) · Design etag `1789296808981454` · 132,410 B on both sides · read back 2026-09-13 via `render_preview` → curl → harness strip: **byte-identical** to git; refreshed and re-pushed the same day by the first currency sweep (`deck-facts <slug> --refresh`)` | rendered 2026-09-13, page 20835 px (1240 px wide, headless Chromium, no clipped/blank region, 0 overflowing elements); head + Infographic Deck: standalone ahead (lockstep slice pending) |

Against the floors: acts 6/6 · sections 22 ≥ 18 · inline SVG 4 ≥ 3 · bytes 132,410 ≥ 90,000 ·
tables 8 ≥ 3 · cast: eight full station cards (role, motto, paragraph, CLI verbs, ledger chips) ·
offline: only the Google Fonts `<link>` is remote; no `<x-dc>`, no `support.js`, no scripts, no
raster images. No section of the standard's set was dropped (the contract-at-a-glance and
workforce sections are additions, numbered in sequence). Ledger correction recorded here:
`recipes_count` derives to 7864 on the clean tree (an earlier derivation on an unclean checkout
read 7872 — untracked local recipe dirs). Full-page PNG: `.herald/deck-qa/pyforge-atlas/standalone.png`
(gitignored). Mirror push (CAP-4) is the operator's step: after review, `DesignSync finalize_plan →
write_files (localPath)` to project `2acb0575-9997-442b-bb0e-6207d78f6648`, then record the etag here.
## Ledger — 2026-09-14 currency sweep (spec-deck-family-currency CAP-6)

The poster had gone stale on the fleet's own merges since the 2026-09-13 rebuild — 16 ledger
rows drifted (`doctor_epics_done_total`, `doctor_stories_done_total`, `fleet_epics_done_total`, `fleet_stories_done_total`, `groundtruth_pixi_envs`, `herald_epics_done_total`, `herald_stories_done_total`, `marshal_epics_done_total`, `marshal_stories_done_total`, `mason_epics_done_total`, `mason_stories_done_total`, `scribe_epics_done_total`, `scribe_stories_done_total`, `steward_epics_done_total`, `steward_stories_done_total`, `tree_commit_date`). Swept repo-side first, per CAP-6:
`pixi run -e local-recipes deck-facts pyforge-atlas --refresh --check` at tree `168bbedb13` re-derived
`facts.yaml` and rewrote **20** stale `data-fact` literals in place, keeping their shape; the
re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 77/77`. Then the mirror (CAP-4): pushed via DesignSync `finalize_plan` →
`write_files` (`localPath`, no context relay) to project `2acb0575-9997-442b-bb0e-6207d78f6648`, and read back through the
serve URL with the injected harness stripped — **byte-identical to disk**.

| Artifact | Bytes | Design etag | Read-back |
|---|---|---|---|
| `PyForge Atlas Infographic standalone.html` | 132,413 | `1789417170414785` | identical ✓ |

Not touched by this sweep (by design): the `- Infographic.dc.html` head and `- Infographic Deck.dc.html`
still carry the 2026-09-13 literals — deriving them from the standalone is herald Epic 21
(Stories 21.1–21.4), not a refresh.
