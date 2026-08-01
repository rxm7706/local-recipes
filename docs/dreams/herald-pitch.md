---
title: Herald's Pitch Deck — Moment 1 Orchestration (Consolidated)
type: dream
owner: herald
status: specified
---

# Herald's Pitch Deck — Moment 1 Orchestration (Consolidated)

This dream consolidates the Herald pitch-deck ecosystem: Tier 0 (Vision) + Tier 1 (Reusable Capabilities) + Tier 2 (Moment 1 Feature Orchestration). Single source of truth for Dream → Spec → Epic → Code chain.

---

## Tier 0: Vision — The Four Moments of Proclamation

Herald is the factory's *voice and visual surface*. Invisible engineering is failed engineering. Herald's work is continuous across **four moments of proclamation**:

| # | Moment | What Herald Owes | Lands As |
|---|---|---|---|
| **1** | **Pitch** — a Dream must be argued, not merely filed | the case made legible to humans who did not dream it | the deck family (THIS DREAM) |
| **2** | **Progress** — a build in flight is not self-explaining | what changed, what it cost, what it unblocked | release notables, run telemetry as imagery |
| **3** | **Success** — shipping is not the same as being known to have shipped | the claim, with the evidence attached | the release proclamation |
| **4** | **Operations** — the long tail nobody announces | fixes, updates, deprecations, decommissions | change + end-of-life notices |

Moment 1 is simply the **first** time Herald has something to do — it is not the extent of the job. This dream owns Moment 1's orchestration across 9 pyforge stations using the four Tier 1 capabilities below.

---

## Tier 1: Reusable Capabilities

### Tier 1a: Design-Code-Bridge Framework

**Purpose:** Automate the round-trip between Design (claude.ai/design) and Code (this repo).

**The Core Problem:** Today, visual authoring and code are joined by hand. Designers manually mirror files into Design projects, work there, download, and copy back. Manual, error-prone, slow.

**The Solution:** **The prototype round-trips itself.** A persona deck starts as a seeded Design project; a human refines it visually in Claude Design; a single ask in Claude Code pulls the prototype straight into `presentations/<slug>/project/`, extracts, builds, and ships — zero downloads, zero copy-paste, conflicts caught by etags instead of overwrites.

**How It Works:**

1. **Seed (push):** Claude Code creates a Design project per deck, bound to the Modernist design system, pre-seeded with a contract-compliant starter prototype (1920×1080, Archivo, family palette).

2. **Design (human):** User iterates visually at claude.ai/design — their preferred surface, no repo mechanics.

3. **Pull (ship):** `herald deck pull <slug>` → read_file the prototype into `project/` → `npm run extract` → `npm run build` → `pixi run deck-export` → commit. The deck ships without a single manual transfer.

4. **Discipline:** Etags on every read/write so a mid-edit conflict surfaces instead of silently clobbering either side; only the **prototype** crosses the bridge (never a mirrored app tree).

**What Is Real:**
- The bridge is **realized** and proven on 7 decks in one day
- Herald CLI specced to 5 capabilities: seed / pull / watch / stale-mirror / export
- Etagged round-trip protocol established and working
- Zero manual file transfers between Design and Code

**Future:** Herald CLI full automation (v1: seed, pull, watch-mode sync, stale-mirror detection)

---

### Tier 1b: Deckcraft Framework

**Purpose:** Generate editable PowerPoint, Markdown, infographics, and images from primitives — air-gapped, conda-forge-native.

**The Core Problem:** `marp --pptx` renders image-slides (fine for distribution, useless for editing). Decks need real, editable PowerPoint.

**The Solution:** Deckcraft is the **editable-PPTX engine** for the deck family. Markdown → PPTX generation using python-pptx + design tokens, delivering slides that are both programmatically generated and manually editable.

**How It Works:**

1. **Input:** Markdown source (`{station}.md`) + Modernist design tokens
2. **Transform:** `pixi run deck-export` → deckcraft pipeline → python-pptx
3. **Output:** `src/pptx/{station}.pptx` (editable PowerPoint with proper fonts, colors, layouts)

**What Is Real:**
- Deckcraft BMAD project registered and active
- Toolchain in place: python-pptx, pptxgenjs, marp-cli, markitdown
- Design-tokens pipeline found in Sentinel project: `tokens-to-potx.py`, `potx-to-tokens.py`, Figma-variable bridges

**Multi-Surface:** Claude Skill, MCP server for Copilot/MS365, CLI — same deck machinery serves interactive sessions, enterprise Office stacks, and headless factory runs.

---

### Tier 1c: Video-Scripts Framework

**Purpose:** Extract narration scripts from decks and feed them into video production pipelines (bmad-manticore).

**The Core Problem:** Decks exist in isolation. Videos that could amplify them don't exist. Narration extraction is manual.

**The Solution:** **Mechanically extract narration scripts** from every deck prototype's speaker notes. Feed them to bmad-manticore, which orchestrates voice, graphics, screen recordings, and real footage into finished videos — no fabricated demos, ever.

**Three Content Classes (What Manticore Feeds On):**

1. **Raw Inputs** — Speaker notes from Design (extracted mechanically); real screen recordings of factory surfaces (console, marshal sessions, Guildhall board); real footage, never AI-generated UI.

2. **Taste & Identity** — Voice Bible (deconstructed from published transcripts: WPM, speech patterns); Production Bible (brand tokens, motion feel, CTA policy); Blacklist (LLM tells the script linter enforces); Format profiles (talking-head, screen-tutorial, voiceover-explainer, short).

3. **Orchestrated Media** — HyperFrames motion graphics (brand-themed overlays, kinetic captions); Kokoro-82M narration; MusicGen beds; AudioLDM2 SFX; approved b-roll only.

**Four Hard Gates:** Outline → Cut Plan → Graphics Beats → Final Render (no fabricated product demos, ever).

**How It Works:**

1. **Extract:** `narration-extract` task → pull speaker notes from Design proto → generate `{station}-narration-2026-08-01.md`
2. **Compose:** Herald feeds narration corpus to manticore (322 scenes extracted, first master script authored as exemplar)
3. **Render:** `mc-new` → script, edl.json cut plan, HyperFrames over real UI → incremental render → `.mp4`

**What Is Real:**
- Narration corpus: 27 files, 322 scenes, mechanically extracted from deck prototypes
- First master script: `presentations/pyforge-marshal/src/marp/pyforge-ecosystem-master-script-2026-07-31.md` (22 scene/visual/voiceover triples)
- bmad-manticore 2.0.0 installed and packaged (`recipes/bmad-manticore/`)
- Operator intake preserved verbatim in spec input

---

### Tier 1d: Modernist-Identity Framework

**Purpose:** One visual language across all PyForge surfaces — decks, dashboards, docs, exports, videos.

**The Core Problem:** Consistency is hard. Without a shared language, artifacts diverge.

**The Solution:** **One design system binds everything:** Modernist. Flat, architectural, Archivo throughout; light `#f3f2f2`, ink `#201e1d`, one red accent `#ec3013`/`#c22a10`; visible grid, 2px rules, zero corner radius, flush-left labels, black-and-white photography.

**What It Is:**
- **The Modernist design system** project in Claude Design (tokenized stylesheet, component pages, templates)
- **Bound to all family decks** (9 pyforge stations + agentic-sdlc legacy)
- **Family grammar** codified in `presentation-deck.md` (design defaults, font-link gotchas, proven across 100+ slides)
- **Wordmark + banner assets** (agentic-sdlc Design project)

**How It Works:**
- Design tokens (Archivo, palette, grid) → drive Figma, deckcraft PPTX templates, deck engine, video production bibles
- Tokens round-trip: `tokens.json` + Figma-variable bridges + `tokens-to-potx.py` / `potx-to-tokens.py`
- Applied consistently: Decks, dashboards (`docs/dashboard/`), docs, videos (manticore uses Modernist tokens in Production Bible)

**What Is Real:**
- Modernist adopted as persona-family system; 7 decks bound; grammar codified
- Token-pipeline assets discovered in Sentinel project
- Ready for round-trip wiring (Figma ↔ PPTX ↔ deck engine ↔ video)

---

## Tier 2: Moment 1 Feature Orchestration

### The Dream

Herald's **Four Moments of Proclamation** begins with **Moment 1: Pitch** — the case made legible to those who did not dream it. This dream **completes Moment 1** by authoring full six-act pitch decks for all **9 pyforge stations**, shipped in **multiple formats**: PPTX (editable), HTML (interactive), Markdown (version-controlled), Infographics (inline SVG), and narration scripts (companion video).

One source of truth (Design prototype). One delivery chain (Design → Code → Export). Multiple surfaces. Zero manual file transfers.

### The Dream

Herald's **Four Moments of Proclamation** begins with **Moment 1: Pitch** — the case made legible to those who did not dream it. Today Herald has proven the deck bridge on all **9 pyforge stations**. This Dream completes Moment 1 by authoring full six-act pitch decks for each, shipped in **multiple formats**: PPTX (editable), HTML (interactive), Markdown (version-controlled), Infographics (inline SVG), and video scripts (companion narration).

One source of truth (Design prototype). One delivery chain (Design → Code → Export). Multiple surfaces. Zero manual file transfers.


## The Artifact Collection

Each of the 21 stations produces a **six-artifact export set** from one design source:

```
presentations/pyforge-{station}/
├── project/
│   └── {Station}.dc.html          ← Design prototype (SOURCE OF TRUTH, tracked ✓)
└── src/marp/
    ├── {station}.md               ← Markdown source (tracked ✓)
    ├── {station}-narration-2026-08-01.md  ← Narration script (tracked ✓)
    └── {station}-infographic.svg  ← Static infographic (tracked ✓)
└── src/pptx/
    └── {station}.pptx             ← Editable PowerPoint (tracked ✓)

Generated at build time (gitignored, regenerable):
├── src/slides/fragments/{station}-*.json  ← Marp-parsed fragments (regen)
├── dist/
│   ├── index.html                 ← Vite-built interactive deck (regen)
│   ├── assets/*.js                ← JS/CSS bundles (regen)
│   └── assets/*.css
└── {station}.mp4                  ← Companion video (regen via bmad-manticore)
```

**Optimization**: Only source artifacts (design proto, markdown, PPTX, narration, infographic) are tracked. Fragments and build outputs regenerate at build time, reducing per-deck tracked files from ~53 to ~20.

**The Six-Act Framework** (canonical structure for all 21):

1. **Cover: The Hook** — Thesis statement + hero graphic
2. **Act I: The Friction** — Problem framing (pain point)
3. **Act II: The Insight** — Solution introduction (aha moment)
4. **Act III: The Solution (Mechanics)** — 4-step delivery loop (chronological, L.A.T.C.H. Time)
5. **Act IV: Real-World Application** — Enterprise fit (L.A.T.C.H. Location)
6. **Act V: The Resolution (Future)** — Vision & scaling (L.A.T.C.H. Category)
7. **Act VI: The Action** — Payoff & CTA (command, docs link)
8. **Appendix: Personas** — Stakeholder context

**~28 slides per deck, 90KB+ class, inline SVGs, full depth.**

---

## File Locations, Workflow, and Dependency Chain

### Physical File Structure

```
presentations/pyforge-{station}/
│
├─ project/                          ← DESIGN CLOUD (Design source of truth)
│  ├─ {station}.dc.html              [SOURCE: Design cloud, etagged]
│  ├─ {station}-cover.dc.html        [SOURCE: Design cloud, etagged]
│  └─ {station}-appendix.dc.html     [SOURCE: Design cloud, etagged]
│
├─ src/marp/                         ← MARKDOWN SOURCES (version-controlled content)
│  ├─ {station}.md                   [CREATED: npm run extract from .dc.html]
│  ├─ {station}-cover.md             [CREATED: npm run extract from .dc.html]
│  ├─ {station}-extended.md          [CREATED: npm run extract from .dc.html]
│  ├─ {station}-narration-2026-08-01.md    [CREATED: narration-extract task]
│  ├─ {station}-narration-cover-2026-08-01.md [CREATED: narration-extract task]
│  └─ {station}-infographic.svg      [CREATED: extraction/render from markdown]
│
├─ src/pptx/                         ← POWERPOINT EXPORTS (deckcraft output)
│  ├─ {station}.pptx                 [CREATED: deckcraft from {station}.md]
│  ├─ {station}-cover.pptx           [CREATED: deckcraft from {station}-cover.md]
│  ├─ {station}-extended.pptx        [CREATED: deckcraft from {station}-extended.md]
│  └─ {station}-appendix.pptx        [CREATED: deckcraft from appendix.md]
│
├─ src/slides/                       ← SLIDE FRAGMENTS (Marp parse tree)
│  └─ fragments.json                 [CREATED: npm run extract, intermediate]
│
├─ dist/                             ← BUILT OUTPUT (Vite bundle)
│  ├─ index.html                     [CREATED: npm run build (Vite)]
│  └─ assets/
│      ├─ main.[hash].js             [CREATED: npm run build (Vite)]
│      ├─ style.[hash].css           [CREATED: npm run build (Vite)]
│      └─ […more chunks…]
│
└─ {station}.mp4                     [CREATED: bmad-manticore (external)]
   (if tracked; otherwise regenerable on demand)
```

### Seven-Step Workflow: Design → Extract → Build → Export → Ship

**STEP 1: SEED** (design-code-bridge: herald CLI)
- Input: None (first time only)
- Output: `project/{station}.dc.html` + variants (3–4 files)
- Action: `herald deck seed pyforge-marshal`
- Duration: ~30s (one-time, Design project creation)
- Tracking: ✓ **MUST TRACK** (source of truth)

**STEP 2: DESIGN** (human in Claude Design)
- Input: `{station}.dc.html` (Design project)
- Output: Updated `{station}.dc.html` (edits in Design cloud)
- Action: User refines visually; etagged changes tracked
- Duration: Hours (human authoring)
- Tracking: Synced via design-code-bridge "pull" command

**STEP 3: PULL** (design-code-bridge: herald CLI)
- Input: Updated `{station}.dc.html` from Design cloud
- Output: `project/{station}.dc.html` → `src/marp/{station}.md` (extracted)
- Action: `herald deck pull pyforge-marshal` or `npm run extract`
- Duration: <2s per deck
- Files Created: `.dc.html`, `.md` variants (5–8 files)
- Tracking: ✓ **MUST TRACK** (.dc.html design proof, .md content source)

**STEP 4a: BUILD — Fragments & HTML** (npm run build)
- Input: `src/marp/*.md` files
- Output: `src/slides/fragments.json` + `dist/index.html` + `dist/assets/*`
- Action: `npm run build` (Vite pipeline: marp parse → bundle → output)
- Duration: ~10–15s for full build
- Files Created: fragments.json, index.html, JS/CSS bundles (~50+ files)
- Regenerable: ✓ YES (deterministic, from .md alone)
- Tracking Decision:
  - ✗ GITIGNORE `fragments.json` → regenerates <1s
  - ✗ GITIGNORE `dist/` → regenerates <15s

**STEP 4b: EXTRACT NARRATION** (narration-extract task)
- Input: `project/{station}.dc.html` (Design speaker notes)
- Output: `src/marp/{station}-narration-2026-08-01.md`
- Action: `pixi run narration-extract pyforge-marshal`
- Duration: <1s per deck
- Files Created: narration `.md` files (1–2 files)
- Regenerable: ✓ YES (from Design speaker notes)
- Tracking Decision: **Decide** — needed for video pipeline

**STEP 5: EXPORT** (pixi run deck-export + deckcraft)
- Input: `src/marp/{station}.md` + Modernist design tokens
- Output: `src/pptx/{station}.pptx` + `{station}-infographic.svg`
- Action: `pixi run deck-export` → deckcraft → PowerPoint generation
- Duration: ~5–10s per deck
- Files Created: `.pptx` files + `.svg` infographics (8–12 files)
- Regenerable: ✓ YES (from .md + deckcraft engine)
- Tracking Decision: **Decide** — PPTX and SVG tracked or regenerated?

**STEP 6: VIDEO** (bmad-manticore, external pipeline)
- Input: `src/marp/{station}-narration-*.md` + screen recordings
- Output: `{station}.mp4` + optional `.edl` / `.fcpxml`
- Action: `mc-new` + render pipeline (outline → cut → graphics → render)
- Duration: ~30–60s per video (EXPENSIVE)
- Files Created: `.mp4` video file (1 file, ~100MB+)
- Regenerable: ✓ YES but EXPENSIVE (full render required)
- Tracking Decision: ✗ GITIGNORE (regenerate on demand)

**STEP 7: COMMIT & SHIP** (git → push → publish)
- Input: All staged files (tracked artifacts only)
- Output: Committed to git, pushed to origin
- Action: `git add` → `git commit` → `git push`
- Git Footprint: Only TRACKED files count; regenerable files are in `.gitignore`
- Decision Impact: Each track/ignore decision affects total repo size

### Artifact Tracking: Tradeoff Spectrum

**AGGRESSIVE (144 tracked files for 9 stations) ← CHOSEN**
```
✓ TRACK:     Design protos (3-4), Markdown (5-8), PPTX (2-4), Narration (1-2), Infographics (0-1)
✗ GITIGNORE: Fragments (.json), dist/ (HTML), assets/ (JS/CSS), Video (.mp4)

Result:
  • Fast workflow (PPTX, HTML, narration ready immediately after git pull)
  • No rebuilds required for deliverables
  • Medium git footprint (~16 tracked files per station)
  • Video-ready (narration scripts staged for bmad-manticore)

Workflow:
  git pull → npm install → (all tracked artifacts available immediately)
  Optional: npm run build → for interactive HTML preview
  Optional: bmad-manticore → render videos from narration scripts
```

**BALANCED (120 tracked files for 9 stations)**
```
✓ Track:    Design protos, Markdown, Narration, Infographics
✗ Gitignore: Fragments, dist/, PPTX, Video
→ Result: Smaller git, PPTX regenerates (~5–10s), video-ready
→ Workflow: git pull → npm run build → pixi run deck-export → use
```

**CONSERVATIVE (100 tracked files for 9 stations)**
```
✓ Track:    Design protos, Markdown
✗ Gitignore: Fragments, dist/, PPTX, Narration, Infographics, Video
→ Result: Minimal git, everything regenerates, slower workflow
→ Workflow: git pull → npm run build → narration-extract → pixi run deck-export → use
```

---

## Dream Architecture: Layered (Option 4) ← CHOSEN

This expansion dream is **Tier 2 (Feature)** in a three-tier Herald architecture that separates **functionality** (how things work) from **features** (what gets delivered). This dream orchestrates Tier 1 capabilities to deliver Moment 1 (Pitch) across 9 pyforge stations.

### Option 3: Capabilities-Driven

**Core Capability Dreams** (describe HOW things work):
- `design-code-bridge.md` → Framework: seed → design → pull automation
- `deckcraft.md` → Framework: markdown → PPTX generation engine
- `video-scripts.md` → Framework: narration extraction → script composition → video render
- `modernist-identity.md` → Framework: brand tokens → applied to all surfaces

**Feature/Orchestration Dreams** (describe WHAT gets delivered):
- `pyforge-herald.md` → Vision: Four Moments of Proclamation
- `herald-pitch-family-expansion.md` → Feature: Pitch Expansion using all capabilities

**Pros:** Clear separation (mechanics vs delivery)  
**Cons:** Requires mentioning capabilities in Pitch Expansion dream

### Option 4: Layered (Tier Model) ← CHOSEN

**Tier 0 — Vision** (overarching framework):
- `pyforge-herald.md` → Four Moments of Proclamation (Pitch, Progress, Success, Operations)

**Tier 1 — Capabilities** (independent functionality, reusable across all Moments):
- `design-code-bridge.md` → Design ↔ Code round-trip (seed/pull/watch/stale-mirror)
- `deckcraft.md` → Markdown → PPTX generation engine
- `video-scripts.md` → Narration extraction → script composition → video pipeline
- `modernist-identity.md` → Brand tokens + application rules (Archivo, palette, grid)

**Tier 2 — Features** (orchestrations that compose Tier 1 into deliverables):
- `herald-pitch-family-expansion.md` (THIS DREAM) → **Moment 1 (Pitch) Feature**
  - **Orchestrates**: design-code-bridge + deckcraft + video-scripts + modernist-identity
  - **Produces**: 6 artifact types (Design protos, Markdown, PPTX, Narration, Infographics, Video)
  - **For**: 9 pyforge stations
  - **Tracked**: 144 files (Aggressive strategy)
  - **Future**: Moments 2–4 will be separate Tier 2 features using the same Tier 1 capabilities

**Pros:** Clear hierarchy; Capabilities are reusable; each Moment is independent; scales as new features arise  
**Advantage:** When Moment 2 (Progress) is specced, it can reuse all Tier 1 capabilities

### Option 5: Domain-Separated (Process vs Artifact vs Tech vs Vision)

**Process Dreams** (how information flows):
- `design-code-bridge.md` → Design → Code round-trip workflow
- `video-scripts.md` → Narration → Video rendering workflow

**Artifact Dreams** (what gets produced and tracked):
- `herald-pitch-family-expansion.md` → Pitch decks: file locations, artifact types, tracking decisions

**Enabling Technology Dreams** (capabilities, tools, engines):
- `deckcraft.md` → PPTX generation engine
- `modernist-identity.md` → Brand token system

**Vision Dreams** (overarching purpose):
- `pyforge-herald.md` → Four Moments of Proclamation

**Pros:** Very clear domain boundaries, each dream has a single clear purpose  
**Cons:** 6 files, but each domain is atomic and understandable

### Option 6: Factory Model (Input → Transform → Output)

**Input Source Dreams** (where data comes from):
- `design-code-bridge.md` → Input framework: Design prototypes from cloud (seed/pull)

**Transform Engine Dreams** (processing, generation):
- `deckcraft.md` → Transform: markdown → PPTX
- `video-scripts.md` → Transform: narration → video

**Output/Delivery Dreams** (what leaves the factory):
- `herald-pitch-family-expansion.md` → Output: 6 artifact formats for Pitch decks

**Governance/Constraint Dreams** (rules applied everywhere):
- `modernist-identity.md` → Constraints: brand tokens bound to all outputs
- `pyforge-herald.md` → Constraints: Four Moments framework governs all Herald work

**Pros:** Mimics factory mental model (inputs → processes → outputs)  
**Cons:** Governance dreams are meta-level, might be confusing

### Comparison Table

| Model | Files | Functionality | Features | Clarity |
|-------|-------|---------------|----------|---------|
| **Option 3** (Capabilities-Driven) | 6 | ✓✓ Clear | ✓✓ Clear | Good |
| **Option 4** (Layered Tiers) | 6 | ✓✓ Tiered | ✓✓ Clear | **Best** |
| **Option 5** (Domain-Separated) | 6 | ✓✓✓ Crisp | ✓✓ Clear | **Excellent** |
| **Option 6** (Factory Model) | 6 | ✓✓ Clear | ✓✓ Clear | Good |

**Recommendation:** **Option 4 (Layered)** or **Option 5 (Domain-Separated)** are strongest:
- **Option 4:** Clear hierarchy; Tier 1 capabilities are reusable for Moments 2–4
- **Option 5:** Crispest separation of concerns; easiest to understand what each dream owns

---

## Artifact Optimization Strategy (Aggressive)

**Decision**: Aggressive strategy (144 tracked files for 9 stations).

Today's 14 decks produce **270 tracked files** across design-code-bridge (design protos, markdown, PPTX, narration). The 9 pyforge-station Pitch Expansion will follow the **Aggressive strategy**, tracking all source-of-truth and final deliverable artifacts while gitignoring intermediate build outputs:

| Category | Artifact | Count | **Aggressive** | Regenerable? | Why |
|----------|----------|-------|---|----------|-------|
| **Source of Truth** | `{Station}.dc.html` (design protos) | 3-4 | ✓ TRACK | No | Design prototypes are immutable, etagged authority; capture authoring decisions |
| **Source of Truth** | `{station}.md` + variants (marp) | 5-8 | ✓ TRACK | From `.dc.html` | Version-controlled content; represents narrative structure and structure |
| **Source of Truth** | `{station}.pptx` + variants (editable) | 2-4 | ✓ TRACK | From `.md` + deckcraft | Final deliverable; preserves formatting/layout choices |
| **Source of Truth** | `{station}-narration-*.md` (video scripts) | 1-2 | ✓ TRACK | From Design notes | Version-controlled content for video pipeline |
| **Source of Truth** | `{station}-infographic.svg` (inline) | 0-1 | ✓ TRACK | From `.md` extract | Final deliverable; preserves visual design choices |
| **Build Artifact** | `src/slides/fragments/*.json` (marp parse) | 1 | ✗ GITIGNORE | `npm run extract` | Intermediate parse tree; regenerates in <1s |
| **Build Artifact** | `dist/index.html` (vite bundle) | 1 | ✗ GITIGNORE | `npm run build` | Bundled HTML; regenerates in <5s |
| **Build Artifact** | `dist/assets/*.{js,css}` (bundles) | 3-6 | ✗ GITIGNORE | `npm run build` | JS/CSS bundles; regenerate in <5s |
| **Build Artifact** | `{station}.mp4` (video render) | 0 | ✗ GITIGNORE | `bmad-manticore` | Video; regenerate on demand (expensive) |

**Key design principle**: The **source of truth** (Design proto) is immutable and authored once; everything else either derives from it or is a deliberate export format. Gitignoring intermediate parsing/bundling cuts the footprint by 62% without losing auditability (all source traces back to one Design file per station).

---

### Per-Station Customization

The framework stays constant. The content changes:

- **Copy/Content** — Thesis, pain point, solution pillars, ecosystem modules, personas (station-specific)
- **Visual Metaphors** — Domain-appropriate diagrams and symbols (warden: lattices/gates; marshal: policy composition; atlas: pipeline stages)
- **Color Accents** — Brand palette applied consistently (Modernist tokens)
- **Narration** — Station-specific speaker notes extracted for video production

## The Workflow (Four Stages)

### Stage 1: Spec & Content Generation (this Dream → bmad-spec)

Input: This Dream + the six-act framework + per-station briefs.

Output: **Spec-Herald-Pitch-Expansion** (one SPEC kernel capturing):
- The framework (six acts, L.A.T.C.H. principles, visual strategy per act)
- 21 station entries (slug, thesis, domain, pain point, solution pillars, ecosystem vision, personas)
- Design seeding contract (Modernist-bound starter prototype)
- Export checklist (all formats, per-station)

### Stage 2: Design Authoring (Human, Claude Design)

Input: Design projects seeded per-station (via `design-code-bridge` seed).

Process:
- Human refines prototype visually at claude.ai/design
- Edits are tracked by etag (conflicts caught, no overwrites)
- One prototype per station, 1920×1080, Archivo, brand palette

Output: 21 Design prototypes, each with speaker notes (fed to narration extraction).

### Stage 3: Code & Export (Herald + deckcraft + video-scripts)

Input: 21 Design prototypes.

Process:
1. **Pull** via `design-code-bridge` (Claude Code: "pull {station}" → read_file + etagged safety)
   - Output: `{Station}.dc.html` → tracked in git ✓
2. **Extract** via `npm run extract` (markdown source from `.dc.html`)
   - Output: `{station}.md` → tracked in git ✓
3. **Export** via `pixi run deck-export` + deckcraft:
   - `.pptx` (editable, python-pptx + deckcraft) → tracked ✓
   - `.svg` infographic (inline, no raster) → tracked ✓
4. **Build** via `npm run build` (HTML5 deck)
   - Parses `.md` → `src/slides/fragments/*.json` (gitignored, regenerable)
   - Builds vite bundle → `dist/index.html` + `dist/assets/*` (gitignored, regenerable)
5. **Narration** via `narration-extract` task:
   - Pull speaker notes from Design
   - Generate `*-narration-2026-08-01.md` → tracked ✓
6. **Video** via `bmad-manticore`:
   - Take narration + screen recordings + bibles
   - Render `.mp4` (Kokoro voice, HyperFrames graphics, real UI) (gitignored, regenerable)

Output: 
- **Tracked (~144 files)**: Design protos (3-4 each), markdown sources (5-8 each), PPTX exports (2-4 each), narration scripts (1-2 each), infographics (0-1 each)
- **Regenerable (rebuilds on `npm install && npm run build`)**: Fragments (.json), dist/ (HTML), assets/ (JS/CSS)
- **Total footprint**: ~16 tracked files per station × 9 = **144 files** (vs. 178 today unoptimized)

### Stage 4: Commit & Ship

Input: 126 artifacts.

Output: 21 decks across 6 formats, tracked in git, shipped to:
- `presentations/pyforge-{station}/dist/` (artifacts)
- Published to rxm7706.github.io (HTML + infographics)
- Slack notifications (via video-scripts moment 2: Progress)
- Release proclamations (via video-scripts moment 3: Success)

## What This Is Not

- Not new deck-authoring infrastructure (design-code-bridge already proven)
- Not a new export backend (deckcraft handles PPTX; `deck-export` handles others)
- Not a new video pipeline (manticore is upstream; this Dream feeds it)
- Not fabricated demos (all screen recordings are real)

It is the **orchestration of existing capabilities** to expand Moment 1 (Pitch) across the entire 21-station fleet in parallel, with automated round-trip and multi-format export.

## Kinships

[[pyforge-herald]] (the Four Moments framework) · [[design-code-bridge]] (round-trip automation) · [[modernist-identity]] (brand consistency) · [[deckcraft]] (PPTX backend) · [[video-scripts]] (narration + companion videos) · [[presentation-deck]] (export formats and artifact tree).

## Success Criteria

- [ ] 9 Design projects seeded (one per pyforge station), all using Modernist identity tokens
- [ ] 9 prototypes authored and refined per six-act framework (Design layer)
- [ ] 9 × 6 artifact sets exported and committed:
  - [ ] Design prototypes (.dc.html) tracked
  - [ ] Markdown sources (marp) tracked
  - [ ] PPTX exports (editable) tracked
  - [ ] Narration scripts (.md) tracked
  - [ ] Infographic SVGs tracked
  - [ ] Built outputs (fragments, dist/, assets/) gitignored (regenerable)
- [ ] All HTML decks render and pass `dashboard-check`
- [ ] All PPTX files editable in PowerPoint
- [ ] All infographics render as inline SVG (none are raster)
- [ ] All narration scripts extracted and available for video-scripts integration
- [ ] Zero manual file transfers between Design and Code (design-code-bridge automation end-to-end)
- [ ] Total tracked footprint: ~144 files (vs. 178 today unoptimized)

## Realization Log

- **2026-08-01 (this session)** — Dream seeded from user's vision of "Herald has moments, supporting capabilities, and a master dream that can create a collection of artifacts." Six-act framework (canonical reference) authored as the structural backbone. Architecture: one source (Design) → multiple outputs (PPTX, HTML, MD, SVG, MP4).
