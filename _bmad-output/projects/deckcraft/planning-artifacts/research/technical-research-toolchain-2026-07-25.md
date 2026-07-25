---
title: "Technical Research: deckcraft V1 Core Toolchain Viability Check"
research_type: technical
project: deckcraft
date: 2026-07-25
inputs:
  - "_bmad-output/projects/deckcraft/planning-artifacts/prd.md (authored 2026-05-09)"
  - "_bmad-output/projects/deckcraft/planning-artifacts/architecture.md (authored 2026-05-09)"
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft.md"
  - "docs/dreams/deckcraft.md, docs/dreams/modernist-identity.md"
  - "docs/intake/gists/open-source-powerpoint-agent-skills/Open-Source_PowerPoint_Agent_Skills.md"
  - "pixi.toml (post-deckcraft additions, current lockfile state)"
methodology: "gh api / gh search (GitHub REST + code search) + WebFetch against PyPI project pages; WebSearch was unavailable (session budget exhausted before this run started)"
---

# Technical Research: deckcraft V1 Core Toolchain Viability Check

## Executive Summary

Deckcraft has not started implementation (`apps/deckcraft/`, `recipes/deckcraft/` do not exist yet; `sprint-status.md` shows 0/28 stories started). This research re-verifies, 11 weeks after the PRD/architecture were authored (2026-05-09), whether the locked toolchain bets are still sound before the build slot arrives.

**Bottom line: the core bets hold.** Every pinned runtime dependency in `pixi.toml` still resolves to a current, actively-licensed release, and `python-pptx`'s dormancy — the architecture's single biggest named risk — is not just confirmed but *worse* than described (534 open issues, zero commits since 2024-08-07, now closing in on two years quiet). Two findings are new and actionable:

1. **A license landmine in an already-pinned dependency.** `pymupdf` (used for `FR-46c` PDF style extraction) is dual-licensed **AGPL-3.0 / Artifex commercial**, not MIT/Apache-2.0. This directly conflicts with the project's own founding constraint (the intake gist's acceptance criterion: "must contain exactly zero proprietary code... must be MIT or Apache 2.0") and is the kind of dependency that killed deckcraft's predecessor tool. Neither the PRD, the architecture, nor `pixi.toml`'s inline comments flag this.
2. **A dominant new open-source competitor has emerged since the PRD was written.** `hugohe3/ppt-master` — the intake gist's "Option C," cited then as a minor drop-in skill — has grown to **41,032 GitHub stars and 3,406 forks in under 8 months** (created 2025-12-10, still pushed today), is genuinely MIT-licensed, and now claims most of deckcraft's own differentiators (native shapes, transitions, charts/tables on demand, BYO templates). This changes the competitive framing materially — see the companion domain-research report.

One PRD claim is now stale: `fastmcp` is quoted in the PRD (line 230) as "v3.2.4" — current PyPI latest is **3.4.4** (`pixi.toml` already tracks `>=3.4.4`, so the *build* is fine; only the PRD's prose citation is dated).

No dependency has been abandoned, relicensed unfavorably (other than the pre-existing pymupdf finding), or lost conda-forge availability since May. The Spike-0 benchmark gate (AD-06) has still not been run — it remains the correct first action whenever implementation starts.

---

## Table of Contents

1. Methodology & Constraints
2. Per-Dependency Findings (the locked V1 stack)
3. New Finding: pymupdf's AGPL/commercial license
4. New Finding: Design-tokens ↔ POTX round-trip viability
5. New Entrants Since May 2026 (PPTX agent skills / MCP servers)
6. Air-Gap / Offline Feasibility Recheck
7. Recommendations

---

## 1. Methodology & Constraints

This session's `WebSearch` tool reported its budget exhausted (200/200 calls used elsewhere in the session) before any query could run. Research instead used:
- `WebFetch` against PyPI project pages (renders current version, release date, license classifier)
- `gh api` / `gh search repos` against the GitHub REST/search API (renders `pushed_at`, license SPDX, archived status, star/fork counts, and file contents for feedstock recipes)

Both are live, current-as-of-2026-07-25 sources, not training-data recall. Every claim below is sourced to one of these two mechanisms. Where a claim could not be independently re-verified (e.g., internal precedent for the tokens-to-potx pipeline, which lives in an external Claude Design project not present in this repo's filesystem), that is stated explicitly as a gap rather than asserted.

---

## 2. Per-Dependency Findings (the locked V1 stack)

All versions below are compared against the pin in `pixi.toml` (already reflects deckcraft additions) and the narrative claims in `product-brief-deckcraft.md` / `prd.md` / `architecture.md`.

| Dependency | Role in deckcraft | pixi.toml pin | Verified current (2026-07-25) | License | Status vs. PRD/architecture claim |
|---|---|---|---|---|---|
| `python-pptx` | Core PPTX engine (FR-15, wrapped by `pptx_engine` adapter) | `>=1.0.2` | **1.0.2**, released 2024-08-07 (PyPI). GitHub: `pushed_at` 2024-08-07, **534 open issues**, no commits since | MIT | **CONFIRMED, worse than stated.** PRD/architecture call it "dormant since 2024-08-07" — true, and now ~23 months quiet with issue backlog growing. AD-07's vendor-trigger criteria remain the correct mitigation; no upstream signal of revival. |
| `markitdown` | Document ingestion (FR-01–FR-08) | `>=0.1.6` | **0.1.6**, released 2026-05-26 (PyPI) | MIT | CONFIRMED current — this is in fact the latest release, and it postdates the PRD (2026-05-09), meaning the pin is already the freshest available. |
| `fastmcp` | MCP server surface (FR-39/40) | `>=3.4.4` | **3.4.4**, released 2026-07-09 (PyPI) | Apache-2.0 | **DATED PRD citation.** PRD line 230 says "requester-maintained at v3.2.4" — that's the version at authoring time; `pixi.toml` has already moved the pin to `>=3.4.4` and current PyPI matches. Build is fine; only the PRD prose is stale. |
| `pydantic-ai` | LLM adapter (FR-33/34) | `>=2.15.0` | **2.18.0**, released 2026-07-25 (today) (PyPI) | MIT | CONFIRMED, actively released (shipped a version the same day as this research). Pin is a floor, not exact — no action needed. |
| `mermaid-py` | Diagram rendering (FR-16/17) | `>=0.8.4` | **0.8.4**, released 2026-03-09 (PyPI) | MIT | CONFIRMED — pin matches latest exactly. |
| `diffusers` | Image gen engine (FR-19/20) | `>=0.39.0` | **0.39.0**, released 2026-07-03 (PyPI) | Apache-2.0 | CONFIRMED — pin matches latest exactly. |
| `sentence-transformers` | RAG/dedup (FR-43/44) | `>=5.6.0` | **5.6.1**, released 2026-07-23 (PyPI) | Apache-2.0 | CONFIRMED, minor patch ahead of floor pin — no action needed. |
| `mlx-lm` | macOS LLM backend (AD-02) | `>=0.31.3` | **0.31.3**, released 2026-04-22 (PyPI) | MIT | CONFIRMED — pin matches latest exactly. |
| `llama.cpp` | Default LLM backend (FR-34) | `>=10003` | GitHub `ggml-org/llama.cpp` pushed **today** (2026-07-25), 1,910 open issues (large, active project — issue count is normal for this project's scale) | MIT | CONFIRMED, very actively maintained. No concerns. |
| `python-docx` | `.docx` style extraction (FR-48) | `>=1.2.0` | GitHub `python-openxml/python-docx` last push 2025-06-17 (~13 months quiet), 504 open issues | MIT | **Mild aging signal**, not dormancy on python-pptx's scale. Worth a watch note, not an architecture change — the project shipped no PRD/architecture claim about python-docx's maintenance cadence, so nothing is contradicted. |
| `pymupdf` | PDF style extraction (FR-46c) | `>=1.28.0` | GitHub `pymupdf/PyMuPDF` pushed 2026-07-24, very active | **AGPL-3.0 / Artifex commercial dual license** | **See § 3 — new finding, not previously flagged.** |
| `marp-cli` | Marp render engine (FR-23/24) | `>=4.2.3` | Upstream GitHub latest release **v4.5.0** (2026-07-17); conda-forge feedstock still pinned at **4.2.3** (verified via feedstock recipe) | MIT | Informational only: conda-forge packaging lags upstream by 3 minor versions. This is an upstream-feedstock timing gap, not a deckcraft-side action — the pin is `>=4.2.3` so no build break, and `presentation-deck.md`'s existing marp workflow already targets 4.2.3 successfully. |
| `pptxgenjs` | *Not consumed by deckcraft's architecture* | `>=4.0.1` (via non-standard `SelfExplainML` conda channel — **no conda-forge feedstock exists**, confirmed 404) | GitHub `gitbrent/PptxGenJS` latest release v4.0.1 (2025-06-26), pushed 2025-11-28 | MIT | **Scope clarification, not a contradiction.** `pptxgenjs` appears in the Dream's toolchain inventory (`docs/dreams/deckcraft.md`) but is absent from every PRD/architecture FR/AD — deckcraft's own renderer is exclusively `python-pptx`. It was added to `pixi.toml` for the intake gist's "Option E" reference evaluation (ppt-master lineage), not as a deckcraft runtime dependency. Its off-conda-forge channel is real but doesn't touch DR-02 ("all runtime dependencies from conda-forge") since it isn't a runtime dependency of deckcraft itself. |
| `ollama` (Go server) | Vision backend (FR-21/22) | present | GitHub `ollama/ollama` pushed 2026-07-25 (today), 3,520 open issues (normal for project scale) | MIT | CONFIRMED, very active. |
| `litellm` | Deferred per architecture (pydantic pin conflict) | commented out, not added | conda-forge feedstock still pinned at **1.93.0** (recipe verified); upstream `pyproject.toml` requires `pydantic>=2.10.0,<3.0.0` | MIT | **CONFIRMED still deferred correctly.** The conda-forge feedstock has not caught up to relax whatever pin conflict motivated the original deferral — AD's "revisit when conda-forge litellm relaxes the pydantic pin" gating criterion has not fired. No action needed; decision stands. |

**Net assessment:** every FR/AD tied to a specific dependency version in the PRD and architecture remains buildable today. The only genuine drift is the two items called out below.

---

## 3. New Finding: `pymupdf`'s AGPL/commercial license (contradicts a founding constraint)

**What was verified:** PyPI's project page for `pymupdf` states the license as *"Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License."* This is confirmed directly from the package's own PyPI metadata, not a secondary source.

**Why it matters:** deckcraft's own origin document — `docs/intake/gists/open-source-powerpoint-agent-skills/Open-Source_PowerPoint_Agent_Skills.md`, § 4 Acceptance Criteria — states: *"License Check: The final integrated solution must contain exactly zero proprietary code (must be MIT or Apache 2.0)."* That constraint was the explicit reason deckcraft exists at all (the prior `document-skills/pptx` tool was rejected for being Anthropic-proprietary). AGPL-3.0 is not proprietary, but it is a strong network-copyleft license that many organizations — including regulated/air-gapped enterprises, deckcraft's own secondary user segment — treat as equally blocking for embedding in a distributed tool, because AGPL's copyleft obligations can propagate to combined works. `pymupdf` is currently a **hard runtime dependency** for `FR-46c` (PDF style extraction with OCR fallback), pinned in `pixi.toml` (`pymupdf = ">=1.28.0"`) and named explicitly in `architecture.md`'s AD-13 decision tree and dependency inventory. Neither the PRD, the architecture, nor the pixi.toml inline comment flags the license.

**This CONTRADICTS an unstated-but-load-bearing assumption**, not an explicit FR — no FR claims "all deps are MIT/Apache," but DR-02 ("all runtime dependencies must come from conda-forge") and the founding intake gist's acceptance criterion together imply exactly that bar, and `pymupdf` misses it.

**Mitigation options for the operator to weigh at story-kickoff (S-3.2, PDF style loader):**
- Accept AGPL for this one optional-capability path (FR-46c is already gated as a `--style <path>.pdf` opt-in, not core-path) and document the exception explicitly, OR
- Swap to `pdfplumber` (already a runtime dep elsewhere in the env, requester-maintained, MIT-family) for font/color sampling — weaker layout-pattern inference than `pymupdf` but license-clean, OR
- Purchase/negotiate the Artifex commercial license if `pymupdf`'s superior extraction quality is worth it for an internal/enterprise deployment (not compatible with a permissively-licensed public conda-forge recipe, though — DR-04 wants `recipes/deckcraft/` accepted to staged-recipes, and conda-forge itself is fine hosting AGPL packages as a *dependency*, so this is a redistribution-of-deckcraft concern, not a conda-forge-acceptance concern).

This is a decision for the human operator (license risk tolerance), not something this research resolves — flagged for `plan-validation-notes-2026-07-25.md`.

---

## 4. New Finding: Design-tokens ↔ POTX round-trip viability

**Context:** `docs/dreams/deckcraft.md` and `docs/dreams/modernist-identity.md` both reference a "found asset" — a working `tokens-to-potx.py` / `potx-to-tokens.py` pipeline discovered in the repo's Sentinel Claude Design project (2026-07-23). No source for these scripts exists in this repo's filesystem (`find` for `tokens-to-potx*` / `potx-to-tokens*` returned nothing) — they live only in the external Claude Design MCP project, which this research session did not have live access to inspect byte-for-byte.

**What could be verified:** there is **no dedicated open-source library** for a design-tokens-to-PowerPoint-template round trip. `gh search repos` for "pptx theme tokens," "design tokens powerpoint," and "figma tokens pptx" all returned **zero results**. This confirms the pipeline described in the Dream is genuinely bespoke, not an adaptation of an existing tool — consistent with how it's framed ("found," not "adopted").

**General technical viability (from first principles, since no direct precedent exists):** a `.potx`/`.pptx` file is a ZIP archive of OOXML parts; its theme lives at `ppt/theme/theme1.xml` (color scheme, font scheme) and is addressable via direct XML manipulation (`lxml`, which is already a pixi.toml dependency) even though `python-pptx`'s high-level API doesn't expose full theme-editing. This is the same "escape hatch" pattern architecture.md's AD-07 already anticipates for `python-pptx` gaps generally — reading/writing `theme1.xml` XML directly, alongside `python-pptx` for everything else, is a well-established (if manual) OOXML technique, not a novel risk. The `Style` Pydantic schema (`A-02`, `AD-01`) is already the right shape to carry token data (`Theme.primary`, `Theme.accents`, `Theme.heading_font`, etc. map cleanly to typical design-token JSON: color, typography, spacing tokens).

**Assessment:** technically viable, no library gap that blocks it, but **currently unverified against the actual found asset** — this research could not confirm the found scripts' approach matches (or diverges from) the `Style` schema, what OOXML edge cases they've already solved, or their code quality/license (internal artifact, presumably fine, but not yet audited). Recommend a light verification pass (pull the actual scripts from the Sentinel Claude Design project via the `claude-design` MCP tools) before any story assumes the pipeline is "already built" — the Dream's "what is real" framing may be overstating readiness versus "a promising prototype exists."

---

## 5. New Entrants Since May 2026 (PPTX agent skills / MCP servers)

Re-checked all five candidates named in the intake gist (`Open-Source_PowerPoint_Agent_Skills.md`), plus a fresh sweep for anything new.

| Candidate | Intake gist's framing (May 2026) | Current status (2026-07-25) | Verdict |
|---|---|---|---|
| **Office-PowerPoint-MCP-Server** (GongRzhe) — "Option A," called "the most complete OSS Python option" | Active, 32 tools | **ARCHIVED** 2025-12-31 (GitHub `archived: true`), 1,843 stars, last push before archiving | **DATED — this recommendation no longer holds.** The gist's top-recommended comprehensive option is now unmaintained. Any future evaluation of "adopt vs. build" should not lean on this repo without accounting for its archived status. |
| **mcp-server-ppt** (trsdn) — "Option B," COM Interop, Windows-native | — | Alive, low-traction (35 stars), last push 2026-07-01 | Unchanged assessment — still niche/Windows-only, still not relevant to deckcraft's cross-platform requirement. |
| **ppt-master** (hugohe3) — "Option C," described modestly as "a direct drop-in CLI skill" | Minor option in the gist | **41,032 stars, 3,406 forks**, created 2025-12-10, pushed **today**. Genuinely MIT-licensed. Python-primary (4.2 MB Python vs. 293 KB JS). Description now claims native shapes, transitions/animations, data-backed charts/tables, audio narration from speaker notes, BYO `.pptx` template support | **Major shift.** This is no longer a minor drop-in option — it has become one of the most popular open-source PPTX-generation tools on GitHub in under 8 months, and its stated feature set now substantially overlaps deckcraft's own differentiators (editable native shapes, BYO templates). This is the single most important domain-research finding — detailed competitive analysis in the companion domain-research report. |
| **pptx-tools** (jongalloway) — "Option D," .NET Core | — | Alive but low-traction (8 stars), last push 2026-07-20 | Unchanged — .NET stack was already out of scope for deckcraft's Python-first architecture. |
| **MiniMax `pptx-generator`** fork (bruc3van/bruce-pptx-generator) — "Option E," Node.js/PptxGenJS | Framed as "open-source fork... adapted from the MiniMax skills library" | **License: none detected** (GitHub API returns `license: null` — no LICENSE file in the repo). 5 stars, last push 2026-04-17 | **Contradicts the intake gist's framing.** A repo with no detected license is not confirmed open-source usable — default copyright applies. The gist's "Option E" note doesn't hold up on inspection; this was likely never properly verified license-wise even at intake time. |

**Sweep for other new entrants (GitHub code/repo search, "pptx MCP", "pptx generator", sorted by stars/recency):** no other candidate approaches ppt-master's scale. Most are single-digit-star personal projects, several with no license file at all (a recurring pattern in this space — worth treating "no LICENSE file visible on GitHub" as a standing verification step for any future PPTX-tool adoption decision, not just a one-time check).

---

## 6. Air-Gap / Offline Feasibility Recheck

No dependency in the verified table (§ 2) requires network access at runtime beyond the documented, already-designed exceptions (model weight downloads via `hf-transfer`, opt-in cloud LLM adapters). Specifically:
- `python-pptx`, `markitdown`, `mermaid-py`, `diffusers`, `sentence-transformers`, `mlx-lm`, `llama.cpp`, `pymupdf`, `python-docx` — all pure-local libraries once installed; none phone home.
- `fastmcp` / `pydantic-ai` — local process/library code; network use is entirely a function of which backend URL deckcraft's own config points them at (already governed by architecture's P-07 offline gate).
- `ollama` — local Go server; model pulls are the only network dependency, already covered by DR-03/AD-15.

No new air-gap risk surfaced. The one dependency that changes the calculus is `pymupdf`'s license (§ 3) — a *legal* redistribution concern, not a network/telemetry one, so it doesn't affect NFR-11/NFR-18/NFR-19 (air-gapped network posture), only DR-02's spirit.

---

## 7. Recommendations

1. **Resolve the `pymupdf` license question explicitly before S-3.2 (PDF style loader) starts.** Options are in § 3. This is the single highest-priority action item from this research — it's a founding-constraint conflict, not a nice-to-have.
2. **Re-read the domain-research companion report before finalizing V1's competitive narrative** — `ppt-master`'s growth (§ 5) is material enough that "deckcraft is the missing fourth option" (product brief's framing) may need a sharper differentiation statement against a now-dominant MIT alternative, not just against Gamma/Presenton/hand-rolled scripts.
3. **Verify the actual tokens-to-potx/potx-to-tokens scripts** (via the `claude-design` MCP tools against the Sentinel project) before any story assumes the pipeline is implementation-ready — treat the Dream's "found asset" claim as "promising, unverified" until pulled and read.
4. **Correct the PRD's stale `fastmcp` version citation** (line 230, "v3.2.4" → current is 3.4.4) — cosmetic, but PRDs that quote stale versions invite future confusion; a one-line edit is low-cost whenever the PRD is next touched (this research doc does not edit the PRD directly, per this run's scope).
5. **No re-tiering, no architecture changes, no new spikes required.** AD-06's Spike-0 benchmark remains the correct first implementation action; nothing in this research changes that gate or its pass criterion.

---

## Sources

- PyPI project pages (WebFetch, 2026-07-25): python-pptx, markitdown, fastmcp, pydantic-ai, mermaid-py, diffusers, sentence-transformers, mlx-lm, pymupdf
- GitHub REST API (`gh api repos/...`, 2026-07-25): `scanny/python-pptx`, `marp-team/marp-cli`, `gitbrent/PptxGenJS`, `ggml-org/llama.cpp`, `python-openxml/python-docx`, `pymupdf/PyMuPDF`, `GongRzhe/Office-PowerPoint-MCP-Server`, `trsdn/mcp-server-ppt`, `hugohe3/ppt-master`, `jongalloway/pptx-tools`, `bruc3van/bruce-pptx-generator`, `ollama/ollama`, `BerriAI/litellm`, `conda-forge/marp-cli-feedstock`, `conda-forge/litellm-feedstock`
- GitHub code/repo search (`gh search repos`, 2026-07-25): "pptx generator", "MiniMax pptx", "pptx MCP", "pptx theme tokens", "design tokens powerpoint", "figma tokens pptx"
- Repo-internal: `pixi.toml`, `pixi.lock`, `_bmad-output/projects/deckcraft/planning-artifacts/{prd,architecture,sprint-status}.md`, `docs/dreams/{deckcraft,modernist-identity}.md`, `docs/intake/gists/open-source-powerpoint-agent-skills/Open-Source_PowerPoint_Agent_Skills.md`
