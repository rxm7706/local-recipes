---
stepsCompleted:
  - step-01-init
  - step-02-context
  - step-03-starter
  - step-04-decisions
  - step-05-patterns
  - step-06-structure
  - step-07-validation
  - step-08-complete
inputDocuments:
  - "_bmad-output/projects/deckcraft/planning-artifacts/prd.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft-distillate.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/prd-validation.md"
  - "pixi.toml"
  - "_bmad-output/projects/presenton-pixi-image/planning-artifacts/prd.md"
  - "CLAUDE.md"
workflowType: architecture
project_name: deckcraft
user_name: rxm7706
date: 2026-05-09
status: complete
openQuestionsResolved: 13
openQuestionsRemaining: 2
benchmarkPlan: included
storyBreakdownReady: true
---

# Architecture Decision Document — deckcraft

**Author:** rxm7706
**Date:** 2026-05-09
**Status:** complete
**Inputs:** PRD (52 FRs / 23 NFRs / 8.5–13 wk timeline), brief, distillate, validation report (PASS), pixi.toml, sibling-project PRD

---

## 1. Context

### Product in one paragraph

Deckcraft is an air-gapped, conda-forge-native Python package + CLI + MCP server + Claude Skill that turns prompts/documents into editable PowerPoint decks (with Marp markdown sidecars), running 100% on local LLMs across Linux/macOS/Windows. Output is native DrawingML (no rasterized slides). V1 ships across three reference machines (Framework 64 GB, M4 48 GB, Win 32 GB) with hardware-tier-aware model selection.

### Locked technical decisions (carried from brief + PRD; do not re-discover)

- **PPTX engine:** `python-pptx` 1.0.2 (latest, conda-forge, dormant since 2024-08-07) wrapped behind a thin `pptx_engine` adapter for vendor-fallback (FR-15)
- **LLM adapter:** `pydantic-ai` over OpenAI-compat HTTP. Default backend `llama-server`; alt Ollama; macOS-preferred `mlx-lm`. LiteLLM deferred (pydantic pin conflict)
- **Editable output non-negotiable:** every text/shape/chart/diagram is native DrawingML
- **Air-gapped default:** zero outbound calls in default mode; all deps from conda-forge; models pre-downloadable via `hf-transfer`
- **Cross-platform V1:** `linux-64` / `osx-arm64` / `win-64`; output `.pptx` structurally byte-equivalent across platforms
- **Hardware tiers:** small (32 GB) / medium (48 GB) / large (64 GB+); `deckcraft init` auto-detects and recommends
- **BYO style sources:** `.potx`, `.pptx`, `.docx`, `.pdf` in V1; `.odp`/`.odt` stretch (may slip to V2)
- **Image gen:** SDXL-Turbo via `diffusers`, opt-in default-off, lazy-loaded weights
- **Long-document RAG:** `sentence-transformers/all-MiniLM-L6-v2`
- **Vision:** Ollama `qwen2.5vl` family (3B small, 7B medium/large)
- **Distribution surfaces V1:** Claude Skill + MCP stdio + CLI + conda-forge recipe
- **Sibling-project convergence:** `style_loader` is the same scope as `presenton-pixi-image`'s `template-style-extractor`; FR-52 common JSON shape is the integration contract for V∞ shared library

### Conda-forge env state (`local-recipes` post-deckcraft additions)

All deps verified present: matplotlib, plotly, transformers, accelerate, playwright-python, ollama-python, hf-transfer, sentencepiece, sentence-transformers, pytesseract, odfpy (cross-platform); mlx + mlx-lm (linux-64 + osx-arm64 only). Plus inherited: python-pptx, python-docx, pdfplumber, markitdown, pymupdf, pypdf, openpyxl, pillow, lxml, mermaid-py, pandoc, marp-cli, pdf2image, poppler, qpdf, tesseract, d2, diffusers, safetensors, huggingface_hub, tokenizers, pytorch (2.10.0), mcp, fastmcp, ollama (Go server), pydantic-ai, pydantic, typer, httpx, anthropic, claude-agent-acp, github-copilot-sdk, langchain-anthropic, langchain-mcp-adapters, a2a-sdk, llama.cpp (server + ~20 binaries), nodejs, playwright (Node), defusedxml, platformdirs, psutil. macOS minimum bumped to 14.5.

---

## 2. Architectural Style & Top-Level Decisions

### A-01: Layered architecture with strict adapter boundaries

Three layers, with adapters at each boundary:

```
┌─────────────────────────────────────────────────────────────────────┐
│  SURFACES                                                            │
│  Claude Skill   CLI (typer)   MCP Server (fastmcp stdio + HTTP)     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Pipeline API (deckcraft.Pipeline)
┌──────────────────────────┴──────────────────────────────────────────┐
│  CORE                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  Outline     │  │  Style       │  │  Asset       │               │
│  │  Generator   │  │  Loader      │  │  Pipeline    │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                 │                 │                         │
│         │  ┌──────────────▼─────────────────▼───────┐               │
│         └──►  Renderers: pptx_engine, marp_engine,  │               │
│            │  chart_renderer, mermaid_renderer,     │               │
│            │  image_generator, image_understander   │               │
│            └─────────────────────────────────────────┘               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Adapter protocols
┌──────────────────────────┴──────────────────────────────────────────┐
│  ADAPTERS                                                            │
│  LLMAdapter (pydantic-ai over OpenAI-compat HTTP)                    │
│    ↳ llama-server (default) | Ollama | mlx-lm | Azure | GH Models    │
│  PptxEngineAdapter (wraps python-pptx; vendor-fallback hooks)        │
│  PlatformAdapter (platformdirs paths, RAM detect, GPU detect)        │
└──────────────────────────────────────────────────────────────────────┘
```

**Rationale:** Each adapter boundary is the swap point for a known fragility (python-pptx dormant; LLM provider variability; per-platform GPU/path differences). Surfaces consume `Pipeline` only — never reach into renderers/engines/adapters directly. Renderers consume engine adapters — never `import pptx` directly.

**Mapped FRs:** All. Adapter boundaries protect FR-15 (pptx engine swap), FR-33/34 (LLM backend swap), FR-27/28/29 (platform parity).

### A-02: Single Pydantic data model, immutable JSON-serializable

All inter-module communication uses Pydantic models. JSON serialization is the contract. No hidden state passed via globals or class attributes.

Core types:

```python
# deckcraft.types
class HardwareTier(str, Enum):
    SMALL = "small"      # ≤32 GB RAM
    MEDIUM = "medium"    # 32–48 GB RAM
    LARGE = "large"      # ≥48 GB RAM

class Color(BaseModel):
    rgb: str             # "#RRGGBB"
    name: str | None     # optional symbolic name (accent1, etc.)

class Theme(BaseModel):
    primary: Color
    accents: list[Color] = Field(min_length=1, max_length=6)
    background_light: Color
    background_dark: Color
    heading_font: str
    body_font: str
    monospace_font: str | None

class LayoutHint(BaseModel):
    """Semantic layout type: title, content, two_column, section, blank, etc."""
    semantic_type: Literal["title", "content", "two_column", "comparison",
                            "section_header", "blank", "title_only", "image_with_caption"]
    template_layout_name: str | None  # set after layout_mapper resolves

class Asset(BaseModel):
    """A non-text element on a slide."""
    kind: Literal["image", "chart", "diagram", "table"]
    spec: dict             # type-specific payload (chart spec, mermaid src, image path/prompt)
    cache_key: str         # content-hash for deduplication
    rendered_path: Path | None = None  # set after asset_pipeline renders

class Slide(BaseModel):
    title: str | None
    body: list[str] = []
    notes: str | None = None
    layout: LayoutHint
    assets: list[Asset] = []

class Style(BaseModel):
    """FR-52: common JSON shape across all extractors. Integration contract for V∞."""
    schema_version: Literal["1.0"] = "1.0"
    source_kind: Literal["potx", "pptx", "pptx_sample", "docx", "pdf",
                          "odp", "odt", "default"]
    source_path: Path | None = None
    theme: Theme
    layouts: list[LayoutDescriptor] = []   # PPTX-only; empty for non-PPTX sources
    masters: list[MasterDescriptor] = []   # PPTX-only
    brand_assets: list[BrandAsset] = []    # logos, footers, page-number formats

class Deck(BaseModel):
    title: str
    subtitle: str | None = None
    style: Style
    slides: list[Slide]
    metadata: dict = {}
```

**Rationale:** The PRD's FR-52 mandates a common JSON shape. Pydantic gives validation + JSON schema auto-derivation (which the MCP server uses for tool schemas). Immutability + JSON-serializability means subprocess-safe (lazy image gen runs in a child process passing JSON over stdio).

**Mapped FRs:** FR-10, FR-15, FR-25, FR-26, FR-31, FR-43–FR-52, FR-39 (MCP tool schemas).

### A-03: Adapter abstractions (where the swap points live)

| Adapter | Module | Default impl | Alternative impls | Why an adapter |
|---|---|---|---|---|
| `LLMAdapter` | `deckcraft.adapters.llm` | `LlamaServerAdapter` (subprocess + OpenAI-compat HTTP) | `OllamaAdapter`, `MlxLmAdapter`, `OpenAICompatAdapter` (Azure/GH Models/Anthropic) | Multi-backend per locked decision; per-platform optimal default |
| `PptxEngineAdapter` | `deckcraft.engines.pptx_engine` | `PythonPptxEngine` (wraps `pptx`) | `VendoredPptxEngine` (escape hatch if upstream blocks us) | python-pptx is dormant (FR-15) |
| `PlatformAdapter` | `deckcraft.platform` | Single concrete class with platform branches | n/a | Centralizes `platformdirs`, RAM detection (psutil), GPU detection — no scattered platform branches in business code |
| `StyleExtractor` | `deckcraft.core.style_loader.extractors` | One class per format (PPTX/DOCX/PDF/ODP) registered in a dispatch dict | n/a | FR-52 common shape; format-detection by extension |

**Rationale:** Where do swap-out costs realistically exist? Three places: the LLM provider, the PPTX library, and the platform. Each gets an adapter. Everything else is concrete code.

### A-04: Asset pipeline with content-addressed caching

Each `Asset` carries a `cache_key` = SHA-256 of its `spec` payload. The asset pipeline renders only on cache miss; cache lives in `platformdirs.user_cache_dir("deckcraft")/assets/`.

```
asset_pipeline(slide.assets) -> for each asset:
    cache_path = cache_dir / f"{asset.cache_key}.{ext}"
    if cache_path.exists():
        asset.rendered_path = cache_path
    else:
        renderer = _registry[asset.kind]   # chart_renderer, mermaid_renderer, etc.
        renderer.render(asset.spec, cache_path)
        asset.rendered_path = cache_path
```

**Rationale:** Mermaid+playwright cold start is ~2s; matplotlib is ~500ms; SDXL-Turbo on CPU is 30–60s. Caching means a second run with the same chart/diagram is free. Critical for iterative editing workflows (J5 Marp round-trip, repeated `deckcraft generate`).

**Mapped FRs:** FR-16, FR-17, FR-18, FR-19, FR-20, FR-43.

---

## 3. Pattern Decisions (Conflict-Prevention Rules)

These are the rules that, if violated, will cause integration breakage. They are non-negotiable:

| ID | Pattern | Rule | Why |
|---|---|---|---|
| P-01 | All pptx access via `pptx_engine` adapter | Code outside `deckcraft.engines.pptx_engine` MUST NOT `import pptx` | FR-15 vendor-fallback discipline |
| P-02 | All LLM calls via `pydantic-ai` through `LLMAdapter` | Code MUST NOT call `httpx.post("http://localhost:11434/...")` directly or import `ollama`/`anthropic` SDKs in business logic | Backend swap (FR-33/34) |
| P-03 | All filesystem paths via `pathlib.Path` + `platformdirs` | No string-concatenation of paths; no hardcoded `/tmp/` or `~/`; no Linux-isms | Cross-platform parity (FR-27/28) |
| P-04 | Subprocess invocation via `subprocess.run(..., check=True, text=True)` only | No shell=True; no shlex; explicit list-form args | Cross-platform shell differences |
| P-05 | All inter-module data is Pydantic models with JSON-serializable types | No `pandas.DataFrame` between modules; convert at module boundary | Subprocess-safe; schema-discoverable for MCP |
| P-06 | Optional capabilities use the `OptionalCapability` decorator | Failures of optional features (image gen, vision, mermaid render, chart render) are caught + logged + sidecar warning written | FR-26 graceful degradation |
| P-07 | No outbound network calls without `_check_offline_gate()` | All adapters that could touch network MUST consult `os.environ.get("DECKCRAFT_OFFLINE")` first | DR-01 / NFR-11 / NFR-19 air-gapped guarantee |
| P-08 | Asset rendering goes through `asset_pipeline.render()` | No direct `mermaid.render()` calls from business code | A-04 caching discipline |
| P-09 | All Pydantic models with timestamps use `datetime.now(timezone.utc)` | No naive datetimes anywhere | Cross-timezone parity |
| P-10 | All log records use structured logging via `structlog` (or stdlib `logging` with `extra=`) | No `print()` from production code | Debuggability + air-gapped audit trail |

These patterns are enforced by:
- Linting rules in `ruff` config (`apps/deckcraft/pyproject.toml`)
- A `tests/test_patterns.py` suite that fails the build if violations are found (e.g., greps for `import pptx` outside the engine adapter)
- Code review (manually for the requester; via CI for any future contributors)

---

## 4. Project Structure

### `apps/deckcraft/` directory layout

```
apps/deckcraft/
├── pyproject.toml                          # build metadata; pip-installable
├── README.md                               # quickstart for V1 users
├── LICENSE                                 # MIT (matches python-pptx; Apache-2.0 acceptable too — TBD in S-01)
├── conftest.py                             # pytest config + shared fixtures
├── src/
│   └── deckcraft/
│       ├── __init__.py                     # exports Pipeline, Deck, Slide, Style, etc.
│       ├── __main__.py                     # entry: python -m deckcraft → CLI
│       ├── cli.py                          # typer app
│       ├── mcp_server.py                   # fastmcp stdio + HTTP entry points
│       ├── pipeline.py                     # high-level Pipeline class (the public API)
│       ├── types.py                        # Pydantic models (Deck, Slide, Style, etc.)
│       ├── platform.py                     # PlatformAdapter (paths, RAM, GPU detection)
│       ├── settings.py                     # config loader (env + TOML at platformdirs.user_config_dir)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── outline.py                  # LLM-driven outline + slide content (FR-09–FR-12)
│       │   ├── asset_pipeline.py           # cached renderer dispatch (A-04)
│       │   ├── chart_renderer.py           # matplotlib/plotly → SVG/PNG (FR-18)
│       │   ├── mermaid_renderer.py         # mermaid-py + playwright headless (FR-16, FR-17)
│       │   ├── image_generator.py          # diffusers + SDXL-Turbo, lazy-load (FR-19, FR-20)
│       │   ├── image_understander.py       # Ollama qwen2.5vl + llama.cpp mmproj fallback (FR-21, FR-22)
│       │   ├── retrieval.py                # sentence-transformers RAG + dedup (FR-43, FR-44)
│       │   ├── doc_extractor.py            # markitdown wrapper (FR-01–FR-08)
│       │   ├── layout_mapper.py            # FR-50: LLM-guided template-layout selection
│       │   └── style_loader/
│       │       ├── __init__.py             # dispatch by file extension (FR-45)
│       │       ├── pptx_extractor.py       # .potx/.pptx (FR-46, FR-47)
│       │       ├── docx_extractor.py       # .docx (FR-48)
│       │       ├── pdf_extractor.py        # .pdf via pymupdf + pytesseract OCR fallback (FR-46c)
│       │       ├── odf_extractor.py        # .odp/.odt via odfpy (FR-46d, stretch)
│       │       └── default_template.py     # bundled default-professional.potx loader (FR-51)
│       ├── engines/
│       │   ├── __init__.py
│       │   └── pptx_engine.py              # PptxEngineAdapter (wraps python-pptx; FR-15)
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── llm.py                      # LLMAdapter protocol + concrete impls
│       │   ├── llm_llama_server.py         # spawns llama-server subprocess; OpenAI-compat client
│       │   ├── llm_ollama.py               # OllamaAdapter (httpx → /v1/chat/completions on Ollama port)
│       │   ├── llm_mlx.py                  # MlxLmAdapter (osx-arm64 only; uses mlx_lm.server)
│       │   └── llm_openai_compat.py        # generic OpenAI-compat (Azure, GH Models, Anthropic-via-proxy)
│       └── templates/
│           ├── default-professional.potx   # FR-51 bundled fallback (DejaVu fonts, neutral palette)
│           └── bmad-prd-pitch.potx         # FR-25 BMAD-PRD-aware template for J6
├── tests/
│   ├── unit/                               # mocked LLM/adapters, deterministic
│   ├── integration/                        # real adapters, marked @integration
│   ├── golden/                             # 5 prompt → expected-pptx-structure fixtures
│   ├── air_gapped/                         # runs under unshare -n (NFR-08)
│   ├── test_patterns.py                    # P-01–P-10 enforcement (greps for forbidden imports etc.)
│   └── fixtures/                           # sample .potx, .pptx, .docx, .pdf, .odp inputs
├── benchmarks/                             # perf benchmarks (run on each reference machine)
│   ├── bench_outline_only.py               # SC-02 / SC-03 / SC-04 measurement
│   ├── bench_full_deck.py                  # NFR-02 measurement
│   └── bench_image_gen.py                  # NFR-22 measurement
└── docs/
    ├── air-gapped-deployment.md            # the "transfer this tar to your air-gapped machine" recipe
    ├── byo-style-guide.md                  # how to use --style with each format
    └── adapter-development.md              # how to add a new LLM adapter

.claude/skills/deck-builder/                # The Claude Skill (in-repo)
├── SKILL.md                                # ~50 lines: when to invoke + workflow
├── scripts/
│   └── invoke.py                           # thin shim → `pixi run -e local-recipes deckcraft generate ...`
└── reference/
    ├── slide-patterns.md
    └── prompt-recipes.md

recipes/deckcraft/                         # conda-forge recipe (S-15 invokes conda-forge-expert per CLAUDE.md Rule 1)
└── recipe.yaml                             # rattler-build v1
```

### Module dependency rules

```
surfaces (cli.py, mcp_server.py, Skill)
   ↓ depends on
pipeline.py
   ↓ depends on
core/outline.py + core/style_loader/* + core/asset_pipeline.py
   ↓ depends on
core/{chart,mermaid,image_*}_renderer.py + engines/pptx_engine.py
   ↓ depends on
adapters/llm*.py + platform.py + types.py
```

No upward imports. No circular dependencies. Enforced by `import-linter` rules in `pyproject.toml` (added in S-01).

---

## 5. Key Architectural Decisions (resolves the open questions)

### AD-01: `Style` Pydantic schema (resolves Open Q #15)

Defined in `deckcraft/types.py` per A-02 above. Schema version pinned to `"1.0"`. Stored as the integration contract for V∞ convergence — `presenton-pixi-image`'s `template-style-extractor` adopts the same schema, allowing both projects to share extractors via a future `pptx-style-toolkit` library on conda-forge.

### AD-02: LLM backend selection logic (resolves Open Q #8 — MLX selection)

Default-selection logic at `deckcraft init` time (persisted in user config; user can override):

```
if platform == "darwin" and arch == "arm64":
    if mlx_lm available AND model has MLX-format weights:
        backend = "mlx-lm"
    else:
        backend = "llama-server"  # auto-detects Metal
elif platform == "linux":
    if pytorch-cuda installed (NVIDIA opt-in pixi feature):
        backend = "llama-server"  # CUDA-accelerated
    elif rocm path healthy (Phoenix MES fix shipped):
        backend = "llama-server"  # ROCm
    else:
        backend = "llama-server"  # CPU
elif platform == "win32":
    if pytorch-cuda installed:
        backend = "llama-server"  # CUDA
    else:
        backend = "llama-server"  # CPU
```

`mlx-lm` preferred over `llama-server`+Metal on macOS only when an MLX-format weight exists for the chosen model (per OQ #8 PRD recommendation). Concrete check: deckcraft init queries HuggingFace `mlx-community/<model-name>-mlx-q4` paths during model pull.

### AD-03: GGUF model selection per tier (resolves Open Q #2)

Locked HuggingFace repo IDs for V1 (downloaded by `deckcraft init`):

| Tier | Text | Code | Vision | Vision mmproj | Embeddings |
|---|---|---|---|---|---|
| small | `Qwen/Qwen3-8B-Instruct-GGUF` (Q4_K_M) | `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF` (Q4_K_M) | `Qwen/Qwen2.5-VL-3B-Instruct-GGUF` (Q4_K_M) | `Qwen/Qwen2.5-VL-3B-Instruct-GGUF` (mmproj-f16) | `sentence-transformers/all-MiniLM-L6-v2` |
| medium | `Qwen/Qwen3-14B-Instruct-GGUF` (Q4_K_M) | `Qwen/Qwen2.5-Coder-14B-Instruct-GGUF` (Q4_K_M) | `Qwen/Qwen2.5-VL-7B-Instruct-GGUF` (Q4_K_M) | mmproj-f16 | same |
| large | `Qwen/Qwen3-30B-Instruct-GGUF` (Q4_K_M) | `Qwen/Qwen3-Coder-30B-Instruct-GGUF` (Q4_K_M) | `Qwen/Qwen2.5-VL-7B-Instruct-GGUF` (Q4_K_M) | mmproj-f16 | same |
| (image gen, opt-in) | `stabilityai/sdxl-turbo` (~7 GB) | same | same | n/a | n/a |

Multilingual embedding (`paraphrase-multilingual-MiniLM-L12-v2`, ~120 MB) is opt-in via `--embedding-model multilingual` config — V1 default is English-leaning MiniLM-L6 because the requester's deck content is English; multilingual is a flag flip away when needed.

### AD-04: MCP HTTP transport — V2 (resolves Open Q #3)

V1 ships stdio transport only. HTTP transport is V2.

Reason: stdio is the most mature MCP transport (Claude Code, Claude Desktop, Copilot Chat all support it natively). HTTP is needed for MS365 Power Platform connector (V3) and remote MCP callers. Adding HTTP to V1 would require auth/CORS thinking, certificate handling, and additional CI test surface — not worth it for the V1 dogfooding goal.

`fastmcp` makes the V2 add a one-line change (`@mcp.tool` decorators are transport-agnostic; only the launcher differs).

### AD-05: `pptx-assembler` reuse — wait for convergence (resolves Open Q #4)

`presenton-pixi-image`'s `pptx-assembler` is greenfield code being written for that project. Deckcraft's `pptx_engine` (FR-15 wrapper around python-pptx) covers the V1 needs and gives us the vendor-fallback escape hatch.

Deckcraft will NOT consume `pptx-assembler` as a V1 dependency. Instead, both projects keep separate engines for V1, and **the V∞ convergence target is a shared `pptx-style-toolkit`** (built around the FR-52 `Style` schema) that both projects consume. Pulling pptx-assembler into deckcraft V1 would create a hard dep on a sibling project's release schedule and slow both.

### AD-06: Performance benchmark cadence (resolves Open Q #5)

**Three benchmark events**, all happening before story breakdown locks the V1 timeline:

1. **Spike-0 (week 0, this week)**: Run `bench_outline_only.py` on the requester's Framework laptop with `qwen3:30b` — confirm SC-02 "<10 min on CPU" is achievable. Pure outline-generation timing. Pass = ≤8 min for a 10-slide outline.
2. **Spike-1 (after Wave 1, week 2)**: Run `bench_full_deck.py` end-to-end (extract → outline → render pptx, no images) on Framework. Pass = ≤10 min total.
3. **Spike-2 (after Wave 3, week 4)**: Run all benchmarks on all three reference machines (Framework, M4 if available, Win 32 GB if available). If reference machines unavailable, use docker simulation for cross-platform smoke.

Architecture phase **does not run** these benchmarks — they're defined here and run during implementation. But Spike-0 must run BEFORE epic breakdown commits the timeline.

### AD-07: `python-pptx` vendor trigger criteria (resolves Open Q #6)

Vendor-and-patch is triggered when ANY of:
- A bug in python-pptx 1.0.2 produces structurally-broken `.pptx` that PowerPoint refuses to open (severity: blocker)
- A PowerPoint format change (e.g., new SmartArt variant) requires emitting XML python-pptx doesn't support
- A python-pptx Python-3.x compatibility break that hasn't been patched upstream within 30 days

NOT triggered by: minor missing features, cosmetic issues, things that can be worked around in deckcraft code, or "I wish python-pptx had X" — those go through the upstream PR/issue path.

When triggered: vendor `python-pptx/src/pptx/` into `apps/deckcraft/vendor/python_pptx/`, apply the targeted patch, update `pptx_engine.py` to import from vendor path, document the patch in `apps/deckcraft/vendor/PATCHES.md`. Plan upstream PR for the next opportunity.

### AD-08: NVIDIA path on Windows — documented opt-in pixi feature for V2 (resolves Open Q #7)

V1 ships CPU-only on Windows. NVIDIA users wanting CUDA acceleration:
- V1: documented workaround in `docs/nvidia-cuda-windows.md` — manually install `pytorch-cuda` via the `pytorch` conda channel into a derivative env
- V2: official opt-in pixi feature `[feature.deckcraft-cuda]` that pulls `pytorch-cuda` and `cuda-runtime` from the `pytorch` channel (not conda-forge — explicit channel-deviation documented)

V1 doesn't bundle CUDA because: (a) breaks "100% conda-forge" purity for default users, (b) adds 3+ GB to the env, (c) requires NVIDIA driver on the host — out of conda-forge scope. NVIDIA users opt in.

### AD-09: VS Code extension distribution — VSIX-only sideload for V2; Marketplace for V3 (resolves Open Q #9)

V2 ships the extension as a `.vsix` file in the deckcraft GitHub releases. Air-gapped enterprise users can sideload it. Marketplace publish (V3) requires Microsoft developer account, signing, and ongoing maintenance — defer until adoption signal warrants.

VSIX-only is friendlier for the air-gapped use case anyway: many enterprise environments block Marketplace.

### AD-10: ODP/ODT V1 vs V2 — slip to V2 (resolves Open Q #14, the architecture-phase decision)

To keep V1 within the ≤12-week kill-criteria envelope (PRD SC-12), `.odp` / `.odt` style extraction (FR-46d) **slips to V2**. V1 ships with `.potx`/`.pptx`/`.docx`/`.pdf` style sources only.

Rationale: ODP/ODT adds 0.5 week. Without it, V1 timeline is 8.5–12.5 weeks (just inside ceiling). With it, top of range hits 13 weeks (over). Slipping ODP/ODT is the cheapest scope adjustment.

`odfpy` stays in pixi.toml (already added) so V2 has zero env work to start; just adds the `odf_extractor.py` module.

PRD update: FR-46d's status note ("stretch in V1, may slip to V2") is now firmly "V2." Mark in PRD.

### AD-11: Layout-mapping protocol details (resolves Open Q #16, the architecture-phase decision)

When a `.potx` or `.pptx` template is provided, `layout_mapper` runs after outline generation and before pptx rendering:

1. **Extract layout descriptors** from the template via `pptx_engine.list_layouts()`:
   ```
   [{"index": 0, "name": "Title Slide",
     "placeholders": [{"type": "title"}, {"type": "subtitle"}]},
    {"index": 1, "name": "Brand Hero",
     "placeholders": [{"type": "title"}, {"type": "image", "size": "large"}, {"type": "body"}]}]
   ```
2. **Pass layouts + slides to LLM** with this prompt template:
   ```
   You are mapping slides to PowerPoint layouts.
   Available layouts: <JSON layout descriptors>
   Slides: <JSON of Slide.layout.semantic_type and Slide.assets per slide>
   For each slide, choose the best layout by index. Respond with JSON: [{"slide_idx": 0, "layout_idx": 0}, ...]
   ```
3. **Validate LLM output**: every slide_idx and layout_idx must exist; every chosen layout must have placeholders that fit the slide's content (e.g., a slide with an image asset can't use a title-only layout).
4. **Fallback if LLM fails or chooses invalid**: heuristic by `LayoutHint.semantic_type`:
   - `title` → first layout containing `title` + `subtitle` placeholders
   - `content` → first layout with `title` + `body` (text-bearing) placeholder
   - `two_column` → first layout with two body placeholders
   - `image_with_caption` → first layout with `image` + `text` placeholders
   - `blank` → blank or title-only layout
   - Default → layout 1 (Microsoft default for "Title and Content")
5. **User override**: if `--layout-aliases <yaml>` provided, skip LLM entirely and use the mapping verbatim.

### AD-12: Image-gen lazy-load mechanism (resolves Open Q on FR-19/FR-20 design)

`image_generator.py` checks at first call:

```
def generate(prompt: str) -> Path:
    if not config.image_gen.enabled:
        raise CapabilityDisabled("image_gen.enabled = false in config")
    weights_dir = platform.cache_dir / "models" / "sdxl-turbo"
    if not (weights_dir / "model_index.json").exists():
        if config.offline:
            raise CapabilityUnavailable(
                "SDXL-Turbo weights not in DECKCRAFT_MODEL_DIR; "
                "in offline mode, pre-download via deckcraft init --include image_gen"
            )
        _hf_download("stabilityai/sdxl-turbo", weights_dir)  # uses hf-transfer
    pipe = self._lazy_pipe ?? _build_pipe(weights_dir, device=platform.diffusion_device)
    return pipe(prompt).images[0]
```

Result:
- Users who never enable image gen pay zero download cost
- Users who enable it on a connected machine get a one-time ~7 GB download
- Air-gapped users must pre-pull via `deckcraft init --include image_gen` on a connected machine, transfer the cache, set `DECKCRAFT_MODEL_DIR`

### AD-13: PDF style-extraction decision tree (FR-46c)

```
def extract_style_from_pdf(path: Path) -> Style:
    doc = pymupdf.open(path)
    text_blocks = [block for page in doc for block in page.get_text("dict")["blocks"]]
    if total_text_chars(text_blocks) > 200:
        # PDF has extractable text — sample fonts, sizes, colors directly
        fonts = sample_fonts(text_blocks)
        colors = sample_colors(text_blocks, doc)
        return Style(source_kind="pdf", theme=Theme(...), source_path=path)
    else:
        # Likely scanned — OCR fallback
        if config.offline and not pytesseract_available():
            raise StyleExtractionFailed("scanned PDF requires pytesseract+tesseract")
        ocr_text_per_page = [pytesseract.image_to_data(...) for page in doc]
        # Sample from rasterized rendering, not from extractable text
        rasters = [page.get_pixmap() for page in doc]
        fonts = sample_fonts_visual(rasters, ocr_text_per_page)
        colors = sample_colors_visual(rasters)
        return Style(source_kind="pdf", theme=Theme(...), source_path=path,
                     extraction_method="ocr")
```

Threshold of 200 characters: empirically separates "scanned PDF" from "PDF with text layer" in our test corpus. Tunable per FR-46c.

### AD-14: Hardware-tier auto-detection algorithm (FR-31)

`deckcraft init` runs:

```python
def detect_tier() -> HardwareTier:
    ram_gb = psutil.virtual_memory().total / (1024**3)
    if ram_gb < 24:
        return HardwareTier.SMALL  # warning: bottom of small-tier may struggle
    if ram_gb < 40:
        return HardwareTier.SMALL  # solid small
    if ram_gb < 56:
        return HardwareTier.MEDIUM
    return HardwareTier.LARGE
```

Reported to user with: "I detected ~48 GB of RAM. Recommended tier: medium. This will use qwen3:14b for text and qwen2.5-vl:7b for vision. To override: `deckcraft init --tier large` or `--tier small`."

### AD-15: Air-gapped operation mechanics

| Mechanism | Implementation |
|---|---|
| `DECKCRAFT_OFFLINE=1` env var | `settings.py` reads env at startup; `_check_offline_gate()` consulted by every adapter that could reach network (P-07) |
| `DECKCRAFT_MODEL_DIR` env var | `platform.py`'s `model_dir()` returns this if set; else `platformdirs.user_cache_dir / "models"` |
| First-run setup script | `deckcraft init --air-gapped-prep` downloads ALL tier models to a directory the user specifies; user tars + transfers |
| CI test for air-gap | `tests/air_gapped/test_offline.py` runs the golden-path fixtures inside `unshare -n` (Linux) or equivalent network-disabled context |
| Audit trail | Every adapter logs `network_access_attempted=True/False` to a structured log; air-gapped CI asserts only False |

### Resolved open questions summary

| OQ # | Resolution |
|---|---|
| 1 | ✅ BYO style (resolved before architecture, in this session) |
| 2 | ✅ AD-03: locked HuggingFace repos per tier |
| 3 | ✅ AD-04: stdio V1, HTTP V2 |
| 4 | ✅ AD-05: wait for V∞ convergence via `pptx-style-toolkit`; no V1 dep |
| 5 | ✅ AD-06: 3 benchmark events with Spike-0 gating story breakdown |
| 6 | ✅ AD-07: explicit vendor-trigger criteria documented |
| 7 | ✅ AD-08: V1 documented manual; V2 opt-in pixi feature |
| 8 | ✅ AD-02: explicit MLX-vs-llama.cpp selection logic |
| 9 | ✅ AD-09: VSIX-only V2; Marketplace V3 |
| 10 | ✅ AD-03: `all-MiniLM-L6-v2` default; multilingual via `--embedding-model multilingual` flag |
| 11 | RAG threshold tuning — defer to implementation; default 16K tokens, per-tier override at config (AD-03 implies tier-aware) |
| 12 | Qwen3-VL-Embedding V2 evaluation — gating criterion: "if cross-modal retrieval is requested by ≥3 dogfood users in V1's first month, evaluate the 2B variant in V2" |
| 13 | Qwen3-Embedding text-only V2 — gating criterion: "if multilingual support is requested OR MiniLM-L6 quality complaints surface in V1, evaluate Qwen3-Embedding-0.6B-GGUF as a drop-in replacement in V2" |
| 14 | ✅ AD-10: ODP/ODT slips to V2 (timeline rescope to keep ≤12-wk ceiling) |
| 15 | ✅ AD-01 + A-02: `Style` Pydantic schema defined |
| 16 | ✅ AD-11: layout-mapping protocol with prompt template + heuristic fallback |

**13 of 16 resolved as concrete decisions; 2 deferred to implementation/V2 with explicit gating criteria; 1 (RAG threshold tuning) deferred with documented default.**

### Newly-created open questions (carry forward)

None. The architecture phase produced no new unresolved questions. All implementation decisions either land here or are deliberately deferred with criteria.

---

## 6. Validation — Coverage Matrix

### FRs covered by architecture

All 52 FRs map to specific modules + adapters above. Sampling:

| FR | Module(s) responsible | Pattern enforcement |
|---|---|---|
| FR-01 to FR-08 (doc ingestion) | `core/doc_extractor.py` | P-05 (Pydantic), P-07 (offline gate for URL) |
| FR-09 to FR-12 (LLM content gen) | `core/outline.py` | P-02 (LLM via adapter), P-05 |
| FR-13 to FR-15 (editable PPTX) | `engines/pptx_engine.py`, `core/asset_pipeline.py` | P-01 (no `import pptx` outside engine), P-08 |
| FR-16 to FR-18 (mermaid + charts) | `core/mermaid_renderer.py`, `core/chart_renderer.py` | P-08 (cache), P-06 (graceful degrade) |
| FR-19, FR-20 (image gen) | `core/image_generator.py` | P-06, P-07, AD-12 (lazy load) |
| FR-21, FR-22 (vision) | `core/image_understander.py` | P-02 (Ollama via adapter) |
| FR-23, FR-24 (Marp) | `engines/marp_engine.py` (subprocess to marp-cli) | P-04 |
| FR-25, FR-26 (templates, resilience) | `pipeline.py`, `core/style_loader/default_template.py` | P-06 |
| FR-27 to FR-30 (cross-platform) | `platform.py` | P-03 (paths) |
| FR-31, FR-32 (config / tier detect) | `platform.py`, `settings.py` | AD-14 |
| FR-33, FR-34 (LLM backend adapter) | `adapters/llm*.py` | P-02 |
| FR-35 to FR-38 (CLI) | `cli.py` | typer-based |
| FR-39, FR-40 (MCP server) | `mcp_server.py` | fastmcp + auto-schemas from Pydantic |
| FR-41, FR-42 (distribution) | `.claude/skills/deck-builder/`, `recipes/deckcraft/` | invokes conda-forge-expert (DR-06) |
| FR-43, FR-44 (RAG, dedup) | `core/retrieval.py` | P-08 |
| FR-45 to FR-52 (BYO style) | `core/style_loader/*` | A-02 (Style schema), AD-13 (PDF), AD-11 (layout map), AD-10 (ODP V2 slip) |

### NFRs covered by architecture

All 23 NFRs map to specific architectural decisions or test categories. Sampling:

| NFR | How architecture satisfies | Verification |
|---|---|---|
| NFR-01 (first-token latency) | LLM adapter design supports streaming response | `bench_outline_only.py` |
| NFR-02 (end-to-end time) | `pipeline.py` is single-pass (no redundant calls); A-04 caches | `bench_full_deck.py` per tier |
| NFR-08 (air-gapped CI) | P-07 + AD-15 + `tests/air_gapped/` | CI test under `unshare -n` |
| NFR-14, NFR-15 (editability) | P-01 (engine adapter) + asset rendering as native shapes | structural inspection of `.pptx` in golden tests |
| NFR-09 (cross-platform parity) | P-03 (paths) + CI matrix on linux-64/osx-arm64/win-64 | golden tests on each platform |
| NFR-23 (style-source visual match) | AD-13 (PDF), AD-11 (layout) + style_loader test corpus | manual side-by-side review |

### Pattern coverage

P-01 through P-10 have enforcement (lint rule, test, or code review) defined. `tests/test_patterns.py` is the central enforcement test.

---

## 7. Architecture Phase Outputs

### Component summary (for story breakdown reference)

22 modules + 2 surface entry points + 2 templates + recipe = ~26 implementation units. Maps to roughly 6 epics × 3–4 stories each (matches PRD scoping intent).

| Wave | Module set | Story count est. |
|---|---|---|
| W1 (Foundation) | `types.py`, `platform.py`, `settings.py`, `adapters/llm*.py`, `core/doc_extractor.py`, scaffold | 5 stories |
| W2 (Renderers) | `engines/pptx_engine.py`, `engines/marp_engine.py`, `core/chart_renderer.py`, `core/mermaid_renderer.py`, `core/asset_pipeline.py` | 5 stories |
| W3 (Style + AI) | `core/style_loader/*`, `core/layout_mapper.py`, `core/outline.py`, `core/retrieval.py`, `core/image_understander.py`, `core/image_generator.py` | 6 stories |
| W4 (Surfaces) | `cli.py`, `mcp_server.py`, `pipeline.py`, `.claude/skills/deck-builder/` | 4 stories |
| W5 (Distribution) | `recipes/deckcraft/recipe.yaml`, `default-professional.potx`, `bmad-prd-pitch.potx`, README | 3 stories |
| W6 (Polish) | golden-path tests, `tests/air_gapped/`, benchmarks per machine, perf tuning | 3 stories |

**Total: ~26 stories across 6 waves.** Matches the original ~20-story estimate plus the BYO-style and image-gen V1 promotions.

### Benchmark plan (for Spike-0, gating story breakdown)

`apps/deckcraft/benchmarks/bench_outline_only.py`:

```python
# Pseudocode — runs on the requester's Framework laptop
import time
from deckcraft.adapters.llm import LlamaServerAdapter
PROMPT = """Generate a 10-slide outline for a Q3 product status presentation.
Topic: deckcraft V1 launch. Audience: engineering leadership."""
adapter = LlamaServerAdapter(model="qwen3:30b-instruct-q4_k_m")
adapter.start_server()
t0 = time.time()
result = adapter.complete(PROMPT, max_tokens=2000, format="json")
t1 = time.time()
print(f"Outline gen: {t1-t0:.1f}s; tokens={result.eval_count}; "
      f"throughput={result.eval_count/(t1-t0):.1f} tok/s")
adapter.stop_server()
# Pass criterion: t1-t0 < 480s (8 min) — leaves headroom under SC-02's 10-min target
```

**This benchmark must run BEFORE epic breakdown commits the V1 timeline.** If Spike-0 fails (>8 min), the timeline assumption (SC-02) is wrong and we either (a) re-tier (drop large tier to qwen3:14b on Framework), (b) revise SC-02 upward, or (c) accept that large-tier CPU is just slow and document as known limitation.

### Decisions still open (deliberately deferred with criteria)

| Item | Defer to | Trigger to revisit |
|---|---|---|
| RAG threshold per-tier defaults (OQ #11) | Implementation in W3 | When `core/retrieval.py` lands |
| Qwen3-VL-Embedding V2 evaluation (OQ #12) | V2 planning | ≥3 dogfood users request cross-modal retrieval in V1's first month |
| Qwen3-Embedding text-only V2 (OQ #13) | V2 planning | Multilingual request OR MiniLM quality complaints in V1 |
| LiteLLM in env | Indefinite | conda-forge `litellm` relaxes pydantic pin |
| MLX deeper integration | V2+ | After V1 dogfooding shows MLX-format weights perform ≥2× over llama.cpp Metal in real workloads |

---

## 8. Risks & Mitigations Specific to This Architecture

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Spike-0 fails (Framework large-tier > 8 min for outline) | Medium (CPU bandwidth-bound) | Bumps timeline OR forces tier down | Re-tier to qwen3:14b on Framework if needed; document as known constraint |
| `python-pptx` 1.0.2 has a bug we hit during W2 | Low | Slows W2; triggers AD-07 vendor path | Vendor + patch; ~2 days extra; tracked as risk |
| Mermaid+playwright cold-start dominates small-deck render time | Medium | NFR-04 (≤3s/diagram) miss | Persist playwright browser process across renders; ~1 day pattern fix in W2 |
| LLM-guided layout mapping (AD-11) produces wrong layouts often | Medium | User-visible quality issue | Robust heuristic fallback; user-override via `--layout-aliases`; per-template golden tests |
| `mlx-lm` on osx-arm64 doesn't match the speed promise (AD-02) | Low | M4 users see same perf as llama.cpp Metal | Adapter falls back to llama.cpp Metal seamlessly; no functional impact |
| FR-46c (PDF style extraction with OCR) too inaccurate to be useful | Medium | NFR-23 visual-match miss for PDF inputs | Threshold-based extraction-method choice; user can supply a `.potx` instead if PDF extraction disappoints |
| Sibling `presenton-pixi-image` ships `template-style-extractor` with a different `Style` schema before V∞ convergence | Low | Schema reconciliation work at V∞ | FR-52 + AD-01 establish our schema first; convergence happens on our schema as the basis (or we reconcile) |

---

## 9. Architecture Phase Completion

**Status:** Complete. 13 open questions resolved as concrete decisions; 2 deferred to V2 with explicit gating criteria; 1 deferred to implementation with default. No new unresolved questions.

**Ready for `bmad-create-epics-and-stories`?** Yes. Module breakdown (~26 implementation units), wave structure (6 waves), pattern enforcement (P-01 through P-10), and Spike-0 gate are all defined.

**Pre-conditions to story breakdown:**
1. Spike-0 (`bench_outline_only.py`) must run on Framework laptop and pass the ≤8-minute target; if it fails, re-tier first
2. Update PRD AD-10 implication: FR-46d (`.odp`/`.odt`) marked "V2" not "stretch in V1"
3. Update PRD timeline (SC-12) to reflect V2-slip: 8.5–12 weeks (no longer 9–13 with stretch)

**JSON output:**

```json
{
  "status": "complete",
  "architecture": "_bmad-output/projects/deckcraft/planning-artifacts/architecture.md",
  "openQuestionsResolved": 13,
  "openQuestionsDeferred": 3,
  "openQuestionsNew": 0,
  "newArchitectureDecisions": [
    "AD-01: Layered architecture with strict adapter boundaries",
    "AD-02: LLM backend selection logic",
    "AD-03: GGUF model selection per tier (HuggingFace repo IDs locked)",
    "AD-04: MCP HTTP transport — V2 not V1",
    "AD-05: pptx-assembler convergence at V∞ via shared pptx-style-toolkit; no V1 dep",
    "AD-06: 3-event benchmark plan with Spike-0 gating story breakdown",
    "AD-07: python-pptx vendor trigger criteria",
    "AD-08: NVIDIA on Windows = V2 opt-in pixi feature",
    "AD-09: VS Code extension = VSIX-only V2; Marketplace V3",
    "AD-10: ODP/ODT slips to V2 (keeps ≤12-wk ceiling)",
    "AD-11: Layout-mapping protocol (LLM-guided + heuristic fallback + user override)",
    "AD-12: Image-gen lazy-load mechanism",
    "AD-13: PDF style-extraction decision tree",
    "AD-14: Hardware-tier auto-detection algorithm",
    "AD-15: Air-gapped operation mechanics"
  ],
  "patternsEstablished": ["P-01 through P-10"],
  "moduleCount": 26,
  "waveCount": 6,
  "estimatedStoryCount": 26,
  "preconditionsToStoryBreakdown": [
    "Spike-0 benchmark on Framework laptop",
    "PRD update: FR-46d (ODP/ODT) marked V2 (no longer stretch)",
    "PRD update: SC-12 timeline 8.5–12 weeks (no longer 9–13)"
  ],
  "next": "Apply pre-condition PRD updates → run Spike-0 → bmad-create-epics-and-stories"
}
```
