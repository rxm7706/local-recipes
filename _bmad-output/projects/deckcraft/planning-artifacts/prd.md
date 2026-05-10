---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
inputDocuments:
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft-distillate.md"
  - "_bmad-output/projects/deckcraft/.bmad-config.toml"
  - "pixi.toml (post-deckcraft additions)"
  - "CLAUDE.md (BMAD multi-project + conda-forge-expert integration rules)"
  - "_bmad-output/projects/presenton-pixi-image/planning-artifacts/prd.md"
  - "docs/specs/copilot-bridge-vscode-extension.md"
referenceProjects:
  - "https://github.com/scanny/python-pptx (engine, MIT, dormant since 2024-08-07)"
  - "https://github.com/OscarPellicer/pptx2marp (Apache-2.0, code reference for element mapping)"
  - "https://github.com/OscarPellicer/python-pptx (Apache-2.0 fork, selective patches vendored as needed)"
workflowType: prd
projectName: deckcraft
projectType: "Python library + CLI + MCP server + Claude Skill + conda-forge package"
adoptionPattern: "single-release with prioritized must-have / nice-to-have within V1; deferred items marked V2/V3"
releaseMode: single-release-prioritized
---

# Product Requirements Document — deckcraft

**Author:** rxm7706
**Date:** 2026-05-09
**Status:** draft v1
**Sibling project:** [`presenton-pixi-image`](../../presenton-pixi-image/planning-artifacts/prd.md) (complementary; convergence is the V∞ endgame)

---

## Executive Summary

Deckcraft is an air-gapped, conda-forge-native AI pipeline that turns a prompt or source document (PDF / DOCX / PPTX / Markdown / URL) into a fully editable PowerPoint deck — with native shapes, real charts, vector infographics, and optional AI-generated images — plus a round-trippable Marp markdown source. It runs entirely on local hardware with local LLMs (llama.cpp by default, Ollama optional, MLX preferred on Apple Silicon), produces output that PowerPoint users can hand-edit immediately, and exposes itself through every AI surface the user already has: a Claude Skill in this repo, an MCP server (stdio + HTTP) that any MCP-aware AI tool can call, a CLI for direct human use, and (future waves) a VS Code extension and an MS365 Power Platform connector.

The strategic gap deckcraft fills: anyone in a regulated/air-gapped enterprise who wants AI-assisted slide creation today must choose between cloud tools they can't use (Gamma, Beautiful.ai, Copilot Pages with cloud generation), turnkey self-hosted apps that need a Kubernetes cluster (Presenton — which the requester is *also* repackaging in this repo via `presenton-pixi-image`), or hand-authoring slides with no AI help. Deckcraft is the missing fourth option: a primitive-level pipeline embedded inside the AI assistants people already use, runs as a single Python process on a laptop, produces deliverables that are immediately editable in the tool everyone already has — Microsoft PowerPoint.

V1 ships across three reference platforms (Linux 64 GB / Windows 32 GB / macOS M4 48 GB) using the same conda-forge stack. The primary success measure is dogfooding adoption by the requester (≥1 real deck per week for 4 consecutive weeks post-V1). Anything else is supporting evidence.

---

## Success Criteria

### Primary success criterion (the master switch)

**The requester uses deckcraft to produce ≥1 real, ship-quality deck per week for 4 consecutive weeks following V1 release.** If this fails, no other metric saves the product. It joins the long list of devtools-built-by-engineers-for-themselves that died at the dogfooding step. All supporting metrics either reinforce this signal or trigger the kill-criteria gate.

### Supporting metrics (testable / measurable)

| ID | Metric | Target | Measurement approach |
|---|---|---|---|
| SC-01 | End-to-end time prompt → editable `.pptx` ready to ship (LLM + manual editing combined, large tier) | ≤ 30 minutes | Wall-clock log on dogfooded decks; weekly self-report |
| SC-02 | LLM-only generation time for a 10-slide deck, no images, large tier on CPU | < 10 minutes | Benchmark fixture run on Framework Laptop 16 |
| SC-03 | LLM-only generation time, medium tier (M4) | < 4 minutes | Benchmark on M4 with Metal/MLX |
| SC-04 | LLM-only generation time, small tier (Windows 32 GB CPU) | < 15 minutes | Benchmark on reference Windows machine |
| SC-05 | Output editability | 100% of text / shapes / charts / diagrams in generated `.pptx` are native DrawingML; zero rasterized | Automated structural inspection of generated `.pptx` |
| SC-06 | First-draft usefulness (subjective) | ≥ 70% of slides accepted as-is or with minor edits, averaged across 5 evaluators on 10 sample prompts | Review rubric, scored 1–10, threshold 7 |
| SC-07 | Air-gapped functional parity | Every V1 feature works identically when network interfaces are down | CI integration test runs deckcraft inside `unshare -n` |
| SC-08 | Cross-platform parity | Generated `.pptx` from same prompt + tier is structurally identical (same slide count, same shape count per slide, same chart types) on linux-64 / osx-arm64 / win-64 | CI golden-path fixture, diff structural report |
| SC-09 | Distribution surfaces live by V1 release | 3 of 6 (Claude Skill + MCP stdio + CLI) | Each surface invokes deckcraft and produces a valid `.pptx` |
| SC-10 | Distribution surfaces live by V2 release | 5 of 6 (above + VS Code extension + MCP HTTP) | Same |
| SC-11 | Conda-forge package status | `recipes/deckcraft/` accepted to `conda-forge/staged-recipes` | PR merged |
| SC-12 | Builder time investment for V1 | 8.5–12 weeks of focused work pending story-level estimation. Adds vs original 6–10 baseline: image gen V1 promotion (+1 week), BYO style sources `.potx`/`.pptx`/`.docx` (+1.5 weeks), PDF style extraction with OCR fallback + legacy-format rejection (+0.5 week). ODP/ODT slipped to V2 per architecture AD-10 to stay inside ≤12-wk kill-criteria envelope. Subject to Spike-0 benchmark validation before story breakdown locks the estimate. | Sprint tracking via `bmad-sprint-status` |

### Kill criteria (project paused / rescoped if any of these hold at week 6 post-V1)

- The requester is not using deckcraft for ≥1 real deck per week.
- The deck output requires more than 60 minutes of hand-editing to ship-ready (i.e., it's not actually faster than the existing prose-to-PowerPoint workaround).
- The maintenance burden (broken Skill, MCP issues, conda recipe drift) exceeds 1 hour/week.

If any of these triggers, the right move is to converge what's salvageable with `presenton-pixi-image` (shared `pptx-assembler` library) and shut down standalone deckcraft.

---

## User Journeys

Six concrete journeys derived from the brief's jobs-to-be-done. Each maps to one or more functional requirements (cross-referenced in the FR table).

### J1 — "Turn this PDF into a draft slide deck I can hand-edit in PowerPoint"

**Actor:** the requester (or any deckcraft user)
**Trigger:** they have a source document and need to present it. They invoke `deckcraft generate --input /path/to/report.pdf --out deck.pptx` (CLI), or say "make a deck from this PDF" inside Claude Code (Skill), or call the `generate_deck` MCP tool from Copilot Chat.
**Flow:**
1. Deckcraft extracts text from the PDF via `markitdown`.
2. The LLM adapter (default: `llama-server`) receives the extracted markdown plus a prompt template, returns structured slide JSON.
3. The pptx renderer turns the JSON into an editable `.pptx` with native shapes (titles, bullets, autoshapes, native PowerPoint charts where data is structured).
4. The marp renderer turns the same JSON into a `.md` source the user can hand-edit and re-render.
5. The user opens the `.pptx` in PowerPoint, hand-edits, ships.
**Success:** total time (including hand edits) < the user's prior workaround (~30–60 minutes).
**Maps to FRs:** FR-01, FR-02, FR-03, FR-09, FR-13, FR-14, FR-15, FR-25.

### J2 — "Add an infographic / flowchart / chart to slide N — make it editable, not a screenshot"

**Actor:** any deckcraft user mid-edit.
**Trigger:** the user wants a flowchart or chart on a specific slide. They edit the Marp source (or pass a directive in the original prompt) to add a mermaid block or a chart spec.
**Flow:**
1. Deckcraft detects the mermaid / chart directive during render.
2. mermaid-py + headless playwright renders the diagram to SVG offline.
3. matplotlib / plotly renders chart specs to SVG (or as native PowerPoint charts where the data fits).
4. The pptx renderer embeds the SVG as ungroupable native shapes (PowerPoint can convert SVG → editable shapes natively).
**Success:** every infographic in the output is editable in PowerPoint (selectable, group-broken-apart, color-changeable). Zero screenshots.
**Maps to FRs:** FR-16, FR-17, FR-18, FR-25.

### J3 — "Generate a hero image for the cover slide"

**Actor:** any deckcraft user, optionally.
**Trigger:** the user wants a photorealistic image (e.g., cover slide, illustration). Image generation is opt-in (default off in small tier) and degrades gracefully when memory or hardware is unavailable.
**Flow:**
1. The image generation module loads SDXL-Turbo via `diffusers` on the appropriate device (CPU / MPS / CUDA / ROCm).
2. The LLM produces an image prompt from the slide context.
3. The diffuser generates a PNG (~30–60s on CPU; ~5–10s on M4 MPS; ~3–5s once the requester's iGPU is healthy).
4. The pptx renderer embeds the PNG.
**Success:** image lands in the deck without hanging the pipeline; if generation fails for any reason, the slide ships with a placeholder + a graceful warning, not a crash.
**Maps to FRs:** FR-19, FR-20, FR-26 (graceful degradation), FR-32 (config-driven enable).

### J4 — "Read this image and explain what's in it"

**Actor:** any deckcraft user ingesting visual input.
**Trigger:** the source material includes images (e.g., a PDF with embedded charts; a screenshot the user wants to summarize on a slide). They invoke `deckcraft describe-image --input /path/to/img.png` or include the image in a deck-generation request.
**Flow:**
1. The vision module sends the image to the local vision LLM (Ollama `qwen2.5vl:7b` for medium/large tier; `qwen2.5vl:3b` for small tier; or llama.cpp `--mmproj` equivalent).
2. The model returns a structured description (caption + key elements + extracted text).
3. Deckcraft uses the description as input to the outline generator, OR returns it directly to the user.
**Success:** the description is accurate enough that the LLM-generated slide content reflects what's in the image.
**Maps to FRs:** FR-21, FR-22.

### J5 — "Convert this deck back to Marp markdown so I can edit and re-render it"

**Actor:** any deckcraft user with an existing `.pptx`.
**Trigger:** the user wants to round-trip a deck through markdown for batch editing or version-control diffability.
**Flow:**
1. Deckcraft reads the `.pptx` via `python-pptx`.
2. The marp renderer (in inverse mode — implementation reference: `OscarPellicer/pptx2marp` element mapping) emits a Marp `.md` source preserving titles, bullets, images, tables, and (best-effort) layout.
3. The user edits the `.md` and re-runs `deckcraft generate --input edit.md --out updated.pptx`.
**Success:** round-trip preserves text content, slide order, image references, chart data, and major formatting decisions. Lossy elements (e.g., custom animations, complex SmartArt) are flagged in a sidecar warning file.
**Maps to FRs:** FR-23, FR-24.

### J6 — "Turn this BMAD PRD into a stakeholder pitch deck"

**Actor:** the requester (and BMAD-using colleagues).
**Trigger:** the user has a BMAD planning artifact (`prd.md`, `epics.md`, `architecture.md`) and needs to present it. This is a built-in V1 use case; BMAD artifact ingestion is "free" given the existing BMAD installation in the repo.
**Flow:**
1. Deckcraft detects BMAD-style frontmatter and section structure.
2. A specialized template ("BMAD-PRD-pitch") maps PRD sections to slide groups (Executive Summary → 1–2 slides; Success Criteria → 1 slide; User Journeys → 1 slide each; FRs → grouped by capability; etc.).
3. The output is a stakeholder-friendly pitch deck preserving the substance but reformatting the prose.
**Success:** the requester can run `deckcraft generate --input _bmad-output/projects/deckcraft/planning-artifacts/prd.md --template bmad-prd-pitch --out deckcraft-pitch.pptx` and get a usable deck without manual prompt engineering.
**Maps to FRs:** FR-04, FR-05, FR-25 (template-driven layout).

---

## Domain Requirements

### Air-gapped operation

**DR-01 — Mandatory air-gapped default mode.** Every V1 feature must work identically when no network interfaces are available. Cloud LLM/image/vision APIs are documented opt-ins (Anthropic / Azure OpenAI / GitHub Models adapters) but never the default. CI must verify air-gapped operation via `unshare -n` or equivalent network isolation.

**DR-02 — All runtime dependencies must come from conda-forge.** No PyPI-only deps in the runtime path. Verified package-by-package against conda-forge as of 2026-05-09; the only non-conda-forge runtime artifact is the pre-downloaded GGUF / safetensors model weights (which can be transferred to air-gapped environments via mirror or USB).

**DR-03 — Model artifacts must be air-gappable.** Deckcraft must support a `DECKCRAFT_MODEL_DIR` environment variable / config setting pointing at a pre-populated local cache. First-run setup downloads via `hf-transfer` (3× faster than baseline); air-gapped deployment expects the cache to be pre-populated.

### Conda-forge-native distribution

**DR-04 — Deckcraft itself must be installable via `conda install -c conda-forge deckcraft`.** A recipe at `recipes/deckcraft/` (rattler-build v1 format) submitted to `conda-forge/staged-recipes` is required for V1 release.

**DR-05 — Cross-platform parity.** Three reference platforms — `linux-64`, `osx-arm64`, `win-64` — must produce structurally equivalent `.pptx` output from the same prompt and tier. Only LLM-generated text content varies between runs (LLM is non-deterministic).

### Compliance with this repo's `BMAD ↔ conda-forge-expert integration` rules (per CLAUDE.md)

**DR-06 — Recipe authoring invokes `conda-forge-expert` skill.** Story S-15 (recipe submission) must invoke the skill before producing recipe content, per CLAUDE.md Rule 1.

**DR-07 — Closeout retro touches the conda-forge-expert skill.** Per CLAUDE.md Rule 2, the deckcraft project's closeout includes a `bmad-retrospective` focused on the `conda-forge-expert` skill (corrections / refinements / additions); CHANGELOG entry and version bump per semver.

---

## Innovation Analysis

### Innovation Pattern 1 — Multi-AI surface as a single product

Most AI-assisted deck tools are bound to one platform (Gamma's web UI, Copilot Pages inside MS365, Beautiful.ai's app). Deckcraft inverts this: the *primitive layer* is the product, and it surfaces through every AI assistant a user already has via MCP. This is enabled by Anthropic's Model Context Protocol going GA in Claude Desktop (Nov 2024) and reaching VS Code Copilot Chat (1.99, early 2025). Deckcraft is one of the first products that treats MCP as the *primary* distribution surface rather than an afterthought.

**Innovation enabler:** `fastmcp` (conda-forge, requester-maintained) provides a Python-native MCP server with stdio + HTTP transports, which means deckcraft's MCP surface is one decorator-and-function pattern, not a separate codebase.

### Innovation Pattern 2 — Editable native shapes, always

The deck-generation tool category is full of products that "support PowerPoint output" by rendering slides as images and embedding them in a `.pptx` shell. Deckcraft commits to native DrawingML — every text box, autoshape, chart, and diagram in the output is selectable and editable in PowerPoint. This is non-negotiable per the brief. Reference: `OscarPellicer/pptx2marp` shows the element-mapping logic in the inverse direction (PPTX → Marp); deckcraft applies the same conventions in reverse (Marp/JSON → PPTX with native shapes).

### Innovation Pattern 3 — Backend-agnostic via `pydantic-ai`

Most LLM-driven tools hard-code one provider. Deckcraft's LLM adapter is one library (`pydantic-ai`) over an OpenAI-compatible HTTP endpoint. The same code path works against `llama-server` (default, conda-forge native, all 3 platforms), Ollama (existing IDE-client setup), `mlx-lm` (Apple Silicon optimization, ~2–3× over llama.cpp Metal), Azure OpenAI (corporate cloud), and GitHub Models (Copilot subscription tier). Adding a new backend is a config change, not a code change.

### Innovation Pattern 4 — BMAD-as-input deck

Treating BMAD planning artifacts (PRD, epics, architecture) as first-class inputs is a "free feature" given the requester's existing BMAD installation. Other deck tools assume cold-start prompt engineering; deckcraft assumes the user already has structured planning content and just needs it presented.

---

## Project-Type Requirements

Deckcraft is a **Python library + CLI + MCP server + conda-forge-distributed package**. This is a multi-surface distribution pattern, not a typical web-app or CLI-only project. The requirements break down by surface:

### Library requirements

- Pure Python 3.12 (matching the local-recipes pixi env's `python 3.12.*`)
- Importable as `import deckcraft` from any pixi env that includes the deckcraft package
- Public API: `deckcraft.Pipeline`, `deckcraft.Deck`, `deckcraft.Slide`, `deckcraft.render_pptx()`, `deckcraft.render_marp()`, etc.
- Pydantic data models for all structured types (Deck, Slide, Theme, Asset, LayoutHint, HardwareTier)

### CLI requirements

- Built with `typer` (already on conda-forge in env)
- Entry-point: `deckcraft` console script
- Commands: `deckcraft generate`, `deckcraft init`, `deckcraft describe-image`, `deckcraft convert`, `deckcraft list-templates`, `deckcraft preview`
- Cross-platform: must run on bash / zsh / cmd / PowerShell

### MCP server requirements

- Built with `fastmcp` (conda-forge, requester-maintained at v3.2.4)
- stdio transport for V1 (Claude Code, Copilot Chat, Claude Desktop)
- HTTP transport for V2 (MS365 connector, remote callers)
- Tools exposed: `generate_deck`, `add_slide`, `render_chart`, `render_diagram`, `describe_image`, `extract_document`
- Self-describing: tool schemas auto-generated from Pydantic types

### Claude Skill requirements (in this repo)

- Located at `.claude/skills/deck-builder/`
- SKILL.md describes when to invoke + workflow + examples
- Thin invocation wrapper: calls `pixi run -e local-recipes deckcraft generate ...`
- No duplicated logic — skill is a routing layer, not a reimplementation

### conda-forge package requirements

- Recipe at `recipes/deckcraft/recipe.yaml` (rattler-build v1 format, per the repo's standard)
- Dependencies match the actual deckcraft runtime needs (matplotlib, plotly, transformers, accelerate, playwright-python, ollama-python, hf-transfer, sentencepiece, sentence-transformers, python-pptx, markitdown, mermaid-py, marp-cli, fastmcp, mcp, pydantic-ai, typer, llama.cpp, diffusers, pytorch, etc.)
- Platform support: noarch where possible; otherwise linux-64 + osx-arm64 + win-64 (with `mlx` + `mlx-lm` conditional on linux-64 + osx-arm64 only — Windows excluded by upstream mlx skip rule; macOS minimum 14.5)
- License: MIT (or Apache-2.0; finalized in S-01 with pyproject.toml)
- Maintainer: rxm7706 (with optional co-maintainers)

### VS Code extension requirements (V2)

- Reuses the existing 12-story spec at `docs/specs/copilot-bridge-vscode-extension.md` as a basis
- Registers deckcraft's MCP server in `.vscode/mcp.json`
- Adds `/deck` slash command in Copilot Chat
- Distribution: VSIX sideload + optional VS Code Marketplace publish

### MS365 Copilot connector requirements (V3, gated)

- Power Platform custom connector spec
- Calls deckcraft's MCP HTTP transport
- Declarative agent manifest for Copilot Studio
- Gated on tenant admin + Power Platform availability — explicitly *not* a V1/V2 commitment

---

## Project Scoping

### Strategy & Philosophy

Deckcraft adopts a **single-release-prioritized** model for V1, with explicit must-have / nice-to-have separation. This is NOT a "phased delivery" — V1 is one shipping target with a prioritized backlog within it. Deferred items go to V2 / V3 nice-to-have lists, not to fabricated "phases." This matches the requester's input documents (the brief defines V1 / V2 / V3 as "release horizons," not as MVP gates).

**Approach:** ship V1 as a focused, dogfoodable tool. Don't gold-plate. Validate the dogfooding success criterion before investing in V2's surface expansion.

**Resource Requirements:** one builder (the requester), 6–10 weeks of focused work for V1 pending story-level estimation in the architecture phase.

### Complete V1 Feature Set

#### Core User Journeys Supported (V1)

All 6 JTBDs. J1 (PDF/prompt → editable pptx), J2 (infographics/charts), J3 (hero image — opt-in), J4 (image understanding), J5 (deck → Marp), J6 (BMAD PRD → pitch deck).

#### Must-Have Capabilities (V1)

- Document ingestion (PDF, DOCX, PPTX, MD, URL) via `markitdown` (FR-01 to FR-05)
- LLM-driven outline + slide content generation via `pydantic-ai` (FR-09 to FR-12)
- Editable `.pptx` rendering with native DrawingML via `python-pptx` (FR-13 to FR-15)
- Marp markdown rendering (FR-23 to FR-24)
- Mermaid diagrams via `mermaid-py` + `playwright` (FR-16, FR-17)
- Chart rendering via `matplotlib` + `plotly` (FR-18)
- Image understanding via Ollama vision models (FR-21, FR-22)
- Image generation via `diffusers` + SDXL-Turbo (FR-19, FR-20) — opt-in default-off, lazy-loaded weights
- Bring-your-own style sources: `.potx`, `.pptx`, `.docx`, `.pdf` (with OCR fallback for scanned PDFs) accepted via `--style <path>` (FR-45 through FR-52); legacy `.ppt`/`.doc` explicitly rejected with helpful error; `.odp`/`.odt` stretch goal; LLM-guided layout mapping; theme colors flow through to charts and diagrams; common `Style` JSON shape across all extractors (V∞ convergence target with `presenton-pixi-image`'s `template-style-extractor`)
- Cross-platform operation on linux-64 / osx-arm64 / win-64 (FR-27 to FR-30)
- Hardware tier auto-detection in `deckcraft init` (FR-31, FR-32)
- LLM backend adapter (llama-server default; Ollama and mlx-lm as alternatives) (FR-33, FR-34)
- CLI surface (`typer`-based) (FR-35 to FR-38)
- MCP server surface (stdio transport) via `fastmcp` (FR-39, FR-40)
- Claude Skill (`.claude/skills/deck-builder/`) (FR-41)
- conda-forge recipe (`recipes/deckcraft/`) (FR-42)
- BMAD PRD as input template (J6) (FR-04, FR-05)
- Air-gapped operation (DR-01 enforcement; tested in CI) (NFR-08)
- Engine adapter wrapping `python-pptx` (DR-04 escape hatch) (FR-15)

#### Nice-to-Have Capabilities (deferred to V2 within the same release-thinking model)

- VS Code extension with `/deck` slash command (reuses `copilot-bridge-vscode-extension.md` spec)
- MCP HTTP transport (needed for MS365 Copilot path; deferred unless V3 is pursued earlier)
- LiteLLM-based routing layer (deferred until conda-forge `litellm` relaxes the `pydantic` pin conflict)
- Expanded template library (corporate / technical / pitch / academic — V1 ships one corporate template)
- Notebook surface (importable from Jupyter via `pixi-kernel`; free but unfocused)

#### Discretionary (V3, not committed)

- MS365 Copilot Power Platform connector — gated on tenant admin
- `pptx-assembler` library convergence with `presenton-pixi-image` (the V∞ endgame)
- Contribution back to upstream `python-pptx` (revival PR for equation parsing + TIFF support)
- `mlx-lm` deeper integration on macOS (custom backend module if it offers further perf wins beyond the OpenAI-compat wrapping)

### Risk Mitigation Strategy

**Technical Risks:**
- *Risk:* `python-pptx` upstream is dormant (last release 2024-08-07). *Mitigation:* wrap all pptx calls behind `deckcraft.engines.pptx_engine` adapter (FR-15); vendor + patch the library if a critical issue arises (no preemptive fork). Reference projects (`OscarPellicer/python-pptx`, `pptx2marp`) are studied and selectively vendored under attribution.
- *Risk:* MCP/Copilot maturity unknown (Copilot's MCP support GA in VS Code 1.99 but real-world bug count unproven). *Mitigation:* V1 MCP path uses stdio against Claude Code (most mature MCP host); Copilot/MS365 paths are V2+ and bumpable.
- *Risk:* Phoenix iGPU compute path is broken on the requester's primary dev machine; CPU-only inference until kernel/firmware fix. *Mitigation:* deckcraft assumes CPU as baseline; iGPU revival is a perf upgrade, not a functional dependency. Architecture uses `pytorch` (already installed) which handles both paths transparently.
- *Risk:* SDXL-Turbo on CPU is slow (~30–60 s/image). *Mitigation:* image generation is **opt-in default-off in V1**; lazy-pulled weights mean users who never enable it pay zero cost; mermaid + matplotlib cover most infographic needs without diffusion.

**Market / Adoption Risks:**
- *Risk:* First-deck friction kills dogfooding before week 4. *Mitigation:* V1 includes a "starter prompt library" + a corporate template matching the requester's actual brand, so deck #1 is plausible without any prompt engineering.
- *Risk:* The dogfooding criterion fails — requester abandons deckcraft for the existing manual workaround. *Mitigation:* explicit kill criteria (≥1 deck/week, ≤60 min per deck, ≤1 hr/week maintenance) trigger pause/rescope at week 6. Convergence with `presenton-pixi-image` is the documented graceful exit.

**Resource / Capacity Risks:**
- *Risk:* V1 takes longer than 10 weeks. *Mitigation:* must-have capabilities are scoped tightly (no image gen, no VS Code ext, no MS365); story-level estimation in architecture phase will catch over-scope before commit.
- *Risk:* Multi-surface maintenance burden compounds over time. *Mitigation:* surfaces beyond V1's three (Skill + MCP stdio + CLI) are gated on actual demand; `bmad-retrospective` discipline (per CLAUDE.md) catches drift early.

---

## Functional Requirements

The capability contract for deckcraft V1. Every FR is testable. Each FR specifies WHO can do WHAT (no HOW). UX, architecture, and epic breakdown will trace back to this list. **Anything not listed here will not exist in V1 unless explicitly added.**

### Document Ingestion

- **FR-01:** A user can pass a PDF file path as input and deckcraft extracts its text content via `markitdown`.
- **FR-02:** A user can pass a DOCX file path as input and deckcraft extracts its text content.
- **FR-03:** A user can pass a PPTX file path as input and deckcraft extracts its slide content.
- **FR-04:** A user can pass a Markdown file path as input and deckcraft uses it directly.
- **FR-05:** A user can pass a BMAD-style markdown file (with structured frontmatter + sections) and deckcraft applies BMAD-aware section mapping.
- **FR-06:** A user can pass a URL as input and deckcraft fetches + extracts its text content (only if a network is available; respects air-gapped mode).
- **FR-07:** A user can pass an XLSX file path and deckcraft extracts tabular data via `markitdown`.
- **FR-08:** A user can combine multiple input sources (e.g., a prompt + a PDF + an image) in a single deck-generation request.

### Retrieval & Embeddings

- **FR-43:** When an extracted document exceeds a configurable token threshold (default 16K tokens), deckcraft uses `sentence-transformers` to embed document sections and retrieves only the most semantically relevant ones for each slide (RAG fallback). Default embedding model: `sentence-transformers/all-MiniLM-L6-v2` (~80 MB, air-gappable). User-overridable via config.
- **FR-44:** Deckcraft detects semantically near-duplicate slides in LLM output (cosine similarity ≥ configurable threshold, default 0.92) and either collapses or reorders them before final render.

### LLM-Driven Content Generation

- **FR-09:** A user can provide a free-text prompt and deckcraft generates a slide outline via the configured LLM backend.
- **FR-10:** Deckcraft can produce a complete slide deck JSON (slide count, titles, body content, layout hints, asset references) from extracted document content + optional prompt.
- **FR-11:** A user can specify a target slide count and deckcraft generates a deck of that approximate length.
- **FR-12:** A user can specify a target audience or tone (technical / executive / sales / academic) and deckcraft adjusts content style accordingly.

### Editable PPTX Rendering

- **FR-13:** Deckcraft renders slide JSON into a `.pptx` file that opens cleanly in Microsoft PowerPoint 2019+ on Windows and Office 365.
- **FR-14:** All text content in generated slides is rendered as editable PowerPoint text boxes (selectable, font-changeable, color-editable).
- **FR-15:** All shape content (titles, bullets, autoshapes, callouts) is rendered as native DrawingML shapes accessed exclusively through a `deckcraft.engines.pptx_engine` adapter (so vendor-and-patch of `python-pptx` is a clean swap if needed).

### Marp Markdown Rendering

- **FR-23:** Deckcraft generates a Marp-compatible `.md` file as a sibling of every `.pptx` output.
- **FR-24:** A user can edit the Marp `.md` file by hand and re-run deckcraft to produce an updated `.pptx`.

### Templates, Style Sources & Resilience

- **FR-25:** A user can specify a built-in template by name (e.g., `--template bmad-prd-pitch`, `--template default-professional`) and deckcraft applies that template's layout, branding, fonts, and color scheme. V1 ships at minimum two built-in templates: `default-professional` (the generic fallback used when no `--style` is provided) and `bmad-prd-pitch` (BMAD-PRD-aware for J6).
- **FR-26:** When optional capabilities (image generation, vision, mermaid rendering, chart rendering) fail or are unavailable, deckcraft completes the deck with placeholders and writes a sidecar warning file describing what failed and why. The pipeline never crashes due to a failed optional capability.

### Bring-Your-Own Style Sources

A unified style-source abstraction: deckcraft accepts `.potx`, `.pptx`, `.docx`, `.pdf`, and (stretch) `.odp` / `.odt` as a brand source via a single `--style <path>` flag. Auto-detects intent by extension. All sources resolve to a common `Style` JSON shape (theme colors, heading/body fonts, optional layouts, optional masters, optional brand assets) which the pptx engine and the chart/diagram renderers consume.

This `style_loader` is functionally equivalent to `presenton-pixi-image`'s `template-style-extractor` and is a candidate for V∞ convergence into a shared `pptx-style-toolkit` library that both projects consume. Format-detected dispatch over PPTX/DOCX/PDF using `python-pptx` + `python-docx` + `pymupdf` + `pytesseract`; ODP/ODT via `odfpy` is stretch.

- **FR-45:** A user can pass `--style <path>` and deckcraft auto-detects the source type by extension. Supported in V1: `.potx`, `.pptx`, `.docx`, `.pdf`. Stretch in V1: `.odp`, `.odt`. Legacy binary formats (`.ppt`, `.doc`) are explicitly rejected with a clear error: "save as .pptx/.docx and retry."
- **FR-46:** When the style source is `.potx` or `.pptx`, deckcraft uses it directly as the basis — new slides are written into the template's slide masters and layouts, inheriting its theme, fonts, logos, footers, page numbers, and background images.
- **FR-46c:** When the style source is `.pdf`, deckcraft extracts style via `pymupdf` (font sampling per page, color-palette sampling from text+shapes, heading-size detection, layout pattern inference). For scanned/image-based PDFs where text extraction yields nothing, falls back to `pytesseract` OCR + visual-pattern color sampling. Output is the common `Style` JSON shape.
- **FR-46d** *(V2 — slipped from V1 per architecture phase AD-10 to keep ≤12-wk kill-criteria envelope):* When the style source is `.odp` (OpenDocument Presentation) or `.odt` (OpenDocument Text), deckcraft uses `odfpy` to extract style (theme colors, fonts, layouts where available). `odfpy` already in V1 env so V2 add is module-only.
- **FR-47:** When the style source is `.pptx` and the user passes `--as-sample`, deckcraft introspects the file for style (theme, fonts, layout shapes) and generates a fresh deck using the extracted `Style` — the sample file's actual slides are discarded.
- **FR-48:** When the style source is `.docx`, deckcraft extracts Word's theme colors, heading fonts, body fonts, and accent palette via `python-docx`, then applies them to deckcraft's bundled `default-professional.potx` base (FR-51).
- **FR-49:** Charts (`matplotlib` / `plotly`) and Mermaid diagrams automatically use the loaded `Style`'s accent palette — `rcParams` for matplotlib, theme-CSS injection for mermaid. When a template is provided, native PowerPoint charts (FR-18) inherit theme colors automatically through DrawingML.
- **FR-50:** Layout mapping (when a PowerPoint template provides custom layouts) is LLM-guided by default — deckcraft passes the template's layout names + placeholder counts/types to the LLM, which selects the best layout per slide. User can override via `--layout-aliases <path-to-yaml>` to bypass LLM for predictable layouts.
- **FR-51:** Deckcraft ships a `default-professional.potx` base template (DejaVu-family fonts, neutral palette) used when no `--style` is provided and as the application base when the style source is `.docx`, `.pdf`, `.odp`, or `.odt` (which provide style data but no PowerPoint layouts).
- **FR-52:** All `Style` extractors emit a common JSON shape (`Style` Pydantic model) regardless of source format. Schema is stable across V1 and is the integration contract for V∞ convergence with `presenton-pixi-image`'s `template-style-extractor`.

### Diagrams & Charts

- **FR-16:** A user can include a Mermaid block in their input or prompt; deckcraft renders it via `mermaid-py` + headless `playwright` (offline) and embeds the SVG.
- **FR-17:** Embedded Mermaid SVGs are convertible to native PowerPoint shapes (PowerPoint's "Convert to Shape" feature works on the embedded SVG).
- **FR-18:** A user can request a chart of a given type (bar / line / scatter / pie / etc.) with structured data; deckcraft uses `matplotlib` (or `plotly` for interactive HTML output) to render it, embedding as a native PowerPoint chart where the data fits a standard chart type.

### Image Operations

- **FR-19:** A user can request a generated image for a slide; deckcraft uses `diffusers` + SDXL-Turbo on the available device (CPU / MPS / CUDA / ROCm) to produce the image and embed it. **V1 with opt-in default-off**: enabled via `--enable-image-gen` CLI flag or `image_gen.enabled = true` in config. SDXL-Turbo weights are lazy-pulled on first use, not at `deckcraft init` time, so users who never enable image gen pay zero download cost.
- **FR-20:** A user can pass an image-generation prompt explicitly per slide via the slide JSON / Marp markdown directive (overrides the LLM's auto-generated image prompt).
- **FR-21:** A user can pass an existing image (PNG / JPG / SVG) as input and deckcraft describes it via the configured vision LLM (Ollama `qwen2.5vl` family or `llama-server --mmproj`).
- **FR-22:** A user can request that the LLM use the image description as additional context when generating slide content for the relevant slide.

### Cross-Platform Operation

- **FR-27:** Deckcraft runs identically on `linux-64`, `osx-arm64`, and `win-64`.
- **FR-28:** Deckcraft uses `platformdirs` for all model cache, config, and log paths (no Linux-isms).
- **FR-29:** Deckcraft auto-detects the host platform's GPU acceleration availability (Metal on macOS; ROCm/CUDA on Linux/Windows where present) and routes diffusion + LLM workloads accordingly.
- **FR-30:** Generated `.pptx` files from the same prompt + tier are structurally byte-equivalent across platforms (only LLM text content varies due to non-determinism).

### Configuration & Setup

- **FR-31:** A user runs `deckcraft init` and the tool auto-detects RAM + platform + available GPU and recommends a hardware tier (small / medium / large).
- **FR-32:** A user can override any auto-detected setting via a config file (`platformdirs.user_config_dir("deckcraft")/config.toml`) or environment variables.

### LLM Backend Adapter

- **FR-33:** Deckcraft talks to any OpenAI-compatible HTTP endpoint via `pydantic-ai`.
- **FR-34:** Default backend is `llama-server` from conda-forge (started on demand by deckcraft); alternative backends (Ollama, `mlx-lm`, Azure OpenAI, GitHub Models, Anthropic, custom OpenAI-compat) are selectable via config.

### CLI Surface

- **FR-35:** A user can run `deckcraft generate --input <path> --out <path>` to produce a deck.
- **FR-36:** A user can run `deckcraft init` to perform first-run setup.
- **FR-37:** A user can run `deckcraft describe-image --input <path>` to get a vision-LLM description of an image.
- **FR-38:** A user can run `deckcraft convert --input deck.pptx --to marp` to round-trip a deck through Marp markdown.

### MCP Server Surface

- **FR-39:** A user (or an AI assistant on their behalf) can invoke deckcraft as an MCP server (stdio transport) and call exposed tools (`generate_deck`, `describe_image`, `extract_document`, `render_chart`, `render_diagram`).
- **FR-40:** MCP tool schemas are auto-generated from Pydantic types; documentation strings on Python functions surface as tool descriptions.

### Distribution Surfaces

- **FR-41:** Claude Code users in this repo can invoke `.claude/skills/deck-builder/` and the skill routes to `pixi run -e local-recipes deckcraft generate ...`.
- **FR-42:** Anyone with conda + conda-forge channel access can install deckcraft via `conda install -c conda-forge deckcraft`.

---

## Non-Functional Requirements

### Performance

- **NFR-01:** First-token latency for LLM-generated outline ≤ 3 seconds (large tier on CPU; faster tiers proportionally).
- **NFR-02:** End-to-end deck generation (10 slides, no images) ≤ 10 minutes on large tier CPU; ≤ 4 minutes on medium tier with Metal/MLX; ≤ 15 minutes on small tier CPU.
- **NFR-03:** PPTX rendering (separated from LLM time) ≤ 5 seconds for a 10-slide deck on any tier.
- **NFR-04:** Mermaid diagram render ≤ 3 seconds per diagram via headless `playwright`.
- **NFR-05:** First-run model download via `hf-transfer` is at least 3× faster than baseline `huggingface_hub` download.
- **NFR-22:** Image generation (when opt-in flag is enabled) completes per image: ≤ 60 s on small/large CPU tiers, ≤ 15 s on medium tier (M4 with MPS). Failure is non-fatal per FR-26.
- **NFR-23:** When a user-supplied `Style` source (`.potx`, `.pptx`, `.docx`, `.pdf`, or stretch `.odp`/`.odt`) is provided, the generated deck visually matches the source: brand colors, fonts, logos, footers, and page numbers in the output match the source. Acceptance: side-by-side visual inspection on a corpus of 5 `.potx` templates, 3 `.pptx`-as-sample inputs, 3 `.docx` style guides, 3 `.pdf` brand guides (including 1 scanned PDF requiring OCR fallback), and 2 `.odp`/`.odt` files (stretch — only if FR-46d is in scope at acceptance gate).

### Reliability

- **NFR-06:** A failed image generation (e.g., out-of-memory) does not crash the pipeline; the slide ships with a placeholder + sidecar warning.
- **NFR-07:** A failed LLM call (e.g., backend unavailable) returns a structured error with a suggested next step; deckcraft does not silently produce a broken deck.
- **NFR-08:** All V1 features verified to work in `unshare -n` (network-isolated) environment via CI test.

### Cross-Platform Parity

- **NFR-09:** CI runs the golden-path fixture suite on linux-64, osx-arm64 (when available), and win-64; structural diff of generated `.pptx` files must match.
- **NFR-10:** Font rendering uses the DejaVu family (already in env) for cross-platform consistency; templates may override per-platform.

### Air-Gapped Operation

- **NFR-11:** Default mode makes zero outbound network connections after first-run model download.
- **NFR-12:** All conda-forge dependencies are pre-mirrorable to internal Artifactory / JFrog; deckcraft documentation includes the air-gapped install procedure.
- **NFR-13:** Model artifacts are pre-downloadable to a local cache; `DECKCRAFT_MODEL_DIR` env var lets users point at a pre-populated directory.

### Output Editability

- **NFR-14:** 100% of text content in generated `.pptx` files is editable in Microsoft PowerPoint (selectable, font-changeable, color-editable, content-modifiable).
- **NFR-15:** 100% of shape and chart content is rendered as native DrawingML; zero rasterized content in the output unless the user explicitly enabled image generation.

### Distribution & Setup Friction

- **NFR-16:** A new user can go from `pixi install` to first generated deck in ≤ 30 minutes (including one-time GGUF model download).
- **NFR-17:** `deckcraft init` succeeds on a clean install and produces a working test deck on all three platforms.

### Security & Compliance

- **NFR-18:** Deckcraft does not exfiltrate input documents to any external service in default mode.
- **NFR-19:** Cloud LLM/image/vision adapters (opt-in only) explicitly log when they are about to make an outbound call, and respect a `DECKCRAFT_OFFLINE=1` environment variable that hard-blocks any outbound network even when adapters are configured.

### Maintenance

- **NFR-20:** Deckcraft's per-week maintenance burden does not exceed 1 hour for the requester (kill-criteria-aligned).
- **NFR-21:** All conda-forge dependency drift is caught by `pixi-outdated` (already in env); deckcraft pins minimum versions, not exact versions.

---

## Open Questions (carried forward to architecture phase)

These were surfaced during brief + distillate creation and remain unresolved at PRD-completion gate. They must be resolved in `bmad-create-architecture` before story breakdown begins.

1. **Corporate template for V1 — RESOLVED:** BYO via FR-45/46/47/48. Users provide their organization's `.potx`, `.pptx`, or `.docx` and deckcraft applies it. V1 ships `default-professional.potx` as the no-style fallback and `bmad-prd-pitch.potx` for J6. No employer-specific template hand-coding required.
2. **GGUF model selection per tier:** specific HuggingFace repos and quantizations per tier (small / medium / large) — confirm before model-pull stories begin.
3. **MCP HTTP transport — V1 or V2?** Currently V2 in this PRD. Earlier promotion if MS365 path is pursued.
4. **`pptx-assembler` reuse from `presenton-pixi-image`:** pull as a dependency, fork, or wait for convergence? Affects S-15 (recipe) timing.
5. **Performance benchmark cadence:** when does the architecture phase produce the first real-hardware benchmark on each of the three reference machines?
6. **`python-pptx` vendor trigger:** what specific issue/feature would cause us to vendor patches from `OscarPellicer/python-pptx`? (Default: react when blocked, not preemptively.)
7. **NVIDIA path on Windows:** opt-in pixi feature using the `pytorch` channel — V1 documented or V2 added?
8. **MLX backend selection logic:** when does the LLM adapter prefer `mlx-lm` over `llama.cpp` on osx-arm64? Default proposal: prefer mlx-lm if model has an MLX-format weight available; fall back to llama.cpp GGUF otherwise.
9. **VS Code extension distribution:** Marketplace publish vs. VSIX-only sideload — affects V2 timeline.
10. **Embedding model selection for FR-43:** default proposal is `all-MiniLM-L6-v2` (English-leaning, fast, 80 MB). For multilingual decks: `paraphrase-multilingual-MiniLM-L12-v2` (~120 MB). Architecture phase confirms which ships in V1's `deckcraft init` flow.
11. **RAG threshold tuning:** default 16K-token threshold for FR-43 may be too aggressive for the small tier (qwen3:8b at 32K context) or too lax for the medium tier. Architecture phase sets per-tier defaults.
12. **`Qwen3-VL-Embedding` evaluation for V2+ (verified 2026-05-09):** real, two sizes — `Qwen/Qwen3-VL-Embedding-2B` (popular, ~2.3M downloads) and `Qwen/Qwen3-VL-Embedding-8B` (~1.5M downloads), Apache-2.0, GitHub repo last updated 2026-04-08. Multimodal: combines image + text understanding into one vector space. Could replace `sentence-transformers/all-MiniLM-L6-v2` (text RAG, 80 MB) AND parts of `qwen2.5-vl` (vision LLM, 3-6 GB) workflow with a single model (~1.5–6 GB depending on size). Unlocks cross-modal retrieval ("find slides whose text or image matches this prompt"). V1 sticks with the dual-stack for simplicity; **V2 should evaluate the 2B variant** as a unified replacement for the embedding + vision-understanding paths.
13. **`Qwen3-Embedding` (text-only) for V2+:** the text-only Qwen3-Embedding family also exists in 0.6B / 4B / 8B sizes with GGUF quantizations (usable via llama-server). Larger than MiniLM but multilingual and higher quality. V2 could replace MiniLM with `Qwen/Qwen3-Embedding-0.6B-GGUF` (~400 MB) for better embedding quality at modest cost.

---

## Recommended Model Stack (V1 ship-list)

The complete set of model artifacts deckcraft downloads at first-run setup. **All air-gappable** — pre-downloadable to a local cache and deployable via `DECKCRAFT_MODEL_DIR` (DR-03). Total disk varies by tier; see per-tier rollups below.

### Per-tier model defaults

| Role | Tier `small` (32 GB Win) | Tier `medium` (48 GB M4) | Tier `large` (64 GB Linux) |
|---|---|---|---|
| **Text generation** (outline + slide content) | `qwen3:8b-instruct-q4_k_m` (~5 GB) | `qwen3:14b-instruct-q4_k_m` (~9 GB) | `qwen3:30b-instruct-q4_k_m` (~17 GB) |
| **Code generation** (chart code, mermaid syntax, JSON-schema-conformant output) | `qwen2.5-coder:7b-instruct-q4_k_m` (~5 GB) | `qwen2.5-coder:14b-instruct-q4_k_m` (~9 GB) | `qwen3-coder:30b-instruct-q4_k_m` (~17 GB) |
| **Vision** (image understanding for J4) | `qwen2.5-vl:3b-instruct-q4_k_m` + mmproj (~3 GB) | `qwen2.5-vl:7b-instruct-q4_k_m` + mmproj (~6 GB) | same as medium (~6 GB) |
| **Embeddings** (RAG for FR-43, dedup for FR-44) | `sentence-transformers/all-MiniLM-L6-v2` (~80 MB) | same | same (multilingual variant `paraphrase-multilingual-MiniLM-L12-v2` ~120 MB optional) |
| **Image generation** (V1, opt-in default-off; lazy-loaded on first use for J3) | `stabilityai/sdxl-turbo` (~7 GB) | same | same |

### Tier disk totals

V1 default-install (image gen NOT enabled — SDXL-Turbo lazy-loaded only when user opts in):

| Tier | V1 footprint (text + code + vision + embeddings) | + image gen if user opts in (lazy pull) |
|---|---|---|
| small | ~13 GB | ~20 GB |
| medium | ~24 GB | ~31 GB |
| large | ~40 GB | ~47 GB |

### Backend mapping per platform

| Platform | LLM serve mechanism | Notes |
|---|---|---|
| Linux 64-bit | `llama-server` (CPU on Framework today; ROCm on healthy AMD or CUDA on NVIDIA via opt-in pixi feature) | Default. `mlx-lm` available as alternative experimental runner |
| macOS osx-arm64 | `llama-server` (auto-detects Metal) **OR** `mlx-lm` (preferred when an MLX-format weight is available; ~2–3× over llama.cpp Metal) | M-series only |
| Windows 64-bit | `llama-server` (CPU; CUDA opt-in via separate pixi feature) | MLX not available (upstream skip rule) |

### Where to download

All weights are HuggingFace artifacts. First-run setup via `hf-transfer` (3× faster than baseline). Specific repo IDs:

| Model | HuggingFace repo (or family) |
|---|---|
| Qwen3 GGUF (text) | `Qwen/Qwen3-{8B,14B,30B}-Instruct-GGUF` (Q4_K_M variant) |
| Qwen2.5-Coder GGUF | `Qwen/Qwen2.5-Coder-{7B,14B}-Instruct-GGUF` (Q4_K_M) |
| Qwen3-Coder 30B GGUF | `Qwen/Qwen3-Coder-30B-Instruct-GGUF` (Q4_K_M) |
| Qwen2.5-VL GGUF + mmproj | `Qwen/Qwen2.5-VL-{3B,7B}-Instruct-GGUF` (Q4_K_M) — vision model + separate mmproj projector file |
| Sentence-Transformers (embeddings) | `sentence-transformers/all-MiniLM-L6-v2` (default); `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (multilingual) |
| SDXL-Turbo (image gen, V2) | `stabilityai/sdxl-turbo` (FP16 safetensors) |

### Air-gapped distribution

For air-gapped deployment:
1. On a connected machine, run `deckcraft init --tier <small|medium|large>` to download the tier's full model set into `~/.cache/deckcraft/models/` (or `DECKCRAFT_MODEL_DIR` if set).
2. `tar` the cache directory and transfer via approved method (USB, internal mirror, etc.).
3. On the air-gapped target, untar to the same path. Set `DECKCRAFT_OFFLINE=1`.
4. Run `deckcraft generate ...` — no outbound network calls.

Total air-gap transfer per tier (V1 only, no image gen): ~13 / 24 / 40 GB respectively.

### Optional / future additions to the stack (not V1)

- **`Qwen/Qwen3-VL-Embedding-2B`** (verified 2026-05-09; Apache-2.0; ~2.3M HF downloads; GitHub repo updated 2026-04-08) — multimodal embedding model unifying image + text in one vector space. Could subsume both `sentence-transformers/all-MiniLM-L6-v2` (text RAG, 80 MB) and parts of `qwen2.5-vl` (vision LLM, 3-6 GB) into a single model (~1.5 GB at Q4). **V2 evaluation target** per Open Question 12. Unlocks cross-modal retrieval ("find slides whose text or image matches this prompt"). 8B variant exists for higher quality.
- **`Qwen/Qwen3-Embedding-0.6B-GGUF`** — text-only Qwen3 embedding, 0.6B params, multilingual, GGUF format usable through llama-server. Larger than MiniLM (~400 MB vs 80 MB) but better quality and multilingual. V2 candidate for text-RAG upgrade per Open Question 13.
- **`mlx-community/<model>-mlx-q4`** — MLX-format weights for osx-arm64; required if `mlx-lm` backend is preferred over llama.cpp Metal (per FR-34). Downloaded only on macOS in `deckcraft init`.
- **FLUX.1-schnell or SD3.5** — better image generation quality than SDXL-Turbo, requires `sentencepiece` (already in env). V3 if image gen becomes a heavily-used workflow that benefits from photorealism upgrade.

---

## References

- Product brief: `_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft.md`
- Distillate: `_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft-distillate.md`
- Sibling project PRD: `_bmad-output/projects/presenton-pixi-image/planning-artifacts/prd.md`
- VS Code extension spec (V2 reuse): `docs/specs/copilot-bridge-vscode-extension.md`
- Pixi env state: `pixi.toml` (deckcraft additions section + osx-arm64 mlx target deps)
- BMAD ↔ conda-forge-expert integration rules: `CLAUDE.md`
- python-pptx (engine): https://github.com/scanny/python-pptx (1.0.2, MIT, dormant since 2024-08-07)
- pptx2marp (code reference): https://github.com/OscarPellicer/pptx2marp (Apache-2.0)
- python-pptx fork (selective patch source): https://github.com/OscarPellicer/python-pptx (Apache-2.0)

---

*PRD complete. Next workflow: `bmad-validate-prd` (gate) → `bmad-create-architecture` → `bmad-create-epics-and-stories` → `bmad-check-implementation-readiness` → `bmad-sprint-planning` → `bmad-generate-project-context`.*
