---
stepsCompleted: ['step-01-validate-prerequisites']
inputDocuments:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-pitch/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-herald-pitch-2026-08-01/ARCHITECTURE-SPINE.md
---

# Herald Pitch Deck Family Expansion - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Herald's Pitch Deck orchestration across 9 PyForge stations (Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald), decomposing the Spec, PRD, and Architecture into implementable stories with acceptance criteria.

**Core Mission**: Produce 6 artifact formats per station from a single Design source using proven Tier 1 capabilities (Design-Code-Bridge, Deckcraft, Video-Scripts, Modernist-Identity) with zero manual file transfers and aggressive footprint optimization (62% reduction).

**Herald CLI v0.1.0 Status**: Herald CLI is already shipped with seed/pull commands. This effort extends beyond CLI to the full design-to-delivery pipeline for all 9 station decks, including PPTX export, narration extraction, HTML deck builds, and comprehensive validation.

---

## Requirements Inventory

### Functional Requirements (20 FRs)

**Design Source & Seeding (CAP-1: Design-Code-Bridge)**
- FR1: System must seed Design projects per station via 'herald deck seed <station>' command
- FR2: System must pull updated Design protos into Code with etagged safety via 'herald deck pull <station>'
- FR3: System must extract markdown sources from Design protos automatically
- FR18: System must support round-trip Design ↔ Code via Design-Code-Bridge with etagged safety

**PPTX Generation & Design Tokens (CAP-2: Deckcraft Framework)**
- FR4: System must transform markdown sources into editable PowerPoint files (PPTX)
- FR5: System must apply Modernist design tokens to PPTX generation
- FR9: System must maintain one design system (Modernist-Identity) with tokens for Figma → JSON → PPTX → deck engine → video

**Narrative & Video Scripts (CAP-3: Video-Scripts Framework)**
- FR6: System must generate {station}-narration-YYYY-MM-DD.md files from Design speaker notes
- FR7: System must feed narration corpus to bmad-manticore for video production
- FR16: System must enforce voice bible consistency (WPM, speech patterns, tone markers) via linter
- FR17: System must prevent fabricated demos—all video content must be real screen recordings

**Deck Framework & Structure (CAP-5: Six-Act Deck Framework)**
- FR10: System must structure all decks per six-act framework (Cover, Acts I-VI, Appendix) with ~28 slides
- FR11: System must apply L.A.T.C.H. visual principles (Location, Analogy, Time, Color, Hierarchy) to all decks

**Infographics & Multi-Format Export (CAP-6: Multi-Format Export)**
- FR8: System must extract SVG infographics from Design protos
- FR14: System must build interactive HTML decks from Markdown via Vite (gitignored, regenerable <5s)
- FR15: System must validate all 9 HTML decks render without error via 'dashboard-check'
- FR19: System must track 6 artifact formats per station: .dc.html, markdown, PPTX, narration, SVG, HTML (built)
- FR20: System must gitignore intermediate artifacts (fragments.json, dist/, assets/, .mp4) with deterministic regeneration

**Station Customization (CAP-7: Station-Specific Customization)**
- FR12: System must support per-station customization (thesis, pain point, solution pillars, personas)
- FR13: System must support per-station visuals (domain-appropriate diagrams per 9 stations)

### Non-Functional Requirements (12 NFRs)

- NFR1: All Design ↔ Code transfers must validate etags; conflicts must fail loudly, never silently overwrite
- NFR2: All 9 PPTX files must open and edit correctly in Microsoft PowerPoint with fonts/colors/layouts preserved
- NFR3: All infographics must render as inline SVG (zero raster .png/.jpg images)
- NFR4: All 9 HTML decks must render without error; 'dashboard-check' pass is terminal validation
- NFR5: No fabricated product demos—all screen recordings must be real, never AI-generated mockups or synthetic UI
- NFR6: Narration must pass linter validation (voice bible + blacklist) before video pipeline accepts it
- NFR7: HTML deck regeneration must complete in <5 seconds
- NFR8: Video regeneration must complete in <60 seconds
- NFR9: Design protos must be tracked as immutable source of truth; code-side never pushes back to Design
- NFR10: Tracked footprint must not exceed ~144 files (9 stations × ~16 files); 62% reduction from ~270 unoptimized
- NFR11: All 9 stations must inherit tokens from single Modernist-Identity source (no per-station token drift)
- NFR12: Speaker notes → narration extraction must be mechanical and deterministic (no hand-authoring)

### Additional Requirements (10 Architecture Decision Records - ADRs)

- **AD-1**: Each of 9 PyForge stations has exactly one immutable Design prototype (.dc.html) as source of truth
- **AD-2**: Etagged safety protocol: read-file includes etag; write-file requires matching etag or fails explicitly
- **AD-3**: Multi-format export pipeline with explicit ownership (Design → Markdown → PPTX, Narration, SVG → HTML, Video)
- **AD-4**: Aggressive tracking strategy: track source + finals (~144 files), gitignore regenerables (fragments, dist/, assets/, .mp4)
- **AD-5**: Modernist tokens as single authority: Figma → design-tokens.json → templates (PPTX, deck engine, video bibles)
- **AD-6**: Identical framework across all 9 stations; per-station content varies (thesis, pain point, solution, personas)
- **AD-7**: Narration extraction mechanical from Design speaker notes; deterministic, tracked, fed to video pipeline
- **AD-8**: Video pipeline boundary: Herald orchestrates extraction/sourcing; bmad-manticore handles render (voice, graphics, SFX, final .mp4)
- **AD-9**: No fabricated demos constraint: Herald enforces real footage sourcing; Manticore enforces at graphics-beats gate
- **AD-10**: Narration voice identity enforced by linter (WPM, patterns, tone markers); blacklist blocks non-matching narration

### Requirements Coverage Map

| Requirement Category | Epic(s) | Stories | Status |
|---|---|---|---|
| Design seeding & pulling (FR1-3, FR18) | Epic 1 | 1.1-1.3 | Ready |
| PPTX & token application (FR4-5, FR9) | Epic 2 | 2.1-2.2, 2.5 | Ready |
| Narration extraction (FR6-7, FR16-17) | Epic 3 | 3.1-3.4 | Ready |
| SVG infographic extraction (FR8) | Epic 2 | 2.3 | Ready |
| Six-act framework & L.A.T.C.H. (FR10-11) | Epic 1 | 1.2, 1.4 | Ready |
| HTML decks & validation (FR14-15) | Epic 2 | 2.4-2.5 | Ready |
| Per-station customization (FR12-13) | Epic 4 | 4.1-4.9 (9 stories) | Ready |
| Artifact tracking & optimization (FR19-20) | Epic 0 | 0.2-0.3 | Ready |
| Modernist tokens foundation (AD-5) | Epic 0 | 0.1 | Ready |
| All ADRs (AD-1 through AD-10) | All epics | All stories | Ready |

---

## Epic List

- **Epic 0**: Foundation & Infrastructure — Design-Code-Bridge etagged protocol, Modernist tokens, aggressive tracking strategy
- **Epic 1**: Design Authoring & Seeding — Create 9 Design projects, establish six-act framework structure, seed with contract-compliant prototypes
- **Epic 2**: Multi-Format Export Pipeline — Markdown, PPTX, SVG, HTML deck engine with etagged safety
- **Epic 3**: Narration Extraction & Validation — Mechanical extraction, linter enforcement, video pipeline staging
- **Epic 4**: Station-Specific Customization — 9 stations × 6 formats with domain-appropriate content and visuals
- **Epic 5**: Build, Validation & Shipping — Comprehensive validation, footprint verification, git commit and narration staging

---

## Epic 0: Foundation & Infrastructure

**Goal**: Establish infrastructure for Design-Code-Bridge, Modernist design tokens, and aggressive artifact tracking strategy.

### Story 0.1: Set up Modernist-Identity design system and token exports

As a **design system curator**,
I want **Modernist design tokens to be centralized and exportable**,
So that **all 9 station decks inherit consistent visual language without drift**.

**Acceptance Criteria:**

**Given** the Modernist-Identity design system is defined in Figma
**When** design-tokens.json is generated from Figma variables
**Then** the JSON contains all required token categories:
- Colors: light palette (#f3f2f2), ink (#201e1d), red accent (#ec3013/#c22a10)
- Typography: Archivo font family with size/weight scale
- Spacing: Grid-based spacing scale (8px baseline)
- Borders: 2px rules, zero corner radius
**And** the token structure supports round-trip (Figma → JSON → PPTX templates → deck engine → video bibles)

**Given** design-tokens.json exists
**When** a PPTX template references tokens
**Then** token values are applied correctly (no hardcoded colors/fonts)
**And** regenerating PPTX preserves token-driven styling

### Story 0.2: Establish .gitignore strategy and artifact tracking matrix

As a **repo maintainer**,
I want **.gitignore to reflect the aggressive optimization strategy (62% reduction)**,
So that **tracked footprint stays ~144 files (vs. 270 unoptimized) with deterministic regeneration**.

**Acceptance Criteria:**

**Given** the artifact tracking matrix is defined (track source + finals, gitignore intermediates)
**When** .gitignore is updated
**Then** the following are gitignored:
- fragments.json (deck extraction intermediates)
- dist/ (HTML deck build output)
- assets/ (compiled JS/CSS)
- .mp4 (video renders)
- node_modules, build caches
**And** the following are tracked:
- .dc.html (design protos, 1 per station)
- .md (markdown sources, 5-8 per station)
- .pptx (PPTX exports, 2-4 per station)
- narration .md files (1-2 per station)
- .svg infographics (0-1 per station)

**Given** the tracking strategy is in place
**When** artifacts are built and committed
**Then** tracked file count for 9 stations ≈ 144 (±10%)
**And** all gitignored artifacts regenerate deterministically (<5s for HTML, <60s for video)

### Story 0.3: Implement Design-Code-Bridge etagged pull protocol

As a **developer**,
I want **etagged pull operations to prevent silent overwrites**,
So that **Design ↔ Code transfers are safe across concurrent edits**.

**Acceptance Criteria:**

**Given** a Design proto exists at design-cloud:/{station}.dc.html
**When** `herald deck pull <station>` is executed
**Then** the pull reads the etag from Design cloud
**And** stores the etag alongside the pulled artifact
**And** all subsequent writes to the same artifact require matching etag or fail explicitly

**Given** a pull operation is in-flight
**When** Design edits occur concurrently
**Then** the next pull validates etagged responses
**And** detects mismatch, fails with clear error message
**And** does not silently merge or overwrite

---

## Epic 1: Design Authoring & Seeding

**Goal**: Seed 9 Design projects per PyForge station, establish seeding contract, and author initial prototypes per six-act framework.

### Story 1.1: Create 9 Design projects (seed per station)

As a **design system curator**,
I want **9 Design projects created and bound to Modernist identity**,
So that **each PyForge station has a dedicated visual authoring surface**.

**Acceptance Criteria:**

**Given** the Herald seeding contract is defined (1920×1080, Archivo, Modernist palette)
**When** `herald deck seed <station>` is executed for each of the 9 stations (Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald)
**Then** a Design project is created with:
- Name: `pyforge-{station}-pitch`
- Bound to Modernist-Identity design system
- Starter prototype (1920×1080 canvas, Archivo font, light palette, visible grid, 2px rules)
- Speaker notes section ready for narration
- Etagged tracking enabled

### Story 1.2: Establish six-act framework structure in Design prototypes

As a **deck author**,
I want **each Design prototype structured per six-act framework**,
So that **all 9 decks tell coherent stories with consistent narrative arc**.

**Acceptance Criteria:**

**Given** a Design project is seeded
**When** a deck author begins editing
**Then** the prototype includes slide placeholders for:
- Cover (hook + thesis statement)
- Act I (friction/pain point)
- Act II (insight/aha moment)
- Act III (mechanics, 4-step delivery, L.A.T.C.H. Time)
- Act IV (real-world fit, L.A.T.C.H. Location)
- Act V (future/vision, L.A.T.C.H. Category)
- Act VI (action/CTA)
- Appendix (personas + stakeholder context)

**Given** the six-act structure is in place
**When** a deck is authored
**Then** each deck contains ~28 slides total
**And** all speaker notes are written for narration extraction

### Story 1.3: Extract markdown sources from Design prototypes

As a **developer**,
I want **markdown sources extracted from Design protos automatically**,
So that **version-controlled markdown becomes available for downstream pipelines**.

**Acceptance Criteria:**

**Given** a Design proto is finalized in Design cloud
**When** `herald deck pull <station>` is executed
**Then** the Design proto is pulled into Code as .dc.html
**And** markdown extraction occurs automatically (mechanical, no hand-authoring)
**And** markdown file is saved to `src/marp/{station}.md`
**And** extraction is deterministic (same Design proto → same markdown every time)

### Story 1.4: Validate station-specific narrative content in all 9 decks

As a **content reviewer**,
I want **each station's deck to include domain-specific narrative**,
So that **station personas and solutions are articulated clearly**.

**Acceptance Criteria:**

**Given** all 9 decks are authored
**When** a content reviewer audits them
**Then** each deck contains:
- Station thesis (unique value proposition)
- Pain point (friction/problem framing specific to domain)
- Solution pillars (3-5 pillars of the solution, domain-specific)
- Ecosystem vision (how the station fits in PyForge, long-term direction)
- Personas (stakeholder context, voting records, challenges)

---

## Epic 2: Multi-Format Export Pipeline

**Goal**: Implement automated pipeline to produce 6 artifact formats per station from Design protos (Markdown, PPTX, SVG, HTML, Narration, Build artifacts).

### Story 2.1: Implement deckcraft pipeline (Markdown → PPTX with tokens)

As a **developer**,
I want **markdown sources to transform into editable PowerPoint files**,
So that **presenters can open and edit decks in Microsoft PowerPoint**.

**Acceptance Criteria:**

**Given** markdown source is available
**When** `pixi run deck-export` is executed
**Then** deckcraft pipeline processes markdown for each station:
- Reads markdown source (marp format)
- Applies Modernist design tokens (fonts, colors, spacing from design-tokens.json)
- Generates PPTX using python-pptx
- Outputs to `src/pptx/{station}.pptx`
**And** pipeline completes in 5-10s per deck

**Given** a PPTX file is generated
**When** it is opened in Microsoft PowerPoint
**Then** it opens without errors
**And** all fonts are Archivo (or fallback applied correctly)
**And** all colors match design tokens (light, ink, accent, derivatives)
**And** content can be edited without breaking the deck

### Story 2.2: Implement SVG infographic extraction from Design

As a **developer**,
I want **SVG infographics extracted from Design as inline assets**,
So that **diagrams are vector-based, regenerable, and never raster**.

**Acceptance Criteria:**

**Given** Design protos contain diagrams/infographics
**When** `herald deck pull <station>` extracts the Design
**Then** diagrams are exported as SVG:
- One infographic per station (stored in `src/marp/{station}-infographic.svg`)
- SVG is inline, self-contained (no external dependencies)
- Colors use design tokens (not hardcoded hex)

**Given** SVG infographics are extracted
**When** they are inspected
**Then** they contain:
- No raster images (.png, .jpg, .gif)
- Only vector shapes, paths, and text

### Story 2.3: Build interactive HTML decks via Vite (gitignored, regenerable)

As a **developer**,
I want **HTML decks to be built from markdown via Vite in <5 seconds**,
So that **decks are interactive, navigable, and regenerable on-demand**.

**Acceptance Criteria:**

**Given** markdown sources and design tokens are available
**When** `pixi run build-decks` is executed
**Then** Vite builds all 9 decks:
- Compiles markdown to HTML via deck engine
- Applies design tokens to CSS
- Each deck is standalone, self-contained
- Build completes in <5s total

**Given** HTML decks are built
**When** they are served or opened locally
**Then** all 9 decks render without console errors
**And** keyboard navigation works

### Story 2.4: Validate all 9 decks via dashboard-check

As a **CI/QA**,
I want **all 9 HTML decks validated by dashboard-check**,
So that **render failures are caught before shipping**.

**Acceptance Criteria:**

**Given** all 9 HTML decks are built
**When** `pixi run dashboard-check` is executed
**Then** the check validates:
- All 9 decks load without 404s or broken assets
- All 9 decks render in browser (no console errors)
- All fonts load correctly (Archivo)
- All colors are present (light, ink, accent)
- All slides are navigable
**And** exit code is 0 if all pass, non-zero if any fail

### Story 2.5: Establish Modernist design token application across all 9 PPTX files

As a **design system owner**,
I want **all 9 PPTX files to inherit Modernist tokens without per-station overrides**,
So that **visual consistency is guaranteed and token changes flow downstream**.

**Acceptance Criteria:**

**Given** design-tokens.json is the single authority
**When** any PPTX template is regenerated
**Then** it consumes tokens from design-tokens.json only (no hardcoded values)
**And** all 9 PPTX files use identical token values (no per-station drift)

---

## Epic 3: Narration Extraction & Validation

**Goal**: Extract narration scripts from Design speaker notes, validate against voice bible and blacklist, and stage for video pipeline.

### Story 3.1: Implement mechanical narration extraction from Design speaker notes

As a **developer**,
I want **narration scripts extracted mechanically from Design speaker notes**,
So that **narrator text is deterministic, reproducible, and fed to video pipeline**.

**Acceptance Criteria:**

**Given** Design protos include speaker notes for all slides
**When** `herald deck pull <station>` extracts the Design
**Then** narration extraction occurs automatically:
- Speaker notes are parsed from each slide
- Extracted to `src/marp/{station}-narration-{YYYY-MM-DD}.md`
- Extraction is deterministic (same Design → same narration every time)

### Story 3.2: Implement narration linter (voice bible + blacklist enforcement)

As a **video producer**,
I want **narration to be validated against voice bible and blacklist before video render**,
So that **tonal consistency and accuracy are guaranteed**.

**Acceptance Criteria:**

**Given** narration script is extracted
**When** `pixi run lint-narration <station>` is executed
**Then** linter validates:
- WPM (words per minute) falls within character's established range
- Speech patterns match
- Tone markers are appropriate
- Blacklist items are not present

**Given** linter fails
**When** error report is generated
**Then** report includes:
- Specific violation
- Location (slide number, line number)
- Guidance for correction

### Story 3.3: Stage narration scripts for bmad-manticore video pipeline

As a **video orchestrator**,
I want **all 9 narration scripts staged and available for Manticore**,
So that **video production can proceed on-demand**.

**Acceptance Criteria:**

**Given** all 9 narration scripts are extracted and linter-validated
**When** a manifest is generated for video pipeline
**Then** manifest includes:
- Station name and slug
- Narration script path
- Real screen recording source paths (curator-verified)

### Story 3.4: Enforce "no fabricated demos" constraint

As a **quality assurance**,
I want **all video content to use real screen recordings**,
So that **product claims are authentic and liability is minimized**.

**Acceptance Criteria:**

**Given** screen recordings are sourced for video pipeline
**When** a curator verifies real-footage sources
**Then** each source is marked as:
- Real product behavior (recorded from live system)
- Never AI-generated mockup or synthetic UI

---

## Epic 4: Station-Specific Customization

**Goal**: Customize content and visuals for all 9 PyForge stations while maintaining identical framework and design system.

### Story 4.1–4.9: Customize each of 9 stations (Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald)

For each station, implement per-station customization ensuring:
- Station thesis (unique value proposition)
- Pain point (domain-specific friction)
- Solution pillars (3-5 domain-specific capabilities)
- Ecosystem vision (station's role in PyForge)
- Personas (stakeholder context, voting records)
- Per-station visuals (domain-appropriate diagrams)
- All graphics use Modernist design tokens
- All text uses Archivo font

**9 Stories, one per station (4.1–4.9), following identical pattern but with station-specific content.**

---

## Epic 5: Build, Validation & Shipping

**Goal**: Validate all artifacts, verify optimization targets, and commit tracked files to git for publication.

### Story 5.1: Run comprehensive artifact validation (render, format, consistency checks)

As a **QA/release engineer**,
I want **all 9 decks validated comprehensively before shipping**,
So that **shipping is risk-free and quality is guaranteed**.

**Acceptance Criteria:**

**Given** all 9 × 6 artifact sets are built
**When** `pixi run validate-all-artifacts` is executed
**Then** validation includes:
- Render checks: All 9 HTML decks load without errors
- Format checks: All PPTX files open in PowerPoint; all SVG infographics validate
- Consistency checks: All 9 decks follow six-act structure; all use Modernist tokens
- Narration checks: All 9 narration scripts pass linter; voice identity consistent
- Footprint checks: Tracked files ≈ 144; gitignored artifacts regenerate deterministically

### Story 5.2: Verify 62% footprint reduction (tracked vs. unoptimized)

As a **repo maintainer**,
I want **footprint targets verified before shipping**,
So that **git repository stays lean and regenerable**.

**Acceptance Criteria:**

**Given** all 9 stations have been processed
**When** `pixi run footprint-check` is executed
**Then** check counts:
- Tracked files: design protos + markdown + PPTX + narration + SVG (all present)
- Gitignored files: fragments.json, dist/, assets/, .mp4 (all must be gitignored)
- Total tracked: ≈ 144 files (±10%)
- Reduction: ≈ 62% ✓

### Story 5.3: Commit tracked artifacts and stage narration for video pipeline

As a **developer**,
I want **all tracked artifacts committed to git**,
So that **source of record is preserved and narration is staged for downstream video production**.

**Acceptance Criteria:**

**Given** all artifacts are validated
**When** `git add <tracked-files>` is executed
**Then** only tracked files are staged:
- All 9 × `.dc.html` design protos
- All 9 × `.md` markdown sources
- All 9 × `.pptx` PPTX exports
- All 9 × `-narration-*.md` narration scripts
- All 9 × `-infographic.svg` SVG files

**Given** tracked artifacts are staged
**When** narration scripts are staged for video pipeline
**Then** manifest is generated including:
- All 9 narration script paths
- Real screen recording source refs (curator-confirmed)
- Video output specs and priorities

---

## Notes for Implementation

### Known Herald CLI v0.1.0 Status

Herald CLI v0.1.0 is already shipped. The following commands are implemented:
- `herald deck seed <station>` — Seed Design projects
- `herald deck pull <station>` — Pull Design protos with etagged safety

**Stories tied to existing Herald CLI code (may be marked as completed if re-verified)**:
- Story 0.3: Design-Code-Bridge etagged pull protocol (partially implemented in CLI)
- Story 1.1: Create 9 Design projects (already seeded via CLI for some stations)
- Story 1.3: Extract markdown sources (already implemented in CLI)

**New work (not yet implemented)**:
- Epic 0: Foundation & Infrastructure (tokens, tracking strategy, .gitignore)
- Epic 1 Stories 1.2, 1.4: Six-act framework structure, narrative validation
- Epic 2: Multi-Format Export Pipeline (deckcraft, SVG, HTML, dashboard-check)
- Epic 3: Narration Extraction & Validation (extraction, linter, pipeline staging)
- Epic 4: Station-Specific Customization (9 × customization stories)
- Epic 5: Build, Validation & Shipping

### Success Signal Summary

All work complete when:
✅ 9 Design projects seeded with Modernist tokens
✅ 9 prototypes authored per six-act framework
✅ 54 artifacts exported (9 × 6 formats) and tracked
✅ All 9 PPTX files open in PowerPoint
✅ All 9 HTML decks render; dashboard-check passes
✅ All 9 narration scripts extracted and linter-validated
✅ Zero manual file transfers; Design-Code-Bridge validated end-to-end
✅ Footprint: ~144 tracked files (62% reduction)
✅ Narration scripts staged for bmad-manticore

---

**Epics Generated**: 2026-08-01  
**Status**: Ready for developer implementation  
**Next Step**: Developer begins with Epic 0, then proceeding sequentially through Epics 1–5.
