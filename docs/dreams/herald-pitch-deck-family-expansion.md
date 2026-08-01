---
title: Herald's Pitch Deck Family Expansion — 21 Stations, Multiple Formats
type: dream
owner: herald
status: dreamt
---

# Herald's Pitch Deck Family Expansion

## The Dream

Herald's **Four Moments of Proclamation** begins with **Moment 1: Pitch** — the case made legible to those who did not dream it. Today Herald has proven the deck bridge on 7 stations. This Dream expands the family to **21 pyforge + ecosystem stations**, authored once and shipped in **multiple formats**: PPTX (editable), HTML (interactive), Markdown (version-controlled), Infographics (static), and video (companion narration).

One source of truth (Design prototype). One delivery chain (Design → Code → Export). Multiple surfaces.

## The Supporting Capabilities (Already Real)

Herald's Pitch Package rests on five foundational capabilities, all realized or specified:

| Capability | Purpose | Status |
|------------|---------|--------|
| **pyforge-herald** | Four Moments framework; Moment 1 is Pitch | `specified` ✅ |
| **design-code-bridge** | Design ↔ Code round-trip (seed → edit → pull) | `realized` ✅ |
| **modernist-identity** | Brand tokens, Archivo typography, color palette | `realized` ✅ |
| **deckcraft** | Editable PPTX generation from primitives | `specified` ✅ |
| **video-scripts** | Narration extraction, companion video production | `dreamt` ⏳ |

This Dream orchestrates all five to author and export 21 pitch decks in all formats simultaneously.

## The Artifact Collection

Each of the 21 stations produces a **six-artifact export set** from one design source:

```
presentations/pyforge-{station}/project/
├── {Station}.dc.html          ← Design prototype (source of truth)
└── dist/
    ├── {station}.html         ← Interactive deck (HTML5 + Recharts)
    ├── {station}.md           ← Markdown source (version-controlled)
    ├── {station}.pptx         ← Editable PowerPoint (deckcraft)
    ├── {station}-infographic.svg  ← Static infographic
    ├── {station}-narration-2026-08-01.md  ← Narration script (video-scripts)
    └── {station}.mp4          ← Companion video (manticore-rendered)
```

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
2. **Extract** via `npm run extract` (markdown source from `.dc.html`)
3. **Build** via `npm run build` (HTML5 deck)
4. **Export** via `pixi run deck-export` + deckcraft:
   - `.pptx` (editable, python-pptx + deckcraft)
   - `.svg` infographic (inline, no raster)
   - `.html` (interactive, self-contained)
5. **Narration** via `narration-extract` task:
   - Pull speaker notes from Design
   - Generate `*-narration-2026-08-01.md`
6. **Video** via `bmad-manticore`:
   - Take narration + screen recordings + bibles
   - Render `.mp4` (Kokoro voice, HyperFrames graphics, real UI)

Output: Six artifacts per station × 21 stations = **126 artifacts**, all from one Design source.

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

- [ ] 21 Design projects seeded, one per station
- [ ] 21 prototypes authored and refined (Design layer)
- [ ] 21 × 6 artifacts exported and committed (code layer)
- [ ] All HTML decks render and pass `dashboard-check`
- [ ] All PPTX files editable in PowerPoint
- [ ] All infographics render as inline SVG
- [ ] All narration scripts extracted and staged for video
- [ ] First 3 companion videos rendered (exemplars per act)
- [ ] Artifacts published to github.io and available in Release
- [ ] Zero manual file transfers between Design and Code

## Realization Log

- **2026-08-01 (this session)** — Dream seeded from user's vision of "Herald has moments, supporting capabilities, and a master dream that can create a collection of artifacts." Six-act framework (canonical reference) authored as the structural backbone. Architecture: one source (Design) → multiple outputs (PPTX, HTML, MD, SVG, MP4).
