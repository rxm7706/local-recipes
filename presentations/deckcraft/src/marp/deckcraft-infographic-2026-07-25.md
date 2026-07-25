---
marp: true
paginate: true
size: 16:9
title: Deckcraft — the pipeline, at a glance
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

# Deckcraft
## The air-gapped, conda-native editable-deck pipeline — at a glance

Prompt or document in. **Editable `.pptx` + Marp sibling** out. Zero outbound calls by default.

---

## The problem, in one row each

| Who | What breaks today |
| --- | --- |
| **The builder** | 30–60 min of paste-and-format per deck; the AI writes prose and stops |
| **The air-gapped colleague** | Has Copilot/MS365, cannot reach any public AI API — cloud tools blocked by policy |
| **The technical author** | Diagrams rasterize to PNG; charts become screenshots; nothing is editable |

---

## What ships at V1

| Capability | Bar |
| --- | --- |
| Editable output | **100% native DrawingML, zero rasterized** (SC-05), structurally inspected |
| Marp round-trip | `.pptx` ⇄ `.md`; lossy elements flagged in a **sidecar warning file**, never dropped |
| Diagrams & charts | Mermaid offline **≤3s/diagram**; native PowerPoint charts where the data fits |
| Surfaces | Claude Skill + MCP stdio + CLI — **3 of 6** — plus a conda-forge recipe |
| Air gap | Zero outbound calls after first-run download; **CI-verified under `unshare -n`** |

---

## The architecture in one line

Surfaces consume the `Pipeline` API only; renderers consume engine adapters only. **Three swap points, and nothing else is one:** `LLMAdapter`, `PptxEngineAdapter`, `PlatformAdapter`.

Outside `deckcraft.engines.pptx_engine`, nothing may `import pptx` — the discipline that keeps the vendor fallback clean while upstream `python-pptx` sits dormant at 1.0.2 (last release 2024-08-07, ~23 months quiet, 534 open issues).

---

## The two findings on the desk

**The moat moved.** `ppt-master`: MIT, **41,032 stars**, 3,406 forks, under 8 months — matches the editability bar, has no local-LLM-first or offline mode. Air-gap posture now carries the differentiation.

**One license conflict, unresolved.** `pymupdf` is **AGPL-3.0 / Artifex commercial** against a founding **MIT-or-Apache-2.0-only** bar. Options: accept · substitute `pdfplumber` · scope out. Blocks Story 3.2. A human call.

---

<!-- _class: dark -->

## The creed

From primitives, not a repackage. Always editable, never rasterized. Behind the firewall, by construction.

# A prompt in. An editable deck out. No cloud.
