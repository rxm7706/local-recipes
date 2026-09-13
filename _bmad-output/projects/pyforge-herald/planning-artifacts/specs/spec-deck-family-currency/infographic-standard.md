# The infographic standard — what every PyForge poster must carry

Companion to `SPEC.md` (CAP-1). This file is the standard's single home;
`docs/specs/presentation-deck.md` points here. **Unifying Strategy**
(`presentations/pyforge-unifying-strategy/project/PyForge Unifying Strategy Infographic
standalone.html`) is the structure, acts and length reference. **Warden**
(`presentations/pyforge-warden/project/Warden Infographic standalone.html`) is the density and
visual-form reference. Both are byte-exact on disk; measured 2026-09-13.

## Measured references

| Poster | Bytes | Sections | Act bands | Inline SVGs | Role |
|---|---|---|---|---|---|
| Unifying Strategy | 128,783 | 21 | 6 | 9 | structure · acts · length |
| Warden | 411,764 | 18 | 0 | 15 | density · visual form |
| Marshal (2026-07-31 rebuild) | 91,340 | 19 | 6 | 3 | the first six-act family member |

## Floors — a poster below any one of these is not current

| Floor | Value | Measured how |
|---|---|---|
| Act bands | exactly six, `ACT I` … `ACT VI`, full-bleed dark bands in arc order | count of distinct `ACT <roman>` labels |
| Numbered sections | ≥ 18, numbered `01`… continuously, each under one act | `<section` count minus act bands |
| Inline diagrams | ≥ 3 `<svg>` blocks in Modernist tokens, no raster images | `<svg` count |
| Length class | ≥ 90,000 bytes | `stat -c %s` |
| Tables | ≥ 3 (`<table>` or a grid-rendered table equivalent) | `<table` count, grids by eye |
| Cast cards | every station a full card — role paragraph, CLI verbs, status chip — never a motto-only stub | review |
| Facts | every count, version, status, date resolves to a `facts.yaml` row (`facts-ledger.md`) | the `deck-facts --check` advisory |
| Render | headless full-page PNG at 1240 px wide, no clipped or blank region | reviewer looks at the PNG |
| Offline | renders from disk; only the Google Fonts `<link>` is remote and falls back to system fonts | open the file with the network off |

## The six-act arc

| Act | Band label (adapt per subject) | Story-arc phase | Sections it carries |
|---|---|---|---|
| I | the problem and the model | friction → insight | 01 the problem · 02 the pipeline / tiers / topology · the contract at a glance |
| II | the cast | the actors | the station and its neighbours as full cards · the sub-agent team · the persona/skills map |
| III | running the line | mechanics, in time | one unit's journey · the ways work flows · the autonomy gradient · phase × persona × skills · the relay |
| IV | the product | what shipped | the shipped CLI / surface · the doctrine band · the stack table · which tool when · escalation and ledger |
| V | who it serves, where it runs | value, by leader | per-leader value · enterprise and air-gap · integration seams |
| VI | proof and road | receipts, then the map | programs shipped · the seed · now / next / later · the creed (closing band) |

Reorder sections to serve the arc; renumber mechanically. The masthead precedes Act I: kicker
line (chain · owner · spec id), display-brand `<h1>`, one-line spec slug, a one-paragraph
thesis, tag chips, and a five-cell stat strip — every stat a ledger row.

## The section set (Warden pattern, adapt names per subject)

problem · pipeline or tiers · cast · journey · flows · autonomy gradient · phase × persona ×
skills · relay · shipped product · doctrine band · stack table · which-tool-when · escalation
and ledger · per-leader value · enterprise and air-gap · integration seams · proof · seed ·
now / next / later · creed. Drop a section only when the subject genuinely has no content for
it, and say so in the README ledger.

## Diagram set (three minimum)

A topology (hub-and-spoke or tiers), a flow (relay baton or pipeline), and a ladder or
gradient (gates, autonomy, or the roadmap). `viewBox` 1128 wide; `<text>` in Archivo; ink
`#201e1d`, accent `#ec3013`, light `#f3f2f2`, accent-tint `#fbe4de`; arrows via a `<marker>`.

## Authoring template

Copy the `<head>` token block, masthead, act band and numbered-section markup from the
Unifying Strategy poster; keep the section header shape (accent number + `<h2>` on a 2 px ink
rule) and the act band shape (`ACT n` in accent-400 tracking, band title, phase caption on a
dark full-bleed `margin:40px -56px 0` band). Page frame `width:1240px; padding:56px 56px 0`.
Close with the creed band on the accent colour. No `<x-dc>` wrapper, no `support.js` — that
wrapper belongs to the trio head, re-derived in the lockstep slice.

## The README ledger entry a rebuilt poster must carry

```
| Artifact | Measured | Design etag | Notes |
| `<Name> Infographic standalone.html` | <bytes> B · <n> sections · 6 acts · <n> SVG · <n> tables · facts <n>/<n> | `<etag>` | rendered <date>, page <h> px; head + Infographic Deck: standalone ahead |
```
