---
status: workflow
spec_updated: 2026-07-11
---
# Tech Spec: Design-to-Deck — reusable React/Vite presentation workflow (parameterized)

> **Timeless workflow.** Turn a **Claude Design** 1920×1080 prototype
> (`.dc.html` handoff export) into a self-contained **React + Vite**
> slide deck: slide markup is extracted *mechanically* from the prototype
> (no hand-transcription), rendered inside a small deck engine (fit-to-viewport
> stage, keyboard nav, URL-hash routing, overview grid, presenter view with
> speaker notes + timer), and shipped as a static offline-safe bundle plus
> **Marp/Markdown** and **PowerPoint** exports.
>
> **This spec is parameterized by _topic_.** It is not a record of one deck —
> it is the reusable recipe for building *any* deck this way. Fill the
> **Parameters** block for a new subject, follow the **Procedure**, and append
> a new entry under **Worked Examples**. New cases append; they do not
> duplicate the workflow.
>
> **Worked Example 1** (the 45-slide *Agentic AI across the SDLC* deck grounded
> in the BMAD Method) lives at the bottom and is the reference implementation
> shipped in PR #50 under `presentations/agentic-sdlc/`.
>
> This is a **framework-neutral intake spec** (Tier 1, per `AGENTS.md`). Any
> agent/human can execute it. It has **no** conda-forge surface, so CLAUDE.md
> Rules 1 & 2 (invoke `conda-forge-expert`, run a CFE retro) do **not** apply.

---

## How to use this spec

1. **Fill the Parameters block** with the new deck's real values (topic, title,
   slug, output path, palette, fonts, banner sources).
2. **Author the slides in Claude Design** at 1920×1080, honoring the
   [Prototype contract](#the-prototype-contract-designengine-interface) so the
   extractor can read them. Export the handoff `.dc.html`.
3. **Scaffold the app** from the [Repo layout](#repo-layout-the-deliverable) —
   the deck engine (`src/deck/*`) and glue (`src/slides/index.js`,
   `vite.config.js`, `index.html`, `package.json`) are **topic-agnostic**;
   copy them verbatim and only the prototype + `manifest`/`fragments` change
   per deck.
4. **Run the pipeline:** `npm run extract` → `npm run dev` to review →
   `npm run build` for the static bundle. Generate the Marp + PPTX exports.
5. **Verify** against [Acceptance criteria](#acceptance-criteria).
6. **Append a new Worked Example** recording the concrete parameters, slide
   count, act structure, and the PR/commit refs. That becomes a permanent record.

---

## Parameters (fill these per case)

| Parameter | Value (example = Worked Example 1) | Notes |
|---|---|---|
| `topic` | *Agentic AI across the SDLC (BMAD Method)* | The subject the deck teaches |
| `deck_title` | *Agentic AI across the software lifecycle — BMAD Method* | `<title>` + README H1 + PPTX title |
| `slug` | `agentic-sdlc` | Directory name under `presentations/<slug>/` |
| `output_dir` | `presentations/agentic-sdlc/` | App root; **not** a conda recipe path |
| `prototype_file` | `project/Agentic SDLC.dc.html` | The Claude Design handoff export (source of truth) |
| `slide_count` | 45 | Final section count after any restructure |
| `acts` | 6 (case for change → SDD → framework → agent team → four phases → scale/ecosystem) | Narrative structure; drives divider slides |
| `palette` | dark `#0B1626`, light `#F6F4EE`, accent `#F4C233`, blues `#2E9BEE`/`#5BB3F5` | Per-slide `bg` comes from the prototype |
| `fonts` | Space Grotesk (display), IBM Plex Sans (body), IBM Plex Mono (labels) | Google Fonts online, system fallback offline |
| `banner_sources` | 4 dev.to article images → `public/assets/banners/*` | Any remote image referenced by the prototype — localize for offline |
| `screenshot_slots` | slide 40 "In action" (3 panels) | `<image-slot>` placeholders left for real screenshots |
| `branch_name` | `claude/add-<slug>-deck` | One PR per deck |
| `exports` | Marp `.marp.md`, PowerPoint `.pptx` | Distributable non-React formats |

---

## Repo layout (the deliverable)

Everything lives under `presentations/<slug>/`. The **engine + glue are
topic-agnostic** (copy verbatim); only the **prototype** and the **generated**
`fragments/` + `manifest.json` change per deck.

```
presentations/<slug>/
  package.json            scripts: extract | dev | build | preview   (topic-agnostic)
  vite.config.js          base: './'  → bundle works from any static host / file://
  index.html              #root, /src/main.jsx, Google-Fonts <link>   (title per deck)
  .gitignore              node_modules/ dist/ *.local .DS_Store .vite/
  README.md               quick-start + keymap + "how it's structured" (per deck)

  project/                ← DESIGN HANDOFF (source of truth, per deck)
    <Deck>.dc.html          the Claude Design 1920×1080 prototype
    <Deck>.marp.md          Marp/Markdown export of the same deck
    deck-stage.js / image-slot.js / support.js   prototype runtime (design-time only)
    *.png / screenshots/    design assets

  scripts/                ← BUILD PIPELINE
    extract-slides.mjs      prototype → fragments/*.html + manifest.json (topic-agnostic)
    restructure-deck.mjs    OPTIONAL one-time reorder/insert-dividers/renumber (per deck)

  src/
    main.jsx  App.jsx  index.css
    deck/                 ← DECK ENGINE (topic-agnostic — copy verbatim)
      Deck.jsx              fit-to-viewport stage, progress, chrome
      Slide.jsx             scales a 1920×1080 frame by a factor
      useDeck.js            nav + keyboard + URL-hash sync (guards typing in inputs)
      useFit.js             contain-fit scale from a ResizeObserver
      Overview.jsx          thumbnail grid (press O)
      Presenter.jsx         speaker view: current+next, notes, session-persistent timer (press S)
      HelpOverlay.jsx       keyboard cheat-sheet (press ?)
      deck.css              deck chrome styling
    slides/               ← GENERATED (do not hand-edit fragments)
      fragments/*.html      one 1920×1080 slide body per file
      manifest.json         [{ id, label, notes, bg }]  per slide
      index.js              globs fragments (?raw) + manifest → slides[]  (topic-agnostic)
    marp/                 distributable Marp export (mirrors project/*.marp.md)
    pptx/                 PowerPoint export (dated: <slug>-YYYY-MM-DD.pptx)

  public/assets/banners/  remote images localized for offline/export safety
```

---

## The prototype contract (design↔engine interface)

The extractor is a small regex parser, so the Claude Design prototype must
follow a simple contract. Each slide is one `<section>`:

```html
<section
  data-label="The shift"                        <!-- slide title → slug + manifest.label -->
  data-speaker-notes="Frame the problem. …"     <!-- → manifest.notes (presenter view) -->
  style="background:#F6F4EE">                    <!-- first #hex → manifest.bg -->
  …inner slide body, authored at 1920×1080, inline-styled…
</section>
```

Rules that keep extraction lossless:
- **Author at 1920×1080.** `src/slides/index.js` hard-codes `SLIDE_WIDTH/HEIGHT`;
  `Slide.jsx` scales the whole frame, so every slide must share that canvas.
- **Inline styles are fine** — they are copied verbatim (that's the whole point:
  no hand transcription).
- **Remote images** referenced in the prototype must be added to the extractor's
  `BANNER_MAP` so they are rewritten to local `assets/banners/*` (offline/export
  safety). Use **relative** local paths (no leading `/`) so they resolve under a
  site root, a subpath, or `file://`.
- **Drop targets** use `<image-slot placeholder="Drop image"></image-slot>`;
  the extractor converts them to a dashed `.image-slot` placeholder `<div>`
  (the drag-drop runtime is design-time only and is stripped).
- **Footers** may carry `NN / TT` page markers; `restructure-deck.mjs` renumbers
  them to the final total if you reorder.

---

## The pipeline

### 1. (Optional) restructure — `npm run restructure`
`scripts/restructure-deck.mjs` is a **one-time, non-idempotent** transform run
against the prototype *before* extraction when the raw Claude Design output needs
editorial surgery: insert clean act-divider slides, merge/drop redundant slides,
reorder to match a Contents slide, and renumber every footer to `NN / <total>`.
It asserts **no section is silently lost** (every original section is reused or
explicitly dropped). Author a per-deck version; it is not reusable verbatim.

### 2. Extract — `npm run extract`
`scripts/extract-slides.mjs` is **topic-agnostic**. It:
1. reads `project/<Deck>.dc.html`,
2. matches every `<section>…</section>`,
3. pulls `data-label`, `data-speaker-notes`, and the first `background:#hex`,
4. rewrites `BANNER_MAP` remote URLs → local `assets/banners/*`,
5. converts `<image-slot>` → placeholder div,
6. writes `src/slides/fragments/NN-<slug>.html` (slug from the label) and
   `src/slides/manifest.json` (`[{ id, label, notes, bg }]`),
7. prints the slide list with backgrounds.

Re-run any time the prototype changes — **slide content lives in one place**
(the prototype); `fragments/` + `manifest.json` are generated artifacts.

### 3. Render — the deck engine
`src/slides/index.js` eager-globs `./fragments/*.html` as raw strings and pairs
each with its manifest entry into `slides[]` (throws on a missing fragment).
The engine (`src/deck/*`) renders it. Keymap:

| Key | Action |
|---|---|
| `→` · `Space` · `PgDn` | Next slide |
| `←` · `PgUp` | Previous slide |
| `Home` · `End` | First / last |
| `O` | Overview grid (click a thumbnail to jump) |
| `S` | Presenter view (current + next, notes, timer) |
| `F` | Fullscreen |
| `?` | Keyboard cheat-sheet |
| `Esc` | Back to the deck |

The current index is mirrored to the URL hash (`#/12`) → every slide is
deep-linkable and reload-stable. Keyboard shortcuts are suppressed while focus
is in an `INPUT`/`TEXTAREA`/`SELECT`/`contenteditable`. The presenter timer
starts on first open and persists across `S` toggles within a session
(resets on full reload).

### 4. Build & export
- `npm run build` → static `dist/` (relative `base`, self-contained, offline-safe;
  open `dist/index.html` from disk or host anywhere). **Print to PDF** from the
  browser to export (deck chrome hidden in print).
- **Marp** `.marp.md` — a portable Markdown deck kept in `project/` and mirrored
  to `src/marp/`.
- **PowerPoint** `.pptx` — a dated export under `src/pptx/<slug>-YYYY-MM-DD.pptx`.

---

## Design system defaults (parameterizable)

The reference theme (swap per topic):
- **Fonts:** Space Grotesk (display/headlines), IBM Plex Sans (body), IBM Plex
  Mono (kicker labels / footers). Loaded from Google Fonts with system fallback.
- **Palette:** dark ground `#0B1626`, light ground `#F6F4EE`, accent/kicker
  `#F4C233`, secondary blues `#2E9BEE` / `#5BB3F5`.
- **Act dividers:** dark full-bleed slide with a giant translucent roman numeral,
  a mono uppercase kicker (`ACT N`), a Space-Grotesk H2, a one-line subhead, and
  a running footer (`<PROJECT> · <TAG>` left, `NN / TT` right). The template lives
  in `restructure-deck.mjs`'s `divider()` — reuse its shape, restyle to taste.
- **Chapter covers:** full-bleed banner image + dark gradient scrim + optional
  stats row.

---

## Acceptance criteria

- [ ] `npm install && npm run dev` serves the deck at `localhost:5173` with all
      slides rendering at 1920×1080, fit to the viewport.
- [ ] `npm run extract` regenerates `fragments/` + `manifest.json` from the
      prototype with the expected slide count and **no lost sections**.
- [ ] Keyboard nav, `O` overview, `S` presenter (notes + timer), `F` fullscreen,
      `?` help, and `#/<n>` deep-links all work; nav is suppressed while typing.
- [ ] `npm run build` produces a `dist/` that renders correctly opened as
      `file://` (offline) — banners load locally; fonts fall back gracefully.
- [ ] Marp `.marp.md` and `.pptx` exports exist and open.
- [ ] The React app, static bundle, and exports are the same deck (content lives
      only in the prototype → fragments; no divergent hand edits).

---

## Conventions & gotchas

- **Content lives in the prototype, not in JSX.** Never hand-edit
  `src/slides/fragments/*` — they are overwritten by `extract`. Edit the
  prototype and re-extract.
- **Offline-safe by construction.** Localize every remote image; keep `base: './'`;
  don't hard-code absolute asset paths.
- **`&amp;` in a `data-label`** breaks JSON/React text rendering — normalize
  ampersands in labels (see the Act VI fix in `restructure-deck.mjs`).
- **`restructure-deck.mjs` is per-deck and one-shot** — run it once against the
  raw prototype; it is not idempotent and `extract` consumes its output.
- **Engine files are the reusable asset.** When starting a new deck, copy
  `src/deck/*`, `src/slides/index.js`, `vite.config.js`, `package.json` verbatim;
  change only the prototype, `index.html` title, README, and generated slides.
- **`.pptx` is a binary blob** — git can't diff it; updates replace the whole
  file. Date the filename so revisions are distinguishable.
- **Not a conda recipe.** This deck lives under `presentations/`, unrelated to
  `recipes/`; the conda-forge tooling and its `**/[Pp]ackages/*` ignore rules do
  not apply here.

---

## Worked Examples

New decks append a subsection here. Do not modify the workflow above; record the
per-case reality below.

### Example 1 — Agentic AI across the SDLC (BMAD Method) · PR #50

| Field | Value |
|---|---|
| `topic` | Agentic AI across the software development lifecycle, grounded in the [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) |
| `slug` / `output_dir` | `agentic-sdlc` / `presentations/agentic-sdlc/` |
| `slide_count` | 45 |
| `acts` | 6 — the case for change → spec-driven development → choosing a framework → the BMAD agent team → the four phases → scale, governance & ecosystem |
| `prototype` | `project/Agentic SDLC.dc.html` (Claude Design handoff; also `project/Agentic SDLC.marp.md`) |
| `banners` | 4 dev.to article images (framework / phases / testing / ecosystem) → `public/assets/banners/*` |
| `screenshot_slots` | slide 40 "In action" — 3 placeholder panels awaiting real screenshots |
| `fonts` / `palette` | Space Grotesk + IBM Plex Sans/Mono; `#0B1626` / `#F6F4EE` / `#F4C233` / blues |
| `branch` / `PR` | `claude/add-agentic-sdlc-deck` / **PR #50** (merged 2026-07-11 → `main`, `4e7aabb0`) |
| `exports` | `src/marp/agenticaisdlc.marp.md` · `src/pptx/agentic-ai-sdlc-2026-07-11.pptx` |
| `sources` | Built from a Claude Design prototype + a Claude Code web session; the prototype is committed as the design source of truth |

**Notes / deltas from the generic workflow:**
- Ran `restructure-deck.mjs` once to insert Act I–III dividers, merge the
  redundant "Cover · Framework" + "Meet BMAD" pair into a single Act IV banner,
  reorder the agent-team vs. phases acts to match the Contents slide, and
  renumber footers `NN / 45`.
- Post-merge review (Gemini on PR #50) hardened the engine: keyboard nav now
  skips input/textarea/contenteditable focus, and the presenter timer persists
  across presenter-view toggles. A third suggestion (single-or-double-quote
  attribute parsing in `extract-slides.mjs`) was declined — the double-quote
  parser already extracts the real prototype and the proposed regex allowed
  mismatched quotes.
- `spec_updated` reflects when this workflow spec was back-filled (2026-07-11)
  from the shipped effort; the deck itself predates the spec.
