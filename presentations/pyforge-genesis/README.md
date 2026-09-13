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
https://claude.ai/design/p/6af4c28d-d510-4e9b-b788-6c0e5d651183?file=PyForge+Genesis.dc.html
Pull it into this deck with the MCP bridge ("pull genesis") — see
`docs/specs/presentation-deck.md` § *The MCP bridge*.

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
