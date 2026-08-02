---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - "_bmad-output/projects/deckcraft/planning-artifacts/prd.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/architecture.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft-distillate.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/prd-validation.md"
  - "pixi.toml"
project_name: deckcraft
epicCount: 6
storyCount: 28
status: complete
---

# deckcraft — Epic Breakdown

## Overview

Decomposition of deckcraft's PRD (52 FRs / 23 NFRs) and architecture (15 ADs / 10 patterns / 26-module breakdown) into 6 epics and 28 stories. Critical-path story is S-6.1 (Spike-0 benchmark) — gates the timeline commitment for the rest of V1.

Effort scale: XS (≤4 hr), S (½–1 day), M (1–3 days), L (3–5 days). Story IDs use `S-<epic>.<seq>` form (e.g., `S-1.3` = epic 1, story 3).

## Requirements Inventory

### Functional Requirements covered

All 52 FRs (FR-01 through FR-52). FR-46d (`.odp`/`.odt` style extraction) is V2 per architecture AD-10 — not in this epic breakdown.

### Non-Functional Requirements covered

All 23 NFRs (NFR-01 through NFR-23). NFR enforcement is mostly in E6 (Polish) via tests + benchmarks.

### Architecture Decisions covered

All 15 ADs (AD-01 through AD-15) flow into specific stories below. The 10 conflict-prevention patterns (P-01 through P-10) are enforced by S-6.3 (pattern test) and applied throughout E1–E5 stories.

### FR / Story Coverage Matrix

| FR Range | Capability | Owning Story/Stories |
|---|---|---|
| FR-01 to FR-08 | Document ingestion | S-1.4 |
| FR-09 to FR-12 | LLM-driven content gen | S-3.4 |
| FR-13 to FR-15 | Editable PPTX | S-2.1 |
| FR-16 to FR-18 | Diagrams & charts | S-2.4, S-2.3 |
| FR-19, FR-20 | Image generation (opt-in) | S-3.6 |
| FR-21, FR-22 | Vision / image understanding | S-3.5 |
| FR-23, FR-24 | Marp markdown | S-2.2 |
| FR-25, FR-26 | Templates & resilience | S-3.7, S-2.5 |
| FR-27 to FR-30 | Cross-platform | S-1.2 (paths), S-6.4 (CI matrix) |
| FR-31, FR-32 | Config / tier detect | S-1.2 |
| FR-33, FR-34 | LLM backend adapter | S-1.3 |
| FR-35 to FR-38 | CLI | S-4.2 |
| FR-39, FR-40 | MCP server (stdio) | S-4.3 |
| FR-41 | Claude Skill | S-4.4 |
| FR-42 | conda-forge recipe | S-5.1 |
| FR-43, FR-44 | RAG + dedup | S-3.3 |
| FR-45 to FR-52 | BYO style sources | S-3.1 (PPTX/DOCX), S-3.2 (PDF), S-3.7 (default templates), pipeline integration in S-4.1 |

### NFR / Story Coverage Matrix

| NFR Range | Subject | Owning Story/Stories |
|---|---|---|
| NFR-01 to NFR-05 | Performance | S-6.1 (Spike-0 outline), S-6.2 (Spike-1 full deck) |
| NFR-06, NFR-07 | Reliability / graceful | S-2.5 (pattern impl), S-6.3 (pattern test) |
| NFR-08 | Air-gapped CI | S-6.5 |
| NFR-09, NFR-10 | Cross-platform parity | S-6.4 |
| NFR-11 to NFR-13 | Air-gap operation | S-6.5 + S-1.2 |
| NFR-14, NFR-15 | Editability | S-2.1 + S-6.6 (golden tests) |
| NFR-16, NFR-17 | Setup friction | S-4.1 (`init`) + S-5.3 (README) |
| NFR-18, NFR-19 | Security/offline | S-6.5 |
| NFR-20, NFR-21 | Maintenance | S-6.3 (pattern enforcement) |
| NFR-22 | Image gen perf | S-3.6 + S-6.2 |
| NFR-23 | Style-source visual match | S-3.1, S-3.2, S-6.6 (golden tests) |

## Epic List

| Epic | Title | Story Count | Effort Sum |
|---|---|---|---|
| E1 | Foundation | 5 | ~5 days |
| E2 | Renderers | 5 | ~10 days |
| E3 | Style + AI | 7 | ~14 days |
| E4 | Surfaces | 4 | ~6 days |
| E5 | Distribution | 3 | ~5 days |
| E6 | Polish | 4 | ~7 days |
| **Total** | | **28** | **~47 days = 9.5 weeks (single-builder, focused)** |

Wave estimate of 9.5 weeks lands inside the 8.5–12 week PRD SC-12 envelope. Spike-0 (S-6.1) gates this commitment.

---

## Epic 1: Foundation

**Goal:** Establish the project skeleton, data model, platform abstractions, LLM adapter layer, and document ingestion. Everything subsequent stories depend on. **Critical-path: nothing runs without this epic.**

### Story 1.1: Project scaffolding and pyproject.toml

As the deckcraft builder,
I want a clean Python project skeleton at `apps/deckcraft/` with proper packaging metadata,
So that subsequent stories have a stable place to add modules and tests.

**Type:** infra • **Effort:** S • **Deps:** none • **FR/AD:** AD-01, P-01–P-10 (config layer)

**Acceptance Criteria:**

**Given** the local-recipes pixi env is active
**When** the developer runs `pixi run -e local-recipes pip install -e apps/deckcraft/`
**Then** `import deckcraft` succeeds from any Python in the env
**And** `pyproject.toml` declares: name, version, license (MIT or Apache-2.0 — finalize here), Python ≥3.12, no install_requires (deps come from pixi env), entry point `deckcraft = deckcraft.cli:app`
**And** ruff + pyright + import-linter configs are present and lint clean on the empty skeleton
**And** `tests/` directory exists with a passing trivial smoke test
**And** `conftest.py` exists with shared pytest fixtures stub
**And** the directory tree matches architecture.md Section 4 layout

### Story 1.2: Platform adapter (paths, RAM, GPU detection)

As the deckcraft pipeline,
I want a single PlatformAdapter that handles cross-platform paths, RAM detection, and GPU availability checks,
So that no business code branches on `sys.platform` and `deckcraft init` can recommend a hardware tier.

**Type:** foundation • **Effort:** M • **Deps:** S-1.1 • **FR/AD/P:** FR-27, FR-28, FR-29, FR-31, FR-32, AD-14, AD-15, P-03

**Acceptance Criteria:**

**Given** the deckcraft env on linux-64 / osx-arm64 / win-64
**When** the developer calls `deckcraft.platform.get_platform()`
**Then** returned `Platform` object exposes: `cache_dir`, `config_dir`, `log_dir`, `model_dir`, `name` (linux/macos/windows), `ram_gb` (psutil), `gpu_available` (Metal/ROCm/CUDA/CPU), `arch` (x86_64/arm64), `recommended_tier` per AD-14 thresholds
**And** all paths use `platformdirs` (no string-concatenated paths)
**And** `model_dir` honors `DECKCRAFT_MODEL_DIR` env var when set (per AD-15)
**And** `_check_offline_gate()` returns True when `DECKCRAFT_OFFLINE=1` (per AD-15)
**And** unit tests cover all 3 platforms via mocking sys.platform + psutil.virtual_memory

### Story 1.3: LLM adapter layer (pydantic-ai + 4 backends)

As the deckcraft pipeline,
I want a single LLMAdapter protocol with concrete implementations for llama-server (default), Ollama, mlx-lm (osx-arm64), and OpenAI-compat (Azure/GH Models/Anthropic-via-proxy),
So that switching LLM backends is a config change, not a code change.

**Type:** foundation • **Effort:** L • **Deps:** S-1.1, S-1.2 • **FR/AD/P:** FR-33, FR-34, AD-02, AD-03, P-02

**Acceptance Criteria:**

**Given** the deckcraft env with `llama-server` available (it is, conda-forge)
**When** the developer calls `LlamaServerAdapter(model="qwen3:8b").complete(prompt, format="json")`
**Then** llama-server is spawned as a subprocess on a free port, the request goes via OpenAI-compat HTTP, the response is JSON-parsed, the server is shut down on adapter close
**And** `OllamaAdapter(model="qwen3:8b")` talks to existing Ollama on 11434 (no spawn)
**And** `MlxLmAdapter(model="qwen3:8b")` is registered but only attempted on osx-arm64 (skipped on linux/win)
**And** `OpenAICompatAdapter(base_url=..., api_key=..., model=...)` works against any OpenAI-compat endpoint
**And** all adapters honor `DECKCRAFT_OFFLINE=1` (raise CapabilityUnavailable for cloud adapters; allow llama-server / Ollama / mlx-lm)
**And** all adapters return a unified `LLMResponse` Pydantic model
**And** adapter selection logic per AD-02 is implemented in `LLMAdapter.auto_select(platform)` and tested per platform via mocks
**And** `tests/test_patterns.py::test_no_direct_llm_imports_outside_adapters` passes (P-02)

### Story 1.4: Document extractor (markitdown wrapper)

As the deckcraft pipeline,
I want a DocExtractor that takes a path or URL and returns extracted text + metadata as a Pydantic model,
So that downstream LLM stages don't care about input format.

**Type:** foundation • **Effort:** S • **Deps:** S-1.1, S-1.2 • **FR/AD/P:** FR-01 to FR-08, P-05, P-07

**Acceptance Criteria:**

**Given** a PDF / DOCX / PPTX / MD / XLSX / URL input
**When** `DocExtractor.extract(path_or_url)` is called
**Then** returns an `ExtractedDocument` Pydantic model with `text` (markdown), `source_kind`, `metadata` (page count, word count, original path)
**And** PDF / DOCX / PPTX / MD / XLSX paths route to `markitdown` directly
**And** URL inputs respect `_check_offline_gate()` — raise `CapabilityUnavailable` if `DECKCRAFT_OFFLINE=1`
**And** unsupported file types raise `UnsupportedDocumentType` with a clear message
**And** unit tests cover all 6 input types with fixtures

### Story 1.5: Pydantic data model (types.py)

As the deckcraft codebase,
I want all inter-module data structures defined as Pydantic models in one module,
So that JSON serialization is consistent, MCP tool schemas auto-generate, and the FR-52 Style contract is binding.

**Type:** foundation • **Effort:** M • **Deps:** S-1.1 • **FR/AD/P:** FR-52, AD-01, AD-02 (A-02), P-05

**Acceptance Criteria:**

**Given** the architecture's data-model section (architecture.md A-02)
**When** the developer imports from `deckcraft.types`
**Then** the module exposes: `HardwareTier`, `Color`, `Theme`, `LayoutHint`, `LayoutDescriptor`, `MasterDescriptor`, `BrandAsset`, `Asset`, `Slide`, `Style`, `Deck`, `LLMResponse`, `ExtractedDocument`, `Platform`
**And** `Style.schema_version == "1.0"` is pinned per FR-52
**And** all models pass `.model_dump_json()` round-trip without information loss
**And** `Style.model_json_schema()` produces a JSON Schema document that is committed at `apps/deckcraft/schemas/style-v1.0.json` for future V∞ convergence with `presenton-pixi-image`
**And** unit tests cover all model construction + validation + round-trip
**And** `Color.rgb` validates `#RRGGBB` format; `Theme.accents` enforces 1–6 length

---

## Epic 2: Renderers

**Goal:** All output-producing modules — pptx engine adapter, marp engine, charts, mermaid, asset pipeline. The "render" half of deckcraft. Pure text-in / file-out, no LLM, no surfaces.

### Story 2.1: PPTX engine adapter (wraps python-pptx with vendor-fallback hooks)

As the deckcraft codebase,
I want a thin PptxEngineAdapter that wraps every python-pptx call,
So that vendor-and-patch (per AD-07 trigger criteria) is a one-module change, not a 50-file rewrite.

**Type:** foundation • **Effort:** M • **Deps:** S-1.5 • **FR/AD/P:** FR-13, FR-14, FR-15, AD-07, P-01

**Acceptance Criteria:**

**Given** the python-pptx 1.0.2 installed in env
**When** the developer calls `pptx_engine = PythonPptxEngine()` then `deck = pptx_engine.new_deck(style=...)` and adds slides via `pptx_engine.add_slide(deck, slide)`
**Then** the resulting `.pptx` opens cleanly in Microsoft PowerPoint 2019+ and Office 365 with all text as native editable text boxes
**And** `pptx_engine.list_layouts(template_path)` returns `LayoutDescriptor` list (used by S-3.7 layout_mapper)
**And** `pptx_engine.from_template(template_path)` opens an existing `.potx`/`.pptx` as the basis
**And** `pptx_engine.save(deck, output_path)` writes the `.pptx`
**And** NO production code outside `deckcraft.engines.pptx_engine` imports `pptx` (enforced by S-6.3)
**And** unit tests render a 3-slide deck with title, bullets, and a chart placeholder
**And** the saved `.pptx` validates as well-formed OOXML

### Story 2.2: Marp engine (subprocess to marp-cli)

As the deckcraft pipeline,
I want a MarpEngine that converts a Deck to Marp markdown and shells to `marp-cli` to also produce `.pptx`/`.pdf`/`.html`,
So that the Marp markdown source is the human-editable round-trip format (J5).

**Type:** feature • **Effort:** M • **Deps:** S-1.5 • **FR/AD/P:** FR-23, FR-24, P-04

**Acceptance Criteria:**

**Given** the deckcraft env with `marp-cli` available
**When** `MarpEngine().render(deck, output_dir, formats=["md", "pptx", "pdf", "html"])` runs
**Then** `output_dir/deck.md` is a valid Marp markdown source with frontmatter
**And** marp-cli is invoked via `subprocess.run([..., check=True], shell=False)` (P-04)
**And** the generated `.md` round-trips back to a Deck via `MarpEngine().load(md_path)` preserving all titles, bullets, image refs, and slide order
**And** unit tests cover the round-trip for a 3-slide deck
**And** marp-cli invocation timeouts cleanly if it hangs

### Story 2.3: Chart renderer (matplotlib + plotly)

As the deckcraft pipeline,
I want a chart renderer that takes a chart spec (chart type + structured data) and produces SVG/PNG output OR a native PowerPoint chart spec,
So that data viz on slides is editable wherever PowerPoint's native chart support fits.

**Type:** feature • **Effort:** M • **Deps:** S-1.5, S-2.1 • **FR/AD/P:** FR-18, P-05, P-08

**Acceptance Criteria:**

**Given** an `Asset(kind="chart", spec={"chart_type": "bar", "data": ..., "labels": ...})`
**When** `ChartRenderer.render(asset, cache_dir)` runs
**Then** for native-fit chart types (bar/line/scatter/pie), produces a chart spec consumed by `pptx_engine` to write a native PowerPoint `<c:chart>` element (NOT an image)
**And** for non-native chart types, renders to SVG via matplotlib (or plotly when interactive HTML is requested)
**And** when a `Style` with theme colors is provided, matplotlib `rcParams` are set from `Style.theme.accents` (per FR-49)
**And** rendered output path is content-addressed via `Asset.cache_key` (P-08)
**And** unit tests cover bar/line/scatter/pie native paths and one custom matplotlib path
**And** test asserts native chart XML in the `.pptx` for bar/line/scatter/pie

### Story 2.4: Mermaid renderer (mermaid-py + playwright headless, fully offline)

As the deckcraft pipeline,
I want a mermaid renderer that runs offline via headless Chromium with bundled mermaid.js,
So that flowcharts/diagrams are editable SVG embedded in slides without any network calls.

**Type:** feature • **Effort:** M • **Deps:** S-1.5, S-2.1 • **FR/AD/P:** FR-16, FR-17, P-07, P-08, NFR-04

**Acceptance Criteria:**

**Given** an `Asset(kind="diagram", spec={"diagram_type": "mermaid", "src": "graph TD; A-->B"})`
**When** `MermaidRenderer.render(asset, cache_dir)` runs the first time
**Then** playwright launches a persistent headless Chromium process, loads bundled mermaid.js (NO CDN), renders the mermaid src to SVG, saves to `cache_dir/<cache_key>.svg`
**And** subsequent calls in the same process reuse the Chromium process (NFR-04: ≤3s/diagram)
**And** when a `Style` is provided, theme CSS is injected so mermaid node/edge colors match `Style.theme.accents` (FR-49)
**And** the embedded SVG can be ungrouped in PowerPoint to native shapes (FR-17 — verified via manual structural inspection in golden tests)
**And** `_check_offline_gate()` is unnecessary here (no network) but the test asserts no network calls were made (P-07 strict)
**And** unit tests cover 3 diagram types: flowchart, sequence, ERD

### Story 2.5: Asset pipeline with caching + graceful degradation

As the deckcraft pipeline,
I want an asset_pipeline that dispatches Assets to the right renderer with content-addressed caching and graceful degradation on failure,
So that re-renders are free and broken renderers don't crash the deck.

**Type:** feature • **Effort:** M • **Deps:** S-2.3, S-2.4 (S-3.6 image gen integrates later) • **FR/AD/P:** FR-26, AD-04 (caching), P-06, P-08, NFR-06

**Acceptance Criteria:**

**Given** a list of `Slide` objects with mixed `Asset` types (charts, diagrams, future images)
**When** `AssetPipeline.render_all(slides, style, cache_dir)` runs
**Then** each Asset is dispatched to its registered renderer based on `asset.kind`
**And** rendered output is cached at `cache_dir/<asset.cache_key>.{ext}` and `Asset.rendered_path` is set
**And** if a renderer raises an exception, the asset is replaced with a placeholder, a warning is appended to a sidecar warnings list, and the pipeline continues (P-06, FR-26, NFR-06)
**And** the sidecar warnings are written to `<output_dir>/<deck>.warnings.json` if any occurred
**And** unit tests cover the success path, the cache-hit path, and the renderer-failure-with-graceful-degrade path

---

## Epic 3: Style + AI

**Goal:** All AI-driven and style-driven modules — style_loader (PPTX/DOCX/PDF), layout_mapper, outline generator, retrieval, vision, image gen. The "intelligence" half of deckcraft.

### Story 3.1: Style loader — PPTX (.potx + .pptx including --as-sample mode) + DOCX

As the deckcraft pipeline,
I want a style_loader that extracts the `Style` Pydantic model from `.potx`, `.pptx`, and `.docx` inputs,
So that BYO branding works without per-template hand-coding.

**Type:** feature • **Effort:** L • **Deps:** S-1.5, S-2.1 • **FR/AD/P:** FR-45, FR-46, FR-47, FR-48, FR-52, P-05

**Acceptance Criteria:**

**Given** a `.potx`, `.pptx` (template mode), `.pptx` with `--as-sample`, or `.docx` input
**When** `style_loader.load(path, as_sample=False)` is called
**Then** for `.potx`/`.pptx` (default): returns `Style(source_kind="pptx", theme=..., layouts=[LayoutDescriptor], masters=[MasterDescriptor], brand_assets=[BrandAsset])` extracted via python-pptx
**And** for `.pptx` with `as_sample=True`: same Style data but `source_kind="pptx_sample"` and intent flag set so pipeline discards the source's slides
**And** for `.docx`: extracts theme colors + heading/body fonts from python-docx, returns `Style(source_kind="docx", theme=..., layouts=[], masters=[])` (empty layouts because Word has no slide layouts)
**And** legacy `.ppt` and `.doc` raise `UnsupportedLegacyFormat("save as .pptx/.docx and retry")` per FR-45
**And** all Style outputs validate against the v1.0 JSON schema (S-1.5)
**And** unit tests cover all 4 input modes with fixtures + the legacy-rejection case

### Story 3.2: Style loader — PDF with OCR fallback (FR-46c)

As the deckcraft pipeline,
I want PDF style extraction with automatic OCR fallback for scanned PDFs,
So that brand PDFs (designed-in-PDF brand guides) work as style sources.

**Type:** feature • **Effort:** M • **Deps:** S-3.1 • **FR/AD/P:** FR-46c, AD-13, P-07 (OCR may need offline gate eventually but tesseract is local)

**Acceptance Criteria:**

**Given** a `.pdf` input
**When** `style_loader.load(pdf_path)` is called
**Then** `pdf_extractor` opens via pymupdf, counts extractable text characters per AD-13 threshold (default 200)
**And** if text is extractable: samples fonts (font name + size per page), samples colors (text + shape colors), heading-size detection via clustering, returns `Style(source_kind="pdf", extraction_method="text", ...)`
**And** if scanned (text < 200 chars total): uses pytesseract on rasterized pages, samples colors from rasters via Pillow, returns `Style(source_kind="pdf", extraction_method="ocr", ...)`
**And** unit tests include both a text-PDF and a scanned-PDF fixture (small synthetic PDFs)
**And** if OCR is needed but tesseract binary is missing, raises `StyleExtractionFailed` with installation hint

### Story 3.3: Retrieval module — sentence-transformers RAG + slide dedup

As the deckcraft pipeline,
I want a retrieval module that embeds document sections + slides for two purposes: long-document RAG fallback (FR-43) and slide deduplication (FR-44),
So that decks from huge documents work and LLM-output near-duplicates get collapsed.

**Type:** feature • **Effort:** M • **Deps:** S-1.5, S-1.4 • **FR/AD/P:** FR-43, FR-44, AD-03 (default model), P-05

**Acceptance Criteria:**

**Given** an extracted document with > 16K tokens (default threshold per FR-43)
**When** `retrieval.rag_select_sections(doc, target_tokens=12000)` is called
**Then** the document is split into sections (by header or paragraph), each section is embedded with `sentence-transformers/all-MiniLM-L6-v2`, the most semantically relevant ones (within target_tokens budget) are selected and returned
**And** the embedding model is loaded lazily on first call and cached for the process lifetime
**And** `retrieval.dedup_slides(slides, threshold=0.92)` returns a deduplicated list — slides with cosine similarity ≥ threshold collapsed to the first occurrence
**And** when `--embedding-model multilingual` is in config, uses `paraphrase-multilingual-MiniLM-L12-v2` instead
**And** unit tests cover both the RAG path (with a synthetic 50K-token doc) and the dedup path (with intentionally-similar slide pairs)

### Story 3.4: LLM outline generator (prompts + JSON-schema-validated output)

As the deckcraft pipeline,
I want an outline generator that takes a prompt + extracted document context and returns a structured `Deck` Pydantic model from the LLM,
So that LLM hallucinations land in a typed, validated structure ready for rendering.

**Type:** feature • **Effort:** L • **Deps:** S-1.3, S-1.4, S-1.5, S-3.3 • **FR/AD/P:** FR-09, FR-10, FR-11, FR-12, P-02, P-05

**Acceptance Criteria:**

**Given** a prompt (string) + optional `ExtractedDocument` + optional `target_slide_count` + optional `audience` + optional `Style`
**When** `OutlineGenerator.generate(prompt, document=..., target_slide_count=10, audience="executive", style=...)` is called
**Then** the LLM (via the configured `LLMAdapter`) is asked for a JSON response matching `Deck` schema
**And** if the document exceeds 16K tokens, RAG (S-3.3) is used to select the most relevant sections before LLM call
**And** the LLM response is validated against the `Deck` Pydantic schema; if invalid, retry once with "your previous response failed validation: <error>" appended
**And** if validation still fails after retry, raise `LLMOutputInvalid` with the raw response logged
**And** the returned `Deck` has the requested slide count (±1 tolerance) and audience-appropriate tone
**And** unit tests cover happy path with mocked LLM, retry-on-validation-fail, and final-fail paths

### Story 3.5: Image understander (Ollama qwen2.5vl + llama.cpp mmproj fallback)

As the deckcraft pipeline,
I want an image_understander that takes an image path and returns a structured description via local vision LLM,
So that J4 (read-image-and-describe) works air-gapped on all 3 platforms.

**Type:** feature • **Effort:** M • **Deps:** S-1.3 • **FR/AD/P:** FR-21, FR-22, AD-03, P-02, P-07

**Acceptance Criteria:**

**Given** an image at `path` (PNG/JPG/SVG)
**When** `ImageUnderstander.describe(path, mode="full")` is called
**Then** the configured vision model (Ollama `qwen2.5vl:3b` for small tier, `:7b` for medium/large) returns `ImageDescription(caption, key_elements, extracted_text_if_any)`
**And** if Ollama is unavailable but llama.cpp `--mmproj` path is configured, falls back to it
**And** `mode="caption_only"` returns just the caption (faster, fewer tokens)
**And** raises `CapabilityUnavailable` if neither vision backend is available + `_check_offline_gate()` is True
**And** unit tests cover happy path with mocked LLM and unavailable-backend graceful failure

### Story 3.6: Image generator (diffusers + SDXL-Turbo, opt-in default-off, lazy-load)

As the deckcraft pipeline,
I want an image_generator that produces hero/illustrative images via SDXL-Turbo only when explicitly enabled, with lazy weight loading,
So that users who never enable image gen pay zero cost and users who do get J3 working.

**Type:** feature • **Effort:** M • **Deps:** S-1.2, S-2.5 • **FR/AD/P:** FR-19, FR-20, AD-12, P-06, P-07, NFR-22

**Acceptance Criteria:**

**Given** `config.image_gen.enabled = True` and a prompt
**When** `ImageGenerator.generate(prompt)` is called the first time
**Then** SDXL-Turbo weights are pulled via `huggingface_hub` (using `hf-transfer` for speed) into `platform.cache_dir/models/sdxl-turbo/` IF not already present
**And** if `_check_offline_gate()` is True and weights missing, raises `CapabilityUnavailable` with hint to pre-pull via `deckcraft init --include image_gen`
**And** the diffusers pipeline is built once, reused per process (lazy + cached)
**And** device is selected per AD-02: MPS on macOS, CUDA on Linux/Windows-with-CUDA, CPU otherwise
**And** `config.image_gen.enabled = False` (the V1 default) → `generate()` raises `CapabilityDisabled`
**And** failures (OOM, weight corruption) are caught and a placeholder image is returned with a sidecar warning (FR-26, P-06)
**And** unit tests cover: disabled-by-default, lazy-load on first call, cache-hit on second call, failure-with-placeholder, offline-gate-blocking

### Story 3.7: Layout mapper + bundled templates (default-professional + bmad-prd-pitch)

As the deckcraft pipeline,
I want a layout_mapper that uses LLM-guided selection (with heuristic fallback) to assign template layouts to each slide, plus 2 bundled templates,
So that user-supplied templates AND deckcraft's defaults work for arbitrary corporate template structures.

**Type:** feature • **Effort:** M • **Deps:** S-1.3, S-1.5, S-2.1, S-3.1 • **FR/AD/P:** FR-25, FR-50, FR-51, AD-11, P-02, P-05

**Acceptance Criteria:**

**Given** a `Deck` (with slides having semantic `LayoutHint`) + a `Style` with non-empty `layouts` list
**When** `LayoutMapper.map(deck, style)` is called
**Then** the LLM is given the layouts (per AD-11 prompt template) and asked to pick the best layout per slide
**And** the LLM's choice is validated: each layout_idx exists, each chosen layout's placeholders fit the slide's content
**And** if the LLM fails or chooses invalid, falls back to heuristic by `LayoutHint.semantic_type` (per AD-11 heuristic mapping)
**And** if `--layout-aliases <yaml>` is provided, skips LLM entirely and uses the user mapping
**And** `default-professional.potx` is bundled at `apps/deckcraft/templates/` with 5 layouts: title-slide, title+content, two-column, section-header, blank — using DejaVu fonts and a neutral palette
**And** `bmad-prd-pitch.potx` is bundled with layouts oriented around BMAD-PRD section types (executive-summary, success-criteria, journeys, FRs, etc.) for J6
**And** when no `--style` is provided, pipeline uses `default-professional.potx` (FR-51)
**And** when `.docx` style source is provided, layouts are inherited from `default-professional.potx` (per FR-48)
**And** unit tests cover: LLM-guided happy path, LLM-fail-fallback path, user-alias-override path, both bundled templates load successfully

---

## Epic 4: Surfaces

**Goal:** The user-facing entry points: high-level Pipeline, CLI, MCP server, Claude Skill. The "outside-of-pipeline" half — what users actually invoke.

### Story 4.1: Pipeline class (high-level public API)

As a Python developer using deckcraft as a library,
I want a `Pipeline` class that orchestrates extract → outline → style → render,
So that I can write a 5-line script that produces an editable `.pptx` from any input.

**Type:** integration • **Effort:** M • **Deps:** S-1.4, S-3.1, S-3.4, S-3.7, S-2.5, S-2.1, S-2.2 • **FR/AD/P:** FR-25 to FR-52 integration, AD-01, P-05

**Acceptance Criteria:**

**Given** any combination of (prompt, document_path, style_path, target_slide_count, output_path)
**When** the developer calls `Pipeline().generate(prompt=..., document=..., style=..., output=...)`
**Then** orchestration runs in this order: load `Style` (or default-professional.potx fallback), extract document if provided, generate outline (with RAG if needed), map layouts, render assets (charts/diagrams/images-if-enabled), render pptx via `pptx_engine`, render Marp md via `marp_engine`
**And** a `PipelineResult(deck, pptx_path, marp_path, warnings)` is returned
**And** any optional-capability failures are collected in `result.warnings` per FR-26
**And** unit tests cover the full pipeline with all major branches (with-document / no-document, with-style / default-style, with-image-gen-enabled / disabled)
**And** integration test produces a real 5-slide deck end-to-end on the Framework laptop

### Story 4.2: CLI (typer-based, deckcraft generate / init / describe-image / convert)

As a CLI user,
I want a `deckcraft` command that exposes generate / init / describe-image / convert subcommands,
So that I can produce decks and manage models without writing Python.

**Type:** feature • **Effort:** M • **Deps:** S-4.1, S-3.5 • **FR/AD/P:** FR-31, FR-32, FR-35, FR-36, FR-37, FR-38, AD-14, NFR-16

**Acceptance Criteria:**

**Given** the deckcraft package installed
**When** the user runs `deckcraft generate --input /path/to/doc.pdf --style /path/to/brand.potx --out deck.pptx`
**Then** the file is produced and the user sees a structured progress log
**And** `deckcraft init` runs the AD-14 tier-detection algorithm, reports detected RAM + tier recommendation, asks for confirmation, downloads the recommended GGUF models per AD-03 (if connected)
**And** `deckcraft init --tier large` overrides auto-detection
**And** `deckcraft init --air-gapped-prep` downloads ALL tier models for transfer
**And** `deckcraft describe-image --input img.png` calls S-3.5 and prints the description
**And** `deckcraft convert --input deck.pptx --to marp` calls S-2.2's `MarpEngine.load()` then re-renders Marp md
**And** `deckcraft --help` shows all subcommands with helpful descriptions
**And** unit tests use `typer.testing.CliRunner` to cover each subcommand

### Story 4.3: MCP server (fastmcp stdio transport)

As an AI assistant using deckcraft via MCP,
I want a stdio-transport MCP server that exposes deckcraft's capabilities as tools with auto-derived schemas,
So that Claude Code, Claude Desktop, Copilot Chat, and Copilot agents can all invoke deckcraft.

**Type:** feature • **Effort:** M • **Deps:** S-4.1, S-3.5 • **FR/AD/P:** FR-39, FR-40, AD-04, P-05

**Acceptance Criteria:**

**Given** the deckcraft package installed
**When** an MCP client connects via `python -m deckcraft mcp-server` (stdio transport)
**Then** the client sees registered tools: `generate_deck`, `add_slide`, `render_chart`, `render_diagram`, `describe_image`, `extract_document`, with schemas auto-derived from the Pydantic model signatures via `fastmcp`
**And** each tool call routes to the corresponding `Pipeline` / module method
**And** error responses are structured (not raw stack traces)
**And** stdio transport is the default; HTTP transport is V2 (per AD-04) — but the code path for HTTP is already implemented and just gated behind a `--transport http` flag for V2 to flip
**And** integration test connects via the MCP Python SDK and invokes `generate_deck` round-trip
**And** schema export to `apps/deckcraft/schemas/mcp-tools.json` is committed

### Story 4.4: Claude Skill (.claude/skills/deck-builder/)

As a Claude Code user in this repo,
I want a `deck-builder` Skill that activates when I say "make me a deck" and routes to deckcraft via pixi run,
So that deckcraft works inside my AI-assistant flow without me ever touching the CLI.

**Type:** integration • **Effort:** S • **Deps:** S-4.2 • **FR/AD/P:** FR-41

**Acceptance Criteria:**

**Given** a Claude Code session in this repo
**When** the user says "make me a deck about X" or "/deck about X"
**Then** the `deck-builder` skill activates per its SKILL.md description
**And** the skill invokes `pixi run -e local-recipes deckcraft generate --prompt "..." --out <suggested-path>` via the Bash tool
**And** the skill's SKILL.md is ~50 lines: when-to-invoke + workflow + 3 example invocations
**And** scripts/invoke.py is a thin Python shim that constructs the deckcraft CLI args from the user's request
**And** `.claude/skills/deck-builder/reference/slide-patterns.md` and `prompt-recipes.md` exist with concrete examples
**And** an end-to-end manual test: "make me a deck about Q3 status" in Claude Code produces an editable `.pptx`

---

## Epic 5: Distribution

**Goal:** Make deckcraft installable + discoverable via conda-forge, ship default templates, write the docs.

### Story 5.1: conda-forge recipe at `recipes/deckcraft/`

As a colleague who doesn't have this monorepo,
I want to install deckcraft via `conda install -c conda-forge deckcraft`,
So that distribution doesn't require cloning anything.

**Type:** infra • **Effort:** M • **Deps:** S-4.1, S-4.2, S-4.3 • **FR/AD/P:** FR-42, DR-04, DR-06, AD-05

**CLAUDE.md Rule 1 enforcement:** This story MUST invoke the `conda-forge-expert` skill before producing recipe content. The skill's 9-step autonomous loop, Operating Principles, Critical Constraints are authoritative.

**Acceptance Criteria:**

**Given** deckcraft v0.1.0 is published to PyPI (a separate publishing step before this story can complete)
**When** the developer runs `conda-forge-expert` skill on `recipes/deckcraft/`
**Then** a rattler-build v1 `recipe.yaml` is produced at `recipes/deckcraft/recipe.yaml`
**And** the recipe declares all runtime deps matching the actual deckcraft pyproject.toml: matplotlib, plotly, transformers, accelerate, playwright-python, ollama-python, hf-transfer, sentencepiece, sentence-transformers, pytesseract, python-pptx, markitdown, mermaid-py, marp-cli, pandoc, fastmcp, mcp, pydantic-ai, typer, llama.cpp, diffusers, pytorch, etc.
**And** platform support: noarch python where possible (deckcraft itself is pure-Python so noarch); native-binary deps already cross-platform
**And** the recipe passes `pixi run -e local-recipes recipe-build recipes/deckcraft`
**And** PR is opened to `conda-forge/staged-recipes` (gated on user authorization per repo's submit-pr task)
**And** `bmad-retrospective` skill runs at story closeout per CLAUDE.md Rule 2 — captures any conda-forge-expert findings as updates to the skill files

### Story 5.2: Default templates (default-professional.potx + bmad-prd-pitch.potx)

As any deckcraft user,
I want two bundled templates that work out-of-the-box,
So that no `--style` flag still produces a professional deck.

**Type:** feature • **Effort:** S • **Deps:** S-2.1 • **FR/AD/P:** FR-25, FR-51

**Acceptance Criteria:**

**Given** PowerPoint with the bundled `default-professional.potx`
**When** the user opens it and inserts placeholder content
**Then** the layout is clean professional, fonts are DejaVu Sans (heading) + DejaVu Sans (body), palette is neutral (4 accents)
**And** has the 5 layouts per S-3.7: title-slide, title+content, two-column, section-header, blank
**And** `bmad-prd-pitch.potx` has layouts mapping to BMAD PRD sections: exec-summary (1 slide), success-criteria (1 slide), per-journey (1 slide), per-FR-group (1 slide), kill-criteria (1 slide), summary (1 slide)
**And** both `.potx` files are committed at `apps/deckcraft/templates/` and shipped in the conda-forge package
**And** unit test: load each template via pptx_engine, verify layout count + theme colors

### Story 5.3: README + air-gapped deployment guide + BYO style guide

As anyone discovering deckcraft,
I want documentation that gets me from zero to first deck in ≤30 minutes,
So that I actually use the tool.

**Type:** doc • **Effort:** M • **Deps:** S-4.2 • **FR/AD/P:** NFR-16, NFR-17

**Acceptance Criteria:**

**Given** `apps/deckcraft/README.md`
**When** a colleague reads it
**Then** they see: 30-second elevator pitch, 5-minute quickstart (`conda install` → `deckcraft init` → `deckcraft generate`), per-tier model expectations, troubleshooting for common issues
**And** `apps/deckcraft/docs/air-gapped-deployment.md` documents the `deckcraft init --air-gapped-prep` flow + tar/transfer recipe + DECKCRAFT_OFFLINE flag
**And** `apps/deckcraft/docs/byo-style-guide.md` documents how to use `--style` with each format (.potx, .pptx, --as-sample, .docx, .pdf), including troubleshooting visual-mismatch issues
**And** a colleague who hasn't seen deckcraft can produce a deck following the README in ≤30 min on a fresh install
**And** READMEs are tested via the manual checklist (one-time, by the requester)

---

## Epic 6: Polish

**Goal:** Tests, benchmarks, pattern enforcement, cross-platform CI, perf tuning. The "we trust this works" half.

### Story 6.1: Spike-0 benchmark on Framework laptop (CRITICAL PATH)

As the deckcraft project,
I want to validate SC-02's "<10 min CPU outline gen on large tier" claim BEFORE locking the V1 timeline,
So that we either confirm the timeline or re-tier qwen3:30b → qwen3:14b on Framework before story estimation locks downstream commitments.

**Type:** test/spike • **Effort:** XS (benchmark itself; no implementation work besides the benchmark script) • **Deps:** S-1.3 (LLM adapter only — pre-W1 spike) • **FR/AD/P:** SC-02, NFR-02, AD-06

**This story is the critical-path gate for the V1 timeline. Run BEFORE other Wave 1 work begins.**

**Acceptance Criteria:**

**Given** the Framework laptop with `llama-server` available + `qwen3:30b-instruct-q4_k_m.gguf` GGUF downloaded
**When** the developer runs `apps/deckcraft/benchmarks/bench_outline_only.py` with the standard test prompt (10-slide outline, exec audience)
**Then** total wall-clock time is ≤ 8 minutes (per AD-06)
**And** if pass: timeline assumption is validated; downstream stories proceed
**And** if fail: re-tier large→medium for Framework (use qwen3:14b), revise SC-02, document in retrospective
**And** results are saved to `apps/deckcraft/benchmarks/spike-0-results.json` with: model, tokens-in, tokens-out, wall-clock, throughput

### Story 6.2: Spike-1 (full-deck) and Spike-2 (per-machine) benchmarks

As the deckcraft project,
I want to validate the full deck-generation pipeline timing on each reference machine,
So that NFR-02 (per-tier wall-clock targets) is verified, not assumed.

**Type:** test • **Effort:** S • **Deps:** S-4.1 (Pipeline complete), S-6.1 (Spike-0 passed) • **FR/AD/P:** NFR-02, NFR-03, NFR-04, NFR-22, AD-06

**Acceptance Criteria:**

**Given** the full deckcraft pipeline at end of Wave 3
**When** the developer runs `bench_full_deck.py` (extract→outline→render pptx, no images, 10-slide deck) on the Framework laptop
**Then** wall-clock ≤ 10 minutes (NFR-02 large tier CPU)
**And** when run on M4 (if available) ≤ 4 minutes (NFR-02 medium tier with Metal/MLX)
**And** when run on Win 32 GB (if available) ≤ 15 minutes (NFR-02 small tier CPU)
**And** if reference machines unavailable for M4/Win, document constraint and use docker simulation (architecture allows this)
**And** `bench_image_gen.py` measures image-gen wall-clock on each machine + verifies NFR-22 (≤60s CPU, ≤15s M4 MPS)
**And** results are saved as JSON for tracking across V1 and V2

### Story 6.3: Pattern enforcement test suite (P-01 through P-10)

As the deckcraft codebase,
I want a test suite that catches pattern violations at PR time,
So that conflict-prevention rules don't drift over time.

**Type:** test/infra • **Effort:** M • **Deps:** All E1-E4 stories complete (or in progress) • **FR/AD/P:** AD-01 through AD-15 enforcement, P-01 through P-10

**Acceptance Criteria:**

**Given** the deckcraft codebase
**When** `pytest tests/test_patterns.py` runs
**Then** it grep-fails the build if any production code outside `deckcraft.engines.pptx_engine` contains `import pptx` (P-01)
**And** fails if any production code outside `deckcraft.adapters.llm_*` contains `import ollama`, `import anthropic`, or `httpx.post` to LLM ports (P-02)
**And** fails if any string-concatenated paths or `/tmp/` hardcoded references exist (P-03)
**And** fails if `subprocess.run` is called without `shell=False` and `text=True` (P-04 — uses ast scan, not grep)
**And** fails if any module-boundary args use `pandas.DataFrame` (P-05 — must convert to dict/Pydantic at boundary)
**And** fails if any optional-capability call doesn't use the `OptionalCapability` decorator (P-06)
**And** fails if any network-touching adapter doesn't call `_check_offline_gate()` (P-07)
**And** fails if any `mermaid.render` etc. is called outside `asset_pipeline.render` (P-08)
**And** fails if naive datetime construction is found (P-09)
**And** fails if `print()` calls exist in production code under `src/deckcraft/` (P-10)
**And** all 10 patterns have at least 1 test case validating the rule + 1 negative test case (intentional violation that the test catches)

### Story 6.4: Cross-platform CI matrix (linux-64 + osx-arm64 + win-64)

As the deckcraft project,
I want CI that runs the unit + integration test suite on all 3 reference platforms,
So that NFR-09 (cross-platform parity) is enforced at PR time.

**Type:** infra • **Effort:** M • **Deps:** S-6.3 + S-6.5 + S-6.6 (need tests to run) • **FR/AD/P:** FR-27 to FR-30, NFR-09, NFR-10

**Acceptance Criteria:**

**Given** a GitHub Actions workflow at `.github/workflows/deckcraft-ci.yml`
**When** a PR is opened touching `apps/deckcraft/`
**Then** the workflow runs `pixi run -e local-recipes pytest apps/deckcraft/tests/unit/` on linux-64, osx-arm64 (when GH macOS-arm64 runners available), and win-64
**And** integration tests (`@pytest.mark.integration`) run on linux-64 only by default (cost) — opt-in for macOS/Windows via PR label
**And** a structural diff of the golden `.pptx` outputs between platforms passes (NFR-09)
**And** the matrix uses pixi-native setup (not pip-only) to match the actual local-recipes env
**And** failures are clearly labeled (which platform, which test) in the PR check summary

### Story 6.5: Air-gapped CI under unshare -n (Linux)

As the deckcraft project,
I want CI that runs the golden-path tests inside a network-isolated context,
So that NFR-08 (air-gapped functional parity) and DR-01 (no public-internet calls in default mode) are enforced.

**Type:** test • **Effort:** M • **Deps:** S-6.6 (golden tests) • **FR/AD/P:** DR-01, NFR-08, NFR-11, NFR-19, P-07

**Acceptance Criteria:**

**Given** a GHA job that wraps the test command in `unshare -rn` (Linux network namespace isolation)
**When** the air-gapped job runs the golden-path tests
**Then** all tests pass with no outbound network calls
**And** any test that requires the LLM uses a pre-pulled local GGUF model (cached in CI runner)
**And** any test that requires SDXL-Turbo is skipped (the model isn't pre-pulled in CI; that's a separate opt-in test category)
**And** P-07 enforcement: every adapter logs `network_access_attempted=True/False` and the test asserts only False
**And** the `DECKCRAFT_OFFLINE=1` env var is set during the job to verify the offline gate

### Story 6.6: Golden-path test fixtures (5 prompts → expected pptx structure)

As the deckcraft project,
I want a small but representative set of golden-path tests that lock in expected output structure,
So that regressions are caught at PR time, not by users.

**Type:** test • **Effort:** M • **Deps:** S-4.1 + 5 fixture prompts • **FR/AD/P:** SC-05, SC-06, NFR-14, NFR-15, NFR-23

**Acceptance Criteria:**

**Given** 5 golden-path test fixtures at `apps/deckcraft/tests/golden/`:
1. simple-prompt-no-doc (10-slide deck from prompt only)
2. pdf-input (10-slide deck from a 20-page PDF)
3. bmad-prd-input (J6 — deck from this very PRD)
4. with-style-potx (deck using a sample corporate `.potx`)
5. with-style-pdf (deck using a sample brand PDF, requires OCR fallback)
**When** `pytest apps/deckcraft/tests/golden/` runs
**Then** each test produces a `.pptx`, `.marp.md`, and `.warnings.json` (if any)
**And** structural assertions on the `.pptx`: expected slide count (±1), all text in editable text boxes (NFR-14), all charts/diagrams as native-or-SVG-not-raster (NFR-15), style colors match `Style` source for tests 4 and 5 (NFR-23)
**And** any sidecar warnings are logged but don't fail the test
**And** the LLM is mocked at the adapter boundary for fast/deterministic tests (separate `@pytest.mark.live_llm` variant for occasional real-LLM runs)

---

## Story DAG (critical path + key dependencies)

```
Critical path: S-1.1 → S-1.3 → S-6.1 (Spike-0 GATE) → ... rest of work
                          ↘
                            S-3.4 → S-4.1 → S-4.2 → S-4.4 → S-5.3 → DONE
                          ↗
S-1.5 → S-2.1 → S-3.7 → S-4.1 ↗
S-1.4 → S-3.4 ↗
S-2.3, S-2.4 → S-2.5 → S-4.1 ↗
S-3.1, S-3.2 → S-4.1 ↗
S-3.3 → S-3.4 ↗
S-3.5 → S-4.2 ↗
S-3.6 → S-2.5 (asset pipeline picks it up) ↗
S-4.1, S-4.2, S-4.3 → S-5.1 (recipe needs the pkg)
S-5.2 (templates) → S-3.7 (used in default flow)
All E1-E4 → S-6.3 (pattern test) + S-6.6 (golden tests)
S-6.6 → S-6.4 (cross-platform CI) + S-6.5 (air-gapped CI)
S-4.1 → S-6.2 (Spike-1 needs full pipeline)
```

**Critical-path estimation (single builder, no parallelism):** S-1.1 (S) + S-1.2 (M) + S-1.3 (L) + S-6.1 (XS gate) + S-1.5 (M) + S-2.1 (M) + S-3.4 (L) + S-3.7 (M) + S-4.1 (M) + S-4.2 (M) + S-5.3 (M) = ~18 days. Add E2/E3 parallelizable work that's not on critical path: ~30 days more. Add E5 distribution + E6 polish: ~10 days more. Total ~58 days = 11.6 weeks at 5 working days/week. Inside the 8.5–12 week SC-12 envelope. Spike-0 must validate the LLM throughput assumption that underpins this.

---

## Final structured JSON

```json
{
  "status": "complete",
  "epicsFile": "_bmad-output/projects/deckcraft/planning-artifacts/epics.md",
  "epicCount": 6,
  "storyCount": 28,
  "epics": [
    {"id": "E1", "title": "Foundation", "stories": 5, "effort_days": 5},
    {"id": "E2", "title": "Renderers", "stories": 5, "effort_days": 10},
    {"id": "E3", "title": "Style + AI", "stories": 7, "effort_days": 14},
    {"id": "E4", "title": "Surfaces", "stories": 4, "effort_days": 6},
    {"id": "E5", "title": "Distribution", "stories": 3, "effort_days": 5},
    {"id": "E6", "title": "Polish", "stories": 4, "effort_days": 7}
  ],
  "criticalPath": [
    "S-1.1: Project scaffolding",
    "S-1.3: LLM adapter layer",
    "S-6.1: Spike-0 benchmark (GATE)",
    "S-1.5: Pydantic data model",
    "S-2.1: PPTX engine adapter",
    "S-3.4: Outline generator",
    "S-3.7: Layout mapper + default templates",
    "S-4.1: Pipeline class",
    "S-4.2: CLI",
    "S-5.3: README + docs"
  ],
  "criticalPathDays": "~18 days (58 days total V1 with parallelizable work)",
  "specialStories": {
    "spike0": "S-6.1 (CRITICAL — gates V1 timeline)",
    "condaRecipe": "S-5.1 (invokes conda-forge-expert per CLAUDE.md Rule 1; closeout retro per Rule 2)",
    "patternTests": "S-6.3 (P-01 through P-10 enforcement)",
    "airGappedCI": "S-6.5 (NFR-08 enforcement under unshare -n)"
  },
  "dependsOnPrior": ["validation gate PASS", "PRD AD-10 / SC-12 updates applied"],
  "next": "bmad-check-implementation-readiness gate, then bmad-sprint-planning"
}
```
