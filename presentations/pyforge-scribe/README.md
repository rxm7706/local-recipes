# PyForge-Scribe deck (`pyforge.scribe`)

**Status: STARTER — awaiting the Design pass.** Engine + glue copied **verbatim**
from `presentations/pyforge-atlas/` (Archivo / Modernist system). A chapter deck
of the founding Dream (`docs/dreams/pyforge-charter.md`); persona Dream:
`docs/dreams/pyforge-scribe.md`. Motto: *"Capture the decision. Keep the graph. Answer from memory."*

Workflow: `docs/specs/presentation-deck.md` (prototype contract, § Standard
export set, § The MCP bridge). `npm install && npm run extract && npm run dev`.
Engine files stay byte-identical across every deck.

## Design project (the bridge's far end)
Prototype lives in Claude Design project **"PyForge Scribe deck"** (`a1e42dac-7cee-438b-9acc-2523985b5253`):
https://claude.ai/design/p/a1e42dac-7cee-438b-9acc-2523985b5253?file=PyForge%20Scribe.dc.html

## Ledger — 2026-09-13 standard rebuild (Story 20.8)

Rebuilt repo-side to `infographic-standard.md` (spec-deck-family-currency CAP-3) from
`facts.yaml` re-derived at tree `fbefe6eea6`. Every count, version, status and date the
poster prints is a `data-fact` mark resolving to a ledger row; `deck-facts pyforge-scribe
--check` → `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 95/95` (the one
unshown row is `poster_last_commit_date`, deliberately not printed on the poster).

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Scribe Infographic standalone.html` | 144,946 B · 24 sections (23 numbered + creed) · 6 acts · 4 SVG · 9 tables · facts 95/95 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) · Design etag `1789300368983561` · 144,946 B on both sides · read back 2026-09-13 via `render_preview` → curl → harness strip: **byte-identical** to git; refreshed and re-pushed the same day by the first currency sweep (`deck-facts <slug> --refresh`)` (operator pushes via DesignSync after review) | rendered 2026-09-13, page 21684 px; head + Infographic Deck: standalone ahead (lockstep slice pending) |

Floors (standard): acts exactly six ✓ · sections ≥ 18 ✓ · inline SVG ≥ 3 ✓ · bytes ≥ 90,000 ✓ ·
tables ≥ 3 ✓ · cast cards full for all eight stations ✓ · facts all resolved ✓ · headless
full-page PNG at 1240 px reviewed by eye in 2500 px tiles (`.herald/deck-qa/pyforge-scribe/`,
gitignored) ✓ · offline apart from the Google Fonts `<link>` ✓. No section of the standard's
set was dropped; the Warden "sub-agent team" slot is filled by the `GraphStore` drivers behind
the port (§06). `cli_verbs` has no ledger row (the `scribe` parser is typer, not
argparse-literal), so the verbs are named in prose and never counted. Page height is the
settled full-page capture (`scrollHeight` reads ~110 px less before the first capture's
font-metrics reflow).
## Ledger — 2026-09-14 currency sweep (spec-deck-family-currency CAP-6)

The poster had gone stale on the fleet's own merges since the 2026-09-13 rebuild — 18 ledger
rows drifted (`doctor_epics_done_total`, `doctor_stories_done_total`, `epics_done_total`, `fleet_epics_done_total`, `fleet_stories_done_total`, `groundtruth_pixi_envs`, `herald_epics_done_total`, `herald_stories_done_total`, `marshal_epics_done_total`, `marshal_stories_done_total`, `mason_epics_done_total`, `mason_stories_done_total`, `scribe_epics_done_total`, `scribe_stories_done_total`, `steward_epics_done_total`, `steward_stories_done_total`, `stories_done_total`, `tree_commit_date`). Swept repo-side first, per CAP-6:
`pixi run -e local-recipes deck-facts pyforge-scribe --refresh --check` at tree `168bbedb13` re-derived
`facts.yaml` and rewrote **45** stale `data-fact` literals in place, keeping their shape; the
re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 95/95`. Then the mirror (CAP-4): pushed via DesignSync `finalize_plan` →
`write_files` (`localPath`, no context relay) to project `a1e42dac-7cee-438b-9acc-2523985b5253`, and read back through the
serve URL with the injected harness stripped — **byte-identical to disk**.

| Artifact | Bytes | Design etag | Read-back |
|---|---|---|---|
| `PyForge Scribe Infographic standalone.html` | 144,962 | `1789417238206863` | identical ✓ |

Not touched by this sweep (by design): the `- Infographic.dc.html` head and `- Infographic Deck.dc.html`
still carry the 2026-09-13 literals — deriving them from the standalone is herald Epic 21
(Stories 21.1–21.4), not a refresh.
