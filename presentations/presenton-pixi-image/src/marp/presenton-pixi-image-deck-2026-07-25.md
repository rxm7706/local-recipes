---
marp: true
paginate: true
size: 16:9
title: Presenton, Conda-Native — AI decks where SaaS cannot go
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.dark { background:#201e1d; color:#f3f2f2; }
  section.dark h1, section.dark h2, section.dark h3, section.dark code { color:#f3f2f2; }
  section.dark strong { color:#ec3013; }
  hr { border:none; border-top:3px solid #201e1d; margin:.4em 0; }
  table { font-size:.78em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- 01 · Cover -->

PRESENTON, CONDA-NATIVE · PyForge · Mason repackages · Steward operates · Dream: `docs/dreams/presenton-pixi-image.md`

# AI decks where<br>SaaS cannot go.

The open-source Presenton deck generator, repackaged as a **signed, air-gapped OCI image** for Red Hat OpenShift — built from conda-forge recipes, assembled with pixi + pixitainer. Zero LibreOffice, zero external CDN, **no call home**.

| Project | Recipes | Platform | Status |
| --- | --- | --- | --- |
| `presenton-pixi-image` | 5 confirmed · 5–7 for v1 | OpenShift · `restricted-v2` | Phase 0 gates v1 |

---

<!-- _class: dark -->

## Act I

# 11pm in a SCIF

The board deck is due at 8am. Copilot is on the other side of the air gap. **Today she builds it by hand** — slower than her LLM-assisted peers elsewhere in the org, and systematically weaker in structure and language.

---

## Two gates that don't collapse

**Buyer gate — binary, procurement-visible.** Recipes upstream-merged on conda-forge → landed on the customer's JFrog Artifactory mirror → image on the customer's registry. Every build ships an SBOM (CycloneDX primary, SPDX secondary), a `cosign` attestation, and a versioned `/metrics` schema. **He signs once and forgets it.**

**User gate — behavioral, renewal-driving.** **≥60%** of piloted decks show edit-not-rewrite behavior; **≤30 min P95** prompt to first renderable slide; **≤10s P95** per refinement on Tier 1. Quality bar is *"better than writing it by hand at 2am"* — explicitly not M365-Copilot parity.

Three-signatory acceptance within 12 weeks of go-live (18 with the one-time extension), or the program resets to Phase-0 scoping rather than limping forward.

---

## The supply-chain math

**Without this:** the customer integrates **five unsigned upstream artifacts** — a closed-source export bundle, a closed-source PyInstaller converter, a browser binary nobody ships on conda-forge — and owns that integration risk themselves.

**With it:** they integrate **one signed image, one SBOM** — and we own the integration risk.

| Recipe | Replaces / provides |
| --- | --- |
| `presenton-export-node` | Clean-room Playwright export runtime |
| `pptx-assembler` | The closed-source `convert-linux-x64` binary |
| `pptx-thumbnail-inject` | A real `docProps/thumbnail.jpeg` in AI-generated decks |
| `playwright-with-chromium` | Bundled headless browser for the air gap |
| `llmai` | The provider abstraction upstream already depends on |

**Dropped 2026-07-25:** `template-style-extractor` — upstream already does LibreOffice-free template import with the stdlib + `pdfplumber`. The PyMuPDF/AGPL risk left with it.

---

<!-- _class: dark -->

## Act II

# Two planes

Build-time **pipes and filters**: recipes → pixi-locked env → pixitainer OCI assembly → `syft` + `cosign`, each stage consuming only the previous stage's published output.

Run-time **hexagon with exactly one true port**. Nothing else in the running system branches on deployment topology.

---

## One true port, three tiers

The LLM provider is the **only** swappable seam. Presenton and the Helm chart set only `CUSTOM_LLM_URL` / `CUSTOM_LLM_API_KEY`.

| Tier | What it points at |
| --- | --- |
| **Tier 1** | An operator-supplied external corporate proxy — no in-cluster resource; all latency targets measured here |
| **Tier 2** | A `llama.cpp` Service in the same namespace, OpenAI-compatible over HTTP |
| **Tier 3** | The same Service, whose Pod pulls the GGUF from an internal registry via an init container |

Three URLs, one contract, **never a different code path**. The chart defaults to `restricted-v2` on every cluster: all capabilities dropped, `seccompProfile: runtime/default`, no privilege escalation, non-root arbitrary UID, **no hardcoded UID/GID anywhere**. Chromium runs `--no-sandbox` as an explicit, Helm-documented decision — not a silent default.

---

<!-- _class: dark -->

## Act III

# Phase 0 gates the build

**Six exits** — 7 stories of the 30. Nothing in Epics 2–7 starts production work ahead of them. **Two exits can still change the product's shape.**

---

## Exit 6(a) — the Redmond contingency

Microsoft's own disconnected stack — **Azure Local disconnected operations + Microsoft 365 Local + Foundry Local** — went **GA worldwide 2026-02-24**. Every infrastructure primitive needed to run a disconnected Copilot-equivalent is now shipped by Microsoft directly.

**Confirmed:** the supported-services table lists infrastructure primitives only — portal, ARM, RBAC, Arc-enabled VMs/AKS, registry, Key Vault. No Copilot, no M365 apps, no AI service named.

**Unconfirmed:** whether the deck-generation *application layer* is turned on in the disconnected SKU today, or roadmapped. This determines whether Risk R3 is materialized, partially materialized, or infrastructure-only.

**What it cost us to learn:** the standing Microsoft watch — yearly + gate-coupled + always-on RSS on the words `disconnected`, `air-gap` — **missed it**. Phase 0 backtests the watch, not just the question.

Treat the window as **unknown and urgent**, not the falsified 12–24-month runway.

---

## Exit 6(b) — five recipes, or seven

`mem0ai` and `fastembed-vectorstore` are **unconditional Presenton dependencies** and **neither is on conda-forge**. The recipe count is genuinely open — not the fixed "six" the plan used to say.

| Option | What it costs |
| --- | --- |
| **A — add them** as recipes 6 & 7 | Full upstream parity; two more staged-recipes review cycles, two more JFrog allowlist requests, two more drift surfaces |
| **B — drop for v1** | Only stays a "drop" if the import graph no-ops cleanly via env var — **not yet verified**. If it needs a Presenton source patch, this becomes carrying a fork |

Build work is **not blocked** while it is open: the `presenton-memory` pixi feature and `values.memory.enabled` both default **off**, and either answer fits the same shape.

---

<!-- _class: lead -->

## The complement

# The buyer is paying for a deck generator they are allowed to install.

Presenton is the repackaged **app**; deckcraft is the from-primitives **pipeline**. Complementary, not competing — Mason repackages, Steward deploys and operates the OpenShift service.

30 stories · 7 epics · Phase 0 first · **0 LibreOffice · 0 external CDN · 0 calls home**

presenton-pixi-image · conda-forge-native · OpenShift · air-gapped
