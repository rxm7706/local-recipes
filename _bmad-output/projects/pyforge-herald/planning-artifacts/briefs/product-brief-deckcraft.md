---
title: "Product Brief: deckcraft"
status: "complete"
created: "2026-05-09"
updated: "2026-05-09"
inputs:
  - "Conversation transcript (2026-05-09): full deckcraft scoping session"
  - "{project-root}/_bmad-output/projects/local-recipes/project-context.md"
  - "{project-root}/_bmad-output/projects/presenton-pixi-image/planning-artifacts/prd.md"
  - "{project-root}/CLAUDE.md (BMAD multi-project + conda-forge-expert integration rules)"
  - "{project-root}/docs/copilot-to-api.md"
  - "{project-root}/docs/specs/copilot-bridge-vscode-extension.md"
  - "{project-root}/pixi.toml (post-deckcraft additions)"
references:
  - "https://github.com/scanny/python-pptx — canonical PPTX engine (1.0.2, 2024-08-07; dormant but stable)"
  - "https://github.com/OscarPellicer/pptx2marp — Apache-2.0 code reference for PPTX↔Marp element mapping, multi-column heuristics, content-density font sizing"
  - "https://github.com/OscarPellicer/python-pptx — fork adding equation parsing + TIFF support; selective patches vendored as needed"
project_slug: "deckcraft"
---

# Product Brief: deckcraft

## Executive Summary

**Deckcraft** is an air-gapped, conda-forge-native AI pipeline that turns a prompt or source document (PDF / DOCX / PPTX / Markdown / URL) into an editable PowerPoint deck — with native shapes, real charts, vector infographics, and optional AI-generated images — plus a round-trippable Marp markdown source. It runs entirely on local hardware with local LLMs (llama.cpp by default, Ollama optional), produces output that PowerPoint users can hand-edit immediately, and exposes itself through every AI surface the user already has: Claude Code as a Skill, Claude Desktop and GitHub Copilot via MCP, MS365 Copilot via a connector, and a plain CLI for users with no AI tool at all.

Today, anyone in a regulated or air-gapped enterprise who wants AI-assisted slide creation has to choose between (a) cloud AI tools they're not allowed to use (Gamma, Beautiful.ai, Copilot Pages with cloud generation), (b) heavy turnkey web apps that need a Kubernetes cluster and a browser to use (Presenton — already being repackaged in this repo as `presenton-pixi-image`), or (c) hand-authoring slides with no AI help at all. Deckcraft is the missing fourth option: a primitive-level pipeline that's *embedded inside the AI assistants people already use*, runs as a single Python process on a laptop, and produces deliverables that are immediately editable in the tool everyone already has — Microsoft PowerPoint.

The build leans on infrastructure that already exists and is already working: 100% of dependencies are on conda-forge (verified package-by-package); the requester is a maintainer of three of them (`pdfplumber`, `weasyprint`, `fastmcp`); and the existing `local-recipes` pixi environment needs only six small additions to be deckcraft-ready. The project's value compounds with the requester's existing infrastructure (BMAD multi-project workspace, conda-forge factory, Claude/Copilot/MS365 access) rather than requiring new infrastructure.

## The Problem

Three concrete user scenarios drive this:

1. **The requester (and his colleagues), inside this repo, today.** He routinely needs to turn a PDF or a brain-dump into a slide deck. His IDE has Claude Code, GitHub Copilot Chat, and Copilot agents — all capable of writing prose. None can produce an editable `.pptx`. Today this means: prose in the IDE → manual paste-and-format in PowerPoint → 30–60 minutes of repetitive shape work per deck. The AI half-helps and then drops the user.

2. **Air-gapped enterprise colleagues.** They have GitHub Copilot subscriptions and MS365 Copilot, but their environments cannot reach `fal.ai`, OpenAI, Anthropic, Google, or any other public AI API. Cloud-only tools (Gamma, Beautiful.ai, GPT-PowerPoint, etc.) are unusable by policy. They have a working LLM stack (Copilot, llama.cpp, Ollama) but no path from "AI capable of writing prose" to "editable deck on disk."

3. **Authors of analytical / technical decks.** Even cloud tools rasterize their visuals or use proprietary shape formats. Mermaid diagrams come out as PNGs. Charts are screenshots. The output looks fine until you open it in PowerPoint and realize you can't edit a single thing without redoing it from scratch. Editability is a hard requirement that *everyone says they support* and *almost no one actually delivers*.

The cost of the status quo is small per deck (~30 min of fiddling) and large per organization (every employee, every week, multiplied by zero-marginal-cost AI assistance that can't reach the last mile). Worse, it's invisible: it shows up as "AI doesn't really help with slides" rather than as a fixable plumbing gap.

## The Solution

Deckcraft is the plumbing. A small, focused Python package built on conda-forge primitives:

- **Input**: a prompt, a document, a URL, an existing image, or any combination
- **Reasoning**: a local LLM you already have — `llama-server` (default), Ollama (optional), or any OpenAI-compatible endpoint; backend is a configuration choice, not a code choice
- **Renderers**: `python-pptx` for native DrawingML pptx, `marp-cli` for Marp markdown / pptx / pdf / html, `matplotlib` and `plotly` for charts, `mermaid-py` + headless `playwright` for diagrams, `diffusers` + SDXL-Turbo for optional photorealistic images, Ollama `qwen2.5vl:7b` (or llama.cpp equivalent) for image *understanding*
- **Surfaces**: a Claude Skill in this repo, an MCP server (stdio + HTTP) that any MCP-aware AI tool can call, a `typer` CLI for direct human invocation, a future VS Code extension for Copilot Chat slash commands, and a future Power Platform connector for MS365 Copilot

The user types one prompt. Deckcraft routes it to whichever surface they're in, the surface routes to a local LLM, the LLM produces structured slide JSON, the renderers turn it into a `.pptx` (and a Marp `.md`), images are generated where appropriate, and the user hand-edits in PowerPoint. Realistic wall-clock for a 10-slide deck on the requester's CPU-only Ryzen 7 7840HS: under 10 minutes (LLM-bound, no images); faster once iGPU compute is restored on a future kernel; image generation is opt-in and adds ~30–60 seconds per image.

A built-in V1 use case worth calling out: deckcraft accepts BMAD artifacts (`prd.md`, `epics.md`, `architecture.md`) as direct input, since the requester already produces those. "Make a deck from this PRD" is two lines of plumbing given the existing BMAD installation in this repo.

Critically: every shape, text box, chart, and diagram in the output PPTX is *real* PowerPoint geometry. Not screenshots. Not embedded SVGs that you have to "edit linked file." Editable.

## What Makes This Different

| Dimension | Cloud AI deck tools (Gamma, Beautiful.ai, Copilot Pages) | Turnkey self-host (Presenton, others) | Hand-rolled scripts | **Deckcraft** |
|---|---|---|---|---|
| Air-gapped | ✗ | ✓ (with significant integration work — see `presenton-pixi-image`) | ✓ | ✓ |
| Native editable PPTX (real DrawingML) | Partial; varies | Image-overlay-based currently | Author-dependent | ✓ Always |
| Embeds in user's existing AI tool | ✗ (their UI only) | ✗ (their UI only) | ✗ | ✓ (Claude / Copilot / MS365 / CLI) |
| Setup cost | None (cloud) | Container orchestrator + browser + LLM service | Per-script | One pixi env (already 95% installed in this repo) |
| Marp round-trip | ✗ | ✗ | Maybe | ✓ |
| Conda-forge native | ✗ | Bridges (per `presenton-pixi-image`) | Per-author | ✓ End-to-end |
| Vision-language input | Cloud only | Cloud only | Per-author | ✓ Local (qwen2.5vl) |

The unfair advantages are honest: (a) the requester has *already done the conda-forge dependency work* for adjacent projects (`pdfplumber`, `weasyprint`, `fastmcp` — he maintains them; the rest are verified present); (b) he has a *working multi-AI environment* (Claude Code + Copilot + MS365 — not many builders of this kind of tool have all three); (c) the BMAD-driven monorepo pattern in `local-recipes` makes it natural to ship deckcraft as both a Skill and a conda-forge package from the same PR; (d) `pydantic-ai` does the LLM-adapter abstraction work for free, so the "support multiple backends" promise is one library import, not an engineering effort.

There is no technology moat. There is an *integration* moat — the right primitives wired together for the right user, in the right place.

## Who This Serves

**Primary user — the builder himself (and direct colleagues).** Senior engineer, conda-forge maintainer, Framework Laptop 16 with 64 GB RAM, runs a multi-project BMAD workspace. Uses Claude Code daily, Copilot in IDE, MS365 Copilot in Office. Wants a tool that *fits inside his existing AI workflow* — not another browser tab to context-switch to. Success looks like: types "/deck Q3 status from notes/q3.md" in Claude Code, gets an editable `.pptx` in 3 minutes, hand-edits in PowerPoint, ships.

**Secondary user — air-gapped enterprise colleagues.** Same job functions, same need to make decks, but cannot reach public AI APIs. They have GitHub Copilot enterprise and MS365 Copilot. Success looks like: same flow as the builder, but invoked through the Copilot they already use, talking to an internal `llama-server` or LiteLLM proxy. Distribution to them: `conda install deckcraft` from the conda-forge mirror their org already pulls from, plus a VS Code extension or MS365 connector that gives them the entry point in their AI tool.

**Tertiary user — the open-source conda-forge community.** Once published, `conda install deckcraft` on any platform with conda-forge gives anyone the same pipeline. Adjacent: data scientists who already live in Python/conda environments and would happily generate decks from notebooks if the path were there.

## Success Criteria

**The primary criterion (everything else is supporting):** the requester is still using deckcraft to produce ≥1 real deck/week, 4 consecutive weeks after V1 ships. If this fails, no other metric saves the product — it joins the long list of devtools-built-by-engineers-for-themselves that died at the dogfooding step.

Supporting criteria:

| Metric | Target | Why this matters |
|---|---|---|
| End-to-end time, prompt → editable `.pptx` you'd actually ship | ≤ 30 minutes wall-clock total (deckcraft + manual editing) | Must beat the existing workaround (raw prose → manual PowerPoint), which is ~30–60 min. |
| LLM-only generation time (10-slide deck, no images) | < 10 minutes on CPU; < 2 minutes once iGPU compute restored | Sets the "feels fast enough to use" threshold. |
| Output editability | 100% of text / shapes / charts / diagrams are native DrawingML — zero rasterized | The non-negotiable; if this fails, the whole product is just another Gamma clone. |
| Output usefulness (subjective) | First-draft is at least 70% of the way to ship-ready (no need to throw away and start over) | Uselessness disguised as native-shape compliance still kills adoption. |
| Air-gapped functional parity | All non-cloud features identical when offline | Deckcraft must not silently degrade on the corporate laptop. |
| Distribution surfaces live | 3 of 6 (Claude Skill + MCP + CLI) by V1; 5 by V2 | Multi-surface is the differentiator — must be real, not aspirational. |
| Conda-forge package status | Recipe at `recipes/deckcraft/` accepted to staged-recipes | Distribution to colleagues depends on it. |
| Builder time investment | Estimated 6–10 weeks for V1 (pending story-level estimation in Architecture phase) | Beyond ~12 weeks, ROI degrades vs. just hand-editing slides. |

## Technical Approach

A thin Python package (`apps/deckcraft/`) with a layered architecture:

- **Core renderers**: `python-pptx` (native pptx), `marp-cli` (markdown→pptx/pdf/html), `matplotlib` + `plotly` (charts), `mermaid-py` + `playwright-python` (mermaid diagrams via headless Chromium with bundled mermaid.js, fully offline), `diffusers` + SDXL-Turbo (optional CPU image gen), `sentence-transformers` (long-document RAG fallback + slide dedup)
- **LLM adapter**: `pydantic-ai` over OpenAI-compatible HTTP. Default endpoint `llama-server` (conda-forge native, on-demand). Documented alternatives: Ollama (already running), LiteLLM proxy (deferred — pinned-dep conflict in conda-forge, revisit when relaxed)
- **Document ingestion**: `markitdown` (handles PDF/DOCX/PPTX/XLSX/HTML/etc. via local libraries; no cloud)
- **Vision**: Ollama `qwen2.5vl:7b` (or llama.cpp + mmproj) — purely for *understanding* input images, not generating them
- **PPTX engine**: `python-pptx` 1.0.2 (latest, conda-forge). Upstream is dormant but stable. Deckcraft wraps it behind a thin engine adapter so any future need (equation rendering, TIFF support, format edge cases) can be met by selectively vendoring patches from `OscarPellicer/python-pptx` or implementing inverses of `OscarPellicer/pptx2marp`'s element-mapping logic — without forking or replacing the upstream library wholesale. Build on the latest, vendor when needed, contribute back when worthwhile.
- **Surfaces**: `typer` CLI, `fastmcp` MCP server (stdio + HTTP transports), Claude Skill (`.claude/skills/deck-builder/`). Future: VS Code extension (reuses the existing `docs/specs/copilot-bridge-vscode-extension.md` 12-story spec as a basis, not greenfield); MS365 Power Platform connector (subject to tenant admin and Power Platform availability — flagged as discretionary, not a V1/V2 commitment).
- **Adjacent surfaces (free, pixi-kernel already installed)**: importable from Jupyter notebooks for data scientists who want to render slides from analysis output.
- **Distribution**: pip-installable from `pyproject.toml`, conda-installable via `recipes/deckcraft/recipe.yaml` (rattler-build v1).
- **Vision-stack note**: V1 vision goes through Ollama `qwen2.5vl:7b` because that's the simpler path. Equivalent via `llama-server --mmproj` is implementable but more setup work — promoted from optional to required if Ollama is removed in a future wave.

**Cross-platform support is V1 scope.** The pixi env declares `linux-64`, `osx-arm64`, `win-64`; every deckcraft dep has builds for all three. Three reference machines drive the hardware tier strategy:

| Tier | Reference machine | RAM | Compute | Default text/code/vision models |
|---|---|---|---|---|
| **small** | Windows 11 laptop, 32 GB | 32 GB | CPU (or NVIDIA via opt-in CUDA feature) | qwen3:8b / qwen2.5-coder:7b / qwen2.5vl:3b |
| **medium** | MacBook Pro M4, 48 GB | 48 GB unified | Metal via llama.cpp **OR** native MLX (`mlx-lm` on conda-forge for osx-arm64; 2–3× over llama.cpp for some workloads) | qwen3:14b / qwen2.5-coder:14b / qwen2.5vl:7b |
| **large** | Framework Laptop 16, 64 GB | 64 GB | CPU now, ROCm later (Phoenix MES firmware broken on Ubuntu HWE 6.17 today; ~10× speedup once fixed) | qwen3:30b / qwen3-coder / qwen2.5vl:7b |

V1 ships with the **small** tier as default — works on all three machines without per-platform tuning. `deckcraft init` auto-detects RAM and suggests upgrading the user's tier if appropriate. Backend selection per platform is automatic: Metal on macOS, Vulkan/CPU on Linux, CPU/CUDA on Windows. Output `.pptx` is byte-equivalent across platforms; only LLM-generated content varies.

## Relationship to `presenton-pixi-image`

Both projects target the same underlying pain (air-gapped enterprise needs editable AI-generated decks) but solve it differently:

- **`presenton-pixi-image`** (sibling project, already in PRD): repackages the upstream Presenton turnkey web app for OpenShift, replaces opaque components (`presenton-export` JS bundle, `convert-linux-x64` PyInstaller binary, LibreOffice) with conda-forge-native equivalents (`presenton-export-node`, `pptx-assembler`, `template-style-extractor`, `playwright-with-chromium`). Output: a self-contained container image that runs the Presenton web UI in air-gapped K8s.
- **Deckcraft**: a primitives-based pipeline, no web UI, designed to be embedded *inside the AI tools the user already has*. Output: a Python package and a set of AI-tool extensions.

They are complementary, not competitive: Presenton is for users who want a deck-builder web UI in their browser; deckcraft is for users who want deck-building inside their AI assistant. The overlap is intentional and shared infrastructure (e.g., `pptx-assembler` from the Presenton project is a candidate for deckcraft's pptx renderer; they may converge on the same library over time).

## Roadmap Thinking

**V1 (the CLI + Skill + MCP, ~9 weeks):** outline → editable pptx + Marp source; mermaid + matplotlib charts inline; document ingestion via markitdown; image *understanding* via Ollama qwen2.5vl; **image generation via SDXL-Turbo as opt-in default-off** (lazy-pulled weights); **bring-your-own style sources** — accept `.potx` / `.pptx` (template or `--as-sample`) / `.docx` (Word brand guide) / `.pdf` (with OCR fallback for scanned PDFs); stretch: `.odp` / `.odt`; legacy `.ppt`/`.doc` explicitly rejected with "save as .pptx/.docx" error. The `style_loader` is functionally the same package `presenton-pixi-image` plans as `template-style-extractor` — convergence is the V∞ goal; CLI + MCP server + Claude Skill; conda-forge recipe submitted.

**V2 (the surface expansion, ~3 weeks):** VS Code extension for Copilot Chat slash commands; expanded template library (corporate / technical / pitch / academic); LiteLLM-based routing once the conda-forge pin is relaxed; evaluate `Qwen/Qwen3-VL-Embedding-2B` as a unified replacement for `sentence-transformers` + parts of vision LLM (cross-modal retrieval).

**V3 (the enterprise reach, scope-dependent):** MS365 Copilot Power Platform connector; org-deployable package with audit logging and policy hooks.

**V∞ (where this becomes real infrastructure):** if dogfooding holds and adoption sticks, deckcraft becomes the *air-gapped equivalent of Gamma* — the boring, reliable plumbing that turns AI assistants into deck-producers across the enterprise. Convergence with `presenton-pixi-image` (shared `pptx-assembler`, shared template-style-extractor) is the natural endgame; both projects feeding into a common conda-forge ecosystem of editable-presentation primitives that any tool — web UI, IDE assistant, or notebook — can compose.

## Known Risks

- **First-deck friction.** Setup once: pull GGUF weights, wire up the Skill, debug the first prompt that doesn't produce what you want. This is at least an evening of work *before* deckcraft saves any time. If V1 ships and deck #1 is bad, the requester probably never gets to deck #4. **Mitigation**: V1 must include a "starter prompt" library and a corporate template (matching the requester's actual employer brand) so the first deck is plausible without any prompt-engineering.
- **Multi-surface maintenance burden.** Maintaining a Skill + MCP server + CLI + conda recipe + (later) VS Code ext + (later) MS365 connector is real ongoing work. For a 1×/week tool, the maintenance/use ratio degrades quickly. **Mitigation**: the BMAD ↔ conda-forge-expert retro discipline (CLAUDE.md) catches drift early; surfaces beyond V1's three are gated on actual demand.
- **MCP/Copilot maturity is unknown.** GitHub Copilot's MCP support went GA in VS Code 1.99 but real-world bug count and feature coverage are unproven. **Mitigation**: V1's MCP path is the stdio transport against Claude Code (most mature MCP host). Copilot/MS365 paths are V2+ and bumpable.
- **Image generation is opt-in default-off in V1 (post-update 2026-05-09).** SDXL-Turbo on CPU is ~30–60s/image — fine for occasional use, painful for many. Lazy-loaded weights mean users who never set the flag pay zero download cost; users who do (e.g., M4 owners where it's ~5–15s/image) get full J3 support. Dogfooding signal: do users actually flip the flag? If no, V2 either drops image gen or upgrades the model (FLUX.1-schnell / SD3.5).
- **Wall-clock estimates are unbenchmarked.** Brief uses "<10 min on CPU" for the LLM step; this is a calibration target, not a measurement. Architecture phase must produce an early benchmark on real hardware before the 6-week timeline is committed.
- **`python-pptx` upstream is dormant** (last release 1.0.2, 2024-08-07). No alternative exists for native-DrawingML output in Python. **Mitigation**: 1.0.2 is stable for current use cases; deckcraft wraps `pptx` behind an engine adapter so vendor-and-patch is a clean fallback. Existing forks (`OscarPellicer/python-pptx` for equations + TIFF) and reference projects (`OscarPellicer/pptx2marp` for element mappings, layout heuristics) are studied and selectively vendored as needed. Contributing fixes back upstream is the preferred long-term path.
- **Cross-platform fonts.** Calibri ships on Windows but not Linux/macOS by default; Helvetica is reverse. V1 templates default to fonts known-present on all three platforms (DejaVu family) to avoid silent rendering differences; users can override per template.

## Kill Criteria

The project pauses or rescopes if any of the following hold at week 6 post-V1:
- The requester is not using deckcraft for ≥1 real deck per week.
- The deck output requires more than 60 minutes of hand-editing to ship-ready (i.e., it's not actually faster than the existing prose-to-PowerPoint workaround).
- The maintenance burden (broken Skill, MCP issues, conda recipe drift) exceeds 1 hour/week.

In any of these cases the right move is to converge what's salvageable with `presenton-pixi-image` (shared `pptx-assembler` etc.) and shut down the standalone product. The dogfooding criterion is the master switch — every other metric is supporting evidence for or against it.
