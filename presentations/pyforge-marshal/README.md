# PyForge-Marshal deck (`pyforge.marshal`)

**Status: FULL FAMILY — the ecosystem chapter deck.** 26-slide prototype
(six-act arc, 2026-07-31 generation) extracted and built; the complete
five-artifact Design family is current (deck · infographic · Infographic Deck ·
standalone · exec summary). Since the genesis fold, this family carries the
whole big picture: the Charter, the Guild, the Dream-to-Code operating model.
Content standard: full-depth warden-pattern sections with acts — see the
per-deck ledger below. Narration extracts + the master ecosystem script live in
`src/marp/` (inputs for `bmad-manticore` video production).

A self-contained React + Vite slide deck for **PyForge-Marshal** — the Commander — autonomous build-factory supervisor & BMAD-method orchestrator of the PyForge
**"Dream to Code"** PyForge Guild (founding Dream:
`docs/dreams/pyforge-charter.md`). Motto: *"Enforce the spec. Guard the boundaries. Run the line."*

Built with the reusable **Design-to-Deck** workflow
(`docs/specs/presentation-deck.md` — read it first; it defines the prototype
contract, the pipeline, and the § Standard export set this deck must ship).

## Wiring the deck (when the prototype lands)

1. **Author the deck in Claude Design** at **1920×1080** following the prototype
   contract (each slide one `<section>` with `data-label`, `data-speaker-notes`,
   `style="background:#HEX; …"`). Use the family design system: Archivo /
   Archivo Expanded; light `#f3f2f2`, dark `#201e1d`, red `#ec3013` / `#c22a10`.
2. **Drop the handoff export** in `project/` as **`PyForge Marshal.dc.html`** (or update
   `SRC` in `scripts/extract-slides.mjs`; spaces in the name are fine).
3. `npm run extract` → fragments + manifest; `npm run dev` to review;
   `npm run build` for the offline `dist/`.
4. **Exports:** author the three Marp sources in `src/marp/`
   (`pyforge-marshal-deck-<date>.md`, `-executive-summary-<date>.md`, `-infographic-<date>.md`),
   then `pixi run -e local-recipes deck-export pyforge-marshal` regenerates the derived
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

Display brand **Marshal** on the slides; distribution slug `pyforge-marshal` in paths.
Engine files must stay **byte-identical** across every deck — apply any engine fix
to all decks in the same change (`diff -q` to prove it).

## Design project (the bridge's far end)
Prototype lives in Claude Design project **"PyForge Marshal deck"** (`ad84d4f6-c292-42c8-98bf-ede78a567773`):
https://claude.ai/design/p/ad84d4f6-c292-42c8-98bf-ede78a567773?file=PyForge%20Marshal.dc.html

## Ledger — 2026-07-31 six-act rebuild (Design ↔ repo sync)

| Artifact | Slides/size | Design etag |
|---|---|---|
| `PyForge Marshal.dc.html` | 26 slides · 100,631 B | `1785555947450949` |
| `PyForge Marshal - Infographic.dc.html` | 19 sections + 6 acts · 91,060 B | `1785551674739328` |
| `PyForge Marshal Infographic standalone.html` | body-identical mirror | `1785551674739328` |
| `PyForge Marshal - Infographic Deck.dc.html` | 20 slides · 90,658 B | `1785556512103907` |
| `PyForge Marshal - Executive Summary.dc.html` | 1080p one-shot, stats refreshed | `1785556555212786` |

Authored repo-side this generation (inverted from the usual Design-first flow);
pushed byte-for-byte via the DesignSync localPath pipeline. On the next
Design-side edit session, finish with a byte-exact pull per
`docs/specs/presentation-deck.md` § the MCP bridge.

## Ledger — 2026-09-13 standard rebuild (Story 20.6)

Re-derived to `infographic-standard.md` (spec-deck-family-currency CAP-1..3) from
`presentations/pyforge-marshal/facts.yaml` (`pixi run -e local-recipes deck-facts pyforge-marshal
--with-tests`, re-derived on the clean tree of the commit that landed this poster — the ledger's
`tree:` names it, following the 20.2 convention of deriving on the parent commit). The 2026-07-31 six-act arc and its 19-section order are kept;
every count, version, status and date is now a `data-fact` mark resolving to a ledger row — the
July claims (`bmad-method 6.10.0`, `bmad-loop 0.9.0`, "128/333 fleet-wide", "Epic 1 · 10/10",
the per-station July chips, "785 tests", the stack table's module versions) are gone. Dropped for
lack of a fact row: the stack table's per-module versions for BMB / TEA / CIS / SKF / pyforge-core
(column shows `—`; only `bmad_core_version`, `bmad_loop_version`, `cfe_skill_version`,
`package_version` print), the "10 detectors" / "51 skills" / "16 skf" counts, the "8 concurrent
homes" numeral (now "one home per station"), and `bmad-dashboard` (retired console). Sections
kept in full: no section of the standard's set was dropped.

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Marshal Infographic standalone.html` | 112,843 B · 19 sections (21 `<section` incl. doctrine + creed bands) · 6 acts · 4 SVG · 6 tables · facts 128/128 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) · Design etag `1789296212120129` · 112,843 B on both sides · read back 2026-09-13 via `render_preview` → curl → harness strip: **byte-identical** to git; refreshed and re-pushed the same day by the first currency sweep (`deck-facts <slug> --refresh`)` (operator pushes via DesignSync after review) | rendered 2026-09-13 at 1240 px, page 16,427 px, no clipped or blank region; `deck-facts pyforge-marshal --check` → `0 unmarked, 0 mismatch, 0 drifted, 1 unsourced (tests_collected, --with-tests only), 0 unshown`; head + Infographic Deck derived 2026-09-15 via `deck-trio --head --deck` (Story 21.4 local sweep; Design push/read-back still pending) |

Floors: act bands 6/6 · sections 19 ≥ 18 · inline SVGs 4 ≥ 3 · bytes 112,843 ≥ 90,000 · tables
6 ≥ 3 · cast cards 8/8 full (role, motto, paragraph, verbs, stories + epics chips) · render
reviewed as eight 2100 px slices. Render artifacts live under the gitignored
`.herald/deck-qa/pyforge-marshal/`.
## Ledger — 2026-09-14 currency sweep (spec-deck-family-currency CAP-6)

The poster had gone stale on the fleet's own merges since the 2026-09-13 rebuild — 18 ledger
rows drifted (`doctor_epics_done_total`, `doctor_stories_done_total`, `epics_done_total`, `fleet_epics_done_total`, `fleet_stories_done_total`, `groundtruth_pixi_envs`, `herald_epics_done_total`, `herald_stories_done_total`, `marshal_epics_done_total`, `marshal_stories_done_total`, `mason_epics_done_total`, `mason_stories_done_total`, `scribe_epics_done_total`, `scribe_stories_done_total`, `steward_epics_done_total`, `steward_stories_done_total`, `stories_done_total`, `tree_commit_date`). Swept repo-side first, per CAP-6:
`pixi run -e local-recipes deck-facts pyforge-marshal --refresh --check `--with-tests`` at tree `168bbedb13` re-derived
`facts.yaml` and rewrote **56** stale `data-fact` literals in place, keeping their shape; the
re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 0 unshown; facts 128/128`. Then the mirror (CAP-4): pushed via DesignSync `finalize_plan` →
`write_files` (`localPath`, no context relay) to project `ad84d4f6-c292-42c8-98bf-ede78a567773`, and read back through the
serve URL with the injected harness stripped — **byte-identical to disk**.

| Artifact | Bytes | Design etag | Read-back |
|---|---|---|---|
| `PyForge Marshal Infographic standalone.html` | 112,851 | `1789417220069499` | identical ✓ |

Not touched by this sweep (by design): the `- Infographic.dc.html` head and `- Infographic Deck.dc.html`
still carry the 2026-09-13 literals — deriving them from the standalone is herald Epic 21
(Stories 21.1–21.4), not a refresh.

## Ledger — 2026-09-15 infographic head re-derived; deck blocked (Story 21.4)

`pixi run -e local-recipes deck-trio pyforge-marshal --head` at tree `a407cd03f6` mechanically
re-derived the head from the standalone (x-dc/helmet wrap, verbatim `<style>`/`<link>`
relocation, a measured `$preview` height): `PyForge Marshal - Infographic.dc.html` now 112,992 B.
A second `--head` run changed nothing on disk (verified). `--deck` refuses per **DW-4** (open,
`_bmad-output/implementation-artifacts/deferred-work.md:522`): `no <section class="sec">
elements found` — this poster's 19 sections are inline-styled divs, not `section.sec`; the
pre-existing `- Infographic Deck.dc.html` on disk is untouched (not re-derived, not regressed).
Widening the selector or re-authoring the poster is out of this story's Code Map.

`pixi run -e local-recipes deck-facts pyforge-marshal --refresh` then `--check` at the same tree
rewrote **30** stale `data-fact` literals across poster and head (`fleet_epics_done_total`,
`fleet_stories_done_total`, `herald_epics_done_total`, `herald_stories_done_total`,
`poster_last_commit_date`, `tree_commit_date` — drift since the 2026-09-14 sweep). Because a
plain `--refresh` omits `tests_collected` (only derived under `--with-tests`), that first
`--check` flagged the deck's 10 pre-existing `tests_collected` marks (5 on the poster, inherited
onto the freshly-derived head) as `mismatch … no such row in facts.yaml` — a regression from
this deck's established convention (the 2026-09-13 ledger's `1 unsourced (tests_collected,
--with-tests only)`, not a `mismatch`). Re-ran `deck-facts pyforge-marshal --refresh
--with-tests` (pytest `--collect-only` over `pyforge-marshal`'s own suite; count unchanged at
7934) to restore the persisted row. Final re-check reads `0 unmarked, 0 mismatch, 0 drifted, 1
unsourced, 0 unshown; facts 256/256` — the intended state restored, not a new gap.

**Design push/read-back: not performed this session — no working credential.**
`~/.claude/.credentials.json` has no `designOauth` block, and the `claude-design` MCP connector
independently reports `FIRST_PARTY_AUTH_REJECTED` (HTTP 403) this session; re-probed live via
`pixi run -e pyforge-herald herald deck push pyforge-warden` → `AuthError: ... has no
'designOauth' block -- run /design-login in Claude Code to refresh it` (one shared credential
file, so this applies identically to every deck — not re-probed per deck). No push attempted, no
etag fabricated. "Standalone ahead" narrows to: the head is now re-derived and facts-current on
disk, not yet mirrored to Design; the Infographic Deck remains blocked on DW-4, unrelated to the
credential.
