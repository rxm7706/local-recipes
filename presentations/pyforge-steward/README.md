# PyForge-Steward deck (`pyforge.steward`)

**Status: STARTER — awaiting the Design pass.** Engine + glue copied **verbatim**
from `presentations/pyforge-atlas/` (Archivo / Modernist system). A chapter deck
of the founding Dream (`docs/dreams/pyforge-charter.md`); persona Dream:
`docs/dreams/pyforge-steward.md`. Motto: *"Provision the line. Hold the keys. Keep the lights on."*

Workflow: `docs/specs/presentation-deck.md` (prototype contract, § Standard
export set, § The MCP bridge). `npm install && npm run extract && npm run dev`.
Engine files stay byte-identical across every deck.

## Design project (the bridge's far end)
Prototype lives in Claude Design project **"PyForge Steward deck"** (`573d6554-0095-4126-b13f-cd537279ff8a`):
https://claude.ai/design/p/573d6554-0095-4126-b13f-cd537279ff8a?file=PyForge%20Steward.dc.html

## Ledger — 2026-09-13 standard rebuild (Story 20.9)

Rebuilt repo-side to `infographic-standard.md` (spec-deck-family-currency CAP-3) from
`facts.yaml` re-derived at tree `fbefe6eea6`. Every count, version, status and date the
poster prints is a `data-fact` mark resolving to a ledger row; `deck-facts pyforge-steward
--check` → `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 83/83` (the one
unshown row is `poster_last_commit_date`, deliberately not printed).

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Steward Infographic standalone.html` | 163,529 B · 24 sections (23 numbered + creed) · 6 acts · 4 SVG · 10 tables · facts 83/83 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) · Design etag `1789300404919885` · 163,529 B on both sides · read back 2026-09-13 via `render_preview` → curl → harness strip: **byte-identical** to git; refreshed and re-pushed the same day by the first currency sweep (`deck-facts <slug> --refresh`)` (operator pushes via DesignSync after review) | rendered 2026-09-13, page 25069 px (full-page PNG; DOM scrollHeight 24899 px); head + Infographic Deck derived 2026-09-15 via `deck-trio --head --deck` (Story 21.4 local sweep; Design push/read-back still pending) |

Floors (standard): acts exactly six ✓ · sections ≥ 18 ✓ · inline SVG ≥ 3 ✓ · bytes ≥ 90,000 ✓ ·
tables ≥ 3 ✓ · cast cards full for all eight stations ✓ · facts all resolved ✓ · headless
full-page PNG at 1240 px reviewed by eye in ten ~2500 px tiles
(`.herald/deck-qa/pyforge-steward/`, gitignored) ✓ · offline apart from the Google Fonts
`<link>` ✓ · no `<x-dc>`, no `support.js`, no scripts, no raster images ✓. No section of the
standard's set was dropped; the Warden "sub-agent team" slot is filled by Steward's registered
duty set (§06), and the Canopy — Steward's flagship chain — carries the contract-at-a-glance
table (§04). Left out for lack of a fact row: the unifying-strategy Spec's capability count and
its dated realization-log entries, the five-tier `n/n` figure, the registered-duty count, all
two-part and third-party versions (interpreter, Django, PostgreSQL, Redis, MCP SDK, Liquibase),
the deploy-profile plugin count, test counts, and every exit code as a count (exit codes appear
as code literals in their own table cells).
## Ledger — 2026-09-14 currency sweep (spec-deck-family-currency CAP-6)

The poster had gone stale on the fleet's own merges since the 2026-09-13 rebuild — 19 ledger
rows drifted (`cli_verbs`, `doctor_epics_done_total`, `doctor_stories_done_total`, `epics_done_total`, `fleet_epics_done_total`, `fleet_stories_done_total`, `groundtruth_pixi_envs`, `herald_epics_done_total`, `herald_stories_done_total`, `marshal_epics_done_total`, `marshal_stories_done_total`, `mason_epics_done_total`, `mason_stories_done_total`, `scribe_epics_done_total`, `scribe_stories_done_total`, `steward_epics_done_total`, `steward_stories_done_total`, `stories_done_total`, `tree_commit_date`). Swept repo-side first, per CAP-6:
`pixi run -e local-recipes deck-facts pyforge-steward --refresh --check` at tree `168bbedb13` re-derived
`facts.yaml` and rewrote **44** stale `data-fact` literals in place, keeping their shape; the
re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 83/83`. Then the mirror (CAP-4): pushed via DesignSync `finalize_plan` →
`write_files` (`localPath`, no context relay) to project `573d6554-0095-4126-b13f-cd537279ff8a`, and read back through the
serve URL with the injected harness stripped — **byte-identical to disk**.

| Artifact | Bytes | Design etag | Read-back |
|---|---|---|---|
| `PyForge Steward Infographic standalone.html` | 163,535 | `1789417247247941` | identical ✓ |

Not touched by this sweep (by design): the `- Infographic.dc.html` head and `- Infographic Deck.dc.html`
still carry the 2026-09-13 literals — deriving them from the standalone is herald Epic 21
(Stories 21.1–21.4), not a refresh.

## Ledger — 2026-09-15 infographic trio re-derived (Story 21.4)

`pixi run -e local-recipes deck-trio pyforge-steward --head --deck` at tree `a407cd03f6`
mechanically re-derived both files from the standalone (x-dc/helmet wrap, verbatim
`<style>`/`<link>` relocation, a measured `$preview` height for the head; masthead/act-band/
numbered-section/closing-band slides for the deck): `PyForge Steward - Infographic.dc.html` now
163,659 B, `PyForge Steward - Infographic Deck.dc.html` now 169,498 B. A second `--head --deck`
run changed nothing on disk (verified).

`pixi run -e local-recipes deck-facts pyforge-steward --refresh` then `--check` at the same tree
brought poster, head and Infographic Deck current: **33** stale `data-fact` literals rewritten
(`fleet_epics_done_total`, `fleet_stories_done_total`, `herald_epics_done_total`,
`herald_stories_done_total`, `tree_commit_date` — drift since the 2026-09-14 sweep); re-check
reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 249/249`.

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
`573d6554-0095-4126-b13f-cd537279ff8a`, then read back and SHA-256-compared against disk:

| Artifact | Bytes | Design etag | Read-back |
|---|---|---|---|
| `PyForge Steward - Infographic.dc.html` | 163,659 | `1789635960691405` | identical ✓ |
| `PyForge Steward - Infographic Deck.dc.html` | 169,498 | `1789635962583567` | identical ✓ |

Both files are under the 256 KiB `read_file` cap, so a single call plus entity-decoded SHA-256
comparison is the read-back proof (no windowing needed). `deck-facts pyforge-steward --check`
still reads 0 mismatch. Head and Infographic Deck now match Design as well as disk — no surface
here is standalone-ahead any more.
