---
date: 2026-05-09
project_name: deckcraft
totalSprints: 10
gateSprint: 1
totalEstimatedWeeks: 10
confidenceRange: "8.5–12 weeks (matches PRD SC-12 envelope)"
---

# deckcraft — Sprint Plan

**Generated:** 2026-05-09
**Cadence:** Weekly sprints, single-builder pace, ~5 working days per sprint.
**Total:** 10 sprints / 28 stories / ~10 weeks (inside 8.5–12 wk PRD SC-12 envelope).

---

## Sprint Overview

| # | Title | Stories | Effort | Critical-path | Notes |
|---|---|---|---|---|---|
| 1 | **GATE: Foundation + Spike-0** | S-1.1, S-1.2, S-1.5, S-1.4, S-1.3, S-6.1 | 5 days | YES (gates all subsequent) | Spike-0 PASS required to unlock Sprint 2+ |
| 2 | PPTX engine + Marp + Layout mapper | S-2.1, S-2.2, S-3.7 | 6 days | YES | Pipeline-blocking renderers + layout |
| 3 | Charts + Mermaid + Asset pipeline | S-2.3, S-2.4, S-2.5 | 7 days | partial | Renderers complete |
| 4 | Style loader (PPTX + DOCX + PDF) | S-3.1, S-3.2 | 7 days | YES (style integration in pipeline) | BYO style sources land |
| 5 | Retrieval + Outline | S-3.3, S-3.4 | 7 days | YES | LLM content gen + RAG |
| 6 | Vision + Image gen | S-3.5, S-3.6 | 6 days | partial | Optional capabilities |
| 7 | Pipeline + CLI | S-4.1, S-4.2 | 6 days | YES | First end-to-end runnable |
| 8 | MCP server + Claude Skill | S-4.3, S-4.4 | 4 days | partial | AI-surface integration |
| 9 | Recipe + Templates + Docs | S-5.1, S-5.2, S-5.3 | 5 days | YES (S-5.1 = release) | Distribution stories; CLAUDE.md Rule 1+2 invoked in S-5.1 |
| 10 | Polish: Benchmarks + Tests + CI | S-6.2, S-6.3, S-6.4, S-6.5, S-6.6 | 7 days | partial | Quality gates; V1 release prep |

**Total:** 28 stories, ~60 person-days = ~10 single-builder weeks (5 days/week pace).

---

## Sprint-by-Sprint Detail

### Sprint 1 — GATE: Foundation + Spike-0

**Goal:** Establish project skeleton + LLM adapter + run Spike-0 benchmark to validate timeline before committing to E2-E6.

| Story | Title | Effort | Deps | Notes |
|---|---|---|---|---|
| S-1.1 | Project scaffolding | S | none | Day 1 |
| S-1.2 | Platform adapter | M | S-1.1 | Days 1-2 |
| S-1.5 | Pydantic data model | M | S-1.1 | Days 2-3 (parallel with S-1.2) |
| S-1.4 | Document extractor | S | S-1.1, S-1.2 | Day 3 |
| S-1.3 | LLM adapter layer (4 backends) | L | S-1.1, S-1.2 | Days 3-4 |
| S-6.1 | **Spike-0 benchmark** (qwen3:30b outline gen ≤8 min on Framework CPU) | XS | S-1.3 | Day 5 — **GATE** |

**Architecture decisions exercised:** AD-01 (layered), AD-02 (LLM backend selection), AD-03 (model selection), AD-06 (Spike-0), AD-14 (tier detect), AD-15 (air-gap mechanics). Patterns established: P-01 through P-10 (foundation laid).

**Sprint 1 exit criteria:**
- S-6.1 PASS (Spike-0 ≤ 8 min outline gen) → Sprint 2 unlocked
- S-6.1 FAIL → re-tier qwen3:30b → qwen3:14b on Framework, update PRD SC-02/SC-12, then Sprint 2 unlocks

### Sprint 2 — PPTX engine + Marp + Layout mapper

**Goal:** Editable-pptx production capability + Marp markdown round-trip + LLM-guided layout selection.

| Story | Title | Effort | Deps |
|---|---|---|---|
| S-2.1 | PPTX engine adapter (wraps python-pptx, vendor-fallback hooks) | M | S-1.5 |
| S-2.2 | Marp engine (subprocess to marp-cli) | M | S-1.5 |
| S-3.7 | Layout mapper + bundled templates | M | S-1.3, S-1.5, S-2.1 |

**Architecture decisions exercised:** AD-07 (vendor trigger), AD-11 (layout mapping protocol). Patterns enforced: P-01 (no `import pptx` outside engine), P-02 (LLM via adapter for layout-mapping prompt), P-04 (subprocess to marp-cli).

**Carryover:** S-3.7 lists default templates as a sub-deliverable; S-5.2 (E5) refines them later. Per readiness SF-B, treat S-5.2 as "templates polished for distribution" — Sprint 2 ships a working stub.

### Sprint 3 — Charts + Mermaid + Asset pipeline

**Goal:** All non-text rendering capabilities online with caching.

| Story | Title | Effort | Deps |
|---|---|---|---|
| S-2.3 | Chart renderer (matplotlib + plotly, native PowerPoint charts where fit) | M | S-1.5, S-2.1 |
| S-2.4 | Mermaid renderer (mermaid-py + playwright headless, fully offline) | M | S-1.5, S-2.1 |
| S-2.5 | Asset pipeline with caching + graceful degradation | M | S-2.3, S-2.4 |

**Architecture decisions exercised:** A-04 (asset pipeline caching). Patterns enforced: P-06 (graceful degrade), P-07 (offline gate; mermaid local-only), P-08 (asset cache discipline).

### Sprint 4 — Style loader (PPTX + DOCX + PDF)

**Goal:** All BYO style sources working; FR-52 common JSON shape established.

| Story | Title | Effort | Deps |
|---|---|---|---|
| S-3.1 | Style loader — PPTX/DOCX | L | S-1.5, S-2.1 |
| S-3.2 | Style loader — PDF (with OCR fallback) | M | S-3.1 |

**Architecture decisions exercised:** AD-13 (PDF extraction decision tree), AD-10 (ODP/ODT correctly absent — V2). Patterns enforced: P-05 (Pydantic boundary).

### Sprint 5 — Retrieval + Outline

**Goal:** Long-document RAG and LLM-driven content generation.

| Story | Title | Effort | Deps |
|---|---|---|---|
| S-3.3 | Retrieval (sentence-transformers RAG + slide dedup) | M | S-1.5, S-1.4 |
| S-3.4 | Outline generator (prompts + JSON-schema-validated output) | L | S-1.3, S-1.4, S-1.5, S-3.3 |

**Architecture decisions exercised:** AD-03 (embedding model selection — `all-MiniLM-L6-v2`). Per readiness SF-C: S-3.3 should add per-tier RAG thresholds (small=24K, medium=48K, large=96K) — captured here as a story-level acceptance criterion to add at sprint kickoff.

### Sprint 6 — Vision + Image gen

**Goal:** Optional AI capabilities (image understanding + generation).

| Story | Title | Effort | Deps |
|---|---|---|---|
| S-3.5 | Image understander (Ollama qwen2.5vl + llama.cpp mmproj fallback) | M | S-1.3 |
| S-3.6 | Image generator (diffusers + SDXL-Turbo, opt-in default-off, lazy-load) | M | S-1.2, S-2.5 |

**Architecture decisions exercised:** AD-12 (image-gen lazy-load mechanism). Patterns enforced: P-06 (image-gen failure → placeholder + warning), P-07 (offline gate for SDXL-Turbo download).

### Sprint 7 — Pipeline + CLI

**Goal:** First end-to-end runnable deckcraft. The user can produce a real deck after this sprint.

| Story | Title | Effort | Deps |
|---|---|---|---|
| S-4.1 | Pipeline class (high-level public API) | M | S-1.4, S-3.1, S-3.4, S-3.7, S-2.5, S-2.1, S-2.2 |
| S-4.2 | CLI (typer-based) | M | S-4.1, S-3.5 |

**Milestone:** End of Sprint 7 = `deckcraft generate --input /path/to/doc.pdf --out deck.pptx` works end-to-end. **First dogfoodable build.**

### Sprint 8 — MCP server + Claude Skill

**Goal:** Multi-AI surface integration.

| Story | Title | Effort | Deps |
|---|---|---|---|
| S-4.3 | MCP server (fastmcp stdio) | M | S-4.1, S-3.5 |
| S-4.4 | Claude Skill (.claude/skills/deck-builder/) | S | S-4.2 |

**Architecture decisions exercised:** AD-04 (MCP HTTP slipped to V2; stdio only). End of Sprint 8: Claude Code session can invoke deckcraft via `make me a deck about X`.

### Sprint 9 — Recipe + Templates + Docs

**Goal:** Distributable V1.

| Story | Title | Effort | Deps |
|---|---|---|---|
| S-5.1 | conda-forge recipe (invokes conda-forge-expert per CLAUDE.md Rule 1) | M | S-4.1, S-4.2, S-4.3 |
| S-5.2 | Default templates (default-professional + bmad-prd-pitch .potx) | S | S-2.1 |
| S-5.3 | README + air-gapped guide + BYO style guide | M | S-4.2 |

**CLAUDE.md compliance:** S-5.1 invokes `conda-forge-expert` skill before producing recipe content (Rule 1). Closeout retro per Rule 2 happens in Sprint 10.

### Sprint 10 — Polish: Benchmarks + Tests + CI

**Goal:** V1 release-quality.

| Story | Title | Effort | Deps |
|---|---|---|---|
| S-6.2 | Spike-1 + Spike-2 benchmarks (full deck, per-machine) | S | S-4.1 |
| S-6.3 | Pattern enforcement test suite (P-01 through P-10) | M | All E1-E4 |
| S-6.4 | Cross-platform CI matrix | M | S-6.3, S-6.5, S-6.6 |
| S-6.5 | Air-gapped CI under unshare -n | M | S-6.6 |
| S-6.6 | Golden-path test fixtures | M | S-4.1 |

**End of Sprint 10 = V1 release.**

**CLAUDE.md Rule 2 compliance:** Final retrospective via `bmad-retrospective` skill at end of Sprint 10. Updates `.claude/skills/conda-forge-expert/` with any findings from S-5.1.

---

## Inter-sprint dependencies (DAG implications)

- Sprint 1 → ALL (gate)
- Sprint 2 → Sprint 4, Sprint 5, Sprint 7 (pptx engine + layout mapper required)
- Sprint 3 → Sprint 6, Sprint 7 (asset pipeline required)
- Sprint 4 → Sprint 7 (style loader required for pipeline)
- Sprint 5 → Sprint 7 (outline + retrieval required for pipeline)
- Sprint 6 → Sprint 10 (image-gen needs perf benchmarks)
- Sprint 7 → Sprints 8, 9, 10 (pipeline must work first)
- Sprint 8 → Sprint 9 (MCP + Skill before recipe submission)
- Sprint 9 → Sprint 10 (recipe + docs before polish)

---

## Dogfooding milestone

**End of Sprint 7 = first dogfoodable build.** The requester should generate at least one real deck during Sprint 7 to validate the J1 happy path before Sprint 8's surface work begins. If Sprint 7's dogfooding signal is bad (deck too poor to ship), pause Sprint 8+ and revisit outline/render quality in Sprint 7.5.

---

## Per-sprint architecture / pattern tracker

| Sprint | ADs exercised | Patterns enforced |
|---|---|---|
| 1 | AD-01, AD-02, AD-03, AD-06, AD-14, AD-15 | P-01 to P-10 (foundation) |
| 2 | AD-07, AD-11 | P-01, P-02, P-04 |
| 3 | A-04 (asset pipeline) | P-06, P-07, P-08 |
| 4 | AD-13 | P-05 |
| 5 | AD-03 (embedding) | P-02, P-05 |
| 6 | AD-12 | P-06, P-07 |
| 7 | AD-01 (pipeline integration) | P-05 |
| 8 | AD-04 | P-05 |
| 9 | DR-04, DR-06 (CLAUDE.md Rule 1) | n/a |
| 10 | AD-06 (full benchmarks), DR-07 (CLAUDE.md Rule 2 retro) | All P-01 to P-10 enforced via S-6.3 |

---

## JSON output

```json
{
  "status": "complete",
  "sprintPlan": "_bmad-output/projects/deckcraft/planning-artifacts/sprint-status.md",
  "yamlStatus": "_bmad-output/projects/deckcraft/implementation-artifacts/sprint-status.yaml",
  "totalSprints": 10,
  "totalStories": 28,
  "totalWeeks": 10,
  "confidenceRange": "8.5–12 weeks (PRD SC-12)",
  "gateSprint": 1,
  "gateExitCriteria": "S-6.1 (Spike-0) PASS — qwen3:30b outline gen ≤8 min on Framework CPU",
  "dogfoodingMilestone": "End of Sprint 7 (first end-to-end runnable)",
  "v1ReleaseMilestone": "End of Sprint 10",
  "claudeMdRule1": "S-5.1 invokes conda-forge-expert skill",
  "claudeMdRule2": "Final retrospective at end of Sprint 10",
  "next": "bmad-generate-project-context"
}
```
