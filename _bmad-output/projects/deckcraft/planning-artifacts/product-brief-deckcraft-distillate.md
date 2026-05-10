---
title: "Product Brief Distillate: deckcraft"
type: llm-distillate
source: "product-brief-deckcraft.md"
created: "2026-05-09"
purpose: "Token-efficient context for downstream PRD creation"
---

# Distillate — deckcraft

Detail captured during the 2026-05-09 scoping session that goes beyond the executive summary. Optimized for direct consumption by `bmad-create-prd`.

## Locked-in technical decisions (do not re-discover)

- **Default LLM backend: `llama-server`** (llama.cpp, conda-forge native). Stateless, OpenAI-compat, model-on-demand. Already at `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/.pixi/envs/local-recipes/bin/llama-server`.
- **Optional LLM backend: Ollama.** Currently running as systemd service at `/usr/local/bin/ollama` on `127.0.0.1:11434`, holding 5 user-curated models (`qwen3:30b`, `qwen3-coder:latest`, `JetBrains/Mellum-4b-sft-python:latest`, `llama3.1:8b`, `gemma3n:latest`). Kept because the requester's IDE clients (PyCharm, Cursor, Antigravity, Copilot LSP) hit it.
- **LLM adapter abstraction: `pydantic-ai`** (already in env at v1.61.0). Talks OpenAI-compat HTTP. Backend-swappable via single endpoint config.
- **Vision model: Ollama `qwen2.5vl:7b`** (~6 GB, to be pulled). Llama.cpp `--mmproj` is documented alternative, deferred unless Ollama removed.
- **Image generation: `diffusers` + SDXL-Turbo** (Q4 weights, ~7 GB). CPU-only on requester's hardware (~30–60s/image). **Deferred to V2** — not in V1 scope.
- **Editable PPTX engine: `python-pptx`** (v1.0.2 on conda-forge). Native DrawingML output (text boxes, autoshapes, native charts) is non-negotiable.
- **Marp engine: `marp-cli`** (v4.2.3 on conda-forge, Node-based but conda-packaged). Markdown is the editable source format; pptx export from Marp is image-based, so the deckcraft pipeline keeps the markdown as the round-trip surface.
- **Diagram rendering: `mermaid-py` + `playwright-python`** (both on conda-forge). Headless Chromium with bundled mermaid.js for fully-offline rendering. Avoids `mermaid-cli` (`mmdc`) which is NOT on conda-forge.
- **Chart rendering: `matplotlib` + `plotly`** (added in this session).
- **Document ingestion: `markitdown`** (v0.1.5, Microsoft, on conda-forge). Handles PDF/DOCX/PPTX/XLSX/HTML/etc. via local libs.
- **MCP server: `fastmcp`** (v3.2.4, on conda-forge — requester maintains the feedstock).
- **CLI: `typer`** (v0.25.1 on conda-forge).
- **Active project: `deckcraft`** in BMAD multi-project pattern at `_bmad-output/projects/deckcraft/`. Active marker set 2026-05-09.

## Rejected approaches (don't re-propose)

- **Cloud image gen** (fal.ai, Replicate, DALL-E, Together): rejected — air-gapped requirement.
- **Cloud vision** (Claude vision API, GPT-4V, Gemini Vision): rejected — air-gapped requirement.
- **Cloud LLM as default** (Claude API, OpenAI): allowed only as documented opt-in alternative; default must be local.
- **Separate `deckcraft` pixi env**: rejected — 104 of 109 needed packages already in `local-recipes`; adding 5 lines was the minimal-disruption path.
- **`litellm` in `local-recipes` env**: rejected — hard-pins `pydantic==2.12.5`, conflicts with env's `pydantic>=2.13.4`. Deferred to a separate env if/when the conda-forge feedstock relaxes the pin (the requester's `behind-upstream` tooling could open the PR).
- **Marp's pptx output as the editable surface**: rejected — image-based, not editable. Marp's value is the markdown source; pptx editability comes from `python-pptx`.
- **`mermaid-cli` (`mmdc`) Node binary**: NOT on conda-forge; rejected. Replaced by `mermaid-py` + `playwright-python`.
- **`gemma4` for laptop use**: rejected during model curation — smallest variant is 26B (~16 GB), too heavy. `gemma3n` (~7 GB) is Google's actual laptop variant and was used instead.
- **`llama4:maverick`** (228 GB): removed during model cleanup — won't fit in 64 GB RAM (MoE 400B requires ~250 GB at Q4_K_M).
- **Ollama as the primary backend for deckcraft itself**: deprioritized in favor of llama-server (purer conda-forge stack), though Ollama remains the documented optional backend.

## Requirements hints surfaced

- Output PPTX must open clean in Microsoft PowerPoint (not just LibreOffice). Native DrawingML is the test.
- Marp markdown source must round-trip: deckcraft can author it, and a hand-edited version can be re-rendered by Marp without breaking.
- Templates: corporate / technical / pitch / academic. Corporate template should match the requester's actual employer brand on day 1 (V1 stretch — this is a sticky-adoption lever).
- BMAD artifact ingestion: deckcraft accepts `prd.md` / `epics.md` / `architecture.md` as input. "Make a deck from this PRD" is built-in.
- Notebook surface: `pixi-kernel` is in env, so deckcraft is importable from Jupyter. Free adjacent surface.
- Air-gapped means: no `huggingface_hub` calls at runtime (model files must be pre-downloaded and present locally).
- VS Code extension wave reuses `docs/specs/copilot-bridge-vscode-extension.md` (existing 12-story spec) as a basis, not greenfield.
- MS365 Copilot connector: gated on tenant admin, not a V1/V2 commitment.
- Conda-forge recipe at `recipes/deckcraft/` invokes `conda-forge-expert` skill per CLAUDE.md Rule 1; followed by retro per Rule 2.

## Hardware / runtime context — three reference machines

Cross-platform support is V1 scope. The pixi env declares `linux-64`, `osx-arm64`, `win-64`; every dep has builds for all three.

### Tier definitions (drives V1 model defaults and `deckcraft init` auto-suggestion)

| Tier | RAM target | Default text | Default code | Default vision | Image gen |
|---|---|---|---|---|---|
| **small** | 16–32 GB | qwen3:8b or llama3.1:8b (~5 GB) | qwen2.5-coder:7b (~5 GB) | qwen2.5vl:3b (~3 GB) | opt-in only |
| **medium** | 32–48 GB | qwen3:14b (~9 GB) | qwen2.5-coder:14b (~9 GB) | qwen2.5vl:7b (~6 GB) | enabled |
| **large** | 48 GB+ | qwen3:30b (~17 GB) | qwen3-coder:30b (~17 GB) | qwen2.5vl:7b (~6 GB) | enabled |

V1 ships `small` as default — works on all three reference machines below. `deckcraft init` auto-detects RAM and suggests upgrading.

### Reference machines

- **Framework Laptop 16 (Linux, 64 GB) — large tier.** AMD Ryzen 7 7840HS (8C/16T Zen 4), DDR5-5600, integrated Radeon 780M (Phoenix1, gfx1103). Ubuntu 24.04, kernel 6.17.0-23. **GPU compute path BROKEN** — AMD MES firmware (`gc_11_0_4_mes*.bin`, March 2024 vintage) hangs under sustained compositor + Electron/JCEF load. Three system crashes during the session. Until kernel 6.18+ or newer linux-firmware lands, deckcraft is CPU-only on this machine; ~10× speedup expected once fixed. Memory bandwidth ~90 GB/s (DDR5-5600).
- **MacBook Pro M4 (macOS, 48 GB) — medium tier.** Apple Silicon (ARM64), unified memory, Metal Performance Shaders + Neural Engine. `llama-server` from conda-forge auto-detects Metal — no config needed. `diffusers` natively supports MPS backend (`pipe.to("mps")`). Best perf-per-watt of the three machines for AI workloads. **`mlx-lm` IS on conda-forge** (added to env at v0.31.3 alongside `mlx 0.31.2` for `linux-64` + `osx-arm64` targets) — gives 2–3× over llama.cpp+Metal for some workloads. Future further optimization: deeper MLX integration as a dedicated backend module (V2+).
- **Windows 11 laptop (32 GB) — small tier (V1 default).** Tightest RAM budget — drives V1 model defaults. After Windows + IDE + browser overhead, ~22 GB free for AI workloads. Backend: `llama-server` from conda-forge (CPU). NVIDIA path: `pytorch-cuda` is NOT on conda-forge (lives in `pytorch` channel) → opt-in via separate pixi feature, documented but not bundled. Vulkan support in llama.cpp (would help non-NVIDIA Windows GPUs) is a V2 investigation.

### Realistic LLM speeds (CPU-only, large tier example)

qwen3:30b ~3–5 tok/s; qwen3-coder ~3–5 tok/s; llama3.1:8b ~10–15 tok/s; gemma3n ~10–15 tok/s. M4 with Metal: roughly 5–10× faster than Ryzen CPU on equivalent model size.

### Per-platform paths (use `platformdirs` from conda-forge)

| Platform | Model cache | Config | Logs |
|---|---|---|---|
| Linux | `~/.cache/deckcraft/models/` | `~/.config/deckcraft/` | `~/.local/state/deckcraft/` |
| macOS | `~/Library/Caches/deckcraft/models/` | `~/Library/Application Support/deckcraft/` | `~/Library/Logs/deckcraft/` |
| Windows | `%LOCALAPPDATA%\deckcraft\models\` | `%APPDATA%\deckcraft\` | `%LOCALAPPDATA%\deckcraft\logs\` |

### Cross-platform gaps to document (not blockers)

- `pytorch-cuda` not on conda-forge → Windows NVIDIA users need a separate pixi feature with the `pytorch` channel
- `mlx` and `mlx-lm` ARE on conda-forge — installed for `linux-64` + `osx-arm64` via per-target deps. Skipped on `win-64` (upstream conda-forge `mlx` recipe has `skip: "win or ... or (osx and x86_64)"` — Apple framework, no Windows build exists). Primary value on osx-arm64 (Metal acceleration); on linux-64 it runs against libblas/lapack with no perf advantage over the existing pytorch path.
- Vulkan-enabled llama.cpp builds → could be a build-flag PR to the conda-forge `llama.cpp` feedstock
- Playwright Chromium binaries → platform-specific download per machine (one-time, air-gappable via `PLAYWRIGHT_DOWNLOAD_HOST` mirror)
- Fonts → V1 templates use DejaVu family (present on all platforms via conda-forge's font packages); platform-native fonts (Calibri/Helvetica/etc.) are per-template overrides
- macOS minimum bumped to 14.5 (Sonoma) for the local-recipes env — required by `mlx 0.31.2+`. M-series users always above this; affects only ancient Intel Macs (which are already excluded by mlx's skip rule).

## Detailed user scenarios

The 5 jobs to be done (carry through to PRD as use cases):
1. "Turn this PDF/prompt into a draft slide deck I can hand-edit in PowerPoint."
2. "Add an infographic / flowchart / chart to slide N — make it editable, not a screenshot."
3. "Generate a hero image for the cover slide" (degrades gracefully when not feasible).
4. "Read this image and explain what's in it" (vision-language for ingesting existing visuals).
5. "Convert this deck back to Marp markdown so I can edit and re-render it."

Sixth (added during review): "Turn this BMAD PRD into a stakeholder pitch deck."

## Reference projects (study, attribute, vendor selectively — not runtime deps)

- **`scanny/python-pptx`** (the canonical PPTX engine, MIT). Latest release **1.0.2 on 2024-08-07** — dormant for 21+ months, 444 open issues, 85 open PRs, no public maintainer statement. **V1 dependency from conda-forge.** Stable for current use; deckcraft wraps all calls behind a thin `pptx_engine` adapter so vendor-and-patch is a clean fallback if a critical bug or PowerPoint format change requires it. No fork is created upfront.
- **`OscarPellicer/pptx2marp`** (Apache-2.0). PPTX → Marp converter. Reference for: PPTX↔Marp element mapping table (which PPTX shape types map to which Marp directives), automatic multi-column layout heuristics, content-density font scaling classes (small/smaller/smallest), table-with-merged-cells handling, equation parsing as LaTeX, image cropping preservation, presenter-notes handling. **Not a runtime dep** — it depends on `OscarPellicer/python-pptx` (personal fork, not on conda-forge) and goes the wrong direction for deckcraft. **Used as design reference; selective code adaptation under attribution.**
- **`OscarPellicer/python-pptx`** (Apache-2.0 fork of scanny/python-pptx). Adds equation parsing + TIFF support that upstream lacks. **Not a runtime dep** (personal fork, not on conda-forge). **Vendored selectively** when deckcraft needs equation rendering or TIFF input handling. Long-term: contribute these features back to upstream as PRs.

Pattern: build on the latest upstream (1.0.2), wrap behind an adapter, vendor specific patches when needed, contribute fixes back when worthwhile. Avoids both the "personal fork dependency" trap and the "build everything from scratch" trap.

## Competitive intelligence

- **Gamma, Beautiful.ai, Copilot Pages, SlidesGPT, GammaApp**: cloud-only, fail air-gapped requirement.
- **Presenton** (`github.com/presenton/presenton`): turnkey self-hostable web app, image-overlay-based pptx output (not native shapes today), heavy stack (Next.js + FastAPI + Electron + LibreOffice). Being repackaged in this repo as `presenton-pixi-image` to replace opaque components with conda-forge-native equivalents (`presenton-export-node`, `pptx-assembler`, `template-style-extractor`). **Convergence with deckcraft is the V∞ endgame** — shared `pptx-assembler` library would benefit both.
- **`hugohe3/ppt-master`** (14k★): claims native-shape editable pptx, primary backend Claude/GPT/Gemini, no Ollama support, pip install. Tool-invocation model (called by AI agents). Architectural precedent for "native shapes via python-pptx" approach.
- **`marp-team/marp-cli`** itself: markdown-based, well-established, conda-forge packaged.
- **JetBrains AI Assistant**: uses `JetBrains/Mellum-4b-sft-python` model locally (already in user's Ollama). Doesn't generate decks but shows the local-AI-from-IDE pattern.

## Conda-forge dependency verification (all confirmed present 2026-05-09)

Already in `local-recipes` env: `python-pptx`, `python-docx`, `pdfplumber`, `markitdown`, `pymupdf`, `pypdf`, `openpyxl`, `pillow`, `lxml`, `mermaid-py`, `pandoc`, `marp-cli`, `pdf2image`, `poppler`, `qpdf`, `tesseract`, `d2`, `diffusers`, `safetensors`, `huggingface_hub`, `tokenizers`, `pytorch` (2.10.0), `mcp`, `fastmcp`, `ollama` (Go server), `pydantic-ai`, `pydantic`, `typer`, `httpx`, `anthropic`, `claude-agent-acp`, `github-copilot-sdk`, `langchain-anthropic`, `langchain-mcp-adapters`, `a2a-sdk`, `llama.cpp`, `nodejs`, `playwright` (Node), `defusedxml`.

Added in this session (cross-platform, all targets): `matplotlib`, `plotly`, `transformers`, `accelerate`, `playwright-python`, `ollama-python`, `hf-transfer`, `sentencepiece`, `sentence-transformers`. All install + import verified.

Added in this session (linux-64 + osx-arm64 target only — Windows excluded by upstream `mlx` skip rule): `mlx 0.31.2`, `mlx-lm 0.31.3`. Required `[feature.local-recipes.system-requirements] macos = "14.5"` (mlx 0.31.2+ minimum).

Deferred (commented in pixi.toml): `litellm` — hard-pins `pydantic==2.12.5`, conflicts with env's `pydantic>=2.13.4`. Add when conda-forge feedstock relaxes the pin.

Available on conda-forge but NOT in env (potential future adds): `weasyprint` (HTML→PDF, not needed since Marp handles PDF), `llama-cpp-python` (in-process inference vs. server subprocess — useful if deckcraft wants to skip the subprocess overhead).

NOT on conda-forge: `mermaid-cli` (the Node `mmdc` binary). Replaced by `mermaid-py` + `playwright-python` headless rendering. No recipe needs to be authored.

Conflicts: `litellm` 1.83.14 hard-pins `pydantic==2.12.5`, conflicts with env's `pydantic>=2.13.4`. Documented as future work.

## Surface distribution priorities (V1 scope locks)

V1 IN: Claude Skill (`.claude/skills/deck-builder/`), MCP server stdio (fastmcp), CLI (typer), conda-forge recipe.
V1 STRETCH: Corporate template matching requester's brand.
V2: VS Code extension (reuses `copilot-bridge-vscode-extension.md` spec), image gen (SDXL-Turbo opt-in), template library expansion, MCP HTTP transport.
V3: MS365 Power Platform connector (gated on tenant admin), LiteLLM routing.
DEFERRED INDEFINITELY: Real-time collaboration, web UI (Presenton's territory), notebook generation (decks specifically).

## Open questions (carry into PRD)

- **What corporate template?** The requester needs to identify which employer brand template to ship in V1 (or fall back to a generic "professional" template). Affects sticky-adoption.
- **GGUF model selection per tier.** Specific GGUF artifacts to download per hardware tier. small: Qwen3-8B-Instruct-Q4_K_M, Qwen2.5-Coder-7B-Instruct-Q4_K_M, Qwen2.5-VL-3B-Instruct-Q4_K_M + mmproj. medium: same family at 14B. large: 30B class. Author should confirm exact HuggingFace repos before the dev wave starts.
- **MCP HTTP transport — V1 or V2?** Brief currently says V2; if the MS365 path is pursued earlier, HTTP becomes V1.
- **`pptx-assembler` reuse from `presenton-pixi-image`**: pull it in as a dep, fork it, or wait for convergence?
- **Performance benchmark cadence.** When does the architecture phase produce the first real-hardware benchmark on each of the three reference machines?
- **VSCode marketplace publish vs. VSIX-only**: extension distribution model TBD.
- **`python-pptx` vendor trigger:** what specific issue/feature would cause us to vendor patches from `OscarPellicer/python-pptx`? Default: react when blocked, not preemptively. Worth a single sentence in the PRD's risk section.
- **NVIDIA path on Windows:** opt-in pixi feature using the `pytorch` channel for CUDA — V1 documented or V2 added?
- **MLX backend selection logic on osx-arm64:** when does the LLM adapter prefer mlx-lm over llama.cpp? Default: prefer mlx-lm if model has an MLX-format weight available; fall back to llama.cpp GGUF otherwise. Architecture phase to formalize.

## Architecture phase priorities (for `bmad-create-architecture`)

1. **Layered design**: core renderers / engine adapters / LLM adapters / surface adapters / data model.
2. **Data model**: `Deck`, `Slide`, `Theme`, `Asset`, `LayoutHint`, `HardwareTier` Pydantic types. Stable JSON schema for LLM-to-renderer handoff.
3. **`pptx_engine` adapter** (new module): wraps `python-pptx` 1.0.2 calls. All renderers depend on this adapter, never `import pptx` directly. Vendor swap = update one module, not 50 files. Reference: `OscarPellicer/pptx2marp`'s element-mapping logic, applied in inverse.
4. **LLM adapter pattern via `pydantic-ai`**: provider field + endpoint URL drives behavior; no per-provider code. Backend auto-selection: Metal on macOS, CPU/Vulkan on Linux, CPU/CUDA on Windows.
5. **Renderer registry**: pluggable by output format (`pptx`, `marp`, `html`, `pdf`).
6. **Asset pipeline**: chart/diagram/image generation on-demand with content-addressed caching (avoid re-rendering same mermaid twice). Cache lives in `platformdirs.user_cache_dir("deckcraft")`.
7. **Hardware-tier auto-detection**: at first run, detect RAM + platform + GPU presence; suggest tier; persist choice to user config.
8. **First benchmark**: outline + render + 1 chart for a 5-slide deck on each of the three reference machines (Framework CPU, M4 Metal, Windows 32GB CPU). Establishes the per-tier "wall-clock" claim's credibility.
9. **Test strategy**: golden-path fixtures (5 prompts → expected slide structure) run on all three platforms in CI; LLM mocked at adapter boundary; renderers tested with deterministic input. Conda-forge build matrix gives platform coverage for free.

## Scope signals (in / out / maybe for V1)

- IN (V1): prompt-only, document-only, prompt+document inputs; pptx + marp outputs; mermaid + matplotlib charts; markitdown ingestion; Claude Skill + MCP stdio + CLI; conda recipe; image *understanding* via Ollama qwen2.5vl; **image *generation* via SDXL-Turbo as opt-in default-off (lazy-pulled weights, FR-19/FR-20)**; long-document RAG via sentence-transformers (FR-43); slide dedup (FR-44); built-in templates (FR-25, FR-51); graceful degradation of optional capabilities (FR-26); **bring-your-own style sources via `--style <path>` accepting `.potx` / `.pptx` (template or `--as-sample`) / `.docx` (Word brand guide) / `.pdf` (pymupdf extraction with pytesseract OCR fallback for scanned); legacy `.ppt`/`.doc` explicitly rejected; FR-45 through FR-52; LLM-guided layout mapping; theme colors flow through to matplotlib + mermaid + native PowerPoint charts; common `Style` JSON shape across all extractors (V∞ convergence target with `presenton-pixi-image`'s `template-style-extractor`)**.
- V2 (slipped from V1 per architecture AD-10): `.odp` / `.odt` style extraction via odfpy (FR-46d). `odfpy` already in V1 env; V2 add is module-only.
- OUT (V1): HTTP MCP transport; VS Code extension; MS365 connector; templates beyond `corporate` + `bmad-prd-pitch`; notebook surface (free but unfocused).
- V2 candidates: VS Code ext + Copilot slash command; MCP HTTP; expanded template library; LiteLLM routing (when conda-forge pin relaxes); **`Qwen/Qwen3-VL-Embedding-2B` evaluation** as unified embedding+vision replacement (verified on HuggingFace 2026-05-09; Apache-2.0; ~2.3M downloads); `Qwen/Qwen3-Embedding-0.6B-GGUF` as text-RAG upgrade.
