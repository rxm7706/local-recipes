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
https://claude.ai/design/p/ff879a32-9741-4cf5-948f-d67040481d24?file=PyForge%20Herald.dc.html

## Ledger — 2026-09-13 standard rebuild (Story 20.5)

Rebuilt repo-side to `spec-deck-family-currency/infographic-standard.md` from
`facts.yaml` (tree `b5fe5e46fc`, re-derived on the clean branch point before authoring;
40 rows). Every count, version, status and date the poster prints is a `data-fact` mark
resolving to a row; numbers with no row (drift sizes, stub counts, test counts, dates outside
the ledger's date rows) were left out rather than guessed. No section of the standard's set was
dropped; names were adapted per subject (23 numbered sections `01`–`23` plus the creed band).

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Herald Infographic standalone.html` | 137,557 B · 24 sections (23 numbered + creed) · 6 acts · 4 SVG · 6 tables · facts 53/53 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) · Design etag `1789296209988819` · 137,557 B on both sides · read back 2026-09-13 via `render_preview` → curl → harness strip: **byte-identical** to git; refreshed and re-pushed the same day by the first currency sweep (`deck-facts <slug> --refresh`)` (operator pushes via DesignSync after review) | rendered 2026-09-13, page 17,802 px; head + Infographic Deck derived 2026-09-15 via `deck-trio --head --deck` (Story 21.4 local sweep; Design push/read-back still pending) |

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
## Ledger — 2026-09-14 currency sweep (spec-deck-family-currency CAP-6)

The poster had gone stale on the fleet's own merges since the 2026-09-13 rebuild — 18 ledger
rows drifted (`doctor_epics_done_total`, `doctor_stories_done_total`, `epics_done_total`, `fleet_epics_done_total`, `fleet_stories_done_total`, `groundtruth_pixi_envs`, `herald_epics_done_total`, `herald_stories_done_total`, `marshal_epics_done_total`, `marshal_stories_done_total`, `mason_epics_done_total`, `mason_stories_done_total`, `scribe_epics_done_total`, `scribe_stories_done_total`, `steward_epics_done_total`, `steward_stories_done_total`, `stories_done_total`, `tree_commit_date`). Swept repo-side first, per CAP-6:
`pixi run -e local-recipes deck-facts pyforge-herald --refresh --check` at tree `168bbedb13` re-derived
`facts.yaml` and rewrote **21** stale `data-fact` literals in place, keeping their shape; the
re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 53/53`. Then the mirror (CAP-4): pushed via DesignSync `finalize_plan` →
`write_files` (`localPath`, no context relay) to project `ff879a32-9741-4cf5-948f-d67040481d24`, and read back through the
serve URL with the injected harness stripped — **byte-identical to disk**.

| Artifact | Bytes | Design etag | Read-back |
|---|---|---|---|
| `PyForge Herald Infographic standalone.html` | 137,560 | `1789417210958518` | identical ✓ |

Not touched by this sweep (by design): the `- Infographic.dc.html` head and `- Infographic Deck.dc.html`
still carry the 2026-09-13 literals — deriving them from the standalone is herald Epic 21
(Stories 21.1–21.4), not a refresh.

## Ledger — 2026-09-15 infographic head re-derived; deck blocked (Story 21.4)

`pixi run -e local-recipes deck-trio pyforge-herald --head` at tree `a407cd03f6` mechanically
re-derived the head from the standalone (x-dc/helmet wrap, verbatim `<style>`/`<link>`
relocation, a measured `$preview` height): `PyForge Herald - Infographic.dc.html` now 137,686 B.
A second `--head` run changed nothing on disk (verified). `--deck` refuses per **DW-4** (open,
`_bmad-output/implementation-artifacts/deferred-work.md:522`): `no <div class="act"> bands
found` — this poster carries no act-band markup at all; there is no pre-existing `- Infographic
Deck.dc.html` on disk for this deck. Widening the selector or re-authoring the poster is out of
this story's Code Map.

`pixi run -e local-recipes deck-facts pyforge-herald --refresh` then `--check` at the same tree
brought poster and head current: **20** stale `data-fact` literals rewritten
(`epics_done_total`, `fleet_epics_done_total`, `fleet_stories_done_total`,
`herald_epics_done_total`, `herald_stories_done_total`, `stories_done_total`, `tree_commit_date`
— drift since the 2026-09-14 sweep); re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0
unsourced, 1 unshown; facts 106/106`.

**Design push/read-back: not performed this session — no working credential.**
`~/.claude/.credentials.json` has no `designOauth` block, and the `claude-design` MCP connector
independently reports `FIRST_PARTY_AUTH_REJECTED` (HTTP 403) this session; re-probed live via
`pixi run -e pyforge-herald herald deck push pyforge-warden` → `AuthError: ... has no
'designOauth' block -- run /design-login in Claude Code to refresh it` (one shared credential
file, so this applies identically to every deck — not re-probed per deck). No push attempted, no
etag fabricated. "Standalone ahead" narrows to: the head is now re-derived and facts-current on
disk, not yet mirrored to Design; the Infographic Deck remains blocked on DW-4, unrelated to the
credential.
