# Seven-Step Workflow: Design → Extract → Build → Export → Ship

Complete workflow pipeline for Herald Pitch Expansion from Design authoring to multi-format export and delivery.

---

## Stage 1: Spec & Content Generation

**Owner**: BMAD (spec-driven development)  
**Input**: This Dream + six-act framework + per-station briefs  
**Output**: Spec kernel + companion files (this directory)  
**Duration**: ~2-4 hours (first time)

**What happens:**
- Dream analyzed for Vision (Tier 0) + Capabilities (Tier 1) + Features (Tier 2)
- Five-field kernel distilled: Why, Capabilities, Constraints, Non-goals, Success Signal
- Companion files generated: artifact matrix, workflow stages, six-act framework, station roster
- All decisions logged to `.memlog.md` (canonical source of truth)

**Outputs:**
- ✓ SPEC.md kernel (5 fields, 7 capabilities)
- ✓ .memlog.md (decision log)
- ✓ Companion files (artifact tracking, workflow, framework, stations)

**Who does it**: BMAD skills (`bmad-spec` → `bmad-prd` → `bmad-architecture` → `bmad-create-epics-and-stories`)

---

## Stage 2: Design Authoring

**Owner**: Human (visual designer)  
**Input**: Design seeding (via herald CLI or Design → Code bridge)  
**Output**: 9 Design prototypes, each with speaker notes + visual refinements  
**Duration**: Hours to days (human creative iteration)

**What happens:**
- User creates or opens a Design project in claude.ai/design
- Prototype imported (1920×1080, Archivo, Modernist palette, six-act structure)
- Visual iteration: refine cover hook, fill acts I-VI per the framework, add persona appendix
- Speaker notes written per act (input for narration extraction)
- Etagged protocol ensures conflicts are detected, not overwritten

**Artifacts created in Design:**
- `.dc.html` prototype (source of truth, immutable)
- Speaker notes (fed to narration extraction later)
- Visual variants (cover, extended) if needed

**Status tracking:**
- Each prototype has a ready-for-pull checklist
- Design cloud preserves all edits via etagged transfers
- No code-side copies exist until pull

---

## Stage 3: Pull (Design → Code)

**Owner**: Herald CLI + design-code-bridge  
**Input**: Finalized Design prototypes (from Stage 2)  
**Output**: `.dc.html` files in `project/`; `.md` files extracted to `src/marp/`  
**Duration**: <2 seconds per deck  

**What happens:**

**Step 3a: Pull Design Prototype**
```bash
herald deck pull pyforge-marshal
# Calls: design-code-bridge → read_file(.../{station}.dc.html, etag=<old_etag>)
# Checks: etag match (conflicts detected, aborted if mismatch)
# Writes: project/{station}.dc.html (tracked in git)
```

**Step 3b: Extract Markdown**
```bash
npm run extract
# Calls: marp-parse on .dc.html → slide JSON parse tree
# Generates: src/marp/{station}.md + variants (cover, extended, etc.)
# Tracks: All .md files in git
```

**Outputs:**
- ✓ `project/{station}.dc.html` → tracked (source of truth)
- ✓ `src/marp/{station}.md` → tracked (markdown content)
- ✓ `src/marp/{station}-cover.md` → tracked
- ✓ `src/marp/{station}-extended.md` → tracked
- ✓ `src/slides/fragments.json` → gitignored (regenerable)

**Etagged safety:**
- Design cloud + Code both hold etags
- If Design edited since last pull, etag changes
- Next pull fails if etags don't match; user resolves conflict
- No silent overwrites possible

---

## Stage 4a: Build HTML & Fragments

**Owner**: npm (Vite) + marp  
**Input**: `src/marp/*.md` files  
**Output**: `src/slides/fragments.json` + `dist/index.html` + `dist/assets/*.{js,css}`  
**Duration**: ~10–15 seconds total  

**What happens:**
```bash
npm run build
# Step 1: marp parse → src/slides/fragments/*.json (intermediate parse tree)
# Step 2: Vite bundle → dist/index.html + dist/assets/* (minified, optimized)
# Step 3: Output ready for browser viewing or CDN delivery
```

**Outputs:**
- ✗ `src/slides/fragments/*.json` → gitignored (regenerable <1s)
- ✗ `dist/index.html` → gitignored (regenerable <5s)
- ✗ `dist/assets/*.{js,css}` → gitignored (regenerable <5s)

**Live preview:**
```bash
npm run dev
# Vite dev server; hot-reload on .md changes; live iteration feedback
```

---

## Stage 4b: Extract Narration

**Owner**: narration-extract task (pixi)  
**Input**: Design speaker notes from `project/{station}.dc.html`  
**Output**: `src/marp/{station}-narration-2026-08-01.md` (machine-extracted)  
**Duration**: <1 second per deck  

**What happens:**
```bash
pixi run narration-extract pyforge-marshal
# Step 1: Read Design proto ({station}.dc.html)
# Step 2: Extract speaker notes from Design
# Step 3: Parse into scene/visual/voiceover triples (322 scenes per master script)
# Step 4: Generate markdown narration file
# Step 5: Validate against blacklist (script linter enforces brand voice)
```

**Outputs:**
- ✓ `src/marp/{station}-narration-2026-08-01.md` → tracked (video pipeline input)
- ✓ `src/marp/{station}-narration-cover-2026-08-01.md` → tracked (if produced)

**Quality gates:**
- Linter ensures narration voice matches brand (WPM, speech patterns, blacklist)
- Reject non-matching narration; require re-record or edit

---

## Stage 5: Export (Deckcraft + SVG)

**Owner**: deckcraft + svg-extraction  
**Input**: `src/marp/{station}.md` + Modernist design tokens  
**Output**: `src/pptx/{station}.pptx` + `src/marp/{station}-infographic.svg`  
**Duration**: ~5–10 seconds per deck  

**What happens:**

**Step 5a: Deckcraft PPTX Export**
```bash
pixi run deck-export
# Step 1: Read markdown source
# Step 2: Load Modernist design tokens (Archivo, palette, grid)
# Step 3: python-pptx generates PPTX structure
# Step 4: Apply tokens: fonts, colors, slide layouts
# Step 5: Output editable PowerPoint file
```

**Step 5b: SVG Infographic Extraction**
```bash
npm run extract-infographic
# Step 1: Parse markdown for diagrams/visual sections
# Step 2: Convert to inline SVG (no raster)
# Step 3: Apply Modernist design tokens
# Step 4: Output {station}-infographic.svg
```

**Outputs:**
- ✓ `src/pptx/{station}.pptx` → tracked (deliverable, editable)
- ✓ `src/pptx/{station}-cover.pptx` → tracked (if produced)
- ✓ `src/pptx/{station}-extended.pptx` → tracked (if produced)
- ✓ `src/pptx/{station}-appendix.pptx` → tracked (if produced)
- ✓ `src/marp/{station}-infographic.svg` → tracked (inline, no raster)

**Quality gates:**
- [ ] Open PPTX in PowerPoint; verify fonts, colors, layouts correct
- [ ] SVG renders without raster fallback; all shapes are vectors

---

## Stage 6: Video (Manticore Render)

**Owner**: bmad-manticore (external pipeline)  
**Input**: Narration scripts (`src/marp/{station}-narration-*.md`) + screen recordings + brand bibles  
**Output**: `{station}.mp4` (+ optional `.edl`, `.fcpxml`)  
**Duration**: ~30–60 seconds per video (expensive)  

**What happens:**

**Step 6a: Outline**
- Input: Narration markdown (322 scenes per master script)
- Process: Manticore reads outline, maps to scene/visual/voiceover triples

**Step 6b: Cut Plan**
- Generate timing & EDL from narration
- Sync voiceover beats to visual cuts

**Step 6c: Graphics Beats**
- Layer HyperFrames motion graphics (brand-themed overlays, kinetic captions)
- Apply Modernist tokens (color, typography)
- No fabricated UI; only real screen recordings

**Step 6d: Final Render**
- Kokoro-82M narration (voice bible sourced from published transcripts)
- MusicGen bed (brand-appropriate ambient score)
- AudioLDM2 SFX (approved, not synthetic)
- Output `.mp4` codec: H.264, ~100MB per video

**Outputs:**
- ✗ `{station}.mp4` → gitignored (regenerable, expensive)
- ✗ `{station}.edl` → gitignored (optional, regenerable)

**Quality gates:**
- [ ] All b-roll is real (no AI-generated UI)
- [ ] Voice narration matches brand bible
- [ ] Graphics beats sync to narration
- [ ] Final render plays without errors

---

## Stage 7: Commit & Ship

**Owner**: git + publishing pipeline  
**Input**: All staged files (tracked artifacts only)  
**Output**: Committed to git, pushed to origin, published to deliverables  
**Duration**: ~5–10 minutes (includes review)  

**What happens:**

**Step 7a: Stage Tracked Artifacts**
```bash
git add project/ src/marp/ src/pptx/
# Stage: Design protos, markdown, PPTX, narration, SVG
# Ignore: fragments.json, dist/, assets/, .mp4
```

**Step 7b: Commit**
```bash
git commit -m "feat(herald): Pitch Expansion — 9 stations, six-act framework, multi-format export

- 9 Design projects seeded (Marshall, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald)
- 9 prototypes authored per six-act framework
- 9 × 6 artifact sets: design protos, markdown, PPTX, narration, SVG, video scripts
- Total tracked: 144 files (design protos 27-36, markdown 45-63, PPTX 27-36, narration 9-18, SVG 9)
- Gitignored: fragments, dist/, assets/, video (regenerable, -62% footprint reduction)
- All formats render correctly; dashboard-check passes; etagged safety verified"
```

**Step 7c: Push & Publish**
```bash
git push origin feature/herald-pitch-family-expansion
# Triggers CI: linting, tests, dashboard-check, security scans
# On green: publish to rxm7706.github.io/presentations/
# Ship PPTX/video to releases (CDN-backed)
```

**Outputs:**
- ✓ Committed to git (tracked files only; regenerables ignored)
- ✓ Pushed to origin
- ✓ Published to GitHub Pages (HTML + SVG)
- ✓ Released to CDN (PPTX + video)
- ✓ Notified via Slack (via Herald moment 2: Progress)

**Quality gates:**
- [ ] CI passes (linting, tests, dashboard-check)
- [ ] All artifacts present + correct format
- [ ] GitHub Pages live + renders
- [ ] CDN delivery working (PPTX/video downloads)
- [ ] Team notified

---

## Regeneration Paths

### Fast Path (Source + Deliverables Tracked)

```bash
git clone <repo>
npm install
npm run build              # Regenerate fragments, dist/ (10–15s)
pixi run deck-export       # Regenerate PPTX from markdown (5–10s per station)
# Result: All 6 formats ready in ~30s, zero external calls
```

### Complete Path (Include Video)

```bash
git clone <repo>
npm install
npm run build
pixi run narration-extract <station>   # Regenerate from Design speaker notes (1s)
pixi run deck-video <station>          # Render video via manticore (30–60s per station)
# Result: All 6 formats + video ready in ~90s–120s per station
```

### Minimal Path (Design + Markdown Only)

```bash
git clone <repo>
npm install
# Markdown sources available immediately; use for content review/edit
```

---

## Workflow Diagram

```
┌─ Stage 1: Spec ─────────────────────────────────────────┐
│ Dream → SPEC.md (kernel + companions)                   │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─ Stage 2: Design ───────────────────────────────────────┐
│ Human iterates in claude.ai/design                       │
│ Input: Seeded prototype (1920×1080, Archivo)            │
│ Output: 9 `.dc.html` protos + speaker notes             │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─ Stage 3: Pull ────────────────────────────────────────┐
│ herald deck pull <slug> → Design → Code (etagged)      │
│ Input: 9 `.dc.html` protos from Design                 │
│ Output: `.dc.html` (tracked) + `.md` extracted         │
└─────────────────────────────────────────────────────────┘
                           ↓
        ┌──────────────────┴──────────────────┐
        ↓ 4a                                   ↓ 4b
   ┌─ HTML/Build ──┐              ┌─ Narration ──┐
   │ npm run build  │              │ narration-    │
   │ Fragments.json │              │  extract      │
   │ dist/ (ign)    │              │ Script .md    │
   └────────────────┘              └───────────────┘
        ↓                                   ↓
        └──────────────────┬─────────────────┘
                           ↓
┌─ Stage 5: Export ──────────────────────────────────────┐
│ pixi run deck-export                                    │
│ Input: markdown + Modernist tokens                      │
│ Output: PPTX (tracked) + SVG (tracked)                 │
└─────────────────────────────────────────────────────────┘
                           ↓
             ┌─────────────┴─────────────┐
             ↓ 6a                        ↓ 7
        ┌─ Video ──────┐    ┌─ Commit & Ship ──────┐
        │ manticore     │    │ git add/commit/push   │
        │ render .mp4   │    │ CI → GitHub Pages     │
        │ (ign, regen)  │    │ CDN release PPTX/mp4  │
        └───────────────┘    └──────────────────────┘
             ↓                        ↓
      [CDN delivery]          [Published live]
```

---

## Checklist: Seven Stages

- [ ] **Stage 1**: Spec produced (SPEC.md + companions + .memlog.md)
- [ ] **Stage 2**: 9 Design projects seeded; prototypes authored; speaker notes complete
- [ ] **Stage 3**: All 9 `.dc.html` protos pulled; all `.md` variants extracted
- [ ] **Stage 4a**: `npm run build` passes; HTML renderss; fragments regenerable
- [ ] **Stage 4b**: Narration scripts extracted; linter passes (voice brand check)
- [ ] **Stage 5**: PPTX exports regenerable (<10s); SVG infographics inline (no raster)
- [ ] **Stage 6**: Video renders available (or deferred to second pass); CDN-ready
- [ ] **Stage 7**: All files committed; CI green; published to GitHub Pages + CDN

---

## Timing Summary

| Stage | Duration | Parallelizable? | Notes |
|-------|----------|-----------------|-------|
| 1: Spec | 2–4 hours | ✓ | BMAD skills (spec → PRD → arch → epics) |
| 2: Design | Hours–days | ✓ | 9 stations in parallel (human creative) |
| 3: Pull | <2s × 9 | ✓ | Linear, per-station (< 20s total) |
| 4a: Build | 10–15s | ✗ | Single Vite run (all stations) |
| 4b: Narration | <1s × 9 | ✓ | Per-station, parallel |
| 5: Export | 5–10s × 9 | ✓ | Per-station, parallel (deckcraft) |
| 6: Video | 30–60s × 9 | ✓ | Per-station, parallel (manticore) |
| 7: Commit | 5–10 min | ✗ | Linear (includes review + CI) |
| **TOTAL** | **1–2 days** | **Mostly** | Design is the long pole; others highly parallelizable |

**Parallel strategy**: Stages 2, 4b, 5, 6 can run in parallel across 9 stations. Stage 4a (build) is single-run. Stage 7 is linear (review + CI). **Optimize for design iteration time, not for pipeline parallelism.**
