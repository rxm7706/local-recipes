---
marp: true
paginate: true
size: 16:9
title: Deckcraft — editable decks, behind the firewall
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

DECKCRAFT · the deck pipeline · PyForge · Dream: `docs/dreams/deckcraft.md`

# editable decks.<br>behind the firewall.

A prompt or a document in; an **editable** `.pptx` — native DrawingML, real charts, a round-trippable Marp sibling — out. Built **from conda-forge primitives**, not by repackaging a SaaS, and it makes **zero outbound calls** by default.

| Package | Surfaces at V1 | Output bar | Status |
| --- | --- | --- | --- |
| `deckcraft` | Claude Skill · MCP stdio · CLI | 100% native DrawingML | Spec'd · 0 of 28 stories |

---

<!-- _class: dark -->

## Act I

# The last mile

Every assistant on the desk can write the words. **None of them can hand you the file.**

---

## Three people, one gap

**The builder** — Claude Code and Copilot open, prose written, then **30–60 minutes** of paste-and-format per deck. The AI half-helps and drops the user.

**The air-gapped colleague** — has Copilot and MS365, cannot reach OpenAI, Anthropic, Google or fal.ai. Cloud deck tools are **unusable by policy**, and there is no local path from prose to file.

**The technical author** — Mermaid comes out a PNG, the chart is a screenshot. It looks fine until you open it and **cannot edit a single thing**.

---

## Never rasterized

**SC-05, checked not claimed:** 100% of text, shapes, charts and diagrams are native DrawingML; **zero rasterized content** — verified by automated structural inspection of the generated file. Mermaid renders offline in ≤3s a diagram; charts embed as native PowerPoint charts wherever the data fits a standard type.

**And it goes back:** every `.pptx` ships a Marp markdown sibling. Hand-edit the Markdown, regenerate the deck — or convert an existing deck back to Marp. Lossy elements (custom animations, complex SmartArt) are **flagged in a sidecar warning file**, never silently dropped.

---

<!-- _class: dark -->

## Act II

# From primitives

No web app to host, no browser tab to switch to. **A package, three adapters, and the surfaces you are already in.**

---

## Three layers, three swap points

| Layer | What lives there |
| --- | --- |
| **Surfaces** | Claude Skill · MCP server (stdio) · `typer` CLI — **3 of 6 live at V1**, each consuming the `Pipeline` API and nothing deeper |
| **Core** | Outline generator · style loader · asset pipeline, feeding six renderers; one immutable Pydantic model crosses every boundary |
| **Adapters** | `LLMAdapter` (llama-server default, Ollama, mlx-lm) · `PptxEngineAdapter` · `PlatformAdapter` — **the only designed swap points** |

Outside `deckcraft.engines.pptx_engine`, **nothing may `import pptx`** — that discipline is what keeps the vendor fallback clean while upstream `python-pptx` stays dormant (1.0.2, last released 2024-08-07).

```
deckcraft init
deckcraft generate --from prd.md --style brand.potx -o pitch.pptx
deckcraft convert pitch.pptx --to marp
```

---

<!-- _class: dark -->

## Act III

# The honest ledger

The 2026-07-25 research pass moved the moat and found a landmine. **Both go on the slide.**

---

## The moat moved

`hugohe3/ppt-master` — a minor "Option C" at intake — is now **41,032 stars and 3,406 forks**, genuinely MIT, compiling constrained SVG into DrawingML. It meets our editability bar. **Editable-native-PPTX is no longer our distinguishing claim**, and neither is from-primitives.

What it does *not* have: any documented local-LLM-first or offline mode. It rides a cloud-hosted coding-agent model and recommends cloud models for quality. **None of the four comparables match a CI-enforced default-offline posture.**

The claim is now: editable **and** air-gapped **and** embedded beyond coding-agent IDEs — enforced by `unshare -n` in CI (SC-07).

---

## The blocker on the desk

`pymupdf` — pinned as the primary PDF style-extraction library — is **dual-licensed AGPL-3.0 / Artifex commercial**. The founding acceptance criterion is **MIT or Apache-2.0 only**, and that bar is why this project exists: its predecessor was rejected for being proprietary.

| Option | What it costs |
| --- | --- |
| **Accept** | AGPL on one opt-in capability path, exception documented explicitly |
| **Substitute** | `pdfplumber` — already in the env, MIT-family, requester-maintained — at a documented quality cost |
| **Scope out** | Drop the OCR-fallback depth and lose the scanned-PDF style source |

A human license call, **undecided**. It blocks before Story 3.2. *The risk is silence, not difficulty.*

---

<!-- _class: lead -->

## The family's engine

# Every deck in this family currently exports a PowerPoint nobody can edit. Deckcraft is how that stops.

Designated 2026-07-23 as the deck family's editable-PPTX engine — `marp --pptx` renders image-slides, so every family PPTX is an interim artifact until deckcraft lands.

28 stories · 6 epics · ~9.5 weeks · **1 real deck/week × 4 weeks is the master switch**

deckcraft · conda-forge-native · Claude Skill · MCP · CLI
