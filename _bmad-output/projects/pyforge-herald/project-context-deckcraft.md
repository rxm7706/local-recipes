---
project: deckcraft
created: 2026-05-09
status: planning-complete-implementation-pending
purpose: "Token-efficient persistent context for future Claude Code / BMAD sessions per CLAUDE.md persistent_facts pattern"
---

# deckcraft — Project Context

**Air-gapped, conda-forge-native AI pipeline that turns prompts/documents into editable PowerPoint decks (with Marp markdown sidecars), running 100% on local LLMs across Linux/macOS/Windows.** Multi-AI surface (Claude Skill + MCP server + CLI) for Claude Code / Copilot / MS365. Output is native DrawingML — every text/shape/chart/diagram editable in PowerPoint. BYO style sources (`.potx` / `.pptx` / `.docx` / `.pdf`).

## Status

| Item | Value |
|---|---|
| BMAD planning chain | ✅ COMPLETE (brief → distillate → PRD → validation PASS → architecture → epics → readiness READY_WITH_CAVEATS → sprint plan → this context) |
| Implementation | ⏳ Sprint 1 ready to start; Spike-0 (S-6.1) is the gate |
| V1 timeline | 8.5–12 weeks (10-sprint plan) |
| V1 release target | end of Sprint 10 |
| Active project marker | `scripts/bmad-switch deckcraft` already set |

## File-Pointer Index

| Artifact | Path | Why read |
|---|---|---|
| Product brief (executive vision) | `_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft.md` | What & why |
| Distillate (locked decisions, rejected approaches, hardware tiers, reference projects) | `_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft-distillate.md` | Don't re-discover anything captured here |
| PRD (52 FRs / 23 NFRs / scoping) | `_bmad-output/projects/deckcraft/planning-artifacts/prd.md` | Capability contract; binding |
| PRD validation report | `_bmad-output/projects/deckcraft/planning-artifacts/prd-validation.md` | Gate decision PASS |
| Architecture (15 ADs / 10 patterns / 26 modules / 6 waves) | `_bmad-output/projects/deckcraft/planning-artifacts/architecture.md` | All implementation patterns; binding |
| Epic breakdown (28 stories with acceptance criteria) | `_bmad-output/projects/deckcraft/planning-artifacts/epics.md` | Story-level spec for dev work |
| Implementation readiness | `_bmad-output/projects/deckcraft/planning-artifacts/implementation-readiness.md` | Gate decision READY_WITH_CAVEATS; SF-A/B/C noted |
| Sprint plan (markdown) | `_bmad-output/projects/deckcraft/planning-artifacts/sprint-status.md` | Sprint sequencing + critical path |
| Sprint status (machine-readable) | `_bmad-output/projects/deckcraft/implementation-artifacts/sprint-status.yaml` | dev-story tracker; agents update this |
| pixi.toml deckcraft additions | `pixi.toml` lines ~512–540 | Env truth source (matplotlib, plotly, transformers, accelerate, playwright-python, ollama-python, hf-transfer, sentencepiece, sentence-transformers, pytesseract, odfpy, mlx + mlx-lm on linux+osx) |

## Locked Decisions (do not re-discover)

- **PPTX engine:** `python-pptx` 1.0.2 (latest, conda-forge, dormant since 2024-08-07) wrapped behind `pptx_engine` adapter (FR-15) for vendor-fallback per AD-07 trigger criteria.
- **LLM adapter:** `pydantic-ai` over OpenAI-compat HTTP. Default `llama-server` (conda-forge); alt Ollama; macOS-preferred `mlx-lm` (selection logic AD-02). LiteLLM deferred (pydantic pin conflict).
- **Hardware tiers:** small (32 GB → qwen3:8b/qwen2.5-coder:7b/qwen2.5-vl:3b), medium (48 GB M4 → 14B/14B/7B), large (64 GB → 30B/30B/7B). `deckcraft init` auto-detects per AD-14 thresholds.
- **Cross-platform:** linux-64 / osx-arm64 / win-64. mlx + mlx-lm linux-64 + osx-arm64 only (Windows excluded by upstream skip rule). macOS minimum 14.5.
- **BYO style sources V1:** `.potx`, `.pptx` (template + `--as-sample`), `.docx`, `.pdf` (with pytesseract OCR fallback per AD-13). `.odp`/`.odt` slipped to V2 per AD-10 (timeline rescope).
- **Image gen:** SDXL-Turbo via `diffusers`, opt-in default-off, lazy-load weights (AD-12).
- **Long-document RAG:** `sentence-transformers/all-MiniLM-L6-v2` (per-tier thresholds: small=24K, medium=48K, large=96K — readiness SF-C).
- **Vision:** Ollama `qwen2.5vl:3b` (small) / `:7b` (medium+large).
- **Distribution V1:** Claude Skill + MCP stdio + CLI + conda-forge recipe. MCP HTTP V2 (AD-04). VS Code ext V2 VSIX-only (AD-09). MS365 V3.
- **conda-forge purity:** every runtime dep from conda-forge. Verified package-by-package.
- **Air-gapped:** mandatory default. `DECKCRAFT_OFFLINE=1` env + `DECKCRAFT_MODEL_DIR` + `unshare -n` CI test (AD-15).
- **Convergence target:** `style_loader` ↔ `presenton-pixi-image`'s `template-style-extractor` → shared `pptx-style-toolkit` library at V∞ (FR-52 common JSON schema is the integration contract).

## Conflict-Prevention Patterns (P-01 through P-10)

Enforced by `apps/deckcraft/tests/test_patterns.py` (story S-6.3). Non-negotiable. Most relevant for any agent writing deckcraft code:

| ID | Rule |
|---|---|
| P-01 | All `pptx` access via `deckcraft.engines.pptx_engine` adapter — NO `import pptx` outside engine |
| P-02 | All LLM calls via `pydantic-ai` through `LLMAdapter` — NO direct httpx to LLM ports, NO direct ollama/anthropic SDK imports in business code |
| P-03 | All paths via `pathlib.Path` + `platformdirs` — no string concat, no Linux-isms |
| P-04 | Subprocess: `subprocess.run(..., check=True, text=True)`, `shell=False`, list-form args |
| P-05 | All inter-module data is Pydantic (JSON-serializable) — no DataFrame across boundaries |
| P-06 | Optional capabilities use `OptionalCapability` decorator (FR-26 graceful degrade) |
| P-07 | All network-touching adapters consult `_check_offline_gate()` — DR-01 air-gap |
| P-08 | Asset rendering via `asset_pipeline.render()` — content-addressed cache |
| P-09 | All datetimes `datetime.now(timezone.utc)` — no naive |
| P-10 | Structured logging via `structlog` or `logging` — no `print()` in prod code |

## CLAUDE.md Compliance Hooks

- **S-5.1 (conda-forge recipe story)** — must invoke `conda-forge-expert` skill per CLAUDE.md Rule 1 BEFORE producing recipe content.
- **End of Sprint 10** — final retrospective via `bmad-retrospective` skill per CLAUDE.md Rule 2; updates `.claude/skills/conda-forge-expert/` with any findings, CHANGELOG entry + version bump.
- **Active project resolution:** `scripts/bmad-switch --current` should return `deckcraft` for this work; if not, run `scripts/bmad-switch deckcraft` first.

## Critical Path & Next Dev Action

**Sprint 1 (current): foundation + Spike-0 GATE.** Next stories ready to start:

1. **S-1.1** Project scaffolding at `apps/deckcraft/` (XS effort)
2. **S-1.2** Platform adapter (M; deps S-1.1)
3. **S-1.5** Pydantic data model (M; deps S-1.1) — parallel with S-1.2
4. **S-1.4** Document extractor (S; deps S-1.1, S-1.2)
5. **S-1.3** LLM adapter layer (L; deps S-1.1, S-1.2)
6. **S-6.1 Spike-0** benchmark (XS but GATE; deps S-1.3) — must pass before Sprint 2

**Spike-0 pass criterion:** `qwen3:30b-instruct-q4_k_m` outline gen (10-slide deck, exec audience) ≤ 8 minutes wall-clock on Framework Laptop 16 CPU.

**If Spike-0 fails:** re-tier large→medium on Framework (use qwen3:14b), update PRD SC-02/SC-12, then proceed to Sprint 2. NOT a project killer; an architectural amendment.

## Kill Criteria (Per PRD)

Project paused or rescoped if any of these hold at week 6 post-V1:
- Requester not using deckcraft for ≥1 real deck/week
- Decks take > 60 min hand-editing to ship-ready
- Maintenance burden > 1 hr/week

If triggered: converge what's salvageable into shared `pptx-style-toolkit` with `presenton-pixi-image`, shut down standalone deckcraft.

## How Future Agents Should Use This

1. **Open PRD + architecture + epics in this order** when working a deckcraft story — they have everything needed
2. **Find the story** in `epics.md` (S-N.M format) — has acceptance criteria + deps + FR/AD references
3. **Update sprint-status.yaml** as story status changes (backlog → ready-for-dev → in-progress → review → done)
4. **Enforce P-01 through P-10 patterns** in every code change
5. **For conda-forge work**, invoke `conda-forge-expert` skill (CLAUDE.md Rule 1) — applies anywhere in this repo
6. **For any deckcraft story, after merge,** consider whether a CFE-skill retro is warranted (CLAUDE.md Rule 2 if conda-forge-touching)

---

```json
{
  "status": "complete",
  "projectContext": "_bmad-output/projects/deckcraft/project-context.md",
  "bmadPlanningStatus": "COMPLETE for deckcraft V1",
  "planningArtifactsCount": 8,
  "implementationArtifactsCount": 1,
  "totalStoriesPlanned": 28,
  "totalSprintsPlanned": 10,
  "nextDevAction": "Begin Sprint 1: S-1.1 project scaffolding → ... → S-6.1 Spike-0 GATE",
  "blockerToImplementationStart": "none",
  "claudeMdRule1Hook": "S-5.1 (conda-forge recipe story)",
  "claudeMdRule2Hook": "End of Sprint 10 (final retrospective)"
}
```
