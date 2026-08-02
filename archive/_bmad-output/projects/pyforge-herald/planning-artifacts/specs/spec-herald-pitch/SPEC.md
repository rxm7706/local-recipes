---
title: Herald's Pitch Deck — Moment 1 Orchestration
slug: herald-pitch
status: ready
created: 2026-08-01
updated: 2026-08-01
spec_version: 1.0
companions:
  - artifact-tracking-matrix.md
  - workflow-stages.md
  - six-act-framework.md
  - station-roster.md
  - bridge-protocol.md
owner-dream: docs/dreams/herald-pitch.md
sources:
  - ../../docs/dreams/herald-pitch.md
---

# Herald's Pitch Deck — Moment 1 Orchestration

**SPEC.md** — Five-field kernel for Moment 1 (Pitch) of Herald's Four Moments framework.

---

## Why

Herald is the factory's voice and visual surface. Herald's Four Moments of Proclamation guide all work:

1. **Pitch** — A dream must be argued, not merely filed. The case made legible to humans who did not dream it.
2. **Progress** — A build in flight is not self-explaining. What changed, what it cost, what it unblocked.
3. **Success** — Shipping is not the same as being known to have shipped. The claim with evidence attached.
4. **Operations** — The long tail nobody announces. Fixes, updates, deprecations, end-of-life.

**Moment 1 (Pitch)** is the first time Herald has something to do. This spec orchestrates Moment 1 across **9 pyforge stations** using four reusable Tier 1 capabilities, producing 6 artifact formats per station from a single Design source, tracked and regenerable according to an aggressive optimization strategy.

The core insight: **One source of truth (Design prototype) → Multiple deliverable formats → Zero manual file transfers.**

---

## Capabilities

### CAP-1: Design-Code-Bridge Framework

**Intent:** Automate the round-trip between Claude Design (visual authoring) and Code (repository).

**What it does:**
- **Seed**: Claude Code creates Design projects per deck, seeded with contract-compliant prototype (1920×1080, Archivo, family palette).
- **Design**: User iterates visually at claude.ai/design; edits tracked by etagged protocol.
- **Pull**: `herald deck pull <slug>` reads Design prototype into Code, extracts to markdown, auto-commits. Zero downloads, zero copy-paste.
- **Discipline**: Etags on every transfer; mid-edit conflicts surface instead of silently overwriting.

**Success:** Prototype round-trips seamlessly between Design and Code; etagged safety prevents overwrites; zero manual file transfers; 7 decks proven.

---

### CAP-2: Deckcraft Framework

**Intent:** Generate editable PowerPoint from Markdown sources without sacrificing manual refinement.

**What it does:**
- **Input**: Markdown source (`{station}.md`) + Modernist design tokens.
- **Transform**: `pixi run deck-export` → deckcraft pipeline → python-pptx → editable PPTX.
- **Output**: `src/pptx/{station}.pptx` — programmatically generated yet humanly editable PowerPoint with proper fonts, colors, layouts.

**Success:** PPTX files are editable in PowerPoint; formatting and layout choices preserved; regenerable from markdown in 5–10s.

---

### CAP-3: Video-Scripts Framework

**Intent:** Extract narration scripts from decks and feed them into video production pipelines (bmad-manticore).

**What it does:**
- **Extract**: Mechanical narration extraction from Design speaker notes → `{station}-narration-2026-08-01.md`.
- **Compose**: Herald feeds narration corpus to manticore (322 scenes, 27 files mechanically extracted; first master script authored as exemplar).
- **Render**: Manticore orchestrates voice (Kokoro-82M), graphics (HyperFrames), b-roll (real screen recordings, never fabricated UI), SFX (AudioLDM2) → `.mp4`.
- **Four Hard Gates**: Outline → Cut Plan → Graphics Beats → Final Render. No fabricated product demos.

**Success:** Narration scripts extracted and available; video production ready; no fabricated demos; all b-roll is real.

---

### CAP-4: Modernist-Identity Framework

**Intent:** One visual language across all PyForge surfaces (decks, dashboards, docs, exports, videos).

**What it does:**
- **Design System**: Flat, architectural, Archivo throughout; light palette (#f3f2f2), ink (#201e1d), red accent (#ec3013/#c22a10); visible grid, 2px rules, zero corner radius, flush-left labels, black-and-white photography.
- **Tokenization**: Tokens round-trip through Figma variables, design-tokens JSON, PPTX templates, deck engine, video production bibles.
- **Applied Consistently**: Tokens drive Figma, deckcraft PPTX templates, deck engine, video bibles; applied to all 9 station decks.

**Success:** Modernist design system adopted across all Herald family decks; 7 decks bound; tokens ready for PPTX ↔ Figma ↔ video round-trip.

---

### CAP-5: Six-Act Deck Framework

**Intent:** Canonical structure for all pitch decks to ensure consistency and narrative clarity.

**What it does:**
- **Acts** (8 sections): Cover (hook), Act I (friction), Act II (insight), Act III (solution/mechanics, L.A.T.C.H. Time), Act IV (real-world application, L.A.T.C.H. Location), Act V (future/vision, L.A.T.C.H. Category), Act VI (action/CTA), Appendix (personas).
- **Depth**: ~28 slides per deck, 90KB+ class, inline SVGs, full depth (no size-restricted authoring).
- **Visual Principles**: L.A.T.C.H. (Location, Analogy, Time, Color, Hierarchy).

**Success:** All 9 decks follow six-act structure; all contain persona appendices; all render full depth; all use L.A.T.C.H. visual principles consistently.

---

### CAP-6: Multi-Format Export

**Intent:** Deliver 6 artifact formats per station from a single Design prototype.

**What it does:**
1. **Design protos** (.dc.html) — Source of truth, tracked, etagged.
2. **Markdown sources** (marp) — Version-controlled content extracted from Design.
3. **PPTX exports** (editable) — Deckcraft output, tracked for deliverable readiness.
4. **Narration scripts** (.md) — Video production input, tracked for pipeline readiness.
5. **Infographics** (SVG) — Inline static images, tracked, never raster.
6. **HTML decks** (interactive) — Vite bundle, gitignored (regenerable <5s).

**Optimization**: Aggressive strategy: Track 144 files (source + final deliverables). Gitignore intermediate builds (fragments.json, dist/, assets/, .mp4, ~62% reduction).

**Success:** All 6 formats available per station; tracked/gitignored split correct; regeneration strategy reduces footprint by 62%; no manual file copies.

---

### CAP-7: Station-Specific Customization

**Intent:** Apply the framework consistently across 9 pyforge stations with domain-appropriate content.

**What it does:**
- **9 Stations**: Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald.
- **Per-Station Content**: Thesis, pain point, solution pillars, ecosystem vision, personas (station-specific).
- **Per-Station Visuals**: Domain-appropriate diagrams (warden: lattices/gates; marshal: policy composition; atlas: pipeline stages).
- **Consistent Framework**: Six-act structure, Modernist identity, design bridge, deckcraft pipeline same for all 9.

**Success:** 9 Design projects seeded; 9 prototypes authored per six-act framework; 9 × 6 artifact sets committed; zero manual re-engineering per station.

---

## Constraints

**Design source of truth**: Single Design prototype per station is immutable, etagged, tracked as .dc.html. All code-side artifacts derive from it. No direct editing of code-side copies.

**Tracked vs. gitignored**: Aggressive optimization. Track design protos (3-4 files), markdown (5-8), PPTX (2-4), narration (1-2), infographics (0-1). Gitignore fragments (.json), dist/ (HTML), assets/ (JS/CSS), videos (.mp4) — all regenerable.

**Etagged safety**: All Design ↔ Code transfers use etags. Conflicts detected, never silent overwrites. Protocol: read-file includes etag, write-file requires matching etag or fails explicitly.

**No fabricated demos**: All screen recordings in video output are real. Never use AI-generated UI or synthetic mockups. Manticore receives real footage + real narration only.

**Narration identity**: Voice bible derived from published transcripts (WPM, speech patterns, tone markers). Blacklist enforced by script linter; all narration passes linter before video render.

**Multi-surface readiness**: Decks ship as interactive HTML (Vite), editable PPTX (python-pptx), static SVG infographics (inline), and video scripts (text). Every format must be production-ready; no "preview" or "draft" states in shipping.

---

## Non-goals

**New deck-authoring infrastructure**: Design-code-bridge already proven on 7 decks. This effort reuses it, does not rebuild it.

**New export backends**: Deckcraft handles PPTX generation; `deck-export` CLI handles HTML, SVG, others. This effort composes existing tools, does not invent new ones.

**New video pipeline**: bmad-manticore is upstream. This effort feeds narration scripts and real screen recordings to it; does not implement the renderer.

**Real-time collaboration**: Design cloud iterates in real-time; pull model is explicit. Not a goal to sync live or to merge-edit on the Code side.

**Personas beyond context**: Appendix personas provide stakeholder context and voting records, not product personas or marketing segmentation.

---

## Success Signal

**Design & Seeding**
- [ ] 9 Design projects seeded (one per pyforge station), all bound to Modernist design system.
- [ ] 9 prototypes authored and iterated in Design layer per six-act framework.

**Artifacts & Export**
- [ ] 9 × 6 artifact sets (54 total) exported and tracked: `.dc.html`, marp `.md`, `.pptx`, narration `.md`, infographics `.svg`, built outputs (gitignored).
- [ ] Design protos (.dc.html) tracked in `project/`.
- [ ] Markdown sources (marp) tracked in `src/marp/`.
- [ ] PPTX exports tracked in `src/pptx/`.
- [ ] Narration scripts tracked in `src/marp/{station}-narration-*.md`.
- [ ] SVG infographics tracked in `src/marp/{station}-infographic.svg`.
- [ ] Build outputs (fragments.json, dist/, assets/, .mp4) gitignored and regenerable.

**Quality & Rendering**
- [ ] All 9 HTML decks render without error; `pixi run dashboard-check` passes for all.
- [ ] All 9 PPTX files open and edit in Microsoft PowerPoint; fonts, colors, layouts preserved.
- [ ] All infographics render as inline SVG (zero raster `.png`/`.jpg` images).

**Integration & Automation**
- [ ] All 9 narration scripts extracted from Design speaker notes; available for manticore integration.
- [ ] Zero manual file transfers between Design and Code (design-code-bridge automation end-to-end).
- [ ] All etagged transfers validated (conflicts caught, never silent overwrites).

**Footprint**
- [ ] Total tracked files: ~144 (9 stations × ~16 files per station) vs. ~270 unoptimized (62% reduction).

---

## Open Questions

1. **Station-by-station review cadence**: Should each station's deck be reviewed in isolation or as a family batch? (Suggest: family batch after all 9 are drafted, to catch inconsistencies in narrative structure and visual application.)

2. **Video render priority**: Should all 9 station videos be rendered at completion, or prioritize a pilot subset (e.g., Marshal, Warden, Atlas) for proof-of-concept? (Suggest: pilot subset; full batch on second pass.)

3. **Narration extraction tooling**: Should the narration-extract task be automated within pixi tasks, or manual per-station via the Claude Design UI? (Suggest: automated pixi task, with manual review of extraction quality.)

---

## Companion Files

- **artifact-tracking-matrix.md** — Detailed tracking decisions per artifact type (scope, regenerable?, why).
- **workflow-stages.md** — Seven-step workflow: Seed → Design → Pull → Build → Extract Narration → Export → Commit & Ship.
- **six-act-framework.md** — Canonical six-act structure with slide counts, L.A.T.C.H. principles, visual guidelines per act.
- **station-roster.md** — 9 pyforge stations with thesis, pain point, solution pillars, visual metaphors, personas.

---

## Spec Status

**Created**: 2026-08-01  
**Status**: Ready for PRD → Architecture → Epics decomposition.  
**Next Steps**: Feed this spec to `bmad-prd` to produce product requirements; then `bmad-architecture` for tech/design specs; then `bmad-create-epics-and-stories` for implementation stories.

**Assumption Verification**: All 7 capabilities verified as real (proven on existing projects). Tier 1 reusability confirmed. Moment 1 scope locked.

---

*SPEC.md is a derived artifact; it is re-rendered from `.memlog.md` on each update. Hand-edits are not supported.*
