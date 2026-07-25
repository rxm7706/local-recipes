---
marp: true
paginate: true
size: 16:9
title: Presenton, Conda-Native — the image, at a glance
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:25px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.dark { background:#201e1d; color:#f3f2f2; }
  section.dark h1, section.dark h2, section.dark code { color:#f3f2f2; }
  section.dark strong { color:#ec3013; }
  hr { border:none; border-top:3px solid #201e1d; margin:.4em 0; }
  table { font-size:.76em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- _class: lead -->

# Presenton, Conda-Native
## AI deck generation inside the perimeter — at a glance

Five conda-forge recipes → one pixi-locked env → one **signed, SBOM-attested OCI image** on OpenShift.

---

## The two gates

| Gate | Who | What must hold |
| --- | --- | --- |
| **Buyer** (binary) | CISO / platform engineering | Recipes merged → JFrog mirror → customer registry; SBOM (CycloneDX+SPDX) + `cosign` attestation + versioned `/metrics` schema per build |
| **User** (behavioral) | The analyst | **≥60%** edit-not-rewrite · **≤30 min P95** to first renderable slide · **≤10s P95** per refinement on Tier 1 |

Miss either within its window and the program returns to Phase-0 scoping.

---

## The five confirmed recipes

| Recipe | Replaces / provides |
| --- | --- |
| `presenton-export-node` | Clean-room Playwright export runtime (was a closed-source bundle) |
| `pptx-assembler` | The closed-source `convert-linux-x64` binary |
| `pptx-thumbnail-inject` | A real `docProps/thumbnail.jpeg` in AI-generated decks |
| `playwright-with-chromium` | Bundled headless browser for the air gap |
| `llmai` | The LLM provider abstraction upstream already depends on |

**Dropped:** `template-style-extractor` — upstream already ships LibreOffice-free template import (stdlib + `pdfplumber`), and the PyMuPDF/AGPL risk left with it.

---

## The invariants

**AD-2 — one true port.** `CUSTOM_LLM_URL` / `CUSTOM_LLM_API_KEY` is the only swappable seam; `values.llmProvider.tier` picks tier 1/2/3 with **no per-tier code fork**.

**AD-1 — every build URL routes the mirror.** No recipe, build step or CI job hardcodes a public host; `pixitainer` only consumes the lock.

**AD-6 — the phase boundary is CI topology, not convention.** The air-gapped build pipeline has zero network egress, enforced at the runner/network-policy level; online fixture capture never shares a runner with it.

**AD-8 — `restricted-v2` by default.** All capabilities dropped, `seccompProfile: runtime/default`, no privilege escalation, non-root arbitrary UID, no hardcoded UID/GID anywhere.

---

## The two open Phase-0 calls

**6(a) The Redmond contingency.** Microsoft's disconnected stack — Azure Local disconnected operations + Microsoft 365 Local + Foundry Local — **GA worldwide 2026-02-24**. Whether it carries a deck-generation application layer is **unconfirmed**; the supported-services table names infrastructure only. Risk R3 is existential. The standing watch **missed the announcement** — Phase 0 backtests it.

**6(b) Five recipes, or seven.** `mem0ai` + `fastembed-vectorstore` are unconditional Presenton deps, neither on conda-forge. Add both, or feature-drop memory — and the drop only holds if the import graph no-ops without a Presenton patch. **Not yet verified.** Both branches pre-wired, default off.

---

<!-- _class: dark -->

## The creed

Zero LibreOffice. Zero external CDN. Zero calls home. One signed artifact, and we own the integration risk.

# The buyer is paying for a deck generator they are allowed to install.
