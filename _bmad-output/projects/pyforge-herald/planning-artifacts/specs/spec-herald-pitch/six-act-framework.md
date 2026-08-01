# Six-Act Framework — Canonical Structure for Herald Pitch Decks

Authoritative guide for authoring all 21 pitch decks (9 pyforge stations + 12 legacy/extended) using a consistent narrative and visual structure.

---

## Overview

All Herald pitch decks follow a **six-act narrative arc** plus appendix. The framework separates concerns:
- **Narrative** (copy, argument, emotional arc) — unique per station
- **Structure** (slide order, section boundaries, pacing) — constant across all stations
- **Visual language** (L.A.T.C.H. principles, Modernist tokens, typography) — constant across all stations

**Result**: Audience expects a familiar structure; content surprise keeps them engaged.

---

## The Six Acts + Appendix

### Cover: The Hook
**Purpose**: Thesis statement. Hero graphic. Command attention.  
**Emotional Arc**: "What is this about? Why should I care?"

**Slide Structure** (1–2 slides):
1. **Cover Slide** — Wordmark + thesis (1–2 lines max; noun phrase or imperative)
2. **Hook / Context** — Hero graphic + tagline (optional; use if the idea benefits from instant visual framing)

**Modernist Application**:
- Archivo font, 56pt+ for thesis (bold or regular)
- Light background (#f3f2f2) or ink (#201e1d), no alternation mid-cover
- Hero graphic: black-and-white photography or architectural diagram (zero color gradients)
- Visible 2px grid; margin alignment 8px or 16px
- No shadows, no blur, no transparency gradations

**Example Thesis Statements**:
- Marshal: "Policy Composition at Scale"
- Warden: "Dependency Compliance as a Gate"
- Atlas: "The Catalog Beyond Python"

---

### Act I: The Friction
**Purpose**: Problem framing. Paint the pain point.  
**Emotional Arc**: "I recognize this problem. It's costing me."

**Slide Structure** (2–4 slides):
1. **Problem Statement** — Headline + 3–4 supporting bullets (pain point, scope, impact)
2. **Today's Workaround** — Diagram of the current mess (or photo of human friction)
3. **Why It Matters** — Data, testimony, or consequence (make the cost real)
4. *Optional*: **Who Suffers** — User archetype or persona brief

**Modernist Application**:
- Headlines: Archivo Bold, 32pt+
- Body: Archivo Regular, 16–18pt
- Color: Single spot color (red #ec3013 for emphasis; otherwise monochrome)
- Diagrams: 2px lines, visible grid, no fills (or solid black 100%)
- Photography: Black-and-white, high contrast, no filters

**Example Friction Frames**:
- **Marshal**: "Every policy change requires hand-editing 50+ YAML files. Inconsistencies hide. Reviews are manual. Rollback is error-prone."
- **Warden**: "Dependency risks are unknown until build time. No gate. No audit trail. Blocking takes weeks."
- **Atlas**: "PyPI universe is opaque beyond Python ecosystem. Cross-language dependencies are invisible."

---

### Act II: The Insight
**Purpose**: Solution introduction. The aha moment.  
**Emotional Arc**: "There's a better way. I haven't thought of it, but it makes sense now."

**Slide Structure** (1–3 slides):
1. **Insight Headline** — The core idea (short, powerful)
2. **Visual Metaphor** — Diagram showing the insight in action (the "before/after" moment)
3. *Optional*: **Why Now** — Why this solution is timely or possible

**Modernist Application**:
- Insight headline: Archivo Bold, 40pt+, single line (no wrapping)
- Visual metaphor: Architectural diagram, system diagram, or process flow (use L.A.T.C.H. Location principles)
- Spot color: Red #ec3013 for key nodes; rest monochrome
- No photography in Insight (reserved for Friction and Real-World); pure diagrams

**Example Insight Frames**:
- **Marshal**: "A single source of truth (YAML) + composition engine = policy scaling without duplication."
- **Warden**: "Scan source code for known risks + gate on policy = dependency safety by default."
- **Atlas**: "Cross-language dependency graph + unified metadata = PyPI + conda unified view."

---

### Act III: The Solution (Mechanics)
**Purpose**: 4-step delivery loop. How it works. Chronological journey.  
**Emotional Arc**: "I can picture this working. Here's how my team uses it."

**Slide Structure** (4–6 slides):
1. **Loop Overview** — 4-step cycle diagram (what are the steps?)
2. **Step 1** — Detailed walkthrough (who, what, when, where, how)
3. **Step 2** — Detailed walkthrough
4. **Step 3** — Detailed walkthrough
5. **Step 4** — Detailed walkthrough
6. *Optional*: **One Loop Complete** — Diagram showing loop closure

**L.A.T.C.H. Principle: TIME**
- Each step is a moment in time; present them chronologically
- Use arrows, numbering, or timeline layout to show sequence
- Avoid non-linear or branching logic in this section (save that for Act IV if needed)

**Modernist Application**:
- Step headers: Archivo Bold, 24pt+, centered or flush-left
- Body: Archivo Regular, 14–16pt (smaller than Friction; more detailed)
- Step diagram: 2px lines, numbered (1, 2, 3, 4), visible grid, spot red for key actions
- Per-step background: Solid light (#f3f2f2) or white, no gradient; step number in corner (8–16px from edge)

**Example Solution Frames** (Marshal case):
1. **Design**: Author single source of truth (YAML policy root)
2. **Compose**: Composition engine applies layers (repo defaults, team overrides, CLI flags)
3. **Validate**: Schema validation + policy linting (catch conflicts early)
4. **Deploy**: Rendered policy pushed to target (Kubernetes, Docker, systemd)

---

### Act IV: Real-World Application
**Purpose**: Prove it works outside the demo. Enterprise fit.  
**Emotional Arc**: "This scales to my real challenges. I can see my team using it."

**Slide Structure** (2–4 slides):
1. **Real-World Scenario** — A specific use case (customer story, internal example, or archetype scenario)
2. **Scenario Walkthrough** — Diagram or photo of the scenario in action
3. **Outcome** — What changed, what was saved (time, risk, cost)
4. *Optional*: **Scaling Note** — How this scales across multiple teams or orgs

**L.A.T.C.H. Principle: LOCATION**
- Ground the scenario in a real place, organization, or context
- Use photos of real people, real screens, real workflows (never fabricated UI)
- Establish trust by showing real evidence

**Modernist Application**:
- Scenario headline: Archivo Bold, 28pt+
- Body: Archivo Regular, 14–16pt
- Scenario photo: Black-and-white, high contrast, real human or real screen (never AI-generated)
- Outcome metrics: Arquivo Bold, 20pt+, large numbers (cost saved, time reduced, risks eliminated)
- No charts or graphs (too detailed for a pitch); simple numbers and short copy only

**Example Real-World Frames** (Warden case):
- **Scenario**: "Platform team tightens Python dependency policy across 40 repositories"
- **Walkthrough**: Photo of engineer running `warden scan` on CI; gate blocks unsafe deps; team re-reviews + accepts or fixes
- **Outcome**: "47 risky dependencies caught before merge; security risk reduced 62%; zero manual gate reviews needed"

---

### Act V: The Resolution (Future)
**Purpose**: Vision and scaling. Where does this go?  
**Emotional Arc**: "I can imagine a future where this is standard. We're building it together."

**Slide Structure** (1–3 slides):
1. **Vision Statement** — The north star (what does the world look like when this is standard?)
2. **Scaling Path** — Roadmap or expansion diagram (how do we get there?)
3. *Optional*: **Invitation** — Call to contribution, partnership, or adoption

**L.A.T.C.H. Principle: CATEGORY**
- Frame the vision at the category or ecosystem level (not just one use case)
- Align with broader trends (PyPI ecosystem growth, security shifts, open-source momentum)
- Position the station as a node in a larger network

**Modernist Application**:
- Vision headline: Archivo Bold, 40pt+, single line
- Scaling diagram: Architectural diagram showing expansion paths (e.g., Atlas Phase T → Phase U → adoption), 2px lines, visible grid
- Roadmap: Simple timeline or phase diagram (arrows left-to-right or top-to-bottom), no detail
- Invitation: Archivo Bold, 18pt+, centered, no jargon

**Example Vision Frames** (Atlas case):
- **Vision**: "A unified dependency intelligence platform spanning Python, npm, conda, Rust, and beyond"
- **Scaling Path**: "Phase B (PyPI universe complete) → Phase K (scheduler + telemetry) → Phase T (trending discovery) → Phase U (LLM-driven insights)"
- **Invitation**: "Join 100+ open-source projects already using Atlas. Contribute data, report issues, or integrate into your workflow."

---

### Act VI: The Action (CTA)
**Purpose**: Clear next step. Payoff. Command.  
**Emotional Arc**: "I know what to do next. I'm in."

**Slide Structure** (1 slide):
1. **Primary CTA** — One clear action (Link to docs. GitHub repo. Slack channel. Email for demo. Visit URL.)
2. *Optional Secondary CTA* — Alternative action (e.g., GitHub Issues for questions; Twitter for updates)

**Modernist Application**:
- CTA button (or text link): Archivo Bold, 24pt+, ink (#201e1d) on light background (#f3f2f2)
- If using button: 2px border, no fill, no shadow, visible 16px padding
- Secondary CTA: Archivo Regular, 16pt+, below primary
- No decoration, no arrows, no animation

**Example CTAs**:
- **Marshal**: "github.com/pyforge-guild/marshal • #marshal on Slack • marshal.readthedocs.io"
- **Warden**: "github.com/pyforge-guild/warden • Join the compliance guild • Report issues: issues.new"
- **Atlas**: "cf-atlas.readthedocs.io • GitHub: gh-api • Try: `pip install cf-atlas`"

---

### Appendix: Personas
**Purpose**: Stakeholder context. Voting records. Who cares?  
**Emotional Arc**: "I know what role I'm playing here. I see myself."

**Slide Structure** (1–4 slides):
1. *Per Persona*:
   - **Archetype** — Title + 1–2 sentence descriptor
   - **What They Care About** — 3 bullets (outcomes, constraints, motivations)
   - **Why They're Here** — One sentence (what do they gain from this solution?)
   - **Photo** — Real person or architectural avatar (B&W, high contrast)

**Modernist Application**:
- Persona name: Archivo Bold, 20pt+
- Descriptor: Archivo Regular, 14pt+
- Bullets: Archivo Regular, 12pt+
- Photo: Small, corner-anchored (4" × 4" max), B&W
- Layout: 2-column grid (persona + photo side-by-side) or 1-column list

**Example Personas** (for any station):
- **Rosa, Platform Engineer** — Owns 12 microservices. Wants policy consistency without manual overhead. Cares about time-to-deploy and risk reduction. Here because: "This saves us 4 hours per policy change."
- **Malik, Security Lead** — Risk-averse. Reviews every dependency. Wants a gate, not a suggestion. Here because: "This closes the vulnerability window before code lands."
- **Keisha, Open-Source Contributor** — Maintains 5 PyPI packages. Wants to know who depends on her code and why. Here because: "This shows the impact of my maintenance work."

---

## Visual Language: L.A.T.C.H. Applied

| Principle | Act | How |
|-----------|-----|-----|
| **L — Location** | Cover (wordmark place) | Top-center, fixed position; hero graphic grounds the idea spatially |
| **L — Location** | Friction (where pain is) | Photo of real workspace, real human, real problem |
| **A — Analogy** | Insight (new idea) | Visual metaphor compares old → new (2-panel diagram) |
| **T — Time** | Solution (4-step loop) | Numbered 1–4, arrows left-to-right or top-to-bottom |
| **C — Color** | All (brand identity) | Red #ec3013 for emphasis; monochrome default; Archivo throughout |
| **H — Hierarchy** | All (what matters?) | Bold headlines (Archivo Bold); supporting text (Regular) at smaller size |

---

## Slide Counts (Budget)

| Act | Slides | Notes |
|-----|--------|-------|
| Cover | 1–2 | Thesis + optional hook |
| Friction | 2–4 | Problem + context + consequence |
| Insight | 1–3 | Core idea + visual metaphor + timing |
| Solution | 4–6 | 4-step loop + overview |
| Real-World | 2–4 | Scenario + outcome + scaling |
| Vision | 1–3 | North star + roadmap + invitation |
| Action | 1 | CTA |
| Appendix | 1–4 | Personas (1 per slide) |
| **TOTAL** | **~28 slides** | ~90KB+ class, full depth |

---

## Deck Variants

### Main Deck (`{station}.md`)
- **Audience**: Executive, investor, evangelist, open-source contributor
- **Pacing**: All 8 sections, full depth
- **Slides**: ~28 (recommended: do not cut)

### Cover Deck (`{station}-cover.md`)
- **Audience**: Hallway chat, elevator pitch, email attachment
- **Pacing**: Cover + Insight + CTA (skip Friction, Solution detail)
- **Slides**: ~3–5

### Extended Deck (`{station}-extended.md`)
- **Audience**: Deep-dive workshop, architect review, team training
- **Pacing**: All sections + additional slides per act (solution steps expanded, real-world scenarios detailed)
- **Slides**: ~40–50

---

## Design Tokens: Modernist Palette

**Typography**:
- Family: Archivo (sans-serif, architectural, clean)
- Headlines: Archivo Bold, 24–56pt (depending on hierarchy)
- Body: Archivo Regular, 12–18pt
- CTA: Archivo Bold, 18–24pt

**Color**:
- Light background: #f3f2f2 (off-white, warm)
- Ink (text, lines): #201e1d (almost-black, neutral)
- Accent (emphasis, CTAs): #ec3013 (red-orange) / #c22a10 (dark red, hover state)
- No other colors in default palette (grayscale + one red)

**Layout**:
- Grid: Visible 2px lines, 8px or 16px snap-to-grid
- Padding: 16px minimum from edge (content inset from slide edge)
- Margins: 8px between elements
- Alignment: Flush-left text default; centered only for CTAs and cover

**Visual Elements**:
- Diagrams: 2px lines, no fills (or solid black 100%)
- Photography: Black-and-white, high contrast, no filters
- Shapes: No corner radius (all right angles), no shadows, no transparency gradients
- Annotations: Archivo Regular, 12pt, on 2px leader lines (arrows or rules)

---

## Authoring Checklist

- [ ] All 8 sections present (Cover through Appendix)
- [ ] Friction: Real pain point articulated; consequences visible
- [ ] Insight: Core idea is clear and novel
- [ ] Solution: 4-step loop is chronological (L.A.T.C.H. Time)
- [ ] Real-World: Scenario is specific (not abstract); outcomes quantified
- [ ] Vision: North star connects to broader trends (L.A.T.C.H. Category)
- [ ] CTAs: Primary and optional secondary, clickable/actionable
- [ ] Appendix: 1–4 personas, each with archetype + care-abouts + why-here
- [ ] Typography: Only Archivo (no other fonts)
- [ ] Color: Red #ec3013 for emphasis; rest monochrome (B&W)
- [ ] Diagrams: 2px lines, visible grid, no fills
- [ ] Photos: Black-and-white, high contrast, real (never fabricated)
- [ ] Full depth: No size restrictions; slides occupy full 1920×1080 canvas
- [ ] ~28 slides: Aim for recommended count (allow ±2 per act for station-specific needs)

---

## Examples: Opening Acts (Friction + Insight)

### Marshal (Policy Composition)
**Friction Headline**: "Policy Sprawl: 47 Files, Zero Consistency"  
**Friction Image**: Photo of engineer surrounded by YAML files (humorous, real)  
**Insight Headline**: "One Source of Truth, Four Layers of Composition"  
**Insight Diagram**: YAML root → repo defaults → team overrides → CLI flags (nested boxes, arrows)

### Warden (Dependency Compliance)
**Friction Headline**: "The Vulnerability You Don't Know About"  
**Friction Image**: Screenshot of build log with security warning (obscured, real)  
**Insight Headline**: "Risk Detection Before Code Lands"  
**Insight Diagram**: Dependency graph with red nodes (risky deps), gate symbol, CI/CD pipeline flow

### Atlas (Cross-Language Catalog)
**Friction Headline**: "Python Ecosystem Maps. Rust Ecosystem Maps. But Never Together."  
**Friction Image**: Split-screen (PyPI on left, npm on right, no bridge)  
**Insight Headline**: "A Single Source of Truth for All Languages"  
**Insight Diagram**: Unified graph with nodes for Python, npm, CRAN, CPAN (all converging on center)

---

## Companion Resources

- **Modernist Design System** (Claude Design project) — Live component pages, typography scales, color swatches, grid rules
- **Design Tokens** (`tokens.json`) — Machine-readable Archivo scale, palette, grid spec; imports into Figma, PPTX, web
- **Deck Engine** (Vite + Marp) — Live preview server, hot-reload on edit, browser inspect tools
