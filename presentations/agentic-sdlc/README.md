# Agentic AI across the software lifecycle — a deck

A 45-slide field guide for engineers on **agentic AI across the SDLC**, grounded in
the open-source [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD). Built as
a self-contained **React + Vite** presentation app.

The deck walks six acts: the case for change → spec-driven development → choosing a
framework → the BMAD agent team → the four phases → scale, governance & ecosystem.

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
