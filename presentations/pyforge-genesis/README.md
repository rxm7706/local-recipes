# PyForge Genesis deck (`pyforge.genesis`)

**Status: STARTER — awaiting the Design pass.** The **master vision deck** of the
PyForge **"Dream to Code"** factory — the deck for the founding Dream itself
(`docs/dreams/pyforge-charter.md`): the Genesis, the six-persona PyForge Guild,
the Master Pipeline, and the proof it already runs. Each persona deck
(`pyforge-atlas` … `pyforge-doctor`) is one *chapter* of this Dream; Genesis is
the parent narrative — **and the seed**: it lays out the big picture well enough
to initiate a new repo with the operating model, or to adopt the model in a
brownfield repo (this repo was the first brownfield adoption).

Engine + glue copied **verbatim** from `presentations/pyforge-atlas/` (Archivo /
Modernist system). Built with the Design-to-Deck workflow
(`docs/specs/presentation-deck.md` — prototype contract, pipeline, § Standard
export set).

## Quick start

```
npm install
npm approve-scripts esbuild && npm rebuild esbuild   # npm 11+ blocks esbuild's install script
npm run extract && npm run dev
```

Keymap: `→`/`Space` next · `←` prev · `O` overview · `S` presenter · `F` fullscreen ·
`?` help · URL hash (`#/n`) deep-links.

Display brand **PyForge · Dream to Code** on the slides; slug `pyforge-genesis`
in paths. Engine files stay **byte-identical** across every deck.

## Design project (the bridge's far end)
Prototype lives in Claude Design project **"PyForge Genesis deck"** (`6af4c28d-d510-4e9b-b788-6c0e5d651183`):
https://claude.ai/design/p/6af4c28d-d510-4e9b-b788-6c0e5d651183?file=PyForge%20Genesis.dc.html

## Artifact family (2026-07-24 sweep)

Full warden-style set on disk: derived Marp deck + authored Executive Summary
(Marp + `project/PyForge Genesis - Executive Summary.dc.html`) + authored
Infographic (Marp) + `deck-export` outputs (standalone HTML + deck/infographic
PPTX), all dated 2026-07-24. Design-project upload of the light artifacts
(3 Marp + exec-summary dc.html) queued in the family-wide upload pass.

**Infographic hand-expanded in Design + fully round-tripped 2026-07-24.** The
one-pager `PyForge Genesis - Infographic.dc.html` was grown in the Design project
(17,574 → **48,040** bytes; +3 sections: "The autonomy gradient — how far the
leash goes" (L1–L5 ladder), "The SDLC, staffed — phase × persona × skills", and
"The Master Pipeline relay") and pulled to disk **byte-exact** (etag
`1784926929273012`, via render-preview → strip-harness). The whole infographic
family was then refreshed to match and re-synced both ways:
- `Infographic standalone.html` — mechanically re-derived from the edited dc.html
  (x-dc wrapper dropped, helmet hoisted to `<head>`); pushed back to Design.
- `src/marp/…-infographic-2026-07-24.md` — 3 condensed slides added (the ladder,
  the phase×persona table, the relay); pushed back to Design.
- `- Infographic Deck.dc.html` — 3 deck-stage slides added (badges 04–06), Proof
  and seed renumbered to 07/08; pushed back to Design.
- `deck-export` re-run → refreshed `…-infographic-standalone-*.html` +
  `…_infographic_deck-*.pptx` + `…-deck-*.pptx`.

NOT touched (separate branches, not affected by an infographic edit): the main
deck (`PyForge Genesis.dc.html` / `…-deck-*.md`) and the Executive Summary.

## 2026-07-31 — big picture absorbed by the Marshal family

Per the genesis→charter fold (PR #177 amendment set), the ecosystem big picture
this deck carried — the tier pipeline, the eight-station crew, the autonomy
gradient, the phase×persona table, the Master Pipeline relay, the seed — now
ALSO lives, updated and extended, in `presentations/pyforge-marshal/` (the
2026-07-31 six-act generation). This family remains the historical genesis
rendering; new ecosystem edits land in the Marshal family first. Retirement of
this deck rides the constitutional fold application, not this note.

## Ledger — 2026-09-13 standard rebuild (Story 20.11)

Rebuilt repo-side to `infographic-standard.md` (spec-deck-family-currency CAP-3) from
`facts.yaml` re-derived at tree `bc8ae85dd1`. Every count, version, status and date the poster
prints is a `data-fact` mark resolving to a ledger row; `deck-facts pyforge-genesis --check` →
`0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 94/94` (the one `unshown` row
is `poster_last_commit_date`, deliberately not printed). This is the Guild-wide / Charter deck,
so its substance is the Charter itself — the Lexicon, the doctrine, the eight Smiths, the
Dream-to-Code tiers, the autonomy gradient, the Master Pipeline relay, the seed — and at
142,316 B it is the deepest poster in the family, as the master deck should be.

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `PyForge Genesis Infographic standalone.html` | 142,316 B · 28 sections (27 numbered + creed) · 6 acts · 4 SVG · 14 tables · facts 94/94 | `pushed 2026-09-13 via DesignSync `finalize_plan` → `write_files` (localPath) · Design etag `1789308322821013` · 142,316 B on both sides · read back via `render_preview` → curl → harness strip: **byte-identical** to git; refreshed against the day's ledgers before the push (`deck-facts pyforge-genesis --refresh`, 9 literals)` (operator pushes via DesignSync after review) | rendered 2026-09-13, page 24046 px; head + Infographic Deck: standalone ahead (lockstep slice pending) |

Floors (standard): acts exactly six ✓ · sections ≥ 18 ✓ (27) · inline SVG ≥ 3 ✓ (4) ·
bytes ≥ 90,000 ✓ (142,316) · tables ≥ 3 ✓ (14) · cast cards full for all eight stations ✓ ·
facts all resolved ✓ · headless full-page PNG at 1240 px reviewed by eye
(`.herald/deck-qa/pyforge-genesis/standalone.png` plus ten 2500 px tiles, gitignored) ✓ ·
offline apart from the Google Fonts `<link>` ✓ (no scripts, no raster images, no `<x-dc>`).

No section of the standard's set was dropped. Subject-specific adaptations: the "one unit's
journey" slot is one Dream's journey from paragraph to merged code (§11); the "sub-agent team"
slot is the two persona layers — stations versus the BMAD team on the floor (§09); the
"shipped product" slot is the eight station surfaces and what each refuses (§16). Two sections
are Guild-only and have no per-station counterpart: the Lexicon (§03) and the branding law
(§08).

**Left out for lack of a fact row.** The genesis ledger has no `spec_status`, `dream_status`,
`spec_capabilities`, `package_version`, `cli_verbs` or `dream_log_*` rows (the deriver resolves
those from `docs/dreams/<slug>.md` and `spec-<slug>/SPEC.md`, and the constitutive chain lives at
`docs/dreams/pyforge-charter.md` + `docs/governance/spec-pyforge-charter/` instead). So the
poster carries **no dates at all** other than the marked `tree_commit_date`, and states no
Dream or Spec status: the Charter's amendment history, the Realization-log entries, the
six-to-eight roster growth and the capability count are all narrated by name rather than by
number or date. The Charter Spec's eight capabilities are enumerated in §05 without printing a
count; the `pitched` Dream status is shown with an explicit "no row" cell rather than a guess.

Re-based mid-story: `origin/main` moved from `0bfa4d44d3` to `bc8ae85dd1` while the poster was
being authored, so eight rows drifted (`dreams_total`, `dreams_specified`, the two fleet pairs,
`herald_stories_done_total`, both scribe pairs). `deck-facts pyforge-genesis --refresh` rewrote
the 28 stale marked literals from the fresh ledger, and one piece of prose that counted them by
hand — "three stations are complete on both rows" — was corrected to four. `facts.yaml` was then
re-derived on a clean tree so its `tree:` header records the branch base, not a dirty working copy.
## Ledger — 2026-09-14 currency sweep (spec-deck-family-currency CAP-6)

The poster had gone stale on the fleet's own merges since the 2026-09-13 rebuild — 20 ledger
rows drifted (`doctor_epics_done_total`, `doctor_stories_done_total`, `dreams_dreamt`, `dreams_realized`, `dreams_specified`, `dreams_total`, `fleet_epics_done_total`, `fleet_stories_done_total`, `groundtruth_pixi_envs`, `herald_epics_done_total`, `herald_stories_done_total`, `marshal_epics_done_total`, `marshal_stories_done_total`, `mason_epics_done_total`, `mason_stories_done_total`, `scribe_epics_done_total`, `scribe_stories_done_total`, `steward_epics_done_total`, `steward_stories_done_total`, `tree_commit_date`). Swept repo-side first, per CAP-6:
`pixi run -e local-recipes deck-facts pyforge-genesis --refresh --check` at tree `168bbedb13` re-derived
`facts.yaml` and rewrote **54** stale `data-fact` literals in place, keeping their shape; the
re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown; facts 94/94`. Then the mirror (CAP-4): pushed via DesignSync `finalize_plan` →
`write_files` (`localPath`, no context relay) to project `6af4c28d-d510-4e9b-b788-6c0e5d651183`, and read back through the
serve URL with the injected harness stripped — **byte-identical to disk**.

| Artifact | Bytes | Design etag | Read-back |
|---|---|---|---|
| `PyForge Genesis Infographic standalone.html` | 142,319 | `1789417197745702` | identical ✓ |

Not touched by this sweep (by design): the `- Infographic.dc.html` head and `- Infographic Deck.dc.html`
still carry the 2026-09-13 literals — deriving them from the standalone is herald Epic 21
(Stories 21.1–21.4), not a refresh.

## Ledger — 2026-09-15 infographic trio re-derived (Story 21.4)

`pixi run -e local-recipes deck-trio pyforge-genesis --head --deck` at tree `a407cd03f6`
mechanically re-derived both files from the standalone (x-dc/helmet wrap, verbatim
`<style>`/`<link>` relocation, a measured `$preview` height for the head; masthead/act-band/
numbered-section/closing-band slides for the deck): `PyForge Genesis - Infographic.dc.html` now
142,443 B, `PyForge Genesis - Infographic Deck.dc.html` now 149,504 B. A second `--head --deck`
run changed nothing on disk (verified).

`pixi run -e local-recipes deck-facts pyforge-genesis --refresh` then `--check` at the same tree
brought poster, head and Infographic Deck current: **87** stale `data-fact` literals rewritten
(`dreams_specified`, `dreams_total`, `fleet_epics_done_total`, `fleet_stories_done_total`,
`herald_epics_done_total`, `herald_stories_done_total`, `tree_commit_date` — drift since the
2026-09-14 sweep); re-check reads `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced, 1 unshown;
facts 282/282`.

**Design push/read-back: not performed this session — no working credential.**
`~/.claude/.credentials.json` has no `designOauth` block, and the `claude-design` MCP connector
independently reports `FIRST_PARTY_AUTH_REJECTED` (HTTP 403) this session; re-probed live via
`pixi run -e pyforge-herald herald deck push pyforge-warden` → `AuthError: ... has no
'designOauth' block -- run /design-login in Claude Code to refresh it` (one shared credential
file, so this applies identically to every deck — not re-probed per deck). No push attempted, no
etag fabricated. "Standalone ahead" narrows to: head + Infographic Deck are now re-derived and
facts-current on disk, not yet mirrored to Design.
