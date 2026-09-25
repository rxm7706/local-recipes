---
fr-derivation-from: "2026-09-17"
title: Herald's Pitch Deck Family Expansion — PRD
slug: herald-pitch
status: final
created: 2026-08-01
updated: "2026-09-25"   # RE-STAMPED 2026-09-25: chain-currency (spec->prd) — spec-pyforge-herald memlog moved 2026-09-25T04:02 (steward 59.6 surface reconcile); no FR change. Prior 2026-09-20
project: pyforge-herald
spec_source: spec-pyforge-herald/SPEC.md (formerly spec-herald-pitch/SPEC.md, folded in 2026-08-02)
dream_source: docs/dreams/pyforge-herald.md
---

> **Consolidated 2026-08-02.** This PRD is now the single canonical PRD for the
> `pyforge-herald` station (explicit, same-day user override of the keep-chains-separate
> convention). The content through "## Metadata" below is unchanged from its original
> 2026-08-01 authoring. Herald's other live PRD — **Moments 2–4** (`herald-moments-2-4`,
> `prd-herald-moments-2-4-2026-08-02/prd.md`) — is folded in verbatim below as
> `## Satellite: Herald's Proclamation Surfaces — Moments 2–4`; its own folder has been
> archived at `archive/_bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-herald-moments-2-4-2026-08-02/`
> (original, unmodified). Its source Spec (`spec-herald-moments-2-4`) and Architecture
> (`architecture-herald-moments-2-4-2026-08-02`) are likewise folded into this station's
> single Spec and Architecture — see those documents for the equivalent notes.

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
- ✓ All 9 HTML decks render without error; `retired-console-check` passes (renamed from `dashboard-check`, deleted with the Guildhall generator — steward 30.2, 2026-08-25)
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
- Pixi tasks (`deck-export`, `narration-extract`, `retired-console-check` — the `dashboard-check` task named at authoring time was deleted 2026-08-25, steward 30.2)
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
2. ✓ All 9 HTML decks render without error; `retired-console-check` passes
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
- **Spec Source**: `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md` (formerly `spec-herald-pitch/SPEC.md`, folded in 2026-08-02 — capabilities HER-4..HER-10)
- **Dream Source**: `docs/dreams/pyforge-herald.md` (formerly `docs/dreams/herald-pitch.md`, archived/absorbed 2026-08-02)
- **Reviewer**: (pending)

---

## Satellite: Herald's Proclamation Surfaces — Moments 2–4

> Folded in 2026-08-02 from `prds/prd-herald-moments-2-4-2026-08-02/prd.md` (status:
> `draft`, created/updated 2026-08-02). Content below is verbatim from that PRD except this
> note and the corrected cross-references at its end. The original, unmodified folder is
> archived at
> `archive/_bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-herald-moments-2-4-2026-08-02/`.
> Its source Spec (`spec-herald-moments-2-4`) is folded into `spec-pyforge-herald/SPEC.md` as
> capabilities HER-11–HER-13, and its Architecture into
> `architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md` as AD-11–AD-20.

<!-- BEGIN verbatim prd-herald-moments-2-4-2026-08-02/prd.md -->

# Herald's Proclamation Surfaces — Product Requirements Document

---

## Executive Summary

Herald's Four Moments of Proclamation framework guides all factory communications. Moment 1 (Pitch) is production-ready with the deck family specification. **This PRD delivers Moments 2–4** — three missing surfaces that complete the proclamation cycle:

- **Moment 2 (Progress)**: Make shipping motion visible + explainable (cost transparency, unblock narratives)
- **Moment 3 (Success)**: Claim project completion with retrievable evidence (tests, metrics, adoption)
- **Moment 4 (Operations)**: Announce deprecations, fixes, end-of-life notices proactively

Implementation is a **coordinated epic** (7 stories, 12–18 story-points) with shared CLI/web/automation infrastructure, prioritizing **integration correctness** over velocity-to-first-value.

---

## Product Vision & Strategy

### Vision Statement

Herald is the factory's unified voice. The Four Moments ensure every idea is argued (Pitch), every shipping is visible (Progress), every completion is claimed (Success), and every sunset is announced (Operations). This PRD completes Moments 2–4 so no work ships silently and every claim carries proof.

### Strategic Priority

**High** — Herald is infrastructure. Silent shipping creates downstream confusion (what changed? what cost? what unblocked?). Proclamation surfaces are the trust layer for the entire factory.

### Audience

- **Primary**: Factory operators, team leads, project stakeholders (who need visibility into shipping motion)
- **Secondary**: CI/CD systems, dashboard readers (automated evidence sources)
- **Tertiary**: Public-facing systems consuming notices (Moment 4 archive)

---

## Product Scope

### In Scope

**Moment 2 (Progress Visibility)**
- Weekly progress summaries + on-shipping-event updates
- Cost transparency (compute, tokens, wall-clock time)
- Unblock narratives (what downstream work did this unlock?)
- Automation: on-ship webhook + Thursday 2300 UTC weekly fallback
- CLI interface: `herald progress <station> [--update]`
- Web widget: Progress tab with station filter + date range

**Moment 3 (Success Proclamation)**
- Auto-extract success claims on PR-close + passing gates
- Claim structure: project, thesis, proof (tests, metrics, adoption)
- Evidence linking framework (link-to-evidence protocol)
- Operator review gate before publish (quality gate)
- Automation: on-PR-close + passing gates (auto-extract); operator-triggered publish
- CLI interface: `herald success [review <claim-id> | publish <claim-id>]`
- Web archive: Success tab with chronological claims + evidence badges

**Moment 4 (Operations Notices)**
- Manual notice authoring (deprecation, fix, end-of-life)
- Notice template with: what changed, why, migration path, deadline, proof/reason link
- Simple archive indexing (YYYY-MM folders + category tags)
- Permanent URLs + redirect rules for deprecated surfaces
- CLI interface: `herald notice [author | list | archive]`
- Web notice board: Operations tab with category filter + search

**Shared Infrastructure**
- Unified Herald CLI dispatcher (all three Moments under one command)
- Unified Herald web surface (4 tabs: Pitch, Progress, Success, Operations)
- Evidence-linking framework (shared across Moment 3 & 4)
- Automation orchestration (webhooks, cron, gate-based triggers)

### Out of Scope

- **Moment 1 improvements** — Pitch/deck family is complete and separate
- **Video pipeline integration** — Moment 4 feeds narration to bmad-manticore, but video rendering is upstream
- **Marketing/external proclamation** — Moments 2–4 are internal visibility; Moment 1 handles external
- **Full-text search backend** — Simple date/category indexing for Moment 4 archive (full-text addable later)
- **Multi-region Herald surfaces** — Single unified Herald service assumed
- **Real-time collaboration** — No live sync between operators; pull model is explicit

---

## Requirements by Feature

### Feature Group 1: Herald CLI Architecture

**FR-1.1: Unified Command Dispatcher** ← CAP-1
- Single entry point: `herald <subcommand> [--help | --json | --date-range <start>..<end>]`
- Subcommands: `progress`, `success`, `notice`
- Help text comprehensive and discoverable (`herald --help`, `herald <subcommand> --help`)
- Argument parsing handles: JSON output mode, date filtering, station/project filtering
- Extensible for future Moments (not hardcoded to 3)

**FR-1.2: Shared Argument Conventions** ← CAP-1
- All subcommands support `--json` (machine-readable output)
- All subcommands support `--date-range YYYY-MM-DD..YYYY-MM-DD` or `--week recent|last-N` patterns
- All subcommands support station/project filtering where applicable
- Error messages consistent and actionable

**FR-1.3: CLI Authentication & Authorization** ← CAP-1
- [ASSUMPTION: Herald CLI reads from Herald web service with implicit auth (same session)] Confirm with ops team
- Write operations (publish, author) require operator role confirmation
- Read operations (progress, list, archive) are public

---

### Feature Group 2: Herald Web Surface

**FR-2.1: Unified Navigation & Layout** ← CAP-3
- Header nav with 4 tabs: **Pitch** (link to Moment 1 deck family), **Progress**, **Success**, **Operations**
- Unified color scheme and typography (Modernist design system from Moment 1)
- Sidebar: station filter (Warden, Atlas, Marshal, etc.), date range selector, search box
- Responsive (desktop, tablet, mobile)

**FR-2.2: Header & Footer** ← CAP-3
- Header: Herald branding, Moment tab nav, user profile (if applicable)
- Footer: snapshot timestamp, last-updated indicators per section

**FR-2.3: Surface Integration** ← CAP-3
- All three Moments visible in unified web surface (no separate apps or domains)
- Consistent pagination, sorting, and filtering across all tabs
- Cross-moment linking: Moment 3 success claim can link to Moment 4 notice (bidirectional)

---

### Feature Group 3: Moment 2 — Progress Visibility

**FR-3.1: Progress Data Model** ← CAP-11
- **Record structure**: station name, date, shipped capabilities (list), cost (compute hours, token spend, wall-clock), unblock narrative (text)
- **Cost metrics**: derived from sprint-status ledger + bmad-loop journal timestamps
- **Unblock narrative**: operator-authored (auto-suggested from downstream PRs if available)

**FR-3.2: Progress Automation** ← CAP-11
- **Trigger 1**: On-ship event (webhook from CI when PR merges to main)
  - Auto-creates progress record with cost + shipped capabilities extracted from journal
  - Operator authors unblock narrative (prompted)
- **Trigger 2**: Weekly cron Thursday 2300 UTC
  - Collects all shipping events from past week, aggregates into one record
  - Falls back to this when no on-ship events in the week

**FR-3.3: Progress CLI** ← CAP-11
- `herald progress <station>` — show latest progress record for station (JSON or formatted)
- `herald progress <station> --update` — manually trigger progress update (operator only)
- `herald progress --list [--station <name> --week recent|<N>]` — list progress records by filter

**FR-3.4: Progress Web Tab** ← CAP-11
- Latest progress per station (card view or table)
- Sidebar filters: station, date range
- Expandable detail: full cost breakdown, unblock narrative, shipped capabilities list
- Sorting: by date, by cost, by station

---

### Feature Group 4: Moment 3 — Success Proclamation

**FR-4.1: Success Claim Data Model** ← CAP-12
- **Record structure**: project name, shipped date, thesis (one-liner, what we proved), evidence list (URL + type pairs: test_results | metrics | adoption | other)
- **Evidence types**: 
  - `test_results`: CI job URL (links to passing tests)
  - `metrics`: dashboard metric URL (proves real-world impact)
  - `adoption`: downstream PR URL (proves dependent projects use it)
  - `other`: freeform URL (any supporting proof)

**FR-4.2: Success Auto-Extract** ← CAP-12
- **Trigger**: On PR close to main + passing gate-suite
  - Herald webhook receives: PR URL, commit SHA, test job URL, merged-at timestamp
  - Herald auto-extracts: project name (from PR title/labels), test results (CI job)
  - Herald queries dashboard for metrics (if configured) + searches for downstream adoption PRs
  - Generates structured claim with thesis-placeholder ("shipped on [date]")
- **Operator review**: Operator edits thesis (what we proved) and approves/publishes
  - CLI: `herald success review <claim-id>` (shows extracted claim + evidence)
  - Web: review form with editable thesis + evidence list
  - Operator clicks publish → claim becomes public + indexed

**FR-4.3: Success CLI** ← CAP-12
- `herald success review <claim-id>` — show claim under review (JSON or formatted)
- `herald success publish <claim-id> --thesis "<one-liner>"` — publish with operator-authored thesis
- `herald success list [--status draft|published --date-range <start>..<end>]` — list claims by filter
- `herald success get <claim-id>` — retrieve published claim

**FR-4.4: Success Web Archive** ← CAP-12
- Published claims listed chronologically (newest first)
- Claim card: project, thesis, shipped date, evidence badges (green=linked, yellow=pending)
- Click to expand: full evidence list with live links
- Sidebar filters: date range, evidence status
- Search box: project name, thesis keyword

**FR-4.5: Evidence Integrity** ← CAP-12
- All evidence links validated at publish time (404 detection, redirect resolution)
- Dead links surface error before publish (operator fixes or removes)
- Evidence links re-validated weekly (stale links flagged in operator dashboard)

---

### Feature Group 5: Moment 4 — Operations Notices

**FR-5.1: Notice Data Model** ← CAP-13
- **Record structure**: notice type (deprecation | fix | eol), component/feature name, what changed, why, migration path (if applicable), deadline (if applicable), reason link (URL to decision / ticket), notice URL (permanent archive path)
- **Versions**: notices support edit history (who, what, when); old versions remain in archive for audit

**FR-5.2: Notice Authoring** ← CAP-13
- **CLI**: `herald notice author --type <deprecation|fix|eol> --component <name> --reason "<why>" --deadline <YYYY-MM-DD> [--migrate-to <new-component>]`
  - Interactive prompt for missing fields (what changed, why, migration path)
  - Outputs: draft notice (markdown format) + preview URL
  - Operator confirms + publishes (or exits to edit)
- **Web form** (optional, if UI bandwidth): author form with fields matching CLI interface

**FR-5.3: Notice Archive** ← CAP-13
- **Storage**: notices organized by YYYY-MM folders + category tags (directory tree)
- **Indexing**: 
  - `/operations/notices/` lists categories (deprecation, fix, eol)
  - `/operations/notices/deprecation/` lists 2026-08, 2026-07, … (by month)
  - `/operations/notices/deprecation/2026-08/` lists individual notices
- **Permanent URLs**: `/operations/notices/deprecation/2026-08/component-name.md`
  - URL never changes; if component name changes, redirect rule created
- **Search**: Cmd+F in browser (manual search)

**FR-5.4: Notice Lifecycle** ← CAP-13
- **Draft** → **Published** → **Closed** (after deadline or superseded)
- Draft: visible to authors only; editable
- Published: visible to all; read-only (new version can be created if needed)
- Closed: visible to all; archived; no further edits

**FR-5.5: Redirect Rules** ← CAP-13
- When component name or URL structure changes, redirect rule auto-generated
- Operator confirms redirect → persisted
- Old URLs → new archive location (no 404s for historical notices)

**FR-5.6: Notice CLI** ← CAP-13
- `herald notice author [...]` — create and publish notice
- `herald notice list [--type deprecation|fix|eol --month YYYY-MM]` — list by filter
- `herald notice archive` — show archive structure + counts
- `herald notice get <notice-url>` — retrieve notice by archive path

---

### Feature Group 6: Evidence-Linking Framework

**FR-6.1: Shared Evidence Link Protocol** ← CAP-11
- All evidence links follow schema: `{ type: "test_results|metrics|adoption|other", url: "https://...", label: "CI job #123" }`
- Protocol supports: HTTP/HTTPS, link validation (404 detection), redirect resolution
- Links can be bidirectional: success claim links to notice, notice links back to success claim

**FR-6.2: Evidence Validation** ← CAP-11
- Sync validation: test at publish time (404 → error)
- Async validation: weekly check of all links (stale links → operator alert)
- Redirect handling: follow redirects up to 3 hops; warn on redirect chains

**FR-6.3: Evidence Retrieval** ← CAP-11
- Evidence links always retrievable by claim ID + link ID
- Evidence can be unlinked (operator removes broken link)
- Evidence link audit trail: who added, when, any edits

---

### Feature Group 7: Automation Orchestration

**FR-7.1: Webhook Integration** ← CAP-37
- **Moment 2**: on-ship webhook (CI notifies Herald when PR merges to main)
  - Payload: PR URL, commit SHA, test job URL, merged-at timestamp, station tag (if available)
- **Moment 3**: on-PR-close webhook (CI notifies Herald when PR closes + gates pass)
  - Payload: PR URL, commit SHA, test job URL, close-at timestamp

**FR-7.2: Scheduler (Cron)** ← CAP-38
- **Moment 2**: Thursday 2300 UTC weekly (fallback if no on-ship events)
  - Collects all shipping events from past week, generates aggregated record
- **Extensible**: Automation rules stored in Herald config (can be modified per Moment without code changes)

**FR-7.3: Gate-Based Triggers** ← CAP-39
- **Moment 3**: auto-extract only if PR-close event INCLUDES "all gates passed" signal
  - No orphaned claims from incomplete shipping
- **Moment 4**: manual author only (no auto-trigger)

**FR-7.4: Operator Confirmation Gates** ← CAP-37
- Moment 2 progress: operator authors unblock narrative (prompted after auto-extract)
- Moment 3 success: operator approves + authors thesis (required before publish)
- Moment 4 notice: operator authors full notice (required; no auto-generation)

---

## Non-Functional Requirements

**Performance**
- Herald CLI commands respond in <1s (local cache or fast API)
- Herald web tabs load in <2s (even with thousands of records)
- Progress widget (latest per station) renders in <500ms

**Availability**
- Herald web surface ≥99% uptime (SLA tbd with ops)
- Herald CLI works offline (cached data) with graceful degradation

**Security & Authorization**
- Write operations (publish, author) require operator role
- Read operations are public (no auth required for archive)
- Evidence links validated (no malicious URLs in proofs)
- Audit trail: all edits logged (who, what, when)

**Scalability**
- Support 100+ notices per month (Moment 4 archive)
- Support 1000+ success claims per year
- Support 10+ simultaneous operators (no lock contention)

**Data Integrity**
- No claims without evidence (enforced at publish)
- No dead links in evidence (validated at publish + weekly check)
- Archive URLs permanent (redirects for moved/renamed)
- Edit history preserved (no data loss on edit)

**Operator Experience**
- CLI help text clear and actionable
- Web forms simple (auto-filled where possible, dropdown defaults)
- Error messages name the problem + suggest fix
- Notifications/alerts for stale links, review-pending claims

---

## Success Metrics

### Adoption Metrics
- **Moment 2**: ≥80% of shipping events trigger progress update (automatic or manual)
- **Moment 3**: ≥90% of closed projects have published success claims within 7 days of close
- **Moment 4**: ≥70% of deprecations announced before deprecation date (not after)

### Quality Metrics
- **Evidence integrity**: ≤5% of evidence links are stale (404 or permanent redirect broken)
- **Claim completeness**: 100% of success claims have ≥1 evidence link (enforced)
- **Notice accuracy**: 0 operator-reported false/misleading notices

### Operational Metrics
- **CLI performance**: 95th percentile command latency <500ms (local cache)
- **Web performance**: 95th percentile tab load <2s (dashboard included)
- **Automation reliability**: ≥99% of automation triggers execute without error (retry logs)

### Engagement Metrics
- **Visibility**: ≥50% of factory participants read Herald web surface weekly
- **Participation**: ≥25% of operators author notices or approve claims (active, not passive)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Evidence links break (upstream URLs change/404) | Success claims lose proof | Weekly link validation; operator alert on stale link; allow unlinking |
| Operators forget to author unblock narratives (Moment 2) | Progress loses context | CLI prompts + web form; template suggestions from downstream PRs |
| Too many deprecation notices (Moment 4) overload readers | Operator fatigue; notices ignored | Simple archive indexing; category + date filters; encourage bundling related notices |
| Moment 3 auto-extract fails (CI doesn't send webhook) | Silent missing claims | Fallback: operator CLI publish; weekly audit report of unclaimed closes |
| Automation webhook floods Herald (runaway triggers) | Uptime risk | Rate limiting per CI job; queue + dedup; operator alert on anomalies |

---

## Dependencies & Blockers

### Internal Dependencies
- **Herald v0.1.0 CLI**: existing CLI structure extends (no rebuild)
- **Herald web prototype**: existing web surface integrates (add tabs, nav)
- **Sprint-status ledger**: data source for Moment 2 cost metrics (must be accessible)
- **bmad-loop journals**: data source for Moment 2 cost + unblock (must have read access)
- **CI webhook infrastructure**: must support webhook payloads (Moment 2 & 3 auto-triggers)
- **Dashboard infrastructure**: must expose metric URLs for Moment 3 evidence linking

### External Dependencies
- None identified (all infrastructure internal)

### Blockers
- None; all capabilities are foundational to Herald, not dependent on other projects

---

## Open Questions for Architecture Phase

1. **Evidence link storage**: Store links in database (queryable, editable) or as markdown frontmatter in archive files?
2. **Claim versioning**: Support multiple versions of a success claim (edited thesis), or immutable claims + new claims for edits?
3. **Notice edit history**: Preserve full edit history (who, what, when) or just current + audit log?
4. **Automation retry logic**: Exponential backoff for webhook retries, or fixed retry count? Max retry duration?
5. **Evidence extraction**: Query dashboard via API, or parse public metric URLs? Rate limits?

---

## Phasing & Sequencing

**Phase 1: Foundation (Stories 1–2)** — CLI architecture + web layout
- Enables all downstream work
- No visible features yet; foundation only
- 3–4 story-points

**Phase 2: Core Moments (Stories 3–5)** — Implement Moments 2, 3, 4 in parallel
- After Stories 1–2 ship
- 6–10 story-points (can parallelize)
- Each Moment can deploy independently

**Phase 3: Integration & Quality (Stories 6–7)** — Testing + documentation
- After Moments 2–5 feature-complete
- 2–4 story-points
- Ship as coordinated release (all three Moments + CLI + web together)

---

## Appendix: References

- **Spec source**: `../specs/spec-pyforge-herald/SPEC.md` (five-field kernel; formerly `../specs/spec-herald-moments-2-4/SPEC.md`, folded in 2026-08-02 as capabilities HER-11–HER-13)
- **Epic breakdown**: `../planning-artifacts/epics.md` (story dependencies, timeline; formerly cross-referenced as `../specs/spec-herald-moments-2-4/epic-structure.md`, now a companion of `spec-pyforge-herald`)
- **Herald Pitch spec** (Moment 1): `../specs/spec-pyforge-herald/SPEC.md` (design system, patterns; formerly `../specs/spec-herald-pitch/SPEC.md`)
- **Herald v0.1.0 CLI**: existing codebase (entry point for extension)

<!-- END verbatim prd-herald-moments-2-4-2026-08-02/prd.md -->

---

## Currency reconciliation — 2026-08-26

Re-derived against the 2026-08-25 SPEC re-cut (`specs/spec-pyforge-herald/SPEC.md`), the
2026-08-08 research wave, and the as-built package (`src/shared/packages/pyforge-herald/`,
epics 1–17 all `done` in `sprint-status-ledger.yaml`, 61 stories). Both PRD bodies above are
preserved as the historical requirements record; the deltas below are what changed under them:

1. **Metadata correction.** "Status: Draft (ready for architecture → epics decomposition)"
   is long stale — the chain was decomposed and fully implemented. Delivery record:
   Epics 1–12 (47 stories) merged by 2026-08-08 (PRs #111/#114/#116, #308–#316); Epics
   13–17 (14 stories) merged 2026-08-11 → 2026-08-26 (Epic 13 via `loop/pyforge-herald`
   landings `1f5ddee114`/`488105bdc1`/`828a89fadd`/`8ba853c78a`; Epics 14–17 hand-landed,
   `c47a46d1b7` … `a1d0609c4f`).
2. **The satellite PRD's automation requirements have now genuinely shipped — twice-shaped.**
   The 2026-08-08 build delivered FR-3/FR-4/FR-5 data models and CLI/web surfaces
   **scaled down** (operator-triggered CLI, local JSON/markdown stores, static-snapshot
   dashboard — the pivot recorded in the 08-08 retro §4). Epic 13 ("the live backend",
   done 2026-08-13) then delivered the deferred substrate for real, with these deviations
   from the FR text a reader should treat as the as-built truth:
   - **FR-7.1 webhooks:** shipped as framework-agnostic `webhook.py` — HMAC-verified
     (`hmac.compare_digest`, SHA-256) `on-ship` / `on-pr-close` handlers; the triggering CI
     is **GitHub Actions** (recorded first-AC decision, spec-13-4); the endpoint rides
     Steward's `spec-secure-live-dashboards` trust boundary, never a bespoke perimeter.
   - **FR-7.2 scheduler:** weekly aggregation + evidence revalidation run via
     `scheduler.py` and a fifth top-level CLI verb (`herald scheduler run`), CI-scheduled —
     not an always-on Thursday-2300-UTC cron daemon.
   - **Storage (open question 1, "database or frontmatter"):** resolved as stdlib
     **SQLite** (`.herald/herald.db`, WAL, versioned migration runner — `db.py`) behind the
     unchanged pure-function seam; notices' git-tracked markdown remains the durable copy.
     The satellite's PostgreSQL/SQLAlchemy/Celery assumptions were never built.
   - **Concurrency prerequisite** (not in this PRD at all): the lost-update limit every
     store inherited from `state.py` was closed first (story 13.1, stdlib `fcntl`/`msvcrt`
     advisory locking, then SQLite transactions in 13.3) before any second writer existed.
   - **End-to-end proof:** story 13.6 demonstrated a real merge creating a progress record
     and a success-claim draft with no human action — the "no silent shipping" goal proven,
     CI-contained (persistent always-on hosting remains a Steward-owned deployment concern).
3. **Post-PRD scope the PRD does not cover** (governed by `epics.md` + its 2026-08-24
   Canopy/operating-model obligations, deliberately *not* retrofitted into FR form here):
   Epic 14 deck visual-QA gates (`herald deck qa <slug>`: headless-Chromium render gate +
   image-slot scan, report-only); Epic 15 PowerPoint-native editable-deck pipeline
   (template-parse-then-fill + Pillow-measured autofit shapes — unparked 2026-08-22 after
   the shipped Marp PPTX exports were proven to be background-image slides with zero
   editable text runs); Epic 16 exporter hook plugins (Marp/PPTX/`.dc.html` on the shared
   `pyforge.core.hooks` contract; export success is never a PR-gate verdict); Epic 17
   station SKF skill + `bmad-agent-herald` persona and the first `/stations/herald/`
   portal slice (HTMX via PortalClient on the Canopy host — no station origin, no second
   public port; service face is `POST /stations/herald/mcp`).
4. **Audience/market grounding refreshed** — per
   `research/market-herald-post-ship-landscape-research-2026-08-08.md`, Herald's nearest
   external category is now the internal-developer-portal class (records + scorecard
   dashboard), not changelog automation; the telemetry-native sourcing this PRD's
   satellite treats as given did not ship in v1 (operator-typed flags) and is only
   partially closed by Epic 13's automation. Freshness UX ("attested-at as prominent as
   the record") is the standing borrow from that category.
5. **Success-metric status:** the satellite's adoption/engagement metrics (§ Success
   Metrics) remain **unmeasured** — near-zero production usage time; they are targets,
   not results. The authoritative verification record is the package test suite and the
   per-story Review Triage Logs.


## Platform floor — reconciled 2026-09-07

`pyforge-herald` declares **`requires-python = ">=3.14"`**. Raised from `>=3.12` by
marshal Story 32.2 (`spec-fleet-consistency-standard` CAP-5) and folded in here because it
is a product-visible constraint, not an implementation detail: it states which interpreters
this package may be installed onto.

The prior `>=3.12` was an untested claim. `pixi.toml` pins
`python = ">=3.14.7,3.14.*"` and every env-scoped pin in the workspace is `3.14.*`, so no
environment in this repo has ever installed, built or exercised this package on 3.12 — the
floor asserted a compatibility nothing verified. Declaring an untested floor is the same
failure mode as a fabricated test-architecture document: it reads as verified to the next
agent. There is no `recipes/pyforge-herald/`, so the package is built by `pixi-build-python`
for this estate and is not published to conda-forge; no external consumer depended on the
wider floor.

## Currency reconciliation — 2026-09-14

*Chain-currency sweep: `spec-pyforge-herald`'s SPEC.md moved to 2026-09-13 and its
`.memlog` to 2026-09-13T03:35 while this PRD sat at 2026-09-07 — six days, past the
runbook's 2-day grace window.*

**What moved in the Spec.**

1. **The § Success signal was re-grounded twice (2026-09-09, then again 2026-09-12) —
   and the second re-grounding is the substantive one.** The 2026-09-09 text named
   three "effect gaps" between what Herald has built and what the running estate
   actually exercises. Epic 19 closed two of them the next day, and the Spec was
   re-grounded to say so:
   - **The deck-QA gate has a caller** (Story 19.3, PR #1150). Verified live this
     pass: `pixi.toml` declares `[feature.pyforge-herald.tasks.deck-qa]`, and
     `docs/specs/presentation-deck.md`'s verify checklist names it as a step.
   - **The `.pptx` pipeline has rendered a real station deck** (Story 19.4, PR #1155).
     Verified live: `presentations/pyforge-warden/src/content_plan.json` exists — the
     first real `content_plan.json` in the tree.
   - **Still genuinely open:** the live-backend triggers have never run green. Story
     19.1 moved the webhook routes onto the station-API seam, but Story 19.2 ("one
     real ship records itself against a persistent store") is `blocked` on
     **`DW-13-6-1`** — `steward deploy perimeter` renders only a hardcoded
     `myproject.asgi:application` with no `--asgi-application` flag, so Herald has no
     perimeter to host a persistent listener on.
2. **A new § Residual dependencies (2026-09-09).** The Non-goal "the Guildhall is
   Marshal's (`[[factory-console]]`)" is now marked **known-stale pending a Charter
   amendment**, not a Herald decision: `factory-console`'s Spec is `superseded`, the
   Pages GuildHall console is retired-and-guarded (`retired-console-check`), and the
   three live console surfaces are Atlas's Vizro/BSL board, the Wagtail Lane-1 CMS and
   the eight `django-*` station portals — none of them Marshal's. Guildhall is Charter
   Lexicon §7, so the question is constitutional and is raised there, once.
3. **Story 20.1/20.2 deck-family work (memlog, 2026-09-13).** `presentations/README.md`
   gained a pointer to `spec-deck-family-currency/infographic-standard.md`, and ten
   per-deck fact ledgers (`presentations/<slug>/facts.yaml`) were minted — verified
   live this pass at **10 files**.
4. **A `surface-drift-exclude:` block of 32 literal paths.** Detector bookkeeping only:
   `station_api.py` (also governed by `spec-pyforge-core`) plus the 31 deck-family
   files `spec-deck-family-currency` owns and reconciles per poster story. Recorded
   because the *reason* is instructive and already cost one wasted pass: the checker
   matches this list **literally** (`sources/chain.py:1613`), so the four glob entries
   added earlier the same day never matched anything.

**Why none of this changes a requirement here.**

- **(1) and (3) are this PRD's requirements being *exercised*, not amended.** The
  deck-QA gate, the `.pptx` export and the per-deck fact ledgers are all inside the
  deck-family feature set § Requirements by Feature already specifies. A capability
  acquiring its first caller is a realization event; the requirement text was already
  correct and stays as written.
- **(2) is a citation, not a requirement.** The Non-goal's *substance* — the hall is
  not Herald's — is unchanged and remains true. Only the wikilink referent is stale,
  and it is owned by the Charter, not by this PRD. The one-owner-one-question rule
  applies: Herald does not carry a second copy of the question, and this PRD does not
  either. When the amendment lands, the referent is replaced in the Spec and the
  change cascades here in the normal way.
- **(4) is detector bookkeeping.** No requirement describes drift-tracking membership.

**One thing recorded rather than absorbed.** § Success Metrics still reads
"unmeasured — near-zero production usage time." That remains accurate and this pass
does **not** quietly upgrade it: two of three effect gaps closing means two
capabilities now have a caller, which is a strictly weaker claim than the adoption and
engagement metrics § Success Metrics actually asks for. The honest state is that
Herald's deck family is exercised by CI and by the estate's own tooling, and is still
not exercised by an external audience.

**Ledger state at this stamp** (measured with `fleet_scan.parse_sprint_status`, not a
regex): 94 story keys — 82 `done`, 11 `backlog`, 1 `blocked` — across 22 epics (19
`done`, 2 `in-progress`, 1 `backlog`). The single `blocked` story is 19.2 above.

**No requirement added, changed or removed.** `updated:` bumped to record that the
check ran.

## Currency reconciliation — 2026-09-17

One-chain fold reminted spec-pyforge-herald CAP-1..47. Kernel FR ids unchanged; each opening FR line cites a reminted CAP. FR delta: none.

## Currency reconciliation — 2026-09-20

*Chain-currency sweep: `research/docs-site-bmad-method-pattern-2026-09-20.md` (an operator-asked
seed, 09:55Z: the docs site matches BMAD-METHOD's Astro + Starlight + Pages pattern so upstream's
skills and workflows apply unchanged) post-dated the brief and, through it, this PRD (`brief→prd` cascade). It is input for `bmad-spec`, not yet
a capability: no requirement, decision or story changes here until that pass mints the CAP.
`updated:` bumped to record that the check ran; the six decisions the research asks for are listed
in its § 3 and on the Dream's 2026-09-20 entry.*

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this PRD. `updated:` bumped to record that the
check ran.*

## Currency reconciliation — 2026-09-25

`spec→prd` edge: `spec-pyforge-herald`'s `.memlog.md` moved to 2026-09-25T04:02 while this PRD
sat at 2026-09-20.

**What moved, and why the FR delta is none.** One entry: steward Story 59.6
(`spec-pyforge-steward:CAP-137`, the Guild roster collapse) changed
`src/shared/packages/pyforge-herald/src/pyforge/herald/progress.py` so `STATIONS` re-exports
`pyforge.core.roster.STATIONS` instead of declaring its own tuple. Same eight stations, one
declared source; no herald behaviour or requirement changes. `updated:` bumped to record that the
check ran.
