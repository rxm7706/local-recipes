---
marp: true
paginate: true
size: 16:9
title: Presenton, Conda-Native — Executive Summary
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  hr { border:none; border-top:3px solid #201e1d; margin:.4em 0; }
  table { font-size:.8em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- _class: lead -->

PRESENTON, CONDA-NATIVE · `docs/dreams/presenton-pixi-image.md`
**AI deck generation, inside the perimeter**

# One signed image. One SBOM. No call home.

### It's 11pm in a SCIF. The deck is due at 8am. Copilot is on the other side of the air gap.

`presenton-pixi-image` repackages the open-source Presenton AI deck-generation app as a fully air-gapped OCI image for Red Hat OpenShift — built from conda-forge-native recipes, assembled via pixi + pixitainer, with **zero LibreOffice and zero non-conda-forge packages in the runtime**.

---

## Why it matters — three outcomes

**The buyer can approve it once**
Recipes merged upstream on conda-forge → landed on the customer's JFrog mirror → image on their registry, with a CycloneDX+SPDX SBOM, a `cosign` attestation, and a versioned `/metrics` schema on every build.

**The analyst gets a draft worth editing**
Not template-stamping: real long-form-document summarization inside the perimeter. Target ≥60% edit-not-rewrite, ≤30 min P95 to first renderable slide, ≤10s P95 per refinement on Tier 1.

**The operator deploys it like anything else**
A standard Helm chart with `restricted-v2`-compatible defaults, one `llmProvider.tier` enum selecting among three LLM tiers, day-0 preflight and day-2 operational fixtures shipped in the image.

---

## The numbers

| Metric | Value |
| --- | --- |
| Unsigned upstream artifacts the customer integrates today | **5** |
| What they integrate instead | **1 signed image, 1 SBOM** |
| Confirmed conda-forge recipes (v1 range) | **5** (5–7 pending Phase-0 exit 6b) |
| LibreOffice / external CDN / calls home in the runtime | **0 / 0 / 0** |
| Scope: epics / stories | **7 / 30** — Phase 0 first |
| Phase-0 exits still open that can change product shape | **2** |

---

## The honest ledger

**Exit 6(a) — the existential one.** Microsoft's disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local) went **GA worldwide 2026-02-24**. Whether it carries a Copilot-for-PowerPoint-equivalent layer is **unconfirmed** — the supported-services table lists infrastructure only. The standing Microsoft watch missed the announcement; Phase 0 backtests the watch as well as answering the question. Treat the window as **unknown and urgent**.

**Exit 6(b) — the scope one.** `mem0ai` + `fastembed-vectorstore` are unconditional Presenton dependencies, neither on conda-forge: two more recipes, or a documented v1 feature-drop — and the drop only holds if the import graph no-ops without a source patch. Architecture pre-wires both branches, default off, so build work isn't blocked.

---

<!-- _class: lead -->

## The promise

Nothing else clears both halves of the bar: Copilot-class capability **and** survives security review.

**The buyer is paying for a deck generator they are allowed to install.**

presenton-pixi-image · PyForge · Dream to Code
