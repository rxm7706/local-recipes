---
status: workflow
spec_updated: 2026-07-23
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

## Genesis — The Dream & the Ecosystem Crew

Every deck this spec produces is one persona's chapter of a larger story: the
**pyforge** ecosystem's **"Dream to Code"** pipeline. Its genesis (**The Dream** —
the BMAD mission, *Build More Architect Dreams*), its eight-persona **Ecosystem
Crew** (Herald · Marshal · Atlas · Warden · Mason · Doctor · Scribe · Steward), and the Master
Pipeline Flow are defined **once**, in the founding Dream:
**`docs/dreams/ecosystem-crew.md`**. Read the crew there — this spec deliberately
does not duplicate it.

**Where a Dream lives:** `docs/dreams/` is **Tier 0** (per `AGENTS.md`) — the
starting point of every deliverable. Herald reads the Dream to render *The Deck*;
BMAD-method (`bmad-spec`, or the planning chain) turns the same Dream into the
active spec in `_bmad-output/projects/<slug>/planning-artifacts/`. Everything
starts with a Dream. (This file itself predates the model and remains in the
legacy `docs/specs/` tier as a **timeless workflow** doc.)

**Why this matters to this spec:** **Herald is the presentation persona** — the
decks produced by this workflow *are* Herald's output. Each persona gets its own
deck (see § *Worked Examples* → *The live deck family*); a Herald deck is, fittingly,
a deck about the deck engine.

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

The boundary in this workflow is between a **Claude Design** session (where
slides are authored visually) and the **local repo** (where they're wired,
built, and shipped).

### The MCP bridge (canonical since 2026-07-23 — no manual downloads)

When a Claude Code session has the **`claude-design` MCP server** connected
(`/design-login`), the boundary is crossed by tools, not downloads — the Dream
behind this: **`docs/dreams/design-code-bridge.md`** (piloted with the Marshal
deck). The loop:

1. **Seed (repo → Design):** author or update the contract-compliant starter
   `.dc.html` locally; **prove it** (`npm run extract` + `npm run build`); then
   `create_project` (bind `design_system_id` = **Modernist**,
   `fbc1d6c8-b35f-4df6-9044-a64d2675427b`), `finalize_plan` the write paths,
   `create_support_js` at root, `copy_files` a `deck-stage.js` from an existing
   deck project, and `write_files` the prototype (`if_match: "0"` for new).
   Share only the `claude.ai/design/...?file=` link.
2. **Design (human):** the user iterates visually in Claude Design.
3. **Pull (Design → repo):** on "pull <persona>", `read_file` the prototype with
   `if_none_match` = the last-seen etag — `{unchanged:true}` means the repo is
   already current; otherwise **decode the HTML-entity-escaped body**
   (`&amp; &lt; &gt;` → `& < >`), write it to
   `presentations/<slug>/project/<Deck>.dc.html`, re-run
   `extract` → `build` → `deck-export`, and commit.

Discipline: thread **etags** through every read/write (`if_match` /
`if_none_match`) so a concurrent Design edit conflicts instead of being
clobbered; only the **prototype** crosses the bridge — never a mirrored app tree
(the retired *"Local recipes repository connection"* project is the cautionary
tale); `get_claude_design_prompt` is mandatory before any `write_files`.

**Large-file uploads (verified 2026-07-24, atlas seed + 8-project family
pass):** for any disk→Design transfer beyond a few KB, prefer the **`DesignSync`
tool** (`finalize_plan` with `localDir`, then `write_files` with `localPath`)
over the MCP `write_files` inline path — the file is read, encoded and uploaded
server-side, **byte-exact, without ever entering the agent context** (the 75KB
atlas prototype uploaded with a verified exact byte match; hand-relay had
produced a 12-byte drift on a 7KB file). It writes to regular Design projects
(`get_project` → `canEdit: true` suffices; the design-system typing only
matters for design-system semantics). Design→disk **pulls (proven byte-exact
2026-07-24** against the known-identical `Warden Deck.dc.html`)**:**
`render_preview` → `curl` the short-lived serve URL straight to disk → strip
the contiguous `data-omelette-injected` `<style>/<script>` harness block
injected after `<head>` (splice with a single newline; verify the byte count
against `list_files`). This bypasses `read_file`'s 256 KiB cap and its
entity-escaping, and nothing relays through the agent context. Never write the
serve URL into any persisted file. Both directions are now mechanized; the
herald CLI formalizes them but no longer gates them.

### Manual handoff (fallback — no MCP bridge in the session)

This is the original hand-off, learned across Worked Examples 1–3.

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
    marp/                 Marp sources + derived standalone HTML (see § Standard export set)
    pptx/                 marp-derived PowerPoint (deck + infographic, dated)

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

## Standard export set (the deck-family contract)

Every deck in the family ships the **same six companion deliverables** so the set
is uniform and every non-React format is **reproducible from a Marp source**, never
hand-massaged. (The React deck — `prototype → fragments → dist/` — remains the
*primary* artifact; these six are the portable, offline-friendly companions.)

**Marp sources** (hand/Claude-Design-authored — the source of truth for exports),
in `src/marp/`:
1. `<slug>-deck-<YYYY-MM-DD>.md` — the full Marp deck (mirrors the prototype narrative)
2. `<slug>-executive-summary-<YYYY-MM-DD>.md` — a short exec-summary deck
3. `<slug>-infographic-<YYYY-MM-DD>.md` — a single/few-panel infographic

**Derived / companion** (**regenerate, never hand-edit** — engines revised by the
2026-07-23 evening decisions below):
4. `src/marp/<slug>-infographic-standalone-<YYYY-MM-DD>.html` — self-contained
   offline poster. **Design-authored bundle preferred** (the richer Claude-Design
   "bundled page", pulled via the Design↔Code bridge — warden's 411 KB poster is
   the exemplar); `marp --html` render of #3 is the **fallback** when no
   Design-authored bundle exists.
5. `src/pptx/<slug>-deck-<YYYY-MM-DD>.pptx` — target: **editable PowerPoint** via
   the **deckcraft** pipeline (python-pptx / pptxgenjs); `marp --pptx` is the
   explicitly **interim** generator (it renders image-slides, not editable text).
6. `src/pptx/<slug>_infographic_deck-<YYYY-MM-DD>.pptx` — same engine rule as #5
   (underscore form kept from Example 2).

**Export decisions revisited (2026-07-23 evening, user-directed):**
1. **PPTX must become editable.** `marp --pptx` emits each slide as a rendered
   image — fine for distribution, useless for editing. The designated engine is
   the **`deckcraft`** BMAD project (editable PPTX + Marp + infographics,
   air-gapped); `deck-export` grows a backend switch when deckcraft delivers.
   Until then, marp-generated PPTX are **interim** artifacts.
2. **Standalone HTML: Design-authored wins.** Visual quality over pure
   regenerability — reverses the morning's warden regeneration; the Design bundle
   is restored on the next warden pull. Marp render only where no bundle exists.
3. **Derived exports cross the bridge outbound.** After `deck-export`, the herald
   CLI pushes the regenerated set back into the deck's Design project
   (`SPEC-design-code-bridge` CAP-5), so Design holds the complete set too.

**Generation** — from repo root; the `local-recipes` pixi env carries `marp` 4.2.3
and Chrome at `/usr/bin/google-chrome` (Chrome is required for `--pptx`/`--pdf`;
`--html` is pure Node):

```bash
S=presentations/<slug>/src
# 4. standalone infographic HTML (offline, self-contained)
pixi run -e local-recipes marp --allow-local-files \
  "$S/marp/<slug>-infographic-<date>.md" \
  -o "$S/marp/<slug>-infographic-standalone-<date>.html"
# 5 + 6. PPTX (Chrome-backed)
CHROME_PATH=/usr/bin/google-chrome pixi run -e local-recipes marp --allow-local-files --pptx \
  "$S/marp/<slug>-deck-<date>.md" -o "$S/pptx/<slug>-deck-<date>.pptx"
CHROME_PATH=/usr/bin/google-chrome pixi run -e local-recipes marp --allow-local-files --pptx \
  "$S/marp/<slug>-infographic-<date>.md" -o "$S/pptx/<slug>_infographic_deck-<date>.pptx"
```

Or run the **wrapped pixi task** — `scripts/deck_export.py` resolves each deck's
dated `.md` sources and runs exactly the commands above (each output dated from its
own source), so exports stay one command and never drift:

```bash
pixi run -e local-recipes deck-export <slug> [html | deck-pptx | infographic-pptx ...]
```

With no targets it regenerates all three derived artifacts.

**Conformance (as of 2026-07-23):** all three live decks — `pyforge-warden`,
`pyforge-atlas`, and `agentic-sdlc` — carry the full six. The 2026-07-23
standardization pass generated atlas's + agentic's derived companions, regenerated
warden's standalone HTML from its `.md` via `marp` (it had been a one-off Claude
Design "bundled page"), and brought `agentic-sdlc` — the origin deck, on its own
Space-Grotesk theme — into the set by authoring its exec-summary + infographic and
renaming its files to convention. Per-deck **content** still differs (theme, slide
count, wording); the **shape** of the set does not. Under the evening revisit,
the current PPTX and marp-rendered standalone HTML artifacts are **interim** —
superseded per-deck as deckcraft (editable PPTX) and Design-authored bundles
(standalone HTML) come online.

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
- [ ] The **standard export set** (§ *Standard export set*) is complete — 3 Marp
      sources + the marp-derived standalone infographic HTML + 2 PPTX — and every
      derived artifact regenerates from its `.md` source (no hand edits).
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
- **The `index.html` font `<link>` is per-deck — do NOT copy it verbatim.**
  `index.html` is *mostly* boilerplate, but its Google-Fonts `<link>` must load
  exactly the families the prototype/fragments use (`font-family:` declarations),
  because `extract` copies only the `<section>` bodies — the prototype's own
  `<head>` font link is design-time and never reaches the built app. Copying
  `index.html` verbatim from the source deck ships the *wrong* fonts: the
  **pyforge-warden** deck went out with `agentic-sdlc`'s Space Grotesk / IBM Plex
  link while its slides request **Archivo**, so it silently rendered in a
  sans-serif fallback until the 2026-07-23 alignment pass. Pull the `<link>`
  straight from the deck's own prototype `<head>`, and remember it can differ
  between siblings (warden needs `IBM Plex Mono`; atlas uses system mono, so their
  links aren't identical even though both are Archivo decks).
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

**The live deck family.** **`pyforge-genesis`** is the **master vision deck** — the
parent narrative of the founding Dream (and its *seed*: it lays out the operating
model well enough to initiate a new repo or adopt the model in a brownfield one).
Each persona in the § *Genesis* Ecosystem Crew then gets its own chapter deck. **Atlas** and **Warden** have shipped decks (Examples 3 & 2);
**Herald, Marshal, Mason, and Doctor** have seeded starter decks; **Scribe and
Steward** (adopted 2026-07-23) join the backlog as `pyforge-scribe` and
`pyforge-steward` — the existing family convention (matching `pyforge-atlas` /
`pyforge-warden`). All eight persona decks
share one **Modernist / Archivo** design system (display **Archivo** / **Archivo
Expanded**; light `#f3f2f2`, dark `#201e1d`, red `#ec3013` / `#c22a10`) so they
present side-by-side as a family. `agentic-sdlc` (Example 1) is the **origin
engine** they were all forked from and keeps its own Space Grotesk / IBM Plex
theme — so a new persona deck should scaffold from **`pyforge-atlas` or
`pyforge-warden`** (already on the Archivo system), not from `agentic-sdlc`.

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
| `exports` | **full standard set** (6, conformed 2026-07-23) — `src/marp/agentic-sdlc-deck-2026-07-11.md` + `-executive-summary-2026-07-23.md` + `-infographic-2026-07-23.md` + `-infographic-standalone-2026-07-23.html`; `src/pptx/agentic-sdlc-deck-2026-07-11.pptx` + `agentic-sdlc_infographic_deck-2026-07-23.pptx` |
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
- **Export standardization (2026-07-23):** brought agentic into the § *Standard
  export set*. Authored `agentic-sdlc-executive-summary-2026-07-23.md` +
  `agentic-sdlc-infographic-2026-07-23.md` (Marp, in the deck's own Space-Grotesk
  theme — distilled from the 45-slide deck), renamed the deck source + PPTX to
  convention (`agentic-sdlc-deck-2026-07-11.*`), and generated the derived
  standalone HTML + infographic PPTX via `pixi run -e local-recipes deck-export
  agentic-sdlc html infographic-pptx`. The existing deck PPTX was **preserved**
  (renamed, not re-rendered) — its theme differs from the persona decks, so it
  stays the origin exception on Space Grotesk while sharing the set's *shape*.

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
| `exports` | **three Marp decks** — `src/marp/pyforge-warden-deck-2026-07-15.md`, `-executive-summary-2026-07-15.md`, `-infographic-2026-07-15.md` — a **standalone infographic** `-infographic-standalone-2026-07-15.html`, plus **two** PPTX (`src/pptx/pyforge-warden-deck-2026-07-15.pptx`, `pyforge-warden_infographic_deck-2026-07-15.pptx`) |
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

### Example 3 — PyForge-Atlas, the cf_atlas Kedro/Dagster/DuckDB migration

| Field | Value |
|---|---|
| `topic` | **Atlas** — the conda-forge intelligence layer, migrating a ~10,000-LOC hand-rolled orchestrator to declarative **Kedro + Dagster + DuckDB** dataflow (Boring Semantic Layer, Vizro / Vizro-AI read surface, MCP / A2A agent interfaces) |
| `slug` / `output_dir` | `pyforge-atlas` / `presentations/pyforge-atlas/` |
| `slide_count` | 21 |
| `acts` | 5 — from monolith to DAG → node-shaped & agent-maintainable → an agent workforce builds it → new signals (Basilisk / velocity / readiness) → the read surface inverts; + cover & closing |
| `prototype` | `project/PyForge Atlas.dc.html` (Claude Design handoff; **spaces in the name kept**) |
| `banners` | none — `BANNER_MAP = {}`; `dist/` fully offline (bar Google Fonts) |
| `fonts` / `palette` | **Archivo** + **Archivo Expanded** display, **system mono** (`ui-monospace`); Modernist light `#f3f2f2` / dark `#201e1d` / red `#ec3013` / `#c22a10` (matches `pyforge-warden`) |
| `exports` | **full standard set** (6) — 3 Marp sources (`-deck-`, `-executive-summary-`, `-infographic-` `2026-07-23.md`) + the marp-derived standalone `-infographic-standalone-2026-07-23.html` + 2 PPTX (`-deck-`, `_infographic_deck-` `2026-07-23.pptx`) |
| `sources` | Claude Design prototype + Marp exports; the prototype is committed as the design source of truth |

**Notes / deltas from the generic workflow:**
- **Engine + glue copied verbatim from `pyforge-warden`** (already on the Archivo
  system) — only the prototype, `index.html` title + Archivo font link, README, and
  the generated `fragments/` + `manifest.json` are Atlas-specific. Confirmed
  byte-identical to warden + agentic-sdlc via `diff -q` (all 8 `src/deck/*` +
  `src/slides/index.js` + config/glue).
- **System mono, not IBM Plex Mono:** Atlas uses `ui-monospace, 'SF Mono', Menlo`
  for code/labels, so its `index.html` font `<link>` loads only Archivo +
  Archivo Expanded (unlike warden, which also loads IBM Plex Mono).
- **2026-07-23 alignment pass (the change that added this Example).** Audited all
  three live decks for artifact parity. The engine files were already byte-identical;
  the drift was in the surrounding artifacts and was fixed in the same change:
  1. **warden `index.html` fonts** — it loaded `agentic-sdlc`'s Space Grotesk /
     IBM Plex link while its slides request Archivo, so it rendered in a sans-serif
     fallback. Corrected to `Archivo + Archivo Expanded + IBM Plex Mono` (from
     warden's own prototype). Rebuilt green; `dist/index.html` now loads Archivo.
  2. **agentic-sdlc `package.json`** lacked the `allowScripts` `esbuild@0.21.5`
     entry the other two carry (fresh npm-11 clones would fail `build`). Added.
  3. **atlas reproducibility** — it had never been `npm install`ed, so no
     committed `package-lock.json` and no `public/`. Ran `npm install` (→ committed
     lockfile) and added `public/assets/banners/.gitkeep` to match warden. Verified
     all three build green (agentic 69 / warden 69 / atlas 62 modules).
  4. **Export-set divergence — then standardized:** at audit time only warden had
     the full companion set (standalone HTML + 2 PPTX); atlas had the three Marp
     sources only, and agentic-sdlc a single Marp mirror. Rather than leave it, the
     family was standardized in a follow-on step the same day (user directive
     "standardize the family") — see § *Standard export set* + Example 1's
     standardization note. The `deck-export` pixi task was added to keep the derived
     artifacts reproducible.
- **Export standardization (same 2026-07-23 pass):** atlas already had the three
  Marp sources but not the derived companions; generated
  `pyforge-atlas-infographic-standalone-2026-07-23.html` (`marp --html`) and
  `pyforge-atlas_infographic_deck-2026-07-23.pptx` (`marp --pptx`, Chrome-backed)
  so it now carries the full **§ Standard export set** (6 companions), matching
  `pyforge-warden`.
