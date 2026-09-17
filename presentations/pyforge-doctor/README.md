# PyForge-Doctor deck (`pyforge.doctor`)

**Status: SCAFFOLD — prototype pending.** Engine + glue are in place (copied
**verbatim** from `presentations/pyforge-atlas/`, the Archivo persona system);
the Claude Design prototype has not been authored yet, so `src/slides/` holds an
empty `manifest.json` and no fragments.

A self-contained React + Vite slide deck for **PyForge-Doctor** — the Physician — ecosystem health & diagnostics officer of the PyForge
**"Dream to Code"** PyForge Guild (founding Dream:
`docs/dreams/pyforge-charter.md`). Motto: *"Check the vitals. Diagnose the fault. Keep the ecosystem alive."*

Built with the reusable **Design-to-Deck** workflow
(`docs/specs/presentation-deck.md` — read it first; it defines the prototype
contract, the pipeline, and the § Standard export set this deck must ship).

## Wiring the deck (when the prototype lands)

1. **Author the deck in Claude Design** at **1920×1080** following the prototype
   contract (each slide one `<section>` with `data-label`, `data-speaker-notes`,
   `style="background:#HEX; …"`). Use the family design system: Archivo /
   Archivo Expanded; light `#f3f2f2`, dark `#201e1d`, red `#ec3013` / `#c22a10`.
2. **Drop the handoff export** in `project/` as **`PyForge Doctor.dc.html`** (or update
   `SRC` in `scripts/extract-slides.mjs`; spaces in the name are fine).
3. `npm run extract` → fragments + manifest; `npm run dev` to review;
   `npm run build` for the offline `dist/`.
4. **Exports:** author the three Marp sources in `src/marp/`
   (`pyforge-doctor-deck-<date>.md`, `-executive-summary-<date>.md`, `-infographic-<date>.md`),
   then `pixi run -e local-recipes deck-export pyforge-doctor` regenerates the derived
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

Display brand **Doctor** on the slides; distribution slug `pyforge-doctor` in paths.
Engine files must stay **byte-identical** across every deck — apply any engine fix
to all decks in the same change (`diff -q` to prove it).

## Design project (the bridge's far end)
Prototype lives in Claude Design project **"PyForge Doctor deck"** (`46dbbdea-6f8d-45c6-9309-15d1f297beeb`):
https://claude.ai/design/p/46dbbdea-6f8d-45c6-9309-15d1f297beeb?file=PyForge%20Doctor.dc.html

## Ledger — 2026-09-13 standard rebuild (Story 20.4)

Rebuilt repo-side to `infographic-standard.md` (spec-deck-family-currency CAP-3) from
`facts.yaml` re-derived at tree `b5fe5e46fc`. Every count, version, status and date the
poster prints is a `data-fact` mark resolving to a ledger row; `deck-facts pyforge-doctor
--check` → `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 0 unshown; facts 85/85`.

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Doctor Infographic standalone.html` | 135,606 B · 24 sections (23 numbered + creed) · 6 acts · 4 SVG · 9 tables · facts 85/85 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) · Design etag `1789296846077989` · 135,606 B on both sides · read back 2026-09-13 via `render_preview` → curl → harness strip: **byte-identical** to git; refreshed and re-pushed the same day by the first currency sweep (`deck-facts <slug> --refresh`)` (operator pushes via DesignSync after review) | rendered 2026-09-13, page 20012 px; head + Infographic Deck derived 2026-09-15 via `deck-trio --head --deck` (Story 21.4 local sweep; Design push/read-back still pending) |

Floors (standard): acts exactly six ✓ · sections ≥ 18 ✓ · inline SVG ≥ 3 ✓ · bytes ≥ 90,000 ✓ ·
tables ≥ 3 ✓ · cast cards full for all eight stations ✓ · facts all resolved ✓ · headless
full-page PNG at 1240 px reviewed by eye (`.herald/deck-qa/pyforge-doctor/standalone.png`,
gitignored) ✓ · offline apart from the Google Fonts `<link>` ✓. No section of the standard's
set was dropped; the Warden "sub-agent team" slot is filled by Doctor's source registry (§06).
## Ledger — 2026-09-14 currency sweep (spec-deck-family-currency CAP-6)

The poster had gone stale on the fleet's own merges since the 2026-09-13 rebuild — 18 ledger
rows drifted (`doctor_epics_done_total`, `doctor_stories_done_total`, `epics_done_total`, `fleet_epics_done_total`, `fleet_stories_done_total`, `groundtruth_pixi_envs`, `herald_epics_done_total`, `herald_stories_done_total`, `marshal_epics_done_total`, `marshal_stories_done_total`, `mason_epics_done_total`, `mason_stories_done_total`, `scribe_epics_done_total`, `scribe_stories_done_total`, `steward_epics_done_total`, `steward_stories_done_total`, `stories_done_total`, `tree_commit_date`). Swept repo-side first, per CAP-6:
`pixi run -e local-recipes deck-facts pyforge-doctor --refresh --check` at tree `168bbedb13` re-derived
`facts.yaml` and rewrote **40** stale `data-fact` literals in place, keeping their shape; the
re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 0 unshown; facts 85/85`. Then the mirror (CAP-4): pushed via DesignSync `finalize_plan` →
`write_files` (`localPath`, no context relay) to project `46dbbdea-6f8d-45c6-9309-15d1f297beeb`, and read back through the
serve URL with the injected harness stripped — **byte-identical to disk**.

| Artifact | Bytes | Design etag | Read-back |
|---|---|---|---|
| `PyForge Doctor Infographic standalone.html` | 135,616 | `1789417185250666` | identical ✓ |

Not touched by this sweep (by design): the `- Infographic.dc.html` head and `- Infographic Deck.dc.html`
still carry the 2026-09-13 literals — deriving them from the standalone is herald Epic 21
(Stories 21.1–21.4), not a refresh.

## Ledger — 2026-09-15 infographic trio re-derived (Story 21.4)

`pixi run -e local-recipes deck-trio pyforge-doctor --head --deck` at tree `a407cd03f6`
mechanically re-derived both files from the standalone (x-dc/helmet wrap, verbatim
`<style>`/`<link>` relocation, a measured `$preview` height for the head; masthead/act-band/
numbered-section/closing-band slides for the deck): `PyForge Doctor - Infographic.dc.html` now
135,741 B, `PyForge Doctor - Infographic Deck.dc.html` now 142,010 B. A second `--head --deck`
run changed nothing on disk (verified).

`pixi run -e local-recipes deck-facts pyforge-doctor --refresh` then `--check` at the same tree
brought poster, head and Infographic Deck current: **36** stale `data-fact` literals rewritten
(`fleet_epics_done_total`, `fleet_stories_done_total`, `herald_epics_done_total`,
`herald_stories_done_total`, `poster_last_commit_date`, `tree_commit_date` — drift since the
2026-09-14 sweep); re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 0 unshown;
facts 255/255`.

**Design push/read-back: not performed this session — no working credential.**
`~/.claude/.credentials.json` has no `designOauth` block, and the `claude-design` MCP connector
independently reports `FIRST_PARTY_AUTH_REJECTED` (HTTP 403) this session; re-probed live via
`pixi run -e pyforge-herald herald deck push pyforge-warden` → `AuthError: ... has no
'designOauth' block -- run /design-login in Claude Code to refresh it` (one shared credential
file, so this applies identically to every deck — not re-probed per deck). No push attempted, no
etag fabricated. The pre-push gap narrowed to: head + Infographic Deck are now re-derived and
facts-current on disk, not yet mirrored to Design.

## Ledger — 2026-09-17 push + read-back (Story 21.4)

`pyforge-herald`'s `mcp` 2.2.0 transport symbol drift (Story 21.12) is fixed and merged, so the
credential blocker above is resolved: `resolve_design_credential()` succeeds this session. Pushed
via `pyforge.herald.transport.mcp_transport.McpTransport` directly (`finalize_plan` →
`write_files`, inline `data` — `write_files`'s `local_path` field is not implemented
server-side today, so `herald deck push`'s own CLI verb, which covers only the CAP-5
marp-regenerated export, doesn't reach these `project/` trio files) to project
`46dbbdea-6f8d-45c6-9309-15d1f297beeb`, then read back and SHA-256-compared against disk:

| Artifact | Bytes | Design etag | Read-back |
|---|---|---|---|
| `PyForge Doctor - Infographic.dc.html` | 135,741 | `1789635943489853` | identical ✓ |
| `PyForge Doctor - Infographic Deck.dc.html` | 142,010 | `1789635945178614` | identical ✓ |

Both files are under the 256 KiB `read_file` cap, so a single call plus entity-decoded SHA-256
comparison is the read-back proof (no windowing needed). `deck-facts pyforge-doctor --check`
still reads 0 mismatch. Head and Infographic Deck now match Design as well as disk — no surface
here is standalone-ahead any more.
