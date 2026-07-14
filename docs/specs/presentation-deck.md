---
status: workflow
spec_updated: 2026-07-14
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

## Claude Design ↔ repo handoff (operating playbook)

The friction in this workflow is the boundary between a **Claude Design** session
(where slides are authored) and the **local repo** (where they're wired, built,
and shipped). This is the concrete hand-off, learned across Worked Examples 1–2.

**What a Claude Design session hands off (per deck):**
- **One `.dc.html` prototype** — the React deck's source of truth and the *only*
  input to `extract`. Its name is whatever Design exported (`Agentic SDLC.dc.html`,
  `Warden Deck.dc.html`); **spaces are fine** (see gotchas — don't rename it).
- **Zero or more standalone Marp `.md` decks** — a main deck plus optional
  companions (e.g. an **executive summary** and an **infographic**). These are
  **parallel exports** authored in Marp — *not* derived from the prototype and
  *not* consumed by `extract`. They live in `src/marp/` and ship as-is.
- **An optional `.pptx`** — a dated PowerPoint export → `src/pptx/`.

**Wiring it in the repo (the exact steps):**
1. **Scaffold** (first time for a deck): copy the engine + glue verbatim from an
   existing deck (`presentations/agentic-sdlc/`); stub the `index.html` title,
   README, and `package.json` name. This can land as its own PR
   (`claude/add-<slug>-deck`) *before* the content exists.
2. **Drop the prototype** into `project/<Deck>.dc.html`.
3. **Point the extractor:** set `SRC = join(root, 'project', '<Deck>.dc.html')`
   and `BANNER_MAP = {}` (or map each remote image) in `scripts/extract-slides.mjs`.
4. **Drop the Marp exports** into `src/marp/<slug>-*.md` (main + any companions)
   and the `.pptx` into `src/pptx/<slug>-YYYY-MM-DD.pptx`.
5. **Install + unblock the toolchain:** `npm install`, then **approve esbuild's
   install script** — modern npm (11+) blocks it by default:
   `npm approve-scripts esbuild && npm rebuild esbuild`. Commit the resulting
   `package.json` `allowScripts` entry + `package-lock.json` so the next clone
   installs reproducibly. Skipping this makes `dev`/`build` fail — but `extract`
   still runs (it's plain Node, no esbuild).
6. **Extract → build:** `npm run extract` (→ N fragments + manifest),
   `npm run build` (→ offline `dist/`). This can land as `claude/wire-<slug>-slides`.

**Branding — display brand vs. slug.** When the product's *display* brand differs
from its package/repo *slug* (e.g. display **Warden** vs. distribution
**pyforge-warden**), slide **content** carries the display brand while **file and
directory names** use the slug. Don't rebrand the prototype/marp copy to the slug —
keep the display name in the words on the slides.

**The engine is a shared asset — keep every copy byte-identical.** Every deck
copies `src/deck/*` (+ glue) verbatim, so an engine fix (a Gemini finding, a
browser-compat guard) must be applied to **every** deck copy in the same change,
or the copies drift. Verify with
`diff -q presentations/<a>/src/deck/<f> presentations/<b>/src/deck/<f>` before and
after.

**Shipping a `presentations/` PR.** It's a non-recipe change → add the
`maintenance` + `documentation` labels (the `maintenance`-gated lint is what
otherwise reds the staged-recipes linter) and confirm `environment.yaml` is in
sync with `pixi.toml`. See auto-memory `feedback_non_recipe_pr_linter_gates`.

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
- **First-time prerequisite (npm 11+):** `npm install` leaves esbuild's install
  script blocked by allow-scripts, so `dev`/`build` fail until you
  `npm approve-scripts esbuild && npm rebuild esbuild`. Commit the `allowScripts`
  entry it adds to `package.json` so future clones install cleanly. (`extract`
  needs none of this.)
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
- **Engine files are the reusable asset — and must stay byte-identical across
  decks.** When starting a new deck, copy `src/deck/*`, `src/slides/index.js`,
  `vite.config.js`, `package.json` verbatim; change only the prototype,
  `index.html` title, README, and generated slides. Because the copies are
  identical, any engine fix must be applied to **every** deck in the same change
  (see the handoff playbook) — `diff -q` the copies to prove they didn't drift.
- **esbuild's install script is blocked by default (npm 11+).** After
  `npm install`, run `npm approve-scripts esbuild && npm rebuild esbuild`, then
  commit the `allowScripts` entry it writes to `package.json` (+ `package-lock.json`)
  for reproducible installs. `dev`/`build` fail without it; `extract` doesn't care.
- **Spaced prototype filenames are fine — don't fight the Design export name.**
  `Warden Deck.dc.html` / `Agentic SDLC.dc.html` work: the extractor reads the
  path via `path.join()` (never a shell), and git tracks/quotes it. Renaming to
  hyphenate just churns the `SRC` line and diverges from what Design handed off.
- **Display brand vs. slug.** Slide *content* uses the product's display brand;
  *file/dir* names use the repo slug (e.g. **Warden** on the slides,
  `pyforge-warden` in paths). Keep the display name in the prototype/marp copy.
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

### Example 2 — PyForge-Warden, the multi-axis dependency compliance gate · PRs #59, #60

| Field | Value |
|---|---|
| `topic` | **Warden** — a pluggable multi-axis Python dependency **compliance gate** (hygiene · security · license · currency) that never false-greens |
| `slug` / `output_dir` | `pyforge-warden` / `presentations/pyforge-warden/` |
| `slide_count` | 28 |
| `acts` | 6 — the false-green problem → one report + verdict lattice → the two v1 engines (deptry/osv) → deterministic, deny-by-default runs → the six-axis vision (KEV/EPSS, license, currency) → gate-in-CI; + cover & personas appendix |
| `prototype` | `project/Warden Deck.dc.html` (Claude Design handoff; **spaces in the name kept**) |
| `banners` | none — the prototype references **zero** remote images, so `BANNER_MAP = {}` and `dist/` is fully offline (bar Google Fonts) |
| `fonts` / `palette` | **Archivo** display; light `#f3f2f2`, dark `#201e1d`, red accents `#c22a10` / `#ec3013` (from the prototype) |
| `branches` / `PRs` | scaffold `claude/add-pyforge-warden-deck` → **PR #59** (`b90e3aab69`); wire `claude/wire-pyforge-warden-slides` → **PR #60** (`ef5fd000d0`) |
| `exports` | **three standalone Marp decks** — `src/marp/pyforge-warden-deck.md`, `-executive-summary.md`, `-infographic.md` — plus `src/pptx/pyforge-warden-deck-2026-07-14.pptx` |
| `sources` | Claude Design prototype + Marp exports; the prototype is committed as the design source of truth |

**Notes / deltas from the generic workflow:**
- **Two-phase landing:** the scaffold shipped first (PR #59, engine + glue copied
  verbatim from `agentic-sdlc`, empty `manifest.json`), then the prototype was
  dropped and wired in a second PR (PR #60). No `restructure-deck.mjs` was needed —
  the prototype arrived already act-structured across 28 clean `<section>`s.
- **Marp-native companions:** unlike Example 1 (one Marp mirror), this deck shipped
  **three** standalone Marp decks (main + executive-summary + infographic) as
  first-class parallel exports — none derived from the `.dc.html`.
- **Display brand ≠ slug:** slide copy reads **Warden** (the product display name);
  files/dirs use `pyforge-warden` (the distribution). Kept the display name in the
  prototype and Marp copy.
- **esbuild allow-scripts** first bit here: `npm install` blocked esbuild's
  postinstall (npm 11), so `build` failed until `npm approve-scripts esbuild`; the
  `allowScripts` entry is committed for reproducibility.
- **Declined Gemini finding:** the spaced prototype filename `Warden Deck.dc.html`
  was kept (extractor reads via `path.join()`, git quotes it) — consistent with
  Example 1's `Agentic SDLC.dc.html`.
- **Shared-engine hardening (PR #61, branch `claude/deck-engine-hardening`):** the four
  Gemini medium findings raised on the scaffold PR (#59) were fixed in the engine
  and applied to **both** `agentic-sdlc` and `pyforge-warden` in one change, keeping
  the copies byte-identical: `document.exitFullscreen?.()` guard (iOS Safari),
  `setMode` added to the `useDeck` keyboard-effect deps, lazy `useRef` init for the
  presenter timer (Strict-Mode safe), and an explicit `Escape`-closes-help handler
  in `Deck.jsx`. Both decks rebuilt green (69 / 86 modules).
