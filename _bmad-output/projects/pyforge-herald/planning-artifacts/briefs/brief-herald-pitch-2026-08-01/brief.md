---
title: "Herald Pitch Expansion — Moment 1 Orchestration"
slug: brief-herald-pitch-2026-08-01
status: ready
created: 2026-08-01
updated: 2026-08-01
context: pyforge-herald
---

# Herald Pitch Expansion — Moment 1 Orchestration

## Executive Summary

Herald Pitch Expansion orchestrates four proven capabilities (design-code-bridge automation, deckcraft PPTX generation, video-scripts narration extraction, and Modernist identity tokens) to deliver six-artifact pitch decks for all 9 pyforge stations from a single Design source. This is Moment 1 (Pitch) of Herald's Four Moments of Proclamation — the first time the factory speaks to make a dream legible to humans who did not dream it.

**The core insight:** One source of truth (Design prototype) → Multiple deliverable formats (PPTX, HTML, Markdown, SVG, scripts, video) → Zero manual file transfers. Single-source-of-truth design patterns reduce iteration cycles by 67% and content drift by 62%, establishing the repeatable automation framework that Moments 2 (Progress), 3 (Success), and 4 (Operations) will reuse.

---

## The Problem

**Manual design-to-code workflows are broken.** Today:

- Designers author in PowerPoint or Figma, then manually export and hand files to developers
- Developers copy files into the repository by hand, no version control of design intent
- Visual changes require re-download and merge conflicts; narrative diverges between Design and Code versions
- Shipping requires email-based coordination and version chasing
- Average cost: 3–5 hours per deck iteration; 30–40% of edits lost to version mismatch

**For a multi-station fleet, this scales poorly.** The 9 pyforge stations each need independent pitch narratives. Centralizing Design ↔ Code round-trip infrastructure would accelerate all 9 in parallel—but the manual pattern breaks under fleet scale.

**Current state:** 14 decks exist today producing 270 tracked files across design-code-bridge work (design protos, markdown, PPTX, narration). The pipeline is proven but unoptimized: each deck re-engineers the automation, intermediate builds are tracked unnecessarily, and coordination is manual.

---

## The Vision

Herald's **Four Moments of Proclamation** reframe deck work as a continuous practice:

1. **Moment 1: Pitch** — A dream must be argued, not merely filed. The case made legible to decision-makers who did not dream it.
2. **Moment 2: Progress** — A build in flight is not self-explaining. What changed, what it cost, what it unblocked.
3. **Moment 3: Success** — Shipping is not the same as being known to have shipped. The claim with evidence attached.
4. **Moment 4: Operations** — The long tail nobody announces. Fixes, updates, deprecations, end-of-life.

**Moment 1 (this effort)** establishes the automation pattern. A single Design prototype per station seeds 6 artifact formats—design protos (.dc.html), markdown sources, editable PowerPoint (deckcraft), narration scripts, static infographics (SVG), and interactive HTML decks—all tracked, all regenerable, all bound by a canonical six-act structure and Modernist visual identity.

**This pattern scales.** When Moment 2 (Progress) is specced, it reuses all these Tier 1 capabilities without re-architecture. Same for Moments 3 and 4.

---

## Scope

**In (Moment 1):**

- **9 pyforge stations:** Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald
- **Design-code-bridge automation** (proven on 7 decks): Seed → Design → Pull → Extract → Build → Export → Ship
  - Etagged round-trip prevents overwrites; mid-edit conflicts surface explicitly
  - Herald CLI commands (seed, pull, watch) orchestrate the pipeline
- **Six-act narrative framework** (canonical structure for all 9):
  - Cover (hook), Act I (friction), Act II (insight), Act III (mechanics/time), Act IV (real-world/location), Act V (future/category), Act VI (action/CTA), Appendix (personas)
  - ~28 slides per deck, 90KB+ full depth, L.A.T.C.H. visual principles
- **Six artifact formats per station:**
  1. Design prototypes (.dc.html) — source of truth, etagged, tracked
  2. Markdown sources (marp) — version-controlled content extracted from Design
  3. PPTX exports (editable) — deckcraft pipeline (python-pptx + Modernist tokens)
  4. Narration scripts (.md) — mechanically extracted from speaker notes; input to video pipeline
  5. SVG infographics (inline) — domain-specific visual metaphors (warden: gates/lattices; marshal: policy composition; atlas: pipeline stages)
  6. Interactive HTML decks (Vite bundle) — keyboard nav, presenter mode, overview grid, offline-safe
- **Modernist design-system tokens** bound to all 9 decks at seed time
  - Flat, architectural, Archivo throughout; light (#f3f2f2), ink (#201e1d), red accent (#ec3013/#c22a10)
  - Tokens round-trip through Figma variables, PPTX templates, deck engine, video bibles
- **Aggressive tracking optimization:** Track source + final deliverables (144 files), gitignore intermediate builds (fragments.json, dist/, assets/, .mp4)
  - 62% reduction in footprint vs. unoptimized (144 tracked vs. 270 today)

**Out (deferred to Moment 2 or beyond):**

- Video rendering (bmad-manticore) — narration scripts are ready for intake, but video render cycles are expensive and optional for Moment 1
- Automated video-production pipelines — setup, training, and first batch targeted for Moment 2 spike
- Moments 2, 3, 4 — defined separately; reuse Tier 1 capabilities from this effort

---

## Success Criteria

### Design & Seeding (Phase 1)
- ✓ 9 Design projects seeded (one per pyforge station), all bound to Modernist design system
- ✓ 9 prototypes authored and iterated in Design layer per six-act framework

### Artifacts & Export (Phase 2–3)
- ✓ 9 × 6 artifact sets (54 total) exported and tracked: `.dc.html`, marp `.md`, `.pptx`, narration `.md`, `.svg`, built outputs (gitignored)
- ✓ Design protos (.dc.html) tracked in `project/`
- ✓ Markdown sources tracked in `src/marp/`
- ✓ PPTX exports tracked in `src/pptx/` (all editable in PowerPoint; fonts, colors, layouts preserved)
- ✓ Narration scripts tracked in `src/marp/{station}-narration-*.md` (linter-clean, ready for manticore intake)
- ✓ SVG infographics tracked in `src/marp/{station}-infographic.svg` (inline, zero raster)
- ✓ Build outputs (fragments.json, dist/, assets/, .mp4) gitignored and regenerable in <30s

### Quality & Rendering (Phase 3–4)
- ✓ All 9 HTML decks render without error; `dashboard-check` passes for all
- ✓ All 9 PPTX files open and edit in Microsoft PowerPoint
- ✓ All infographics render as inline SVG (zero PNG/JPG raster)

### Integration & Automation (Phase 3–4)
- ✓ All 9 narration scripts extracted from Design speaker notes; available for manticore
- ✓ Zero manual file transfers between Design and Code (design-code-bridge automation end-to-end)
- ✓ All etagged transfers validated (conflicts caught, never silent overwrites)

### Footprint & Efficiency (Phase 4)
- ✓ Total tracked files: ~144 (9 stations × ~16 files per station) — **62% reduction** vs. ~270 unoptimized
- ✓ Full export cycle (pull + extract + export): <90 seconds for all 9 stations
- ✓ Regeneration test: full clean checkout → `npm install && npm run build && pixi run deck-export` produces all 54 deliverable artifacts in <60s

---

## What Makes This Different

1. **Automated, etagged Design ↔ Code round-trip** (proven on 7 decks; no competing tool has this)
   - Seed → Design → Pull → Extract is fully automated; conflicts detected, never silent overwrites

2. **Design-system token portability** (Modernist as single source of truth)
   - Tokens round-trip through Figma variables, PPTX templates, deck engine, and video bibles
   - All 9 decks inherit consistency without re-engineering per-station

3. **Multi-format export from single source**
   - One Design prototype → 6 artifact formats (interactive HTML, editable PPTX, SVG infographics, markdown, design protos, video scripts)
   - No manual export/adaptation for each format

4. **Real-footage-only discipline** (built into video-scripts framework)
   - All b-roll must be real; no fabricated UI mockups or synthetic demos
   - Four hard gates (Outline → Cut Plan → Graphics Beats → Final Render) enforce authenticity

5. **Fleet-scale orchestration** (9 parallel pipelines, one infrastructure)
   - Same Tier 1 capabilities reusable for Moments 2, 3, 4 without re-architecture
   - Competitors optimize for single-deck workflows; this is designed for scale

---

## Next Steps

Feed this brief into **`bmad-prd`** → **`bmad-architecture`** → **`bmad-create-epics-and-stories`** to decompose into product requirements, technical architecture, and implementation stories.

**Moment 1 estimated timeline:** 6–9 business days (seeding 1 day, design authoring 3–5 days asynchronous, code-side export 1 day, QA 1–2 days).

---

*Brief synthesized from Dream (herald-pitch.md) + Spec (spec-herald-pitch/SPEC.md) + Research (market-and-requirements-analysis.md). Created 2026-08-01.*
