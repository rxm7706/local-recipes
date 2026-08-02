---
title: Herald Pitch Orchestration Architecture
slug: herald-pitch
status: final
created: 2026-08-01
updated: 2026-08-01
altitude: feature
---

# Herald Pitch Orchestration Architecture

**Feature**: Herald's Pitch Deck orchestration across 9 PyForge stations, producing 6 artifact formats per station from a single Design source with etagged safety and zero manual file transfers.

---

## Paradigm: Design-Code-Bridge with Etagged Pull Model

**Core insight**: One immutable Design prototype per station → Etagged pull into Code → Multi-format pipeline → Tracked finals + regenerable intermediates.

**Design Source of Truth**: Single `.dc.html` file per station is the immutable design prototype, tracked in git at `project/{station}.dc.html`. All code-side artifacts derive from it via an explicit pull model. Design edits happen in Claude Design cloud; Code never pushes back.

**Etagged Pull Model**: Every Design ↔ Code transfer validates etags. Write operations fail if etags mismatch, preventing silent overwrites. The protocol is deterministic and safe across concurrent edits.

**Multi-Format Export Pipeline**: Pull (etagged) → Markdown (marp) → PPTX (deckcraft) + Narration extraction → HTML deck engine + Video scripts. Each format has explicit ownership and regenerability status.

---

## Architecture Decision Records

### AD-1: Single Immutable Design Prototype per Station

**Binds**: Each of the 9 stations (Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald) has exactly one Design prototype file (`.dc.html`) as the source of truth.

**Prevents**: 
- Design drift between multiple design sources
- Silent overwrites when pulling updated designs
- Ambiguity about which version is current

**Rule**: All markdown, PPTX, narration, SVG, and video scripts derive from the single `.dc.html`. Code-side edits to any derived artifact do not flow back to Design.

**[ADOPTED]** — Proven on 7 existing decks; Design-Code-Bridge framework established.

---

### AD-2: Etagged Safety on All Design ↔ Code Transfers

**Binds**: Every pull operation includes etag validation. Write operations require matching etag or fail explicitly.

**Prevents**:
- Mid-flight Design edits overwriting Code-side pulls
- Silent data loss during concurrent updates
- Ambiguous conflict states

**Rule**: 
- Read: Include `etag` in response metadata.
- Write: Require matching `etag` in request; reject if mismatch.
- On conflict: Fail loudly; never silently merge or prefer one side.

**[ADOPTED]** — Proven in Design-Code-Bridge protocol on 7 decks.

---

### AD-3: Multi-Format Export Pipeline with Explicit Ownership

**Binds**: Artifact derivation follows a single pipeline: Design (source) → Markdown → PPTX, Narration, SVG → HTML deck engine, Video scripts (finals). Each format has a clear owner and regenerability status.

**Prevents**:
- Ambiguity about which format is authoritative
- Multiple code paths producing the same artifact
- Stale intermediate artifacts blocking shipping

**Rule**:
1. **Design protos** (`.dc.html`): Source of truth, tracked, etagged.
2. **Markdown** (marp): Extracted from Design protos, tracked, regenerable.
3. **PPTX** (deckcraft): Generated from Markdown + design tokens, tracked for deliverable readiness.
4. **Narration scripts** (`.md`): Extracted from Design speaker notes, tracked for video pipeline.
5. **SVG infographics**: Extracted as inline assets, tracked, never raster.
6. **HTML decks** (Vite): Built from Markdown, gitignored, regenerable in <5s.
7. **Video scripts** (`.mp4` via manticore): Rendered downstream, gitignored, regenerable in <60s.

**[ADOPTED]** — Workflow stages defined in spec companions; proven on deckcraft (PPTX) and existing deck engines (HTML).

---

### AD-4: Aggressive Artifact Tracking Strategy (62% Footprint Reduction)

**Binds**: Track source + final deliverables; gitignore regenerable intermediates. Total tracked footprint: ~144 files (9 stations × ~16 files) vs. ~270 unoptimized.

**Prevents**:
- Repository bloat from storing regenerable artifacts
- Confusion about what lives where and why
- Wasted storage on build fragments

**Rule**:
- **Tracked**: Design protos (1 each), Markdown (5–8 each), PPTX (2–4 each), Narration (1–2 each), SVG infographics (0–1 each) = ~144 total.
- **Gitignored**: fragments.json, dist/, assets/, .mp4, node_modules, build caches (all regenerable in <15s for HTML, <60s for video).
- **Verification**: `pixi run dashboard-check` validates all tracked artifacts render correctly. Build pipeline proves all gitignored artifacts regenerate deterministically.

**[ADOPTED]** — Optimization strategy verified in spec appendix; no new infrastructure required.

---

### AD-5: Modernist Design Tokens as Single Authority

**Binds**: One source of truth for design tokens (Figma variables). Tokens round-trip through: Figma → design-tokens.json → PPTX templates → deck engine → video production bibles.

**Prevents**:
- Token drift across surfaces (PPTX vs. HTML vs. Video)
- Hardcoded colors/fonts in templates
- Inconsistent visual identity across all 9 stations

**Rule**:
- Figma is the authority for all design tokens (colors, fonts, spacing, grid).
- Token changes flow: Figma → design-tokens.json (automated export) → templates (updated on next build).
- Templates consume tokens declaratively, never hardcode values.
- All 9 stations inherit tokens from the same source; per-station visuals vary (diagrams, photos), not fundamentals.

**[ADOPTED]** — Modernist-Identity framework CAP-4 defines tokens; round-trip proven on existing work.

---

### AD-6: Nine-Station Replication with Identical Framework

**Binds**: Framework (Design-Code-Bridge, Deckcraft, Video-Scripts, Modernist-Identity) is identical across all 9 stations. Per-station content varies: thesis, pain point, solution pillars, ecosystem vision, personas.

**Prevents**:
- Re-engineering the framework for each station
- Inconsistency in narrative structure (six-act framework)
- Manual coordination between station teams

**Rule**:
- One deck workflow applies to all 9 stations: Seed → Design → Pull → Build → Extract → Ship.
- Content customization happens in Design (speaker notes, visuals, personas); Framework never changes.
- Tooling abstractions (deckcraft, video-scripts, design-code-bridge) are station-agnostic.

**[ADOPTED]** — Seven-station consolidation proven in spec; station roster confirms 9 domains ready for content authoring.

---

### AD-7: Narration Script Extraction from Design Speaker Notes

**Binds**: Narration scripts are extracted mechanically from Design speaker notes, generating `{station}-narration-YYYY-MM-DD.md` per deck. Extraction is deterministic and tracked.

**Prevents**:
- Manual narration authoring (error-prone, not reproducible)
- Narration drift from visual story (speaker notes stay in sync)
- Ambiguity about what video pipeline consumes

**Rule**:
- Speaker notes in Design proto → Extracted to narration.md via mechanical extraction.
- Narration enforced linter: WPM, speech patterns, tone markers validated against voice bible.
- Narration blacklist (fabricated claims, misleading language) applied before any video render.
- Tracked in git for source auditability and video pipeline readiness.

**[ADOPTED]** — Mechanical extraction avoids authoring; linter enforced by Video-Scripts framework (CAP-3).

---

### AD-8: Video Pipeline Boundary — Herald Orchestrates, Manticore Renders

**Binds**: Herald orchestrates narration extraction and real screen-recording sourcing. BMad-Manticore is downstream, consuming narration + real footage to render video.

**Prevents**:
- Scope creep into video rendering (out of Herald's scope)
- Fabricated product demos (Herald enforces real footage only)
- Unclear handoff between Herald and Manticore

**Rule**:
- Herald responsibilities: Extract narration, source real screen recordings, validate blacklist.
- Manticore responsibilities: Voice synthesis (Kokoro-82M), graphics (HyperFrames), SFX (AudioLDM2), final video render.
- Handoff: narration.md + real screen recordings → Manticore → `.mp4` output (gitignored, regenerable).
- No fabricated demos: All b-roll is real; Herald enforces this boundary at extraction time.

**[ADOPTED]** — Video-Scripts framework (CAP-3) defines four hard gates: Outline → Cut Plan → Graphics Beats → Final Render. Herald operates gates 1–2; Manticore operates 3–4.

---

### AD-9: No Fabricated Demos — Real Footage Only

**Binds**: All screen recordings fed to video pipeline are real, recorded from actual product or system behavior. No AI-generated mockups, synthetic UI, or fabricated product demos.

**Prevents**:
- False claims about product capabilities
- Liability from misrepresentation
- Loss of trust if synthetic footage is later discovered

**Rule**:
- Screen recording sourcing is explicit: Real product footage only, never synthetic.
- Herald enforces this at narration extraction and footage sourcing stages.
- Manticore enforces this at graphics beats; rejects any synthetic input.
- Video pipeline gate #2 (Graphics Beats) includes a fabrication check before gate #3 (Final Render).

**[ADOPTED]** — Constraint stated in spec CAP-3 and PRD; inherited from existing PyForge quality standards.

---

### AD-10: Narration Voice Identity — Consistency Enforced by Linter

**Binds**: Narration must match a published voice character (WPM, speech patterns, tone markers). Linter enforces consistency; blacklist blocks non-matching narration.

**Prevents**:
- Tonal inconsistency across videos
- Narration that contradicts established voice
- Unauthorized claims or misleading language

**Rule**:
- Voice bible: WPM range, speech patterns, tone markers, blacklisted claims (defined upstream, not in this effort).
- Linter: Validates narration against voice bible before video render.
- Blacklist: If linter flags, narration revision required; video render blocked.

**[ADOPTED]** — Video-Scripts framework (CAP-3) enforces via script linter; voice bible is upstream (external source).

---

## System Boundaries & Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Design Cloud (Claude Design)                                 │
│ - 9 interactive prototypes (.dc.html)                       │
│ - Speaker notes (narration source)                          │
│ - Visual iteration (Modernist tokens applied)               │
└────────────────┬────────────────────────────────────────────┘
                 │ Pull (etagged)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Herald Orchestration Layer (Python/Node)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Design-Code-Bridge                                   │   │
│  │ - Pull .dc.html (etagged)                           │   │
│  │ - Extract Markdown (marp)                           │   │
│  │ - Validate etags (conflict detection)               │   │
│  └──────────────────────────────────────────────────────┘   │
│                     │                                        │
│      ┌──────────────┴──────────────┬──────────────────┐     │
│      ▼                             ▼                  ▼     │
│  ┌────────────────┐          ┌──────────────┐  ┌──────────┐ │
│  │ Deckcraft      │          │Narration     │  │ SVG/     │ │
│  │ (Markdown→    │          │Extraction    │  │Infographic│ │
│  │  PPTX + tokens)│         │(Speaker notes│  │Extraction │ │
│  └────────────────┘          │ → .md)      │  └──────────┘ │
│                              └──────────────┘               │
│  (All tracked: .dc.html, .md, .pptx, narration.md, .svg)   │
└────────────────┬─────────────────────────────────────────────┘
                 │ narration.md + real footage
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ BMad-Manticore (Downstream)                                  │
│ - Voice synthesis (Kokoro-82M)                              │
│ - Graphics (HyperFrames)                                    │
│ - SFX (AudioLDM2)                                           │
│ - Final render (.mp4 gitignored, regenerable)              │
└─────────────────────────────────────────────────────────────┘

Build Layer (Vite):
  Markdown → HTML deck engine (dist/, gitignored, regenerable <5s)
  All 6 formats ready for shipping; dashboard-check validates.
```

---

## Invariants by Slice

### Design Authoring
- **Single source**: One `.dc.html` per station is immutable at Code side.
- **Etagged pulls**: Every pull validates etag; conflicts fail loudly.
- **Token consistency**: Figma tokens applied uniformly via Modernist system.

### Markdown Export
- **Mechanical extraction**: No hand-authoring; derived from Design protos.
- **Six-act structure**: All markdown follows canonical structure (CAP-5 spec).
- **Regenerable**: Markdown re-extracted deterministically from Design on demand.

### PPTX Generation
- **Token-driven**: All fonts, colors, spacing from design-tokens.json, never hardcoded.
- **Editable**: Output opens in PowerPoint; structure + formatting preserved.
- **Tracked**: PPTX files committed to git for deliverable readiness proof.

### Narration Extraction
- **Mechanical**: Speaker notes → narration.md, deterministic, no hand-authoring.
- **Linter-enforced**: Voice identity + blacklist validated before video render.
- **Real footage only**: Screen recordings sourced from actual product, never synthetic.

### HTML Deck Engine
- **Regenerable**: Built from Markdown + tokens in <5s; not committed to git.
- **Validation**: `pixi run dashboard-check` proves all 9 decks render without error.
- **Asset management**: Inline SVGs (no raster images); assets/ gitignored.

### Video Scripts
- **Downstream boundary**: Manticore consumes narration.md + real footage; Herald stops at extraction.
- **No fabrication**: Herald enforces real footage sourcing; Manticore validates at graphics beats.
- **Gitignored output**: .mp4 regenerable on demand; not committed to git.

---

## Deferred Decisions

1. **Station-by-station review cadence**: Should each station's deck be reviewed in isolation or as a family batch? (Deferred to story/sprint planning; spec suggests family batch to catch inconsistencies.)

2. **Narration extraction automation**: Should extraction be pixi-automated or manual per-station via Design UI? (Deferred to story planning; spec suggests automated pixi task with manual review.)

3. **Video render scheduling**: Should all 9 station videos render at completion or prioritize a pilot subset? (Deferred to operations; spec suggests pilot subset for proof-of-concept, then full batch.)

---

## Success Signals

- ✅ 9 Design projects seeded with Modernist tokens applied uniformly.
- ✅ 9 prototypes authored per six-act framework, etagged, tracked.
- ✅ 54 artifacts exported (9 stations × 6 formats) and tracked.
- ✅ All 9 PPTX files open in PowerPoint; fonts, colors, layouts preserved.
- ✅ All 9 HTML decks render; `dashboard-check` passes.
- ✅ All 9 narration scripts extracted and available for video pipeline.
- ✅ Zero manual file transfers; design-code-bridge automation end-to-end.
- ✅ Tracked footprint: ~144 files (62% reduction vs. unoptimized).

---

## Scope Note: Related Efforts

- **Herald Moment 2 (Progress)**: Not in scope; future orchestration of build metrics.
- **Herald Moment 3 (Success)**: Not in scope; future orchestration of ship announcements.
- **Herald Moment 4 (Operations)**: Not in scope; future orchestration of maintenance communications.
- **BMad-Manticore video rendering**: Downstream; Herald feeds it, does not implement.
- **Figma variable management**: Upstream; Herald consumes, does not author tokens.

---

## Architecture Status

**Finalized**: 2026-08-01  
**Altitude**: Feature-level  
**Next Steps**: `bmad-create-epics-and-stories` for implementation breakdown.

---

*Spine distilled from spec-herald-pitch/SPEC.md + prd-pyforge-herald-2026-08-01/prd.md; decisions logged in .memlog.md.*
