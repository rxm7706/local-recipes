# Artifact Tracking Matrix

Comprehensive tracking decisions for all artifact types produced by Herald Pitch Expansion.

---

## Design Prototypes (.dc.html)

| Item | Count | Tracked? | Regenerable? | Why |
|------|-------|----------|-------------|-----|
| Design proto per station | 3-4 per station | ✓ YES | ✗ NO | Source of truth, immutable, etagged authority. Capture all authoring decisions and edits made in Design cloud. |
| Total per 9 stations | 27-36 | ✓ YES | ✗ NO | Essential to recover state if Design cloud account lost. |

---

## Markdown Sources (Marp)

| Item | Count | Tracked? | Regenerable? | Why |
|------|-------|----------|-------------|-----|
| Main deck per station (`{station}.md`) | 1 per station | ✓ YES | Partially | Extracted from `.dc.html` by `npm run extract`. Regenerable but version control needed for narrative history. |
| Cover variant (`{station}-cover.md`) | 1 per station | ✓ YES | Partially | Variant for standalone cover deck. Regenerable from design but worth tracking for editing audits. |
| Extended variant (`{station}-extended.md`) | 1 per station | ✓ YES | Partially | Long-form variant for detailed talks. Regenerable from design but editing history valuable. |
| Narration script (`{station}-narration-*.md`) | 1-2 per station | ✓ YES | Partially | Extracted from Design speaker notes. Regenerable but critical input to video pipeline; track for auditability. |
| Narration cover (`{station}-narration-cover-*.md`) | 0-1 per station | ✓ YES | Partially | Short-form narration for cover deck. Track if produced. |
| Total per 9 stations | 45-63 | ✓ YES | Partially | All markdown tracked for version control + narrative history. |

---

## PowerPoint Exports (Deckcraft)

| Item | Count | Tracked? | Regenerable? | Why |
|------|-------|----------|-------------|-----|
| Main PPTX per station (`{station}.pptx`) | 1 per station | ✓ YES | Yes (5-10s) | Final deliverable. Regenerable from markdown + deckcraft engine. Track because: (1) formatting/layout choices made by deckcraft may evolve, (2) enables users to open without rebuild. |
| Cover PPTX variant (`{station}-cover.pptx`) | 1 per station | ✓ YES | Yes (5s) | Standalone cover deck export. Same reasoning as main. |
| Extended PPTX variant (`{station}-extended.pptx`) | 1 per station | ✓ YES | Yes (5s) | Long-form PPTX for detailed talks. Same reasoning as main. |
| Appendix PPTX (`{station}-appendix.pptx`) | 0-1 per station | ✓ YES | Yes (5s) | Personas appendix as standalone deck. Same reasoning. |
| Total per 9 stations | 27-36 | ✓ YES | Yes | All PPTX tracked for deliverable readiness. Zero downstream rebuild needed; just `git clone && open .pptx`. |

---

## Infographics (SVG)

| Item | Count | Tracked? | Regenerable? | Why |
|------|-------|----------|-------------|-----|
| Infographic per station (`{station}-infographic.svg`) | 1 per station | ✓ YES | Partially | Static inline SVG extracted from markdown. Regenerable from `.md` + rendering engine, but visual refinement history valuable; track it. |
| Total per 9 stations | 9 | ✓ YES | Partially | All SVG tracked. No raster images (zero `.png`/`.jpg`). |

---

## Build Artifacts (Marp → HTML/JSON)

| Item | Count | Tracked? | Regenerable? | Why |
|------|-------|----------|-------------|-----|
| Slide fragments (`src/slides/fragments/{station}-*.json`) | 1 per station | ✗ GITIGNORE | Yes (<1s) | Intermediate Marp parse tree. Regenerates in <1s via `npm run extract`. No value in git. |
| Total per 9 stations | 9 | ✗ GITIGNORE | Yes | Gitignore to reduce noise. |

---

## Vite Bundle Output (HTML/JS/CSS)

| Item | Count | Tracked? | Regenerable? | Why |
|------|-------|----------|-------------|-----|
| Interactive HTML deck (`dist/index.html`) | 1 per station | ✗ GITIGNORE | Yes (<5s) | Bundled, minified Vite output. Deterministic from `.md` sources. Regenerate on `npm run build`. |
| JS bundles (`dist/assets/*.js`) | 3-6 per station | ✗ GITIGNORE | Yes (<5s) | Asset chunks. Gitignore. |
| CSS bundles (`dist/assets/*.css`) | 1-3 per station | ✗ GITIGNORE | Yes (<5s) | Style sheets. Gitignore. |
| Total per 9 stations | ~36-72 | ✗ GITIGNORE | Yes | Entire `dist/` gitignored. Users build locally: `npm install && npm run build`. |

---

## Video Output (Manticore)

| Item | Count | Tracked? | Regenerable? | Why |
|------|-------|----------|-------------|-----|
| Station video (`{station}.mp4`) | 1 per station | ✗ GITIGNORE | Yes (expensive) | Manticore render output. Regenerable but expensive (~30-60s per video). Gitignore, regenerate on demand. |
| Optional exports (`.edl`, `.fcpxml`) | 0-1 per station | ✗ GITIGNORE | Yes (expensive) | Edit decision lists for final-cut integration. Same reasoning as video. |
| Total per 9 stations | 9-18 | ✗ GITIGNORE | Yes (expensive) | Gitignore. Ship video via CDN/release artifacts, not git. |

---

## Summary: Tracked vs. Gitignored

### Tracked (~144 files for 9 stations)

**Source of truth:**
- Design prototypes (27-36 files): `.dc.html` variants
- Total: ~27-36 files

**Version-controlled content:**
- Markdown sources (45-63 files): `.md` marp variants + narration + narration-cover
- Total: ~45-63 files

**Final deliverables:**
- PPTX exports (27-36 files): `.pptx` variants (main, cover, extended, appendix)
- SVG infographics (9 files): inline static images
- Total: ~36-45 files

**Grand Total Tracked**: ~108-144 files

### Gitignored (~180+ files for 9 stations, regenerable)

**Build intermediates:**
- Fragments (9 files): `.json` parse trees
- Total: ~9 files

**Build output:**
- dist/ (36-72 files): `index.html`, `assets/*.js`, `assets/*.css`
- Total: ~36-72 files

**Expensive renders:**
- Videos (9-18 files): `.mp4` + `.edl`/`.fcpxml`
- Total: ~9-18 files

**Grand Total Gitignored**: ~54-99 files (regenerable, reduces footprint by 62%)

---

## Regeneration Workflow

```bash
# Fast regeneration (source tracked in git)
git clone <repo>
npm install
npm run extract     # Fragments from markdown (~2s)
npm run build       # Vite bundle (~10-15s)
pixi run deck-export # PPTX + SVG (~5-10s per station)
# Result: All 6 formats ready in ~30s total

# Expensive regeneration (on-demand)
pixi run narration-extract <station>  # Extract narration from Design speaker notes (~1s)
pixi run deck-video <station>         # Manticore video render (~30-60s per video)
# Result: Video-ready narration + `.mp4` available for CDN/release
```

---

## Footprint Impact

| Strategy | Tracked | Gitignored | Total | Why? |
|----------|---------|------------|-------|------|
| **Conservative** | ~90 files (markdown + design only) | ~180 files | ~270 files | Minimal git; everything regenerates. Slower workflow (must build on pull). |
| **Balanced** | ~120 files (+ PPTX) | ~120 files | ~240 files | Medium git; PPTX regenerates (~5-10s). Good balance. |
| **Aggressive** ← **CHOSEN** | ~144 files (+ narration + SVG) | ~90 files | ~234 files | Fast workflow; narration ready for video pipeline; SVG infographics included. 62% reduction vs. naive ~370 files. |

**Decision**: Aggressive strategy. Tracks all source-of-truth and final deliverables. Gitignores only true intermediates and expensive renders (video). Enables zero-rebuild workflow for desktop users; video regenerates on demand via CDN/releases.
