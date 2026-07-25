---
title: "Domain Research: deckcraft Competitive Landscape (light pass)"
research_type: domain
project: deckcraft
date: 2026-07-25
scope: light
inputs:
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft.md (comparison table, 2026-05-09)"
  - "_bmad-output/projects/deckcraft/planning-artifacts/prd.md"
  - "research/technical-research-toolchain-2026-07-25.md (companion report, same date)"
methodology: "gh api / gh search (GitHub REST + code search) against live repos; WebSearch unavailable this session (budget exhausted)"
---

# Domain Research: deckcraft Competitive Landscape (light pass)

## Purpose

The product brief's differentiation table (`product-brief-deckcraft.md` § "What Makes This Different") was authored 2026-05-09. This light pass re-checks that table against the live state of the four most relevant comparables as of 2026-07-25, with particular attention to `hugohe3/ppt-master` — flagged in the companion technical-research report as having grown from a minor intake-gist mention to 41,000+ GitHub stars in under 8 months.

---

## Comparables

### 1. `hugohe3/ppt-master` — the new dominant open-source entrant

- **Scale:** 41,032 stars, 3,406 forks, created 2025-12-10, pushed today (2026-07-25). License: **MIT**, confirmed via GitHub API.
- **Architecture:** an LLM-driven "skill"/workflow that runs *inside* an existing coding-agent IDE (Claude Code, Codex, Cursor — "whatever comes next"). It is not a standalone service or package. The AI first reasons about narrative structure (a "Strategist" step choosing a mode: pyramid / narrative / instructional / showcase / briefing), then generates a **constrained SVG per slide**, then compiles SVG → DrawingML via scripts. Their own docs describe this explicitly: *"SVG and DrawingML are the same kind of thing — absolute-coordinate 2D vector formats... conversion is a dialect translation, not a format bridge."*
- **Editability:** native DrawingML — slide masters/layouts (`p:sldMaster`/`p:sldLayout` inheritance on the template route), native shapes with adjustment handles, transitions, opt-in entrance animations, speaker-notes-to-narration. Charts/tables default to SVG-derived editable DrawingML shapes for cross-app fidelity; a `--native-charts-and-tables` flag switches eligible ones to true data-backed PowerPoint Chart/Table objects. This is genuinely the same "always-editable, never-rasterized" bar deckcraft sets for itself (FR-14/FR-15, NFR-14/NFR-15) — not a lesser claim.
- **Air-gap / self-host feasibility:** **this is where it does NOT match deckcraft.** Its own "Data Privacy" claim is narrower than it first sounds: *"Your files never leave your machine... The only external communication is between you and your AI editor."* That "AI editor" is the coding agent itself (Claude Code, Codex, Cursor), which for the overwhelming majority of users means a **cloud-hosted model** — Claude, GPT, Gemini, Kimi are the explicitly recommended models, with a stated quality gap for anything else. There is no documented local-LLM-first mode, no llama-server/Ollama/mlx-lm default, and no claim of functioning fully offline. Nothing in the README, why-ppt-master.md, or getting-started.md describes an air-gapped deployment path or a network-isolation test posture.
- **Distribution surface:** effectively one surface — "point a coding-agent IDE at this repo." No MCP server was found in the repo's documented feature set (not ruled out entirely without a full code audit, but not advertised as a capability — the README's "no lock-in" framing is specifically about *which* coding-agent IDE and *which* model, not about additional distribution surfaces like a standalone CLI, importable library, or conda-forge package). No package registry listing (PyPI/conda-forge) was found for it.
- **Performance:** 10–20 minutes for a 10-page deck (serial, page-by-page for cross-slide consistency) — same order of magnitude as deckcraft's own SC-02 target (<10 min large tier, no images), so this isn't a performance differentiator either way.
- **License risk profile:** clean MIT, no concerns.

### 2. `presenton/presenton` — the sibling repo's repackage target

- **Scale:** 9,174 stars, actively pushed today. License: **Apache-2.0**.
- **Architecture:** turnkey self-hosted web app + API (Docker package, or a native Desktop app for macOS/Windows/Linux). Positions itself explicitly as a Gamma/Canva/Beautiful-AI/Decktopus alternative.
- **Editability & air-gap — update since the product brief was written:** the current README claims *"Fully editable PPTX export"* and lists **Ollama and LM Studio** alongside OpenAI/Gemini/Vertex/Azure/Bedrock/Fireworks/Together/Anthropic as supported model backends. This is a broader claim than the product brief's characterization (§ "What Makes This Different": *"Native editable PPTX (real DrawingML) — Partial; varies"* for turnkey self-host tools, and the PRD's "image-overlay-based currently" note). **This research could not independently verify the PPTX structural quality of presenton's current export** (no generated sample was inspected) — flagging this as a claim worth re-verifying against `presenton-pixi-image`'s own findings (that sibling project's PRD is the authoritative source, not this light pass) rather than asserting it's resolved. If accurate, presenton has closed some of the editability gap that originally motivated splitting deckcraft out as a separate, from-primitives effort.
- **Distribution surface:** Docker web app, desktop app, and an API — not embedded inside an existing AI assistant's chat surface (Claude Code, Copilot, MS365 Copilot). This remains the clearest, still-valid differentiator against deckcraft: presenton is a destination you go to; deckcraft (per its founding thesis) is meant to live inside the tools the user is already in.

### 3. Cloud SaaS (Gamma, Beautiful.ai, Canva, Decktopus — grouped)

- Not independently re-researched in depth this pass (no material change expected in a 2.5-month window for this category's fundamentals) — the product brief's characterization stands unchanged: proprietary, cloud-only, unusable under air-gap/regulated-enterprise policy by construction. `presenton`'s own README explicitly markets itself as the open-source alternative to this exact group, which is a useful signal that the "turnkey self-host" category (presenton) is the more relevant comparable to re-check, not the SaaS category itself.

### 4. `GongRzhe/Office-PowerPoint-MCP-Server` — the intake gist's top OSS pick, now archived

- Per the companion technical-research report: **archived 2025-12-31**, 1,843 stars at time of archiving. It was the intake gist's "most complete OSS Python option" (32 tools, MCP-based, python-pptx under the hood) — the closest prior-art to deckcraft's own MCP-server surface (FR-39/40). Its abandonment removes what would have been the single closest architectural precedent for "python-pptx wrapped in an MCP server" — deckcraft is now, as far as this research found, the most actively-planned project taking that specific approach (MCP-server-native, not agent-skill-native like ppt-master).

---

## Synthesis: does deckcraft's angle still differentiate?

**Deckcraft's specific angle is four claims stacked together: (a) from-primitives (not a repackaged app), (b) air-gapped by default, (c) always-editable native DrawingML, (d) embedded across multiple AI surfaces (Skill + MCP + CLI + future VS Code/MS365), not one IDE.**

| Claim | Still differentiating vs. presenton? | Still differentiating vs. ppt-master? | Still differentiating vs. cloud SaaS? |
|---|---|---|---|
| (a) From-primitives, not repackaged app | N/A — this is the defining difference between the two sibling projects, unchanged | **Eroded.** ppt-master is also from-primitives (SVG→DrawingML compiled by their own scripts, not a wrapped app) | Yes, unchanged — SaaS is inherently the "repackaged" end of the spectrum |
| (b) Air-gapped by default (zero outbound network, local LLM default) | **Partially eroded** — presenton now supports Ollama/LM Studio as first-class backends, which is genuine local-LLM support; but presenton's DR-01-equivalent (an enforced, CI-tested default-offline mode) is not evidenced in its README the way deckcraft's architecture specifies it | **Not eroded — this is now the sharpest remaining differentiator.** ppt-master has no documented local-LLM-first or offline mode; it depends on a cloud-hosted coding-agent model by default and recommends specifically cloud models (Claude, GPT, Kimi) for quality | Yes, unchanged |
| (c) Always-editable native DrawingML | **Possibly eroded, unverified** — presenton's README now claims "fully editable" (previously "partial/image-overlay" per the product brief); needs re-verification, not yet confirmed independently | **Eroded — ppt-master meets or matches this bar.** Native shapes, masters/layouts, transitions, animations, narration, all as real OOXML, is at least as deep a claim as deckcraft's own FR-14/FR-15/NFR-14/NFR-15 | Yes, unchanged — SaaS tools still mostly rasterize or produce shallow "editable" skins |
| (d) Multi-AI-surface embedding (not one IDE) | Yes, unchanged — presenton is a destination app/API, not embedded in the user's existing assistant | **Partially eroded.** ppt-master already works inside "any agent-capable AI tool" (Claude Code, Codex, Cursor) via the coding-agent-skill pattern — that's a real multi-surface story, just scoped to *coding agents specifically*, not deckcraft's broader target list (MS365 Copilot, a standalone CLI for non-AI users, a conda-forge-installable library). Deckcraft's distribution list (Skill + MCP + CLI + conda-forge package + future VS Code/MS365 connector) is still broader, but the *margin* is smaller than the brief assumed in May. | Yes, unchanged |

**Bottom line for the operator:** deckcraft's air-gapped-by-default posture (claim b) is now doing more of the differentiation work than the brief originally weighted it to — editability (claim c) and from-primitives (claim a) are no longer uniquely deckcraft's, now that ppt-master exists and is thriving. The differentiation table in `product-brief-deckcraft.md` should be revisited at the next PRD/brief touch-point to reflect this: **"editable native PPTX" is no longer deckcraft's distinguishing claim — "editable native PPTX AND air-gapped AND embedded beyond just coding-agent IDEs" is.** None of this invalidates deckcraft's dogfooding-first success criterion or kill criteria (SC-01–SC-12) — the primary user (an air-gapped/regulated-enterprise-adjacent engineer) still has no tool that is simultaneously local-LLM-first, always-editable, and embedded in MS365/Copilot as well as Claude Code. But the "no technology moat, only an integration moat" framing in the product brief (§ "What Makes This Different") is truer now than when it was written — and the integration moat's most defensible edge has shifted specifically to the air-gap claim.

**One open question this research surfaces but does not resolve:** should deckcraft study ppt-master's SVG-as-intermediate-representation architecture (`AI generates constrained SVG → scripts compile SVG → DrawingML`) as an alternative to its own planned `Slide` JSON → `python-pptx` direct-authoring path (A-02/AD-01)? ppt-master's own rationale — "SVG and DrawingML are the same kind of thing... conversion is a dialect translation, not a format bridge" — is a genuinely different architectural bet than deckcraft's locked approach, and it's the bet that let ppt-master reach native shapes/masters/animations depth quickly. This is not a recommendation to change deckcraft's architecture (that's out of scope for a research-only pass, and AD-01's layered adapter design isn't threatened by this — the `pptx_engine` adapter boundary would absorb either implementation strategy equally well). It's flagged as a concrete idea worth a spike comparison once W2 (renderers) is underway, not a pre-implementation architecture change.

---

## Sources

- GitHub REST API (`gh api`, `gh search repos`, 2026-07-25): `hugohe3/ppt-master` (repo metadata, README, `docs/why-ppt-master.md`, `docs/getting-started.md`), `presenton/presenton` (repo metadata, README), `GongRzhe/Office-PowerPoint-MCP-Server` (archived status, cross-referenced from the companion technical-research report)
- Repo-internal: `_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft.md` § "What Makes This Different", `prd.md`
- Companion report: `research/technical-research-toolchain-2026-07-25.md` § 5 "New Entrants Since May 2026"
