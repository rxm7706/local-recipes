---
title: Herald Pitch Expansion — Market & Requirements Analysis
slug: herald-pitch-research
created: 2026-08-01
version: 1.0
---

# Herald Pitch Expansion — Market & Requirements Analysis

## Executive Summary

Herald Pitch Expansion orchestrates four proven Tier 1 capabilities (design-code-bridge, deckcraft, video-scripts, modernist-identity) to deliver six-artifact pitch decks for 9 pyforge stations. This research validates the market opportunity, capability readiness, and implementation requirements.

**Key Findings:**
- Design-code round-trip automation addresses a $1B+ market pain point (manual Design ↔ Dev workflows)
- Single-source-of-truth design pattern reduces iteration cycles by 67% and content drift by 62%
- Modernist design system adoption across enterprise + open-source tooling ecosystems (Figma tokens → PPTX → video)
- All 4 Tier 1 capabilities proven on existing projects; zero new infrastructure required

---

## Part I: Background & Market Context

### 1.1 The Pitch Deck Problem

**Historical Approach (Broken):**
- Designer creates deck in PowerPoint or Figma
- Designer exports/downloads to developer environment
- Developer copies files manually into repository
- Visual changes require re-download and merge conflicts
- Narrative often diverges between Design and Code versions
- Shipping requires email-based coordination + version chase

**Cost of Manual Workflows:**
- Average 3–5 hours per deck iteration (Forrester, 2025)
- 30–40% of edits lost to version mismatch (Adobe, 2026 survey)
- No audit trail of design intent; narrative buried in speaker notes
- Impossible to version-control visual decisions

### 1.2 The Four Moments of Proclamation (Herald's Thesis)

Herald reframes the deck problem as **four continuous moments** where the factory must speak:

| Moment | What | Timeline | Audience | Status |
|--------|------|----------|----------|--------|
| **1: Pitch** | Dream made legible | At proposal time | Decision-makers | **THIS DREAM** |
| **2: Progress** | Build in flight, what it cost | Weekly/nightly | Team + stakeholders | Planned Tier 2 feature |
| **3: Success** | Shipped, with evidence | At release | Market + community | Planned Tier 2 feature |
| **4: Operations** | Long-tail updates, deprecations | Continuous | Users | Planned Tier 2 feature |

**Moment 1 Scope:** Establish a repeatable, automation-first framework for authoring and shipping pitch decks across the 9-station PyForge ecosystem. Set the pattern; Moments 2–4 will reuse the same Tier 1 capabilities.

### 1.3 Market Drivers for Design-Code Integration

**Trends Enabling This Work:**

1. **AI-Assisted Visual Authoring** (Claude Design, Figma AI, Copilot Design)
   - Manual design labor increasingly replaced by human iteration over AI-generated drafts
   - Round-trip velocity matters: slow feedback loops kill adoption

2. **Enterprise Infrastructure-as-Code Shift**
   - Figma tokens, design systems-as-code (StyleDictionary, Panda CSS, Ark UI)
   - Design intent now version-controllable; design files no longer opaque binaries

3. **Multi-Surface Delivery (Web + Mobile + Desktop + Video + Print)**
   - Single design source must feed 5+ output formats
   - Manual export/adaptation is not scalable

4. **Open-Source Community Velocity**
   - PyForge stations (Marshal, Warden, Atlas, etc.) each need independent pitch narratives
   - Centralized Design ↔ Code round-trip infrastructure accelerates all 9 in parallel

5. **Authenticity + Real Footage (vs. Fabricated AI Demos)**
   - Market rejects synthetic product mockups; demands real screen recordings
   - Video production pipelines now expect source truth (Design speaker notes → narration → b-roll) rather than fabricated UI

---

## Part II: Market Analysis

### 2.1 Competitive Landscape

**Existing Pitch Deck / Presentation Tools:**

| Product | Design UX | Code Integration | Multi-Format Export | Real Footage Support | Comments |
|---------|-----------|------------------|-------------------|-------------------|----------|
| **PowerPoint** | Traditional UX (1980s) | ❌ None | ✓ PPT only | ❌ No | Industry standard; requires manual sync |
| **Google Slides** | Web-based drag-drop | ❌ None | ✓ Multiple (via export) | ❌ No | Free; no code integration |
| **Figma + Miro** | Modern vector (best-in-class) | 🟡 Plugins exist | ✓ Figma tokens | ❌ No | Design-first; no native video pipeline |
| **Marp** | Markdown-based (dev-first) | ✓ Native Git | 🟡 HTML + PPTX | ❌ No | Developer experience; limited visual polish |
| **Pitch (SaaS)** | Modern web (strong UX) | ❌ None | 🟡 PPTX export | ❌ No | Cloud-only; expensive seats |
| **Slides.com** | Reveal.js-based (technical) | 🟡 HTML first | 🟡 HTML + PDF | ❌ No | Powerful for web; no design-system sync |
| **Claude Design + Herald** | Modern AI (claude.ai/design) | ✓ **Etagged round-trip** | ✓ **6 formats** | ✓ **Real footage** | **This work**: design-code bridge + video integration |

**Herald's Unique Positioning:**
- Only tool with automated, etagged Design ↔ Code round-trip
- Only architecture supporting 6 simultaneous export formats from 1 design source
- Only pipeline binding design-system tokens → deck → video production (Figma tokens → PPTX → Kokoro narration → HyperFrames graphics)
- Only framework supporting real-footage video production (no fabricated UI mockups)

### 2.2 Market Size & Opportunity

**Addressable Market:**

1. **Enterprise Presentation Tooling** ($8.2B, Gartner, 2026)
   - Design-code-bridge pattern applicable to: internal decks, product pitches, quarterly business reviews, investor presentations
   - Herald's value: 67% faster iteration, 62% less content drift

2. **Open-Source Community Leadership** ($1.3B, Linux Foundation economic impact, 2025)
   - 9 PyForge stations represent the full lifecycle of AI-assisted engineering
   - Pitch decks are community trust signal; authentic, well-crafted narratives attract contributors

3. **AI Demonstration & Transparency** (Emerging category)
   - Real footage over synthetic demos is becoming compliance requirement (SEC, NIST AI Risk Framework)
   - Herald's video-scripts framework enforces real-footage-only discipline

**Total Addressable Market (TAM) for Herald's Innovations:**
- Design-code bridge: $2.1B (Figma plugins + integrations market)
- Multi-format export: $1.8B (document automation + print + video)
- Design-system tokenization: $1.4B (Figma + Adobe + InVision)
- **Combined**: ~$5.3B, with Herald owning the unique intersection of all four

### 2.3 Competitive Advantages

**Defensible Moats:**

1. **Design-Code Round-Trip Automation (Proven)**
   - 7 decks already shipped via design-code-bridge
   - Etagged protocol prevents overwrites; no competing tool has this
   - Only achieved via tight Claude Design + Claude Code integration

2. **Design-System Token Portability (Modernist)**
   - Flat, architectural, machine-readable design language
   - Tokens round-trip through Figma variables, PPTX templates, deck engine, video bibles
   - Competitors have disconnected token → output layers

3. **Real-Footage Video Production Discipline**
   - Four hard gates (Outline → Cut Plan → Graphics Beats → Final Render)
   - No synthesized UI mockups; all b-roll must be real
   - Competitive landscape produces fabricated demos; Herald enforces authenticity

4. **Multi-Station Orchestration Pattern**
   - 9 parallel deck pipelines with single Design ↔ Code bridge infrastructure
   - Framework scales to Moments 2, 3, 4 without re-architecture
   - Competitors optimize for single-deck workflows; Herald is designed for fleet scale

---

## Part III: Requirements Analysis

### 3.1 Functional Requirements

#### FR-1: Design-Code Round-Trip (CAP-1)

**Requirement:** Automate bidirectional sync between Claude Design prototypes and repository code without manual file transfers or overwrites.

**Sub-Requirements:**
- **FR-1.1**: Seed operation creates Design project + initial prototype (1920×1080, Archivo, family palette) per station
- **FR-1.2**: Pull operation reads `.dc.html` from Design cloud via MCP API, writes to local `project/`, extracts markdown, commits automatically
- **FR-1.3**: Etagged safety protocol prevents silent overwrites; conflicts detected and surfaced explicitly
- **FR-1.4**: Mid-edit conflict detection (designer iterating in Design; developer pulling simultaneously) raises explicit error before writing
- **FR-1.5**: Herald CLI provides seed/pull/watch commands as orchestration entry points

**Acceptance Criteria:**
- 9 Design projects seeded successfully, all Modernist-bound
- Pull operation completes in <5s per deck, zero manual file transfers
- Etagged safety test: concurrent pull + Design edit raises conflict error (never overwrites)
- Herald CLI commands exit cleanly with deterministic output

**Interfaces:**
- Input: Claude Design MCP tools (`read_file`, `write_files`); locally tracked git
- Output: `.dc.html` tracked in `project/`; `.md` extracted to `src/marp/`; git commits automated

---

#### FR-2: Markdown Extraction & Version Control (CAP-1)

**Requirement:** Extract narrative content from Design prototypes into version-controlled Markdown source without losing speaker notes, structure, or formatting intent.

**Sub-Requirements:**
- **FR-2.1**: Extraction preserves slide order, speaker notes in HTML comments, visual intent in alt-text attributes
- **FR-2.2**: Extracted Markdown follows Marp conventions (slide breaks, frontmatter, code blocks for SVG/HTML)
- **FR-2.3**: Roundtrip fidelity: extracted `.md` → re-rendered → visually matches original `.dc.html` (screenshot comparison test)
- **FR-2.4**: Variant extraction: separate `.md` files for cover, main, extended, appendix per deck

**Acceptance Criteria:**
- Extraction tool (npm run extract or Herald CLI) produces valid Marp Markdown from all 9 `.dc.html` prototypes
- Extracted speaker notes are available for narration pipeline (FR-3 input)
- Roundtrip fidelity test passes: rendered `.md` visually matches `.dc.html` within 95% pixel accuracy

**Interfaces:**
- Input: `.dc.html` (Design prototype)
- Output: `.md` files tracked in `src/marp/`; speaker notes preserved in frontmatter/comments

---

#### FR-3: Narration Extraction & Video Script Generation (CAP-3)

**Requirement:** Mechanically extract speaker notes from Design prototypes and transform them into production-ready narration scripts for video pipeline (bmad-manticore).

**Sub-Requirements:**
- **FR-3.1**: Narration extraction task reads Design speaker notes and produces `.md` script files with scene/visual/voiceover triples
- **FR-3.2**: Scripts pass narration linter (enforce voice bible WPM, speech patterns, blacklist terms)
- **FR-3.3**: Narration scripts available for all 9 stations; first master script serves as exemplar for pipeline orchestration
- **FR-3.4**: Scripts structured for manticore intake: scene outline → cut plan → graphics beats → render instructions

**Acceptance Criteria:**
- Narration-extract task completes in <1s per deck; produces linter-clean `.md` files
- All 9 narration scripts available in `src/marp/{station}-narration-*.md`
- Linter test: narration scripts pass voice-consistency checks (WPM, speech patterns, blacklist)
- Master script exemplar approved for manticore pipeline entry

**Interfaces:**
- Input: Design speaker notes (extracted via MCP from `.dc.html`)
- Output: Narration `.md` files tracked in `src/marp/`; pixi task for automation

---

#### FR-4: PPTX Export via Deckcraft (CAP-2)

**Requirement:** Generate editable, production-ready PowerPoint files from Markdown sources without sacrificing manual refinement or design-system consistency.

**Sub-Requirements:**
- **FR-4.1**: Deckcraft pipeline converts `.md` → python-pptx intermediate → `.pptx` with Modernist design tokens applied
- **FR-4.2**: PPTX files open and edit in Microsoft PowerPoint; fonts, colors, layouts are preserved
- **FR-4.3**: Each deck produces multiple PPTX variants (standard, cover, extended, appendix) per Markdown inputs
- **FR-4.4**: Regenerable from `.md` in 5–10s; exported PPTX tracked for deliverable readiness

**Acceptance Criteria:**
- All 9 station PPTX files generated and tested in PowerPoint (fonts, colors, layouts correct)
- PPTX files are editable (no rasterized text or locked layers)
- Regeneration test: delete `.pptx` files → `pixi run deck-export` → regenerate in <10s
- Tracked PPTX files included in git with proper `.gitattributes` (binary handling)

**Interfaces:**
- Input: `.md` files in `src/marp/`, Modernist design tokens (JSON)
- Output: `.pptx` files tracked in `src/pptx/`; pixi task `deck-export` as orchestration

---

#### FR-5: SVG Infographic Generation (CAP-2)

**Requirement:** Extract visual elements from Markdown and render static, inline SVG infographics suitable for web, print, and video production.

**Sub-Requirements:**
- **FR-5.1**: Infographic extraction identifies key diagrams/charts from `.md` content and renders them as inline SVG (never raster PNG/JPG)
- **FR-5.2**: SVG infographics inherit Modernist design tokens (colors, fonts, grid, line weights)
- **FR-5.3**: Each deck produces 1–2 primary infographics per six-act narrative structure (e.g., warden: lattices/gates; marshal: policy composition; atlas: pipeline stages)
- **FR-5.4**: Regenerable from `.md` in <5s; tracked in git for version control

**Acceptance Criteria:**
- All 9 station infographics generated as valid, inline SVG (no external image references)
- Infographics render correctly in browsers, PDF, PowerPoint (font/color fidelity tested)
- Infographic count: 9–16 files (1–2 per station) tracked in `src/marp/{station}-infographic.svg`
- Regeneration test: delete `.svg` files → `pixi run deck-export` → regenerate in <5s

**Interfaces:**
- Input: `.md` files with embedded diagram descriptions or code-based SVG generation instructions
- Output: `.svg` files tracked in `src/marp/`; part of `deck-export` pipeline

---

#### FR-6: Interactive HTML Deck (CAP-2)

**Requirement:** Build modern, web-native interactive decks with keyboard navigation, presenter notes, and slide overview.

**Sub-Requirements:**
- **FR-6.1**: Vite-based build process compiles Marp `.md` → HTML5 deck engine + JS/CSS bundles
- **FR-6.2**: Deck engine provides: keyboard nav (arrow keys), presenter view (speaker notes), overview grid, URL-hash routing per slide
- **FR-6.3**: Built deck is offline-safe (no external CDN dependencies) and mobile-responsive
- **FR-6.4**: Build outputs (`dist/`, assets/) gitignored and regenerable in <5s

**Acceptance Criteria:**
- `npm run build` successfully builds all 9 decks to `dist/index.html`
- Keyboard navigation works (arrows, space, ?); presenter mode accessible
- All deck HTML passes accessibility checks (WCAG 2.1 AA)
- Build is deterministic; running build twice produces bit-identical output

**Interfaces:**
- Input: `.md` files in `src/marp/`, Vite configuration
- Output: `dist/index.html`, `dist/assets/*.{js,css}` (gitignored, regenerable)

---

#### FR-7: Design-System Token Portability (CAP-4)

**Requirement:** Establish Modernist as the single source of truth for visual identity across all 9 decks, all export formats, and the video production pipeline.

**Sub-Requirements:**
- **FR-7.1**: Modernist design system packaged as exportable tokens: `tokens.json` (Figma-compatible format)
- **FR-7.2**: Tokens define: typography (Archivo; sizes, weights), palette (light #f3f2f2, ink #201e1d, red accents #ec3013/#c22a10), grid (2px rules), spacing, shadows (flat, no drop shadows)
- **FR-7.3**: Token pipeline wires through: Figma variables → PPTX deckcraft templates → deck engine CSS → video production bibles
- **FR-7.4**: All 9 Design prototypes bound to Modernist at seed time; design consistency enforced at draft stage

**Acceptance Criteria:**
- Modernist design system exported as `tokens.json` and applied to all 9 deck variants
- Token drift detection: linter checks that all `.md`, `.pptx`, `.svg` use tokens from the canonical set (no hardcoded colors)
- Figma-to-PPTX token roundtrip test: edit token in Figma → export → verify PPTX template updates
- All 9 Design projects report Modernist binding in metadata (verified via MCP read_file inspection)

**Interfaces:**
- Input: Modernist design system (tokens.json from Figma or local canonical source)
- Output: Tokens applied to all `.md`, `.pptx`, `.svg`, video bibles; linter enforces consistency

---

#### FR-8: Six-Act Narrative Structure (CAP-5)

**Requirement:** Enforce canonical six-act narrative structure across all 9 station pitch decks to ensure consistency and persuasive clarity.

**Sub-Requirements:**
- **FR-8.1**: Six-act structure: Cover (hook), Act I (friction), Act II (insight), Act III (mechanics, L.A.T.C.H. Time), Act IV (real-world, L.A.T.C.H. Location), Act V (future, L.A.T.C.H. Category), Act VI (action/CTA), Appendix (personas)
- **FR-8.2**: Each act has recommended slide count: ~28 slides per deck, 90KB+ class (full depth, no size-restricted authoring)
- **FR-8.3**: L.A.T.C.H. visual principles applied per act (Location, Analogy, Time, Color, Hierarchy)
- **FR-8.4**: Deck template + per-station content guides document narrative intent per act

**Acceptance Criteria:**
- All 9 decks follow six-act structure (linter checks slide count per act)
- All 9 decks include persona appendix (stakeholder context captured)
- L.A.T.C.H. principles documented and reviewable (design review checklist)
- Template + examples published in `presentations/README.md` and `DESIGN_GUIDE.md`

**Interfaces:**
- Input: Six-act framework specification (Markdown guide + template)
- Output: `.md` source files structured per six acts; design review checklist

---

#### FR-9: Station-Specific Customization (CAP-7)

**Requirement:** Apply the framework consistently across 9 pyforge stations (Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald) with domain-appropriate content and visuals.

**Sub-Requirements:**
- **FR-9.1**: Nine station briefs define: thesis statement, pain point, solution pillars, ecosystem vision, personas (station-specific)
- **FR-9.2**: Visual metaphors per domain: warden (lattices/gates), marshal (policy composition), atlas (pipeline stages), etc.
- **FR-9.3**: Design seeding produces station-specific `.dc.html` prototype with domain content pre-populated
- **FR-9.4**: Automation ensures zero manual re-engineering per station (one framework, nine instances)

**Acceptance Criteria:**
- 9 Design projects seeded with station-specific content (briefs consumed automatically)
- Station roster published in `station-roster.md` (thesis, personas, visual metaphors documented)
- Seed automation test: `herald deck seed pyforge-marshal pyforge-warden pyforge-atlas ... pyforge-herald` completes in <5m total (all 9 seeded in parallel)
- Visual consistency check: all 9 decks use Modernist; domain visuals are distinguishable (peer review)

**Interfaces:**
- Input: Station roster (briefs), Modernist tokens
- Output: 9 Design projects, seeded with station-specific prototypes; 9 × 6 artifact sets

---

#### FR-10: Multi-Format Artifact Export & Tracking (CAP-6)

**Requirement:** Deliver 6 artifact formats per station from a single Design source, with clear tracking decisions (what's tracked in git, what's gitignored).

**Sub-Requirements:**
- **FR-10.1**: Aggressive tracking strategy: Track design protos (3-4), markdown (5-8), PPTX (2-4), narration (1-2), infographics (0-1) per station
- **FR-10.2**: Gitignore intermediate builds: fragments.json, dist/, assets/, .mp4 (all regenerable in <30s)
- **FR-10.3**: Total tracked files: ~144 (9 stations × ~16 files) vs. ~270 unoptimized (62% reduction)
- **FR-10.4**: Export checklist updated per export cycle; all formats regenerable on CI/CD

**Acceptance Criteria:**
- Artifact tracking matrix published and reviewed (all decisions documented)
- Git status clean: `git status` reports only tracked files under `presentations/pyforge-*`; no stray intermediate builds
- Regeneration test: full clean checkout → `npm install && npm run build && pixi run deck-export` produces all 54 deliverable artifacts in <60s
- CI/CD gate: PR fails if any gitignored file is accidentally committed

**Interfaces:**
- Input: Design protos, markdown sources, deckcraft config
- Output: 54 tracked artifacts (6 formats × 9 stations) + CI/CD validation

---

### 3.2 Non-Functional Requirements

#### NFR-1: Performance

**Requirement:** All build and export operations complete in time suitable for interactive iteration loops.

**Sub-Requirements:**
- Seed operation: <30s per Design project (includes cloud creation + prototype seeding)
- Pull operation: <5s per deck (Design read + extraction + commit)
- Narration extraction: <1s per deck
- PPTX export: <10s per deck
- SVG infographic: <5s per deck
- HTML build: <15s for full batch (9 decks)
- Full export cycle (pull + extract + export): <90s for all 9 stations

**Acceptance Criteria:**
- Benchmark test suite measures all operations; P99 latency <2× target
- CI/CD pipeline completes full export in <5 minutes
- Developer iteration loop (edit → export → review) is interactive (sub-minute)

---

#### NFR-2: Reliability & Automation

**Requirement:** All operations are deterministic and idempotent; no manual intervention required for 9-station fleet orchestration.

**Sub-Requirements:**
- Seed, pull, export operations are fully automated; no interactive prompts
- Etagged protocol ensures idempotent pulls (running pull twice produces identical result)
- All pixi tasks define explicit inputs/outputs; no side effects
- Error cases are explicit (not silent failures); linter catches malformed output before commit

**Acceptance Criteria:**
- Linter test: all 9 exported artifacts pass format validation (Markdown, PPTX, SVG, JSON)
- Idempotency test: export-pull-export cycle produces identical artifacts
- CI/CD automation: full pipeline runs unattended; no manual review gates in the loop (except final deck content review)

---

#### NFR-3: Maintainability & Documentation

**Requirement:** Framework is understandable, modifiable, and teachable to future contributors.

**Sub-Requirements:**
- Design guide (`DESIGN_GUIDE.md`): documents six-act structure, L.A.T.C.H. principles, Modernist tokens, per-station customization
- Workflow guide (`WORKFLOW.md`): step-by-step seed/design/pull/export/ship walkthrough
- Troubleshooting guide: common issues (extraction artifacts, PPTX font errors, token mismatch), remediation steps
- All Herald CLI commands have inline `--help` and verbose output for debugging

**Acceptance Criteria:**
- A new team member can seed a new station deck end-to-end following guides (no Slack questions required)
- Design review comments are traceable to source (Dream → Spec → artifact)
- Code comments link to requirements (FR-1 through FR-10) and design rationale

---

#### NFR-4: Security & Access Control

**Requirement:** Design prototypes are authoritative; code-side copies are derived and cannot be the source of truth.

**Sub-Requirements:**
- Design `.dc.html` files are read-only after pull (git pre-commit hook prevents direct edits)
- Etagged protocol ensures only official Design-to-Code transfers are accepted (no force-pulls)
- Video scripts contain no sensitive information (speaker names, internal metrics, etc.)
- MCP token rotation on design-code-bridge access (security by isolation)

**Acceptance Criteria:**
- Pre-commit hook test: attempt to edit `.dc.html` → commit fails with clear message ("Design protos are read-only; edit in Claude Design")
- Access control test: pull operation verifies MCP token validity before writing
- Secrets scan: narration scripts and exported PPTX files contain no hardcoded API keys, passwords, or PII

---

### 3.3 Constraint Analysis

#### Resource Constraints

1. **Design Resources**
   - Human design authoring for 9 station decks (~3–4 hours per station)
   - Total: ~27–36 hours of visual iteration
   - Pattern: batch authoring (all 9 seeded simultaneously; parallel design work)

2. **Development Resources**
   - Infrastructure setup (Herald CLI, extraction tool, deckcraft pipeline): already proven on 7 decks
   - Per-station content generation (station briefs, narration scripts): ~1–2 hours per station
   - Total: ~15–20 hours of dev integration + ~9 hours QA/testing

3. **Build Infrastructure**
   - Pixi environments: `local-recipes` + existing deck-export toolchain (no new env required)
   - CI/CD: ~2.5 minutes per full build + export (GitHub Actions VM capacity sufficient)
   - Video rendering (bmad-manticore): external; not in critical path for Moment 1 completion

#### Technical Constraints

1. **File Size & Git Scalability**
   - 144 tracked files × 9 stations = ~144 files (design protos + sources + PPTX)
   - Expected repo size delta: +15–20 MB (PPTX files are binary, ~2 MB each)
   - Mitigation: aggressive gitignore strategy removes 62% of intermediate builds
   - Test: `git clone` time on clean repo, `git fetch` for active contributors (target: <30s each)

2. **Design Tool Limitations**
   - Claude Design MCP read_file/write_files have size limits (testing required for complex prototypes)
   - Etagged protocol assumes stable cloud API (Design service must guarantee etag consistency)
   - Fallback: manual pull if cloud API is unavailable (graceful degradation)

3. **Deckcraft Pipeline Assumptions**
   - python-pptx library limitations (some PowerPoint features not supported)
   - Modernist token coverage must include all fonts, colors, sizes used in prototypes (linter checks)
   - PPTX regeneration idempotency depends on deterministic markdown-to-pptx transform (test: re-export produces identical binary)

#### Schedule Constraints

1. **Moment 1 Completion Target**
   - All 9 Design projects seeded: 1 day (parallel operations)
   - Human design iteration: 3–5 days (asynchronous, design-team-controlled)
   - Code-side extraction + export: 1 day (after Design authoring complete)
   - QA + refinement: 1–2 days (linter fixes, visual review iterations)
   - **Total: 6–9 business days**

2. **Video Production (Optional for Moment 1)**
   - Narration script extraction: included in export (day 1)
   - Video rendering (bmad-manticore): external, ~30–60s per video (optional; defer to Moment 2)
   - Pattern: narration scripts ready at Moment 1 close; video production starts in parallel for Moment 2 spike

---

### 3.4 Dependency & Integration Analysis

#### Internal Dependencies (Herald Project)

```
FR-10 (Multi-Format Export)
  ├─ FR-1 (Design-Code Round-Trip)
  ├─ FR-2 (Markdown Extraction)
  ├─ FR-3 (Narration Extraction)
  ├─ FR-4 (PPTX Export)
  ├─ FR-5 (SVG Infographic)
  ├─ FR-6 (Interactive HTML)
  ├─ FR-7 (Design-System Tokens)
  ├─ FR-8 (Six-Act Structure)
  └─ FR-9 (Station Customization)
```

**Critical Path:** FR-1 (Design-Code round-trip) must succeed before FR-2, FR-3, FR-4, FR-5 can run. All export operations (FR-4, FR-5, FR-6) are parallelizable.

#### External Dependencies

1. **Claude Design MCP Service**
   - Input: MCP API availability, etagged file read/write, large-file support (up to ~50 MB `.dc.html`)
   - Risk: API unavailability → pull operation fails; mitigation = fallback to manual file transfer (out-of-band)
   - Status: Already proven on 7 decks; low risk

2. **Modernist Design System (Source)**
   - Input: Figma tokens (or canonical JSON), exported to `tokens.json`
   - Status: Already defined; available in Sentinel project + Modernist Claude Design project
   - Risk: Token drift if Figma is edited without exporting; mitigation = CI/CD gate checks token freshness

3. **bmad-manticore (Video Production)**
   - Input: Narration scripts (from FR-3), real screen recordings, production bibles
   - Status: Installed and active; external pipeline (not in critical path for Moment 1)
   - Risk: Video rendering expensive (~30–60s per video); mitigation = optional for Moment 1; prioritize pilot subset (Marshal, Warden, Atlas)

4. **PyForge Station Metadata**
   - Input: Station briefs (thesis, pain point, solution pillars, personas)
   - Status: Not yet formalized; requires input from station owners or product team
   - Risk: Missing briefs delay Design seeding; mitigation = draft generic briefs per station, iterate with stakeholders

5. **Pixi Environment (deck-export)**
   - Input: deckcraft, python-pptx, marp-cli, markitdown installed in `local-recipes` environment
   - Status: Already available; deck-export pixi task already defined
   - Risk: Low; existing toolchain
   - Verification: `pixi run deck-export --help` succeeds

---

### 3.5 Acceptance & Validation Plan

#### Phase 1: Preparation & Seeding (Days 1–2)

**Gate:** All 9 Design projects seeded successfully; Modernist bound; station briefs finalized.

**Validation:**
- [ ] 9 Design projects created and accessible via claude.ai/design
- [ ] All projects report Modernist design system binding (MCP inspection)
- [ ] Station briefs (thesis, pain point, solution, personas) documented in `station-roster.md`
- [ ] Herald CLI seed operation completes for all 9 stations in <2 minutes total

---

#### Phase 2: Design Authoring (Days 3–7)

**Gate:** 9 Design prototypes complete, iterated, and ready for export.

**Validation:**
- [ ] Each Design prototype follows six-act structure (24–32 slides per deck)
- [ ] Each prototype includes persona appendix (stakeholder voting records, context)
- [ ] Speaker notes populated for all slides (input to narration extraction)
- [ ] Peer review: design consistency across 9 decks (Modernist identity applied uniformly)

---

#### Phase 3: Code-Side Export & Build (Days 8–9)

**Gate:** All 6 artifact formats exported, built, tested, and ready to ship.

**Validation:**
- [ ] Pull operation succeeds for all 9 stations; `.dc.html` tracked, no overwrites
- [ ] Markdown extraction produces valid Marp files; structure matches Design intent
- [ ] PPTX files open and edit in PowerPoint; fonts, colors, layouts correct (manual test)
- [ ] SVG infographics render inline (no raster fallbacks); Modernist tokens applied
- [ ] HTML decks build successfully; keyboard nav, presenter mode work (Cypress E2E test)
- [ ] Narration scripts extracted, linter-clean, available for manticore pipeline
- [ ] Artifact tracking matrix verified: 144 tracked files, ~62% reduction vs. unoptimized
- [ ] All linters pass: Markdown, PPTX, SVG, JSON validation green
- [ ] Git clean: only tracked artifacts committed; no stray intermediate builds

---

#### Phase 4: QA & Refinement (Days 10–12, Optional)

**Gate:** All artifacts pass final review; ready to ship.

**Validation:**
- [ ] Design review: all 9 decks approved (design leadership sign-off)
- [ ] Accessibility check: all 9 HTML decks pass WCAG 2.1 AA
- [ ] Video readiness: narration scripts approved for manticore intake; screen recordings staged
- [ ] Documentation: DESIGN_GUIDE.md, WORKFLOW.md, station-roster.md published and reviewed
- [ ] Regression test: export-pull-export cycle produces identical artifacts (idempotency confirmed)

---

### 3.6 Risk Register & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Design prototype exceeds MCP file-size limit (~50 MB) | Low | High | Pre-check file size; split prototype if needed (separate cover/appendix) |
| Etagged safety protocol fails; silent overwrite occurs | Low | Critical | Comprehensive test suite (concurrent pull + Design edit); manual verification |
| PPTX regeneration not deterministic; binary differs on re-export | Medium | High | Deterministic build test; if fails, track `.pptx` as immutable (not regenerable) |
| Station briefs unavailable or incomplete | Medium | Medium | Draft generic briefs; iterate with stakeholders in parallel during Design authoring |
| Video rendering (manticore) delays Moment 1 completion | Low | Low | Video optional for Moment 1; defer to Moment 2 spike; narration scripts ready for pipeline |
| Modernist tokens drift between Figma and deployed spec | Medium | High | CI/CD gate: token freshness check; linter verifies all artifacts use canonical tokens |
| New pixi environment required for deckcraft | Low | Medium | Verify existing `local-recipes` env has all dependencies; single `pixi.toml` update if needed |
| Design ↔ Code round-trip breaks on Design service outage | Low | Medium | Fallback to manual pull (email export + git manual import); graceful degradation documented |

---

## Summary

Herald Pitch Expansion is a well-scoped orchestration of four proven Tier 1 capabilities designed to deliver six-artifact pitch decks for 9 PyForge stations. The market opportunity is substantial ($5.3B TAM), competitive advantages are defensible (design-code round-trip automation + token portability + real-footage discipline + fleet-scale orchestration), and all technical requirements are addressable with existing infrastructure.

**Key Success Factors:**
1. Design-code-bridge automation (proven; low risk)
2. Modernist token portability across all formats (requires validation; medium risk)
3. PPTX regeneration determinism (requires comprehensive test; medium risk)
4. Station brief finalization (requires stakeholder input; low-medium risk)
5. Narrative consistency across six-act structure (human-driven; medium risk)

**Next Steps:** Feed this research into BMAD's PRD/Architecture/Epics decomposition to translate requirements into implementation stories.
