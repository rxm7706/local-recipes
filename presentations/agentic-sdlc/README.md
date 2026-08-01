# Agentic AI across the software lifecycle — a deck

A 50-slide field guide for engineers on **agentic AI across the SDLC**, grounded in
the open-source [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD). Built as
a self-contained **React + Vite** presentation app.

The deck walks six acts: the case for change → spec-driven development → choosing a
framework → the BMAD agent team → the four phases → scale, governance & ecosystem.

## Ledger — 2026-08-01 refresh

Five new slides landed this pass, plus a reconciliation. Design project:
[f58c0f17-087b-417e-9cfa-c410de6169dc](https://claude.ai/design/p/f58c0f17-087b-417e-9cfa-c410de6169dc).

**New content** (grounded in live-verified sources, not memory):
- *The productivity paradox* (Act I) — Google's 2024 DORA report, the real numbers
  (-1.5% throughput / -7.2% stability per 25% AI-adoption step, ~3,000 respondents),
  plus the 2025 follow-up: throughput recovered, stability didn't.
- *Spec rigor, on a spectrum* (Act II) — spec-first / spec-anchored / spec-as-source;
  BMAD sits at spec-anchored.
- *Governing the agent, not just the code* (Act VI) — OWASP's 2026 Top 10 for
  Agentic Applications, ASI03 Identity & Privilege Abuse, the least-agency principle.

**Reconciled, not new:** *The Lexicon* and *Lexicon to PyForge* existed in Design
since 2026-07-25 but were never pulled to the repo (a real desync — recovered here
per the byte-exact-pull discipline in `docs/specs/presentation-deck.md`). Both, plus
their two standalone poster artifacts (also pulled to the repo for the first time —
see `project/Lexicon Poster.dc.html` / `project/Lexicon to PyForge.dc.html`), were
corrected to match the Charter's own Lexicon, which moved from six nouns to seven
(the Spec, added 2026-07-25) and renamed "Forgemasters" to "Smiths." Dream count
refreshed 25 → 37 against a live `dream-chain-check` run.

45 → 50 sections; 47 carry the page-footer counter (Title and the two dense Lexicon
slides are deliberately un-footered, matching their original convention).

## Quick start

```bash
npm install
npm run dev      # http://localhost:5173
```

Build a static bundle and preview it:

```bash
npm run build    # → dist/
npm run preview
```

The build in `dist/` is fully static and self-contained — host it anywhere, or open
`dist/index.html` from disk. Chapter-banner images are bundled locally, so it works
offline. (Web fonts load from Google Fonts when online, falling back to system fonts.)

## Presenting

| Key | Action |
| --- | --- |
| `→` · `Space` · `PgDn` | Next slide |
| `←` · `PgUp` | Previous slide |
| `Home` · `End` | First / last slide |
| `O` | Overview grid (click a thumbnail to jump) |
| `S` | Presenter view — current + next slide, speaker notes, timer |
| `F` | Fullscreen |
| `?` | Keyboard cheat-sheet |
| `Esc` | Back to the deck |

The current slide is reflected in the URL hash (`#/12`), so any slide is
deep-linkable and survives a reload. **Print to PDF** from the browser to export
(deck chrome is hidden in print).

## How it's structured

Each slide was authored at 1920×1080 in the Claude Design prototype. Rather than
hand-transcribe hundreds of inline style rules into JSX (error-prone), the slide
markup is extracted mechanically and rendered inside a real React deck engine.

```
scripts/extract-slides.mjs   Parses the prototype → per-slide HTML + manifest
                             (also localizes the four remote banner images and
                             converts the drag-drop <image-slot> to a placeholder)
src/slides/
  fragments/*.html           One 1920×1080 slide body per file (generated)
  manifest.json              id, label, speaker notes, background (generated)
  index.js                   Loads fragments (?raw) + metadata into a slides array
src/deck/
  Deck.jsx                   Main view: fit-to-viewport stage, progress, chrome
  Slide.jsx                  Scales a slide's 1920×1080 frame by a given factor
  useDeck.js                 Navigation, keyboard shortcuts, URL-hash sync
  useFit.js                  Contain-fit scale from a ResizeObserver
  Overview.jsx               Thumbnail grid of all slides
  Presenter.jsx              Speaker view with notes + timer
  HelpOverlay.jsx            Shortcut cheat-sheet
  deck.css                   Deck chrome styling
public/assets/banners/       The four chapter banners, bundled locally
project/                     Original Claude Design handoff (source of truth)
```

### Regenerating slides

If the prototype in `project/Agentic SDLC.dc.html` changes, re-run the extractor:

```bash
npm run extract
```

This rewrites `src/slides/fragments/` and `manifest.json` from the prototype so the
React app stays in sync — the slide content lives in one place.

## Notes

- **Banners** were downloaded from the article series and committed under
  `public/assets/banners/` so the deck is offline- and export-safe.
- **The "See it in action" slide** (40) has three placeholder panels. Drop real
  screenshots into `public/assets/` and reference them in
  `src/slides/fragments/40-in-action.html` to fill them in.
