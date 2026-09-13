# PyForge-Herald deck (`pyforge.herald`)

**Status: SCAFFOLD — prototype pending.** Engine + glue are in place (copied
**verbatim** from `presentations/pyforge-atlas/`, the Archivo persona system);
the Claude Design prototype has not been authored yet, so `src/slides/` holds an
empty `manifest.json` and no fragments.

A self-contained React + Vite slide deck for **PyForge-Herald** — the Proclaimer — visual media, presentation & communications engine of the PyForge
**"Dream to Code"** PyForge Guild (founding Dream:
`docs/dreams/pyforge-charter.md`). Motto: *"Capture the dream. Illustrate the telemetry. Proclaim the release."*

Built with the reusable **Design-to-Deck** workflow
(`docs/specs/presentation-deck.md` — read it first; it defines the prototype
contract, the pipeline, and the § Standard export set this deck must ship).

## Wiring the deck (when the prototype lands)

1. **Author the deck in Claude Design** at **1920×1080** following the prototype
   contract (each slide one `<section>` with `data-label`, `data-speaker-notes`,
   `style="background:#HEX; …"`). Use the family design system: Archivo /
   Archivo Expanded; light `#f3f2f2`, dark `#201e1d`, red `#ec3013` / `#c22a10`.
2. **Drop the handoff export** in `project/` as **`PyForge Herald.dc.html`** (or update
   `SRC` in `scripts/extract-slides.mjs`; spaces in the name are fine).
3. `npm run extract` → fragments + manifest; `npm run dev` to review;
   `npm run build` for the offline `dist/`.
4. **Exports:** author the three Marp sources in `src/marp/`
   (`pyforge-herald-deck-<date>.md`, `-executive-summary-<date>.md`, `-infographic-<date>.md`),
   then `pixi run -e local-recipes deck-export pyforge-herald` regenerates the derived
   standalone HTML + PPTX (§ Standard export set).

## Quick start

```
npm install
npm approve-scripts esbuild && npm rebuild esbuild   # npm 11+ blocks esbuild's install script
npm run extract && npm run dev
```

## Keymap

`→`/`Space`/`PgDn` next · `←`/`PgUp` prev · `Home`/`End` first/last · `O` overview ·
`S` presenter (notes + timer) · `F` fullscreen · `?` help · `Esc` back. Slide index
mirrors to the URL hash (`#/12`).

Display brand **Herald** on the slides; distribution slug `pyforge-herald` in paths.
Engine files must stay **byte-identical** across every deck — apply any engine fix
to all decks in the same change (`diff -q` to prove it).

## Design project (the bridge's far end)

Prototype lives in Claude Design project **"PyForge Herald deck"** (`ff879a32-9741-4cf5-948f-d67040481d24`):
https://claude.ai/design/p/ff879a32-9741-4cf5-948f-d67040481d24?file=PyForge+Herald.dc.html
Pull it into this deck with the MCP bridge ("pull herald") — see
`docs/specs/presentation-deck.md` § *The MCP bridge*.

## Ledger — 2026-09-13 standard rebuild (Story 20.5)

Rebuilt repo-side to `spec-deck-family-currency/infographic-standard.md` from
`facts.yaml` (tree `b5fe5e46fc`, re-derived on the clean branch point before authoring;
40 rows). Every count, version, status and date the poster prints is a `data-fact` mark
resolving to a row; numbers with no row (drift sizes, stub counts, test counts, dates outside
the ledger's date rows) were left out rather than guessed. No section of the standard's set was
dropped; names were adapted per subject (23 numbered sections `01`–`23` plus the creed band).

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Herald Infographic standalone.html` | 137,557 B · 24 sections (23 numbered + creed) · 6 acts · 4 SVG · 6 tables · facts 53/53 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) · Design etag `1789296209988819` · 137,557 B on both sides · read back 2026-09-13 via `render_preview` → curl → harness strip: **byte-identical** to git` (operator pushes via DesignSync after review) | rendered 2026-09-13, page 17,802 px; head + Infographic Deck: standalone ahead (lockstep slice pending) |

Floors (`infographic-standard.md`): act bands 6/6 · sections 24 ≥ 18 · inline SVG 4 ≥ 3 ·
bytes 137,557 ≥ 90,000 · tables 6 ≥ 3 · cast: eight full cards (role, motto, paragraph, CLI
verbs, stories + epics chips) · facts: `deck-facts pyforge-herald --check` →
`0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 53/53` (the unshown row is
`poster_last_commit_date`, deliberately not printed: it names the poster's own last commit and
would drift the moment this rebuild merges) · render: headless Chromium at 1240 px, full-page
PNG reviewed in six slices, no clipped or blank region · offline: Google Fonts `<link>` is the
only remote resource, system fallback declared, no external scripts, no `<x-dc>` wrapper,
inline SVG only.

Design mirror (CAP-4) not yet pushed in this PR — the etag cell above is filled by the operator
after the DesignSync `finalize_plan` → `write_files` (`localPath`) push and byte-identical
read-back; `herald deck status pyforge-herald` linked in Story 20.13.
