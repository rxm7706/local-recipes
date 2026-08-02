---
title: Herald's Pitch Deck Family Expansion — PRD
slug: herald-pitch
status: final
created: 2026-08-01
updated: 2026-08-01
project: pyforge-herald
spec_source: spec-herald-pitch/SPEC.md
dream_source: docs/dreams/herald-pitch.md
---

# Herald's Pitch Deck Family Expansion — PRD

**Product**: Herald Pitch Deck orchestration across 9 PyForge stations, producing 6 artifact formats per station from a single Design source.

**Scope**: Moment 1 (Pitch) of Herald's Four Moments of Proclamation framework, orchestrating Design-Code-Bridge, Deckcraft, Video-Scripts, and Modernist-Identity capabilities into a cohesive, multi-format deck family.

---

## Vision

Herald is the factory's **voice and visual surface**. Invisible engineering is failed engineering. Herald's work spans four continuous **Moments of Proclamation**:

1. **Pitch** — A dream must be argued, not merely filed (THIS EFFORT)
2. **Progress** — A build in flight is not self-explaining
3. **Success** — Shipping is not the same as being known to have shipped
4. **Operations** — The long tail nobody announces

**Moment 1 (Pitch)** is the first time Herald has something to do: making the case legible to humans who did not dream it. This PRD orchestrates Moment 1 across **9 PyForge stations** using proven Tier 1 capabilities, producing **6 artifact formats per station** from a single Design source, with zero manual file transfers.

**Core Insight**: One source of truth (Design prototype) → Multiple deliverable formats → Automated round-trip → Fully tracked, regenerable pipeline.

---

## Problem & Opportunity

**Today's State:**
- 7 PyForge station decks exist, authored on ad-hoc basis
- Design-Code-Bridge framework proven but not standardized across stations
- Multiple export formats (PPTX, HTML, SVG) require manual coordination
- Video production pipeline (bmad-manticore) lacks narrative input from decks
- Visual inconsistency across decks (brand tokens not applied uniformly)

**The Gap:**
- No systematic way to author, export, and maintain pitch decks for all 9 stations in parallel
- Each deck requires separate handling; no reusable pattern
- Narrator scripts for video production are manual and error-prone
- Artifacts stored in various locations, not optimized for git tracking

**The Opportunity:**
- Standardize deck authoring with Tier 1 capabilities (Design-Code-Bridge, Deckcraft, Video-Scripts, Modernist-Identity)
- One workflow for all 9 stations → zero re-engineering
- Automatic round-trip from Design to Code, producing 6 formats in parallel
- Feed narration scripts automatically to video pipeline
- Aggressive optimization: track source + finals, gitignore intermediates (62% footprint reduction)

---

## Audience & Success Metrics

### Audience

- **Primary**: PyForge operators, deckhands, and presenters (need pitch decks in multiple formats for talks, proposals, video)
- **Secondary**: Video production pipeline (bmad-manticore) (consumes narration scripts extracted from Design speaker notes)
- **Tertiary**: Design system curators (apply Modernist identity across all surfaces)

### Success Criteria

**Design & Seeding**
- ✓ 9 Design projects seeded (one per PyForge station), all bound to Modernist design system
- ✓ 9 prototypes authored and iterated in Design layer per six-act framework
- ✓ Seeding contract established (1920×1080, Archivo, family palette)

**Artifacts & Export**
- ✓ 9 × 6 artifact sets (54 total) exported and tracked:
  - Design protos (`.dc.html`) — tracked
  - Markdown sources (marp `.md`) — tracked
  - PPTX exports (editable) — tracked
  - Narration scripts (`.md`) — tracked
  - Infographics (inline `.svg`) — tracked
  - Build outputs (fragments.json, dist/, .mp4) — gitignored, regenerable
- ✓ Design protos (.dc.html) tracked in `project/`
- ✓ Markdown sources tracked in `src/marp/`
- ✓ PPTX exports tracked in `src/pptx/`
- ✓ Narration scripts tracked alongside markdown
- ✓ SVG infographics inline, never raster
- ✓ Build outputs gitignored (regenerable in <5s for HTML, <60s for video)

**Quality & Rendering**
- ✓ All 9 HTML decks render without error; dashboard-check passes
- ✓ All 9 PPTX files open and edit in Microsoft PowerPoint; fonts/colors/layouts preserved
- ✓ All infographics render as inline SVG (zero `.png`/`.jpg`)
- ✓ All decks follow six-act structure with ~28 slides, 90KB+ class, inline SVGs

**Integration & Automation**
- ✓ All 9 narration scripts extracted from Design speaker notes; available for manticore
- ✓ Zero manual file transfers (Design-Code-Bridge automation end-to-end)
- ✓ All etagged transfers validated (conflicts caught, no overwrites)
- ✓ Regeneration strategy proves <5% build-time cost

**Footprint**
- ✓ Total tracked files: ~144 (9 stations × ~16 files per station) vs. ~270 unoptimized
- ✓ 62% reduction achieved; gitignored intermediates deterministically regenerable

---

## Capabilities

### CAP-1: Design-Code-Bridge Framework

**What it delivers:**
- Seed Design projects per station (one-time, ~30s, `herald deck seed <station>`)
- Pull updated Design protos into Code with etagged safety (round-trip, <2s, `herald deck pull <station>`)
- Extract markdown sources from Design protos (automated, `npm run extract`)
- Zero manual file transfers between Design cloud and Code repository
- Conflict detection via etags; silent overwrites prevented

**Why it matters:**
- Unifies design authoring (Claude Design visual surface) with code version control
- Proven on 7 existing decks; no new infrastructure required
- Etagged protocol ensures data safety across Design ↔ Code transfers

**Success Signal:**
- Prototype round-trips seamlessly; etags catch conflicts; zero manual downloads

---

### CAP-2: Deckcraft Framework

**What it delivers:**
- Transform markdown sources into editable PowerPoint files
- Apply Modernist design tokens (fonts, colors, layouts) via python-pptx
- Generate PPTX files that preserve both structure and manual-editability
- Deterministic output; regenerable in 5–10s per deck

**Why it matters:**
- PowerPoint is non-negotiable for enterprise/presenter workflows
- Programmatic generation ensures consistency; manual editability preserves agent refinement
- Tokens round-trip through Figma ↔ PPTX ↔ deck engine ↔ video pipelines

**Success Signal:**
- All 9 PPTX files open in Microsoft PowerPoint; fonts, colors, layouts preserved

---

### CAP-3: Video-Scripts Framework

**What it delivers:**
- Extract narration scripts mechanically from Design speaker notes
- Generate `{station}-narration-YYYY-MM-DD.md` files per deck
- Feed narration corpus to bmad-manticore (voice, graphics, screen recordings, SFX)
- Four hard gates enforce no fabricated demos: Outline → Cut Plan → Graphics Beats → Final Render
- Voice bible enforces character consistency (WPM, speech patterns, tone markers)

**Why it matters:**
- Decks are static; videos amplify them across audiences (async viewing, search discovery)
- Narration extraction is mechanical, error-free, deterministic
- Real footage only; no synthetic UI or AI-generated demos

**Success Signal:**
- All 9 narration scripts extracted and available for video pipeline; zero fabricated UI

---

### CAP-4: Modernist-Identity Framework

**What it delivers:**
- One design system across all PyForge surfaces (decks, dashboards, docs, videos)
- Visual tokens: Flat architecture, Archivo font, light palette (#f3f2f2), ink (#201e1d), red accent (#ec3013/#c22a10)
- Grid discipline: visible grid, 2px rules, zero corner radius, flush-left labels, black-and-white photography
- Tokens round-trip: Figma variables → design-tokens JSON → PPTX templates → deck engine → video bibles
- Applied consistently to all 9 station decks

**Why it matters:**
- Consistency builds recognition and professionalism
- Token system enables safe round-trip (Design ↔ Code ↔ Video)
- One source of truth for visual language

**Success Signal:**
- Modernist design system adopted across all Herald family decks; tokens ready for round-trip

---

### CAP-5: Six-Act Deck Framework

**What it delivers:**
- Canonical structure for all pitch decks (8 sections):
  1. **Cover**: Hook + thesis statement
  2. **Act I**: Friction — problem framing (pain point)
  3. **Act II**: Insight — solution introduction (aha moment)
  4. **Act III**: Mechanics — 4-step delivery (L.A.T.C.H. Time)
  5. **Act IV**: Real-World — enterprise fit (L.A.T.C.H. Location)
  6. **Act V**: Vision — future & scaling (L.A.T.C.H. Category)
  7. **Act VI**: Action — CTA + command
  8. **Appendix**: Personas — stakeholder context

- Visual principles: L.A.T.C.H. (Location, Analogy, Time, Color, Hierarchy)
- Depth: ~28 slides per deck, 90KB+ class, inline SVGs, full editorial depth
- Consistency: Applied to all 9 stations

**Why it matters:**
- Narrative structure ensures every deck tells a coherent story
- L.A.T.C.H. principles make visual hierarchy self-evident
- Personas appendix preserves voting records and stakeholder context
- Depth ensures material is usable as self-contained reference or extracted snippets

**Success Signal:**
- All 9 decks follow six-act structure; all contain persona appendices; all render full depth

---

### CAP-6: Multi-Format Export Pipeline

**What it delivers:**
- 6 artifact formats per station from single Design prototype:
  1. **Design protos** (.dc.html) — source of truth, etagged, tracked
  2. **Markdown sources** (marp `.md`) — version-controlled content
  3. **PPTX exports** (editable) — python-pptx output, presentable, editable
  4. **Narration scripts** (`.md`) — video production input
  5. **Infographics** (inline `.svg`) — static visuals, no raster
  6. **HTML decks** (interactive) — Vite bundle, gitignored (regenerable <5s)

- Tracking strategy: Track source + finals; gitignore intermediates
  - Track: `.dc.html`, `.md`, `.pptx`, narration, `.svg` (~16 files per station)
  - Gitignore: `fragments.json`, `dist/`, `assets/`, `.mp4` (~8 files per station)

- Optimization: ~144 tracked files for 9 stations (vs. 270 unoptimized, 62% reduction)

**Why it matters:**
- One source of truth (Design) produces multiple deliverables for different audiences
- Tracking strategy balances git footprint, deliverable velocity, and regenerability
- No manual file transfers; automation end-to-end

**Success Signal:**
- All 6 formats available per station; tracked/gitignored split correct; regeneration validates

---

### CAP-7: Station-Specific Customization

**What it delivers:**
- Apply framework consistently across 9 PyForge stations with domain-appropriate content
- Per-station content: Thesis, pain point, solution pillars, ecosystem vision, personas
- Per-station visuals: Domain-appropriate diagrams (warden: lattices/gates; marshal: policy composition; atlas: pipeline stages)
- Per-station voice: Extracted from Design speaker notes for narration pipeline
- Consistent framework across all: Six-act structure, Modernist identity, design bridge, deckcraft pipeline

**The 9 Stations:**
1. **Marshal** — Policy composition, configuration, state orchestration
2. **Warden** — Compliance gates, audit, dependency validation
3. **Atlas** — Federation, discovery, package intelligence pipeline
4. **Mason** — Build orchestration, artifact generation, reproducible recipes
5. **Steward** — Ecosystem governance, versioning, stability
6. **Scribe** — Documentation, knowledge capture, narrative
7. **Genesis** — Template generation, project scaffolding
8. **Doctor** — Health & diagnostics, troubleshooting
9. **Herald** — Proclamation, messaging, visibility (meta-station)

**Why it matters:**
- Each station has distinct domain, audience, and narrative needs
- Customization at content level; framework stays constant
- Zero re-engineering per station; one pattern scales to N

**Success Signal:**
- 9 Design projects seeded; 9 prototypes authored per six-act framework; 9 × 6 artifact sets committed

---

## Constraints

1. **Design source of truth**: Single Design prototype per station is immutable, etagged, tracked as `.dc.html`. All code-side artifacts derive from it. No direct editing of code-side copies.

2. **Tracked vs. gitignored**: Aggressive optimization strategy.
   - Track: design protos (3–4), markdown (5–8), PPTX (2–4), narration (1–2), infographics (0–1)
   - Gitignore: fragments (.json), dist/ (HTML), assets/ (JS/CSS), videos (.mp4) — all regenerable

3. **Etagged safety**: All Design ↔ Code transfers use etags. Conflicts detected, never silent overwrites. Protocol: read-file includes etag; write-file requires matching etag or fails explicitly.

4. **No fabricated demos**: All screen recordings in video output are real. Never use AI-generated UI or synthetic mockups. Manticore receives real footage + real narration only.

5. **Narration identity**: Voice bible derived from published transcripts (WPM, speech patterns, tone markers). Blacklist enforced by script linter; all narration passes linter before video render.

6. **Multi-surface readiness**: Decks ship as interactive HTML (Vite), editable PPTX (python-pptx), static SVG infographics (inline), and video scripts (text). Every format must be production-ready; no "preview" or "draft" states in shipping.

7. **Six-act framework**: All decks follow canonical structure (Cover, Acts I–VI, Appendix). Deviations allowed only for station-specific content within the frame.

8. **Design system binding**: All 9 Design projects bound to Modernist identity tokens at seeding time. Visual consistency enforced at design-time, not post-hoc.

---

## Non-Goals

**New deck-authoring infrastructure**: Design-Code-Bridge already proven on 7 decks. This effort reuses it; does not rebuild or redesign it.

**New export backends**: Deckcraft handles PPTX; `deck-export` CLI handles HTML, SVG, others. This effort composes existing tools; does not invent new ones.

**New video pipeline**: bmad-manticore is upstream and independent. This effort feeds narration scripts and real screen recordings to it; does not implement the video renderer.

**Real-time collaboration**: Design cloud iterates in real-time; pull model is explicit. Not a goal to sync live or to merge-edit on the Code side.

**Personas beyond context**: Appendix personas provide stakeholder context and voting records; not product personas or marketing segmentation.

**Continuous video export**: Videos are regenerable but expensive. Not a goal to auto-render all 9 videos on every PR; video render happens on-demand or by batch job.

---

## Scope

### In Scope

- Seed Design projects for 9 PyForge stations
- Author prototypes per six-act framework in Design layer
- Pull Design protos into Code with etagged safety
- Extract markdown sources, PPTX exports, narration scripts, infographics
- Build interactive HTML decks (Vite)
- Establish tracking strategy (~144 files, 62% reduction)
- Extract narration scripts for video pipeline
- Validate all artifacts (render checks, format checks, consistency checks)
- Commit and ship to git

### Out of Scope

- Rendering videos (handled by bmad-manticore downstream)
- Real-time Design ↔ Code sync (pull model only)
- Personas as product segmentation (context only)
- New deck-authoring or export tools
- Continuous video export automation

---

## Workflow Stages

### Stage 1: Design & Seeding
- Create Design projects per station
- Seed with contract-compliant starter prototype (1920×1080, Archivo, Modernist palette)
- Bind to Modernist design system

### Stage 2: Authoring (Human in Claude Design)
- Iterate visually at claude.ai/design
- Add speaker notes (fed to narration extraction)
- Finalize prototype per six-act framework

### Stage 3: Pull & Extract (Automated)
1. Pull Design proto into Code (etagged safety)
2. Extract markdown from `.dc.html`
3. Extract narration from speaker notes
4. Build HTML deck (Vite)
5. Export PPTX (deckcraft)
6. Extract/render SVG infographics

### Stage 4: Validation & Ship
- Render checks (HTML, PPTX, SVG all valid)
- Consistency checks (font, color, layout across all 9)
- Commit tracked artifacts to git
- Publish HTML to presentation site
- Stage narration scripts for video pipeline

---

## Dependencies & Integrations

**Tier 1 Capabilities (Reused)**:
- Design-Code-Bridge (seed, pull, etagged round-trip)
- Deckcraft (markdown → PPTX)
- Video-Scripts (narration extraction, script composition)
- Modernist-Identity (design tokens, visual language)

**External Integrations**:
- Claude Design (visual authoring, speaker notes)
- Vite (HTML deck bundling)
- python-pptx (PPTX generation)
- bmad-manticore (video render, downstream)

**Artifacts**:
- Herald CLI (`seed`, `pull`, `watch`, `stale-mirror`, `export` commands)
- Pixi tasks (`deck-export`, `narration-extract`, `dashboard-check`)
- Design system tokens (Modernist-Identity project in Design)
- Presentation site (rxm7706.github.io or similar)

---

## Open Questions

1. **Station-by-station review cadence**: Should each station's deck be reviewed in isolation or as a family batch? *Suggest: family batch after all 9 drafted; catches inconsistencies.*

2. **Video render priority**: Should all 9 station videos render at completion, or pilot subset (Marshal, Warden, Atlas)? *Suggest: pilot subset; full batch on second pass.*

3. **Narration extraction tooling**: Automated within pixi tasks or manual via Design UI? *Suggest: automated pixi task with manual review of quality.*

4. **Infographic tracking**: Track regenerable SVGs or generate on-demand? *Suggest: track finals; regenerable in <1s.*

5. **Presentation site hosting**: Where do HTML decks live? (rxm7706.github.io, presentations.*, local?)

---

## Assumptions

- Design-Code-Bridge framework continues to work as proven on 7 existing decks
- Deckcraft pipeline stable and deterministic
- bmad-manticore available for video pipeline integration
- All 9 station narratives can be extracted mechanically from Design speaker notes
- Modernist design system tokens are current and applicable to all 9 stations
- Git footprint budget accommodates ~144 tracked files

---

## Measurement & Iteration

### Phase 1 Validation
- [ ] 3 Design projects seeded (pilot: Marshal, Warden, Atlas)
- [ ] 3 prototypes authored (Design layer)
- [ ] 3 × 6 artifact sets extracted and validated
- [ ] HTML render check passes; PPTX opens in PowerPoint; SVGs render as inline
- [ ] Narration scripts extracted; sample sent to manticore for proof-of-concept video

### Phase 2 Scale
- [ ] Remaining 6 stations seeded and authored
- [ ] All 9 × 6 artifact sets committed
- [ ] Family consistency review (narrative structure, visual application, tone)
- [ ] Full narration corpus ready for video pipeline
- [ ] Footprint validated (target: ~144 tracked files)

### Iteration & Refinement
- Design feedback loops (Design ↔ Code via etags)
- Narration quality review (script linter, voice bible)
- Video render feedback (manticore → Herald → speaker notes update)
- Modernist consistency review across all 9 (token application, visual language)

---

## Success Signals (Terminal)

**All must pass before marking complete:**

1. ✓ 9 Design projects seeded, prototypes authored, all 9 × 6 artifact sets committed
2. ✓ All 9 HTML decks render without error; dashboard-check passes
3. ✓ All 9 PPTX files open and edit in Microsoft PowerPoint
4. ✓ All infographics inline SVG (zero raster)
5. ✓ All narration scripts extracted and available for video pipeline
6. ✓ Zero manual file transfers (design-code-bridge automation validated end-to-end)
7. ✓ Etagged transfers validated (conflicts caught, no overwrites)
8. ✓ Tracked footprint: ~144 files vs. ~270 unoptimized (62% reduction achieved)

---

## Roadmap: Next Steps (Post-PRD)

1. **Architecture Spec** (`bmad-architecture`) — Design & tech specs for Design-Code-Bridge, Deckcraft pipeline, Modernist tokens, Vite build, Herald CLI
2. **Epics & Stories** (`bmad-create-epics-and-stories`) — Decompose into actionable stories (seed, design, pull, extract, build, export, validate, ship per station/format)
3. **Implementation** (`bmad-quick-dev` or `bmad-dev-auto`) — Execute stories via Herald CLI, Pixi tasks, Design authoring, manual validation gates

---

## Metadata

- **PRD Created**: 2026-08-01
- **Status**: Draft (ready for architecture → epics decomposition)
- **Project**: pyforge-herald (Tier 2: Moment 1 Orchestration)
- **Spec Source**: `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-pitch/SPEC.md`
- **Dream Source**: `docs/dreams/herald-pitch.md`
- **Reviewer**: (pending)
