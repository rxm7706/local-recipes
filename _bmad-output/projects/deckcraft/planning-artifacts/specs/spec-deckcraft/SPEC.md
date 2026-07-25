---
id: SPEC-deckcraft
surface:
  - apps/deckcraft/**             # the package this spec builds (not yet created)
  - recipes/deckcraft/**          # conda-forge recipe (CAP-9)
  - .claude/skills/deck-builder/**  # Claude Skill surface (CAP-9)
companions: []
sources:
  - ../../../../../../docs/dreams/deckcraft.md
  - ../../product-brief-deckcraft.md
  - ../../prd.md
  - ../../architecture.md
  - ../../epics.md
  - ../../research/plan-validation-notes-2026-07-25.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# deckcraft — the air-gapped, conda-native editable-deck pipeline

## Why

A vision to realize, sharpened by a concrete mandate: an air-gapped, conda-forge-native pipeline that turns a prompt or a source document into an **editable** PowerPoint deck — native DrawingML shapes, real charts, vector diagrams, optional local images — plus a round-trippable Marp source, embedded inside the AI tools a user already has (Claude Code, GitHub Copilot, MS365 Copilot) rather than one more browser tab. It exists for three audiences: the requester and colleagues who lose 30–60 minutes per deck to manual PowerPoint formatting today; air-gapped enterprise colleagues who have Copilot/MS365 but no path from AI prose to a shippable file; and authors of technical decks for whom every existing tool rasterizes diagrams and charts into unfixable images. The 2026-07-23 export revisit made this concrete: deckcraft is now designated the deck family's editable-PPTX engine, so `deck-export`'s Standard set depends on it. Deckcraft's differentiator is not a novel technique — every renderer is a known library — it is the integration: the right primitives, wired together, surfaced through every AI assistant the user already has, running entirely on local hardware.

## Capabilities

- **CAP-1**
  - **intent:** A user passes a document (PDF, DOCX, PPTX, Markdown, XLSX, URL, or any combination with a prompt) and deckcraft extracts its text/structure, retrieving only the most relevant sections when the document is long and collapsing near-duplicate slides.
  - **success:** Each supported format (FR-01–08) extracts cleanly via `markitdown`; documents over the configurable token threshold (default 16K) trigger the `sentence-transformers` RAG fallback (FR-43); slides with cosine similarity ≥0.92 are collapsed or reordered (FR-44).
- **CAP-2**
  - **intent:** A user provides a free-text prompt (with optional target slide count, audience, and tone) and deckcraft generates a complete, structured slide-deck JSON via the configured local LLM backend.
  - **success:** Output is schema-valid `Deck` JSON (FR-09–12) satisfying the tier timing budgets — SC-02 <10 min large/CPU, SC-03 <4 min medium/Metal-MLX, SC-04 <15 min small/CPU for a 10-slide, no-image deck.
- **CAP-3**
  - **intent:** Deckcraft renders slide JSON into a `.pptx` that opens cleanly in Microsoft PowerPoint 2019+ / Office 365, with every text box, autoshape, and chart as native, editable DrawingML.
  - **success:** FR-13–15 hold; SC-05 — 100% of text/shapes/charts/diagrams are native DrawingML, zero rasterized content (NFR-14/15) — verified by automated structural inspection of the generated `.pptx`.
- **CAP-4**
  - **intent:** Deckcraft emits a Marp-compatible `.md` sibling for every `.pptx`, and a user can hand-edit that Markdown and regenerate an updated `.pptx`, including converting an existing `.pptx` back to Marp.
  - **success:** FR-23/24 hold; J5's round-trip preserves text content, slide order, image references, and chart data, with lossy elements (custom animations, complex SmartArt) flagged in a sidecar warning file rather than silently dropped.
- **CAP-5**
  - **intent:** A user can request a Mermaid diagram or a typed chart (bar/line/scatter/pie/etc.) with structured data, and deckcraft renders it fully offline and embeds it as an editable, not rasterized, element.
  - **success:** FR-16–18 hold; Mermaid renders via `mermaid-py` + headless `playwright` (≤3s/diagram, NFR-04) and is convertible to native PowerPoint shapes; charts render via `matplotlib`/`plotly`, embedding as native PowerPoint charts where the data fits a standard type.
- **CAP-6**
  - **intent:** A user can have an existing image described by a local vision LLM, and — opt-in, default-off — generate a photorealistic image for a slide.
  - **success:** FR-19–22 hold; image generation is disabled unless explicitly enabled (`--enable-image-gen` or config), weights are lazy-pulled on first use (AD-12) so non-opters pay zero download cost, and any failure degrades gracefully to a placeholder + sidecar warning rather than crashing the pipeline (FR-26, NFR-06, NFR-22).
- **CAP-7**
  - **intent:** A user can pass `--style <path>` (`.potx`, `.pptx`, `.pptx --as-sample`, `.docx`, `.pdf`; `.odp`/`.odt` stretch) and deckcraft extracts a common `Style` JSON shape (theme colors, fonts, layouts, brand assets) that the generated deck, its charts, and its diagrams all inherit, with LLM-guided layout mapping and a heuristic fallback.
  - **success:** FR-25, FR-45–52 hold; NFR-23 — visual match verified across a documented corpus (5 `.potx`, 3 `.pptx`-as-sample, 3 `.docx`, 3 `.pdf` incl. 1 scanned requiring OCR fallback); the `Style` schema (AD-01) is the same shape `presenton-pixi-image`'s `template-style-extractor` targets, per FR-52.
- **CAP-8**
  - **intent:** Deckcraft runs identically on `linux-64`, `osx-arm64`, and `win-64`, and a user running `deckcraft init` gets an auto-detected, overridable hardware-tier recommendation (small/medium/large) with per-tier model defaults.
  - **success:** FR-27–32 hold; SC-08 — the same prompt+tier produces structurally equivalent `.pptx` output (same slide/shape/chart counts) across all three platforms, only LLM text content varying; AD-14's RAM-based tier-detection algorithm and AD-03's locked per-tier GGUF repos are honored.
- **CAP-9**
  - **intent:** Deckcraft is invocable as a CLI (`typer`), an MCP server (`fastmcp`, stdio transport), a Claude Skill (`.claude/skills/deck-builder/`), and is installable from conda-forge.
  - **success:** FR-35–42 hold; SC-09 — 3 of 6 distribution surfaces (Claude Skill + MCP stdio + CLI) live at V1, each producing a valid `.pptx`; SC-11 — `recipes/deckcraft/` accepted to `conda-forge/staged-recipes`.

## Constraints

- **Layered architecture, strict adapter boundaries (A-01):** surfaces (Skill/CLI/MCP) consume only the `Pipeline` API; renderers consume only engine adapters. The three swap points are `LLMAdapter`, `PptxEngineAdapter`, `PlatformAdapter` — nothing else is a designed swap point.
- **Single, immutable, JSON-serializable Pydantic data model (A-02)** for all inter-module data; no `pandas.DataFrame` or hidden global state crosses a module boundary (P-05).
- **pptx-engine-only access (P-01):** code outside `deckcraft.engines.pptx_engine` MUST NOT `import pptx` directly — this is the vendor-fallback discipline protecting FR-15 against `python-pptx`'s dormancy (last release 2024-08-07); vendor-and-patch triggers only on AD-07's explicit criteria (a blocker bug, an unsupported format requirement, or an unpatched 30-day compatibility break), never preemptively.
- **LLM-adapter-only access (P-02):** all LLM calls go through `pydantic-ai` via `LLMAdapter`; no direct `httpx` calls to a backend or direct `ollama`/`anthropic` SDK imports from business logic.
- **Graceful degradation (P-06/FR-26):** every optional capability (image gen, vision, mermaid render, chart render) is wrapped so its failure is caught, logged, and produces a sidecar warning — the pipeline never crashes on a failed optional capability.
- **Offline-first (P-07/DR-01/NFR-11):** no outbound network call without consulting the offline gate first; default mode makes zero outbound connections after first-run model download; CI verifies this under `unshare -n` (NFR-08).
- **Conda-forge-only runtime (DR-02):** every runtime dependency resolves from conda-forge; the sole exception is pre-downloadable GGUF/safetensors model weights, which are themselves air-gappable via `DECKCRAFT_MODEL_DIR`.
- **Cross-platform structural parity (DR-05/SC-08):** `linux-64`/`osx-arm64`/`win-64` must produce structurally equivalent `.pptx` from the same prompt+tier — only LLM-generated text varies.
- **License must be MIT or Apache-2.0 only** (the project's founding acceptance criterion — no proprietary or copyleft code). This directly conflicts with `pymupdf`, pinned as the primary PDF style-extraction library for FR-46c/AD-13: PyPI states it is dual-licensed AGPL-3.0 / Artifex commercial (`research/plan-validation-notes-2026-07-25.md` Finding 2). **Unresolved** — see Open Questions; the conflict is a human license call, not invented away here, and must be settled before Story 3.2 (PDF style loader) starts, not before this Spec.

## Non-goals

- VS Code extension with a `/deck` slash command — V2 (reuses the existing `copilot-bridge-vscode-extension.md` spec as a basis).
- MCP HTTP transport — V2 (AD-04); V1 ships stdio only.
- LiteLLM-based routing layer — deferred until conda-forge's `litellm` feedstock relaxes its `pydantic` pin conflict.
- Expanded template library beyond `default-professional` + `bmad-prd-pitch` — V2.
- A Jupyter notebook surface — technically free via `pixi-kernel` but not a committed V1/V2 surface.
- MS365 Copilot Power Platform connector — V3, gated on tenant-admin and Power Platform availability; not a V1/V2 commitment.
- `pptx-assembler`/`template-style-extractor` library convergence with `presenton-pixi-image` — the V∞ discretionary target (AD-05); V1 keeps separate engines.
- Upstream contribution back to `python-pptx` (equation parsing, TIFF support) — discretionary, not committed.
- `.odp`/`.odt` style sources (FR-46d) — slipped to V2 (AD-10) to keep V1 inside the ≤12-week kill-criteria envelope.

## Success signal

The requester ships ≥1 real, ship-quality deck per week for 4 consecutive weeks following V1 release — the master switch; failing it triggers the documented kill criteria (>60 min/deck hand-editing, or >1 hr/week maintenance burden) and a rescope toward convergence with `presenton-pixi-image`. This is reinforced by two non-negotiable, machine-checkable signals: 100% of generated text/shapes/charts/diagrams are native DrawingML with zero rasterized content (SC-05), and every V1 feature is verified to work identically under `unshare -n` network isolation (SC-07) — plus `recipes/deckcraft/` landing in `conda-forge/staged-recipes` (SC-11).

## Assumptions

- PPTX engine is `python-pptx` 1.0.2 (dormant since 2024-08-07 but stable), wrapped behind `pptx_engine`; vendoring is reactive (AD-07 triggers), never preemptive.
- LLM backend default is `llama-server` (conda-forge, on-demand); `Ollama` and `mlx-lm` (preferred on `osx-arm64` per AD-02) are configured alternatives; `LiteLLM` routing is deferred (non-goal above).
- Hardware tiers are small (≤32 GB RAM) / medium (32–48 GB) / large (≥48 GB), each with locked per-tier GGUF model defaults (AD-03); `deckcraft init` auto-detects and recommends, user can override.

## Open Questions

- **License conflict (blocking before Story 3.2, not before this Spec):** `pymupdf`'s AGPL-3.0/Artifex-commercial dual license contradicts the MIT/Apache-2.0-only founding constraint for FR-46c's PDF style extraction (AD-13). Three named options, undecided: accept AGPL for this one opt-in capability path with documented rationale; substitute `pdfplumber` (already in env, MIT-family, requester-maintained) with a documented quality trade-off; or scope out FR-46c's OCR-fallback depth entirely. A human call.
