---
marp: true
paginate: true
size: 16:9
title: Deckcraft — Executive Summary
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

DECKCRAFT · the deck pipeline · `docs/dreams/deckcraft.md`
**Editable decks, from primitives, behind the firewall**

# A prompt in. An editable deck out. No cloud.

### The AI writes the prose and drops the user before the file exists.

Deckcraft is the plumbing: a small conda-forge-native Python package that turns a prompt or a document (PDF / DOCX / PPTX / Markdown / XLSX / URL) into an **editable** PowerPoint deck plus a round-trippable Marp source — running entirely on local hardware and local LLMs, surfaced through the AI tools the user already has rather than one more browser tab.

---

## Why it matters — three outcomes

**Editable means editable**
100% of text, shapes, charts and diagrams are native DrawingML; zero rasterized content, verified by automated structural inspection — not a claim, a test.

**It works where the cloud can't**
Zero outbound calls after first-run model download; every V1 feature verified under `unshare -n` network isolation in CI. Conda-forge-only runtime, weights air-gappable via `DECKCRAFT_MODEL_DIR`.

**It lives inside the assistant you're already in**
Claude Skill + MCP stdio server + `typer` CLI at V1 (3 of 6 surfaces), plus a conda-forge recipe so colleagues get it from the mirror their org already pulls.

---

## The numbers

| Metric | Value |
| --- | --- |
| Native DrawingML in generated output (SC-05) | **100% — zero rasterized** |
| Distribution surfaces live at V1 (SC-09) | **3 of 6** (Skill · MCP · CLI) |
| Generation time, 10-slide deck, no images, large tier CPU (SC-02) | **< 10 min** |
| Scope: epics / stories / estimate | **6 / 28 / ~9.5 weeks** |
| Master switch | **≥1 real deck per week, 4 consecutive weeks** |
| Open license calls blocking a story | **1** (`pymupdf`, AGPL-3.0/Artifex) |

---

## The honest ledger

**The moat moved.** `hugohe3/ppt-master` (MIT, **41,032 stars** in under 8 months) now matches deckcraft's editability bar — but has no documented local-LLM-first or offline mode. Air-gap posture, not editability, is now the sharpest remaining differentiator.

**One blocker is open.** `pymupdf`, pinned for PDF style extraction, is AGPL-3.0/Artifex dual-licensed against a founding MIT-or-Apache-2.0-only constraint. Three named options — accept with documented rationale, substitute `pdfplumber`, or scope the OCR fallback out. A human call, due before Story 3.2.

---

<!-- _class: lead -->

## The promise

Every deck in the PyForge family currently exports a PowerPoint nobody can edit. Deckcraft is the designated engine that stops that.

**From primitives. Always editable. Behind the firewall.**

deckcraft · PyForge · Dream to Code
