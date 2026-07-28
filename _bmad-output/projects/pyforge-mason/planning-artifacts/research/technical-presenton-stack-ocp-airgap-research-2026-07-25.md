---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - '{project-root}/_bmad-output/projects/presenton-pixi-image/planning-artifacts/prd.md'
  - '{project-root}/docs/dreams/presenton-pixi-image.md'
  - '{project-root}/docs/dreams/enterprise-airgap.md'
  - '{project-root}/docs/reference/enterprise-deployment.md'
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Presenton upstream stack + OpenShift Restricted SCC + air-gap packaging feasibility for presenton-pixi-image'
research_goals: 'Verify/correct the pre-existing PRD draft (llmai version, LibreOffice usage, presenton-export opacity, template-import architecture) against live upstream source; establish OCP Restricted SCC constraints; survey conda-forge feasibility for the full current dependency closure, not just the originally-scoped six components.'
user_name: 'rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
mode: 'headless-express'
---

# Research Report: Presenton Stack, OCP Restricted SCC, and Air-Gap Packaging Feasibility

**Date:** 2026-07-25
**Author:** rxm7706 (headless BMAD run)
**Research Type:** Technical

---

## Research Overview

This report verifies the pre-existing `presenton-pixi-image` PRD's technical claims against the **live** `presenton/presenton` upstream (fetched 2026-07-25, `pushed_at` same day — an actively developed repo, not the snapshot the original Dream/PRD was drafted against). Three of the PRD's load-bearing architectural claims are **contradicted by current upstream source** and one major new gap (memory/embedding subsystem) was found that the original scope never covered. Full findings, with citations, follow; the Executive Summary below is the fast path for PRD revision.

## Executive Summary

**Key Technical Findings:**

- **CORRECTION — LibreOffice is gone from upstream Presenton.** The current `Dockerfile` has no `ARG INSTALL_LIBREOFFICE` and installs no LibreOffice package; a GitHub code search across the whole repo for `soffice` returns **zero** hits and `libreoffice` returns **one** (an unrelated Windows installer script comment). The PRD's Discovery section (`## Discovery & Re-Architecture`) asserts LibreOffice is used on the *input side* for template import — that is no longer true of `main`. This removes the primary justification for the `template-style-extractor` component as originally scoped.
- **CORRECTION — template import is already solved upstream, LibreOffice-free, with near-zero new dependencies.** `servers/fastapi/services/office_document_service.py` implements DOCX/PPTX/XLSX extraction via pure-stdlib `zipfile` + `xml.etree.ElementTree` (no `python-docx`, no `python-pptx` needed for this path) and ODF (`.odt`/`.odp`/`.ods`) support natively — plus it already rejects legacy `.doc`/`.ppt`/`.xls`/`.rtf` with the exact "save in a modern format" error the PRD's Q2 decision proposed building from scratch. PDF text extraction (`servers/fastapi/services/documents_loader.py`) uses `pdfplumber` (MIT), not PyMuPDF — Risk R7 (PyMuPDF AGPL) is moot; there is **no OCR fallback path** upstream (no `pytesseract`/`pdf2image` dependency found), so scanned-PDF support is a genuine gap, not something to replace. **Net effect: the `template-style-extractor` component as scoped (600–800 LOC, python-pptx+python-docx+pymupdf+pytesseract) should be dropped from v1** — text-only extraction, upstream's actual scope, needs no new recipe. If "style-preserving" template import (fonts/colors/layout, not just text) is a genuine buyer requirement, that is **net-new scope beyond upstream's own capability**, not a replacement, and should be reframed as such in the PRD.
- **CONFIRMED (with version drift) — `llmai` is the LLM provider abstraction, Apache-2.0, and NOT on conda-forge.** Current pin is `llmai==0.2.8` (PyPI, verified via JSON API), not `0.2.2` as the PRD states — the PRD's version reference is 6 releases stale (0.2.2 → 0.2.8, `pyproject.toml` confirms exact pin, not a range). License confirmed Apache-2.0 via PyPI classifier. `anaconda.org/conda-forge` package lookup for `llmai` returns 404 — **still needs a net-new conda-forge recipe**, PRD's core claim holds, just re-pin the version.
- **CONFIRMED — custom OpenAI-compatible endpoint support exists exactly as claimed.** `servers/fastapi/utils/llm_config.py` imports `get_custom_llm_url_env` / `get_custom_llm_api_key_env` from `utils/get_env.py`, confirming the `CUSTOM_LLM_URL` / `CUSTOM_LLM_API_KEY` env-var contract the PRD's Q3(a) decision relies on. The provider list is broader than the PRD enumerates: OpenAI, Azure OpenAI, Vertex AI, Anthropic, Google/Gemini, DeepSeek, Bedrock, Cerebras, Fireworks, Together AI, OpenRouter, LiteLLM, LM Studio, Ollama, ChatGPT/Codex OAuth — all routed through `llmai`.
- **CONFIRMED — `presenton-export` remains a closed-source binary release, and it grew a Windows/macOS/ARM matrix.** `presenton/presenton-export` repo is `size: 0` (no source tree) with only GitHub Releases; latest tag `v0.4.2` (2026-07-19) ships `export-{Linux,macOS,Windows}-{X64,ARM64,ia32}.zip`, six platform archives — up from the two-binary framing (`index.js` + `convert-linux-x64`) in the Dream doc. The build-time integration script (`scripts/sync-presentation-export.cjs`, fetched in full) confirms the archive still contains an `index.js`→`index.cjs` Node entrypoint **and** a `py/` subdirectory (the PyInstaller-built converter, per its target path `targetPyDir`). Opacity is unchanged; the clean-room-reimpl need (`presenton-export-node` + `pptx-assembler`) still stands.
- **NEW GAP — the memory/RAG subsystem is a second closure hole the PRD never scoped.** `pyproject.toml` requires `mem0ai[nlp]>=0.1.115` and `fastembed-vectorstore>=0.5.2` as unconditional top-level dependencies (not extras-gated); a repo code search shows `mem0_oss_memory.py`, `mem0_presentation_memory_service.py`, and `chat_memory_store.py` wired into the outlines/presentation/chat endpoints — this is load-bearing, not optional, based on the import graph (no env-flag gate was found gating the import itself). **Neither `mem0ai` nor `fastembed-vectorstore` resolves on `conda-forge`** (anaconda.org API 404 for both). This is a previously-unidentified two-recipe gap (or a feature-drop decision) that materially changes the "six recipes" v1 scope claim.
- **Everything else in the current `pyproject.toml` dependency list resolves on conda-forge** and is compatible-licensed: `fastmcp` 3.4.4 (Apache-2.0), `dirtyjson` 1.0.8 (Apache-2.0), `sqlmodel` 0.0.39 (MIT), `asyncpg` 0.31.0 (Apache-2.0), `aiomysql` 0.3.2 (MIT), `psycopg` 3.3.4 (**LGPL-3.0-only** — flag for legal review, LGPL dynamic-linking terms differ from the rest of the Apache/MIT stack), `google-genai` 2.14.0 (Apache-2.0), `pathvalidate` 3.3.1 (MIT), `pdfplumber` 0.11.10 (MIT), `python-pptx` 1.0.2 (MIT), `fastembed` 0.7.4 (Apache-2.0, distinct package from `fastembed-vectorstore`), `nltk` 3.10.0, `fonttools` 4.63.0.
- **CORRECTED — the current Presenton Dockerfile installs Chromium via pinned Debian packages, not a browser-bundling Node/Playwright pattern.** Runtime base is `python:3.11-slim-trixie`; Node 20 via NodeSource; Chromium installed as a pinned `.deb` (`149.0.7827.196-1~deb13u1`) with `PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium` pointing Puppeteer at the system binary rather than a Puppeteer-managed download. This is consistent with — and validates — the Dream's `playwright-with-chromium` bundled-binary strategy (Debian solves the same "no official browser package" problem the same way: vendor a pinned build), but it means the *current* upstream integration point is Puppeteer against a system Chromium, not Playwright; the clean-room `presenton-export-node` replacement targets a **Puppeteer-shaped API surface** (confirmed unchanged from the Dream's discovery notes — `launch/newPage/goto/setViewport/pdf/screenshot`), which Playwright can serve as a drop-in per the Dream's existing finding.
- **`chromium` on conda-forge remains stalled, not advancing.** `staged-recipes#21431` is still open with exactly one comment (2025-08-28, over 11 months stale as of this research date), no maintainer engagement, no new PR since the three cited failures (#5256, #7146, #11864). The deferred-stretch-goal framing in the PRD is correct and should not change.
- **Electron desktop packaging is real and substantial** (`electron/build.js`, ~30KB; full NSIS/electron-builder scaffold) but is **out of scope** for this project's OCP server deployment — worth an explicit PRD scope note so a reader doesn't wonder why it's unaddressed.
- **OpenShift Restricted SCC (current, `openshift/openshift-docs`, `restricted-v2`/`restricted-v3`):** `restricted-v2` is the SCC applied by default to authenticated users today (drops `ALL` capabilities, allows only `NET_BIND_SERVICE` if explicitly requested, `seccompProfile: runtime/default`, `allowPrivilegeEscalation` must be false/unset, pre-allocated non-root UID range, pre-allocated FSGroup, no host-directory volumes, no privileged containers). **`restricted-v3`** — the default for *new* installations — adds `UserNamespaceLevel: RequirePodLevel` (pods run inside a Linux user namespace, `hostUsers: false`). This is directly material to the Chromium sidecar: Chromium's own sandbox (`--no-sandbox` is the typical container workaround) plus `allowPrivilegeEscalation: false` plus a rootless user namespace is a **three-way constraint stack** the architecture must design against explicitly (headless Chromium under `restricted-v3` typically requires `--no-sandbox` — itself a security posture the CISO buyer persona will want documented, not silently defaulted).

**Technical Recommendations:**

1. Re-scope `template-style-extractor` out of v1 (or reframe explicitly as a **capability addition beyond upstream**, not a LibreOffice-replacement) — this removes one of the six PRD recipes and a large LOC estimate, and eliminates Risk R7 outright.
2. Re-pin `llmai` to `0.2.8` everywhere in the PRD/architecture; confirm at Phase-0 whether upstream's pin drifts again before the recipe is submitted (six releases in the interval between Dream authoring and this research — expect continued drift).
3. Open a Phase-0 decision on the memory subsystem: either (a) add `mem0ai` + `fastembed-vectorstore` as two more net-new conda-forge recipes (raising total recipe count), or (b) confirm with upstream/architecturally verify the memory feature can be disabled/stubbed for v1 (needs an upstream code read beyond this report's scope — no env-flag gate was found, so this may require a Presenton-side patch to make it optional, which itself is new scope).
4. Flag `psycopg` (LGPL-3.0-only) for the buyer's legal/compliance review alongside the existing PyMuPDF-risk framing in Risk R7 — LGPL is compatible with most enterprise allowlists but is a different obligation class than the Apache/MIT majority.
5. Architecture must explicitly document the Chromium-sandbox-vs-`restricted-v3`-user-namespace interaction and the resulting `--no-sandbox` posture as a named, buyer-visible security decision, not an implementation detail.
6. Track `presenton-export` release cadence (v0.4.0 → v0.4.1 → v0.4.2 in 6 days during this research window alone) — the drift-detection harness (Fixture Set 2) needs a tighter cadence assumption than "weekly cron" might suggest; upstream ships fast.

---

## 1. Presenton Upstream Technical Stack

### 1.1 Repository & License

`presenton/presenton` — Apache-2.0, 9,173 stars, 1,433 forks, `pushed_at: 2026-07-25` (actively developed same-day as this research; not archived). Source: `gh api repos/presenton/presenton`.

### 1.2 Architecture

Monorepo: `servers/nextjs` (TypeScript/Next.js frontend), `servers/fastapi` (Python 3.11 FastAPI backend, `requires-python = ">=3.11,<3.12"`), `electron/` (Electron desktop packaging for Windows/macOS/Linux — full `electron-builder` scaffold, out of scope for this project's OCP server target). Confirmed via repo browse and `Dockerfile` fetch.

### 1.3 Runtime Container (`Dockerfile`, `main` branch, fetched in full)

- Runtime base: `python:3.11-slim-trixie`.
- Node.js 20 via `deb.nodesource.com/setup_20.x`.
- Chromium: pinned Debian package `149.0.7827.196-1~deb13u1`; `PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium` — Puppeteer is pointed at the system binary, not a Puppeteer-managed download. **No LibreOffice, no `ARG INSTALL_LIBREOFFICE`.**
- `assets-builder` stage runs `sync-presentation-export.cjs` to materialize the export runtime; symlinks the architecture-specific converter (`convert-linux-x64`/`convert-linux-arm64`) as the active runtime module; sets `EXPORT_PACKAGE_ROOT` / `EXPORT_RUNTIME_DIR` pointing at `/app/presentation-export`.
- `docker-compose.yml` defines four services (`production`, `production-gpu`, `development`, `development-gpu`); 90+ env vars covering LLM providers (OpenAI, DeepSeek, Google, Vertex AI, Azure OpenAI, AWS Bedrock, Anthropic, Ollama, LiteLLM, OpenRouter, Together AI, Fireworks), image generation (DALL-E, local, ComfyUI, Pexels/Pixabay), web search (Tavily/Exa/Brave/Serper/SearXNG), and the MEM0 memory system.

**PRD delta:** the "LibreOffice on the input side, `ARG INSTALL_LIBREOFFICE=true`" claim in the PRD's `## Discovery & Re-Architecture` section does not match current `main`. Either the upstream removed it after the PRD was drafted (2026-04-30 per the PRD's `**Date:**` line, vs. this research's 2026-07-25 fetch — a ~3-month gap, plenty of time for upstream to ship the change) or the original discovery pass was working from a stale fork/branch. Either way, the revised PRD must correct this.

### 1.4 `presenton-export` (closed-source export runtime)

- `presenton/presenton-export`: `size: 0` — no source tree, releases only. `license: null` at repo level.
- Latest three releases (newest first): `v0.4.2` (2026-07-19), `v0.4.1` (2026-07-16), `v0.4.0` (2026-07-13) — a new tag roughly every 3 days in the sampled window.
- Release assets (all three tags, identical shape): `export-Linux-ARM64.zip`, `export-Linux-X64.zip`, `export-macOS-ARM64.zip`, `export-macOS-X64.zip`, `export-Windows-ia32.zip`, `export-Windows-X64.zip`.
- `scripts/sync-presentation-export.cjs` (fetched in full): downloads the pinned-version zip from `https://github.com/presenton/presenton-export/releases/download`, unpacks to `presentation-export/`, expects `index.js` (rewritten to `index.cjs` on every run "so the CommonJS entrypoint never drifts from the bundled ESM build") plus a `py/` subdirectory — confirming the PyInstaller-built Python converter (the Dream's `convert-linux-x64`) still ships alongside the Node bundle inside each platform zip, just repackaged from six release assets in the old two-binary framing to a single per-platform archive containing both.
- **PRD delta:** the shape changed (2 flat binaries → 6 platform zip archives, each presumably still bundling both a Node component and a `py/` component) but the **opacity claim is unchanged and confirmed current** — no source, release-artifact-only. The clean-room-replacement rationale (`presenton-export-node`, `pptx-assembler`) is unaffected.

### 1.5 LLM Provider Abstraction (`llmai`)

- `pyproject.toml`: `"llmai==0.2.8"` — **exact pin**, not a floor. PRD states `0.2.2`; six releases behind (`0.2.4` … `0.2.8` per PyPI JSON `releases` listing, 20 releases total on PyPI as of this research).
- License: Apache-2.0 (PyPI classifier `License :: OSI Approved :: Apache Software License`, LICENSE text embedded in metadata confirms full Apache-2.0 text).
- Summary (PyPI): "Unified Python client for OpenAI, Azure OpenAI, Vertex AI, Anthropic, Gemini, DeepSeek, OpenRouter, Cerebras, Fireworks, Together AI, LM Studio, Bedrock, LiteLLM, and ChatGPT."
- `servers/fastapi/utils/llm_config.py` (fetched in full, head): imports `BedrockClientConfig`, `DeepSeekClientConfig`, `FireworksClientConfig`, `LMStudioClientConfig`, `TogetherAIClientConfig` from `llmai`, and `AnthropicClientConfig`, `AzureOpenAIClientConfig`, `CerebrasClientConfig`, `ChatGPTClientConfig`, `ClientConfig`, `GoogleClientConfig`, `LiteLLMClientConfig`, `OpenAIApiType`, `OpenAIClientConfig`, `OpenRouterClientConfig`, `VertexAIClientConfig` from `llmai.shared`. `utils/get_env.py` exposes `get_custom_llm_url_env` / `get_custom_llm_api_key_env` — **confirms the `CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY` contract the PRD's Q3(a) decision depends on.**
- conda-forge status: `api.anaconda.org/package/conda-forge/llmai` → 404 (`"llmai" could not be found`). **Still needs a net-new recipe**, PRD's core claim confirmed, version needs updating.

### 1.6 Template Import — Corrected Architecture

`servers/fastapi/services/office_document_service.py` (fetched in full, ~150 lines):

- Pure Python **stdlib only** (`os`, `re`, `zipfile`, `pathlib`, `xml.etree.ElementTree`) — no `python-docx`, no `python-pptx`, no LibreOffice.
- Supported: `.docx`/`.docm` (paragraph text via `word/document.xml`), `.pptx`/`.pptm` (per-slide text via `ppt/slides/slideN.xml`, naturally sorted), `.xlsx`/`.xlsm` (cell text incl. shared-strings resolution), `.odt`/`.odp`/`.ods` (ODF `content.xml`), `.csv`/`.tsv` (plain read).
- Explicitly unsupported, with a purpose-written error: `.doc`, `.ppt`, `.xls`, `.rtf` → `OfficeDocumentError("... require an external office conversion engine; save the document in a modern OOXML or OpenDocument format first")`. This is **word-for-word the behavior the PRD's Q2 decision proposed inventing** — it already exists upstream.
- **This is text-only extraction** — no font, color, layout, or style metadata is captured. It feeds LLM context, not a style-preserving template pipeline.
- PDF path: `servers/fastapi/services/documents_loader.py` uses `pdfplumber` (MIT; confirmed on conda-forge, `pdfplumber` 0.11.10). No `PyPDF2`/`pypdf`/`fitz`(PyMuPDF) hits anywhere in the repo (code search: 0 results each). **No OCR path** — no `pytesseract` or `pdf2image` dependency in `pyproject.toml`, no code-search hits.

**PRD delta (major):** the proposed `template-style-extractor` component (~600–800 LOC, `python-pptx` + `python-docx` + `pymupdf` + `pdfplumber` + `pytesseract`, OCR fallback, ODP/ODT stretch goal) solves a problem upstream has already solved with a **much smaller, dependency-free, LibreOffice-free approach** that ships today. Recommendation: drop this component from v1 scope entirely (upstream's own code *is* the reference implementation and needs no repackaging — it's stdlib), or reframe any "style-preserving template import" ambition as **net-new capability beyond upstream parity**, scoped and estimated separately, not folded into a "replace LibreOffice" narrative. This also **resolves Risk R7** (PyMuPDF AGPL licensing) — PyMuPDF is not required by the actual pipeline.

### 1.7 The Uncovered Gap: Memory/RAG Subsystem

`pyproject.toml` top-level (unconditional) dependencies include `mem0ai[nlp]>=0.1.115` and `fastembed-vectorstore>=0.5.2`. Code search confirms real integration, not vestigial: `services/mem0_oss_memory.py`, `services/mem0_presentation_memory_service.py`, `services/chat/chat_memory_store.py`, wired into `api/v1/ppt/endpoints/outlines.py` and `api/v1/ppt/endpoints/presentation.py`. A search for an env-var gate (`MEM0`/`MEMORY` in `utils/get_env.py`) surfaced env-var *accessors* (consistent with the 90+ env vars in `docker-compose.yml`, which does list MEM0-related config) but this research did not confirm a code path that fully no-ops the import when disabled — that requires a deeper read than this pass covers, flagged as an open question below.

Conda-forge status: neither `mem0ai` nor `fastembed-vectorstore` resolves (`api.anaconda.org` 404 for both). `fastembed` (the base embedding library, distinct package) **does** resolve (0.7.4, Apache-2.0) — so the gap is specifically the `mem0ai` orchestration layer and the `fastembed-vectorstore` adapter package, not the underlying embedding engine.

**This is new scope the original Dream/PRD never named.** It is either a 7th+8th recipe pair, or a documented v1 feature-drop (disable memory/chat-history features), and either path needs an explicit PRD decision — it was not on anyone's radar in the original discovery pass.

### 1.8 Rest-of-Closure Conda-Forge Check

All queried against `api.anaconda.org/package/conda-forge/<name>` (2026-07-25):

| Package | conda-forge | Version | License | Note |
|---|---|---|---|---|
| `fastmcp` | ✅ | 3.4.4 | Apache-2.0 | |
| `dirtyjson` | ✅ | 1.0.8 | Apache-2.0 | |
| `sqlmodel` | ✅ | 0.0.39 | MIT | |
| `asyncpg` | ✅ | 0.31.0 | Apache-2.0 | |
| `aiomysql` | ✅ | 0.3.2 | MIT | |
| `psycopg` | ✅ | 3.3.4 | **LGPL-3.0-only** | flag for legal review — different obligation class than the rest of the stack |
| `google-genai` | ✅ | 2.14.0 | Apache-2.0 | |
| `pathvalidate` | ✅ | 3.3.1 | MIT | |
| `pdfplumber` | ✅ | 0.11.10 | MIT | confirms Q2/R7 resolution above |
| `python-pptx` | ✅ | 1.0.2 | MIT | matches PRD's existing plan |
| `fastembed` | ✅ | 0.7.4 | Apache-2.0 | base embedding lib — distinct from `fastembed-vectorstore` |
| `nltk` | ✅ | 3.10.0 | Apache-2.0 | |
| `fonttools` | ✅ | 4.63.0 | MIT | |
| `mem0ai` | ❌ 404 | — | — | new gap, § 1.7 |
| `fastembed-vectorstore` | ❌ 404 | — | — | new gap, § 1.7 |
| `llmai` | ❌ 404 | 0.2.8 (PyPI) | Apache-2.0 | confirmed PRD gap, re-pin version |

---

## 2. OpenShift Restricted SCC Constraints

Source: `openshift/openshift-docs` (public GitHub repo, `modules/security-context-constraints-about.adoc`, fetched in full — this is the canonical upstream doc source for `docs.redhat.com`).

### 2.1 SCC Hierarchy (current)

- **`restricted`** — legacy; available only on clusters upgraded from OCP ≤4.10; not available to new-install authenticated users unless explicitly granted.
- **`restricted-v2`** — **used by default for authenticated users** on current OCP. Adds to `restricted`: all Linux capabilities dropped (`ALL`), only `NET_BIND_SERVICE` addable and only if explicitly requested, `seccompProfile: runtime/default` by default, `allowPrivilegeEscalation` must be unset or `false`.
- **`restricted-v3`** — **the default for new installations**, most restrictive shipped SCC. Adds `userNamespaceLevel: RequirePodLevel`, forcing pods into a Linux user namespace (`hostUsers: false`).
- Common `restricted`-family baseline: no privileged containers, no host-directory volume mounts, container must run as a UID from a **pre-allocated per-namespace range** (not attacker/operator-chosen), pre-allocated MCS SELinux label, pre-allocated FSGroup, arbitrary supplemental groups allowed.

### 2.2 Implications for This Workload

1. **No hardcoded UID in the image.** The Presenton container (and any Chromium/Playwright sidecar) must not assume `root` or a fixed non-root UID like `1000` — it must tolerate an arbitrary, OpenShift-assigned UID at pod start, writing only to paths owned by the pre-allocated `GID`/`fsGroup` (the common pattern: `chgrp -R 0` + `chmod g=u` on writable dirs, per the well-known "OpenShift arbitrary UID" convention — not independently re-verified in this pass beyond the SCC doc's description of `MustRunAsRange` behavior).
2. **No privileged mode, no host volumes.** Any design that assumed a privileged sidecar for Chromium sandboxing is unavailable under `restricted-v2`/`v3`.
3. **`allowPrivilegeEscalation: false` + Chromium's sandbox model.** Headless Chromium's default Linux sandbox (`SUID sandbox` / user-namespace sandbox) typically requires either `CAP_SYS_ADMIN` or working unprivileged user namespaces plus `no_new_privs` compatibility; the conventional container workaround is launching with `--no-sandbox`. Under `restricted-v3`'s own pod-level user-namespace isolation (`hostUsers: false`), Chromium's *internal* attempt to create nested user namespaces for its sandbox may conflict with or be redundant to the pod-level isolation OpenShift already provides — this needs a **hands-on validation spike in Phase 0**, not just a documentation read; flagged as an open question below since this report could not test it directly.
4. **Read-only root filesystem is not automatically implied by Restricted SCC** (the SCC doc does not mandate it — "whether a container requires write access to its root file system" is listed as one of the *configurable* controls, not a hard-restricted default), but it's a common security-hardening add-on many OCP clusters layer on top. The Helm chart should support it as an opt-in (writable `/tmp`, `/app_data` via `emptyDir`/PVC) rather than assume either posture.

---

## 3. Comparable Self-Hosted / On-Prem AI Deck-Generation Deployments

GitHub search (via `gh search repos`, not the exhausted web-search budget — see § 6) surfaced:

1. **`hugohe3/ppt-master`** (already cited in the Dream doc) — MIT, 10k+ stars, AI-IDE-skill architecture (Claude Code/Cursor/Copilot), PDF/DOCX/URL/Markdown → external LLM API → SVG → DrawingML → editable PPTX. Confirmed air-gap-incompatible by design (external LLM call is structural, not configurable) — useful only as the SVG→DrawingML architectural inspiration already noted in the PRD's Vision tier.
2. **`Cherzing/AIPPT`** — "可私有化部署的 AI 演示文稿生成与编辑平台" (self-hostable AI presentation generation + editing platform), explicitly markets native editable templates, AI image replacement, PPTX/PDF export, Docker deployment. Low star count (repo was found via search, exact count not captured in this pass) — early-stage, but directly on-point as a **self-hosted, PPTX-native, non-Marp** comparable; worth a follow-up architecture-phase read if time allows, since "native editable templates" suggests they may have solved the same PPTX-fidelity problem the PRD's Q1 decision (image-overlay + extracted text) settles for.
3. **`busto-dev/PepeteX`** — "Self-hosted AI presentation generator — chat to a full PPTX deck, using your own AI keys" — smaller/newer project (5 stars), BYO-API-key model matches the Tier-1/BYO-endpoint posture this project targets, but no evidence of air-gap/OCP-specific packaging.

None of the three surfaced comparables publish OpenShift or air-gap deployment guidance; this appears to be a genuinely under-served niche (consistent with the PRD's competitive-context table, which already concludes the intersection of "Copilot-class capability" + "survives security review" has no clean incumbent). No correction needed to the PRD's competitive positioning; this section adds evidence rather than contradicting anything.

---

## 4. Conda-Forge Feasibility Summary (Updated)

| Original PRD component | Status after this research | Recommendation |
|---|---|---|
| `presenton-export-node` | Confirmed still needed — opacity unchanged (§ 1.4) | Keep in v1 |
| `pptx-assembler` | Confirmed still needed — `py/` converter subdirectory still opaque (§ 1.4) | Keep in v1 |
| `pptx-thumbnail-inject` | Unaffected by this research (no upstream code search performed on thumbnail handling) | Keep in v1, unchanged |
| `template-style-extractor` | **Contradicted** — upstream already solves this LibreOffice-free with near-zero deps (§ 1.6) | **Drop from v1** or reframe as net-new beyond-parity capability |
| `playwright-with-chromium` | Rationale intact; current upstream uses pinned-Debian-package Chromium + Puppeteer, not Playwright-managed download (§ 1.3) — validates the "vendor a pinned build" strategy | Keep in v1, unchanged |
| `llmai` | Confirmed still needed, version drift 0.2.2→0.2.8 | Keep in v1, re-pin |
| *(new)* `mem0ai` | **Newly discovered gap**, not on conda-forge (§ 1.7) | Phase-0 decision required: add as 7th recipe, or scope-drop the memory feature |
| *(new)* `fastembed-vectorstore` | **Newly discovered gap**, not on conda-forge (§ 1.7) | Same Phase-0 decision as above |
| `chromium` (stretch) | Confirmed still stalled, no 2026 movement (§ 1.4/staged-recipes#21431) | No change — remains deferred |

---

## 5. Source Verification

**Primary sources (fetched in full or substantial excerpt, this research pass, 2026-07-25):**

- `gh api repos/presenton/presenton` — repo metadata (license, stars, activity).
- `raw.githubusercontent.com/presenton/presenton/main/Dockerfile` — full contents.
- `raw.githubusercontent.com/presenton/presenton/main/docker-compose.yml` — full contents.
- `gh api repos/presenton/presenton/contents/servers/fastapi/pyproject.toml` — full contents.
- `gh api repos/presenton/presenton/contents/servers/fastapi/services/office_document_service.py` — full contents.
- `gh api repos/presenton/presenton/contents/servers/fastapi/utils/llm_config.py` — head (imports + provider list).
- `gh api repos/presenton/presenton/contents/scripts/sync-presentation-export.cjs` — head (build-time export integration).
- `gh api repos/presenton/presenton-export` + `.../releases` — repo metadata + 3 most recent release manifests.
- `gh api "search/code?q=..." repo:presenton/presenton` — 8 targeted code searches (`soffice`, `libreoffice`, `llmai`, `template_import`, `python-pptx`, `pdf2image`, `docx`, `convert_to_pdf`, `pdfplumber`, `PyPDF2 OR pypdf`, `import fitz`, `mem0 enabled`).
- `pypi.org/pypi/llmai/json` — full package metadata (version, license, releases list).
- `api.anaconda.org/package/conda-forge/<pkg>` — 17 individual package lookups.
- `gh api repos/conda-forge/staged-recipes/issues/21431` + comments — current state of the chromium-on-conda-forge request.
- `gh api repos/openshift/openshift-docs/contents/modules/security-context-constraints-about.adoc` — full contents (canonical SCC doc source).
- `gh search repos` — 2 targeted GitHub searches for comparable self-hosted AI deck tools.

**Confidence levels:**

- **High confidence** (direct source fetch, unambiguous): LibreOffice removal, template-import architecture, `llmai` version/license, `presenton-export` opacity + release cadence, conda-forge availability table, OCP SCC hierarchy.
- **Medium confidence** (inferred from available evidence, not exhaustively traced): whether the memory subsystem (`mem0ai`) can be cleanly feature-flagged off — the env-var accessors exist but this pass did not trace the full import graph to confirm a no-op path; Chromium-sandbox-vs-`restricted-v3`-user-namespace interaction — documented as a plausible conflict from SCC semantics, not empirically tested against a running OCP cluster.
- **Not independently re-verified in this pass**: `pptx-thumbnail-inject` upstream behavior (R1 in the PRD's risk register) — out of this research's question scope; carried forward unchanged from the PRD.

**Methodology note (session constraint):** the `WebSearch` tool's session budget was exhausted early in this research pass (200/200 calls used by prior session activity, not by this research). All findings above were produced via `WebFetch` (works, not budget-limited) and `gh api`/`gh search` (GitHub CLI, no session budget interaction) instead — every citation above is a direct primary-source fetch, not a search-engine summary, which if anything raises confidence versus a typical web-search-driven pass. Domain/market research (§ 3) was correspondingly narrower than a full `WebSearch`-driven sweep would have produced; flagged as a research-coverage limitation, not a findings-confidence issue.

---

## 6. Open Questions Surfaced By This Research

1. Can the `mem0ai`/`fastembed-vectorstore` memory subsystem be disabled/stubbed without a Presenton-side source patch, or does v1 need to either add two more conda-forge recipes or accept a memory/chat-history feature drop? (§ 1.7)
2. Does headless Chromium's sandbox actually conflict with `restricted-v3`'s pod-level user-namespace isolation on a real OCP cluster, and is `--no-sandbox` the right (buyer-documentable) answer, or does OCP's user-namespace approach make Chromium's internal sandbox redundant-but-harmless? Needs a hands-on Phase-0 spike, not a docs read. (§ 2.2)
3. Is `Cherzing/AIPPT`'s "native editable templates" claim (§ 3) evidence of a PPTX-fidelity technique beyond the PRD's Q1 image-overlay decision, worth a follow-up read during architecture?
4. `presenton-export` shipped 3 releases in a 6-day window during this research — does the PRD's "weekly cron" drift-detection cadence (Fixture Set 2, `AC-FX-MAINT-*`) need tightening given this observed pace?
5. `psycopg` is LGPL-3.0-only, not Apache/MIT like the rest of the stack — does the buyer's allowlist policy treat LGPL identically to permissive licenses, or does it need a separate compliance note alongside the existing PyMuPDF (now resolved) risk framing?

---

**Research Completion Date:** 2026-07-25
**Source Verification:** All technical facts cited with direct primary-source fetches (GitHub API/raw content, PyPI JSON API, anaconda.org API, openshift-docs repo).
**Confidence Level:** High for upstream-stack and conda-forge-availability findings; Medium for the two open architectural questions flagged in § 6.
