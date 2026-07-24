---
marp: true
paginate: true
size: 16:9
title: Atlas — Executive Summary
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

ATLAS · The intelligence layer · BMAD project `pyforge-atlas`
**cf_atlas — the data the whole factory reads**

# From monolith to DAG. Shipped.

### Never hand-wire story 33.

cf_atlas is the intelligence layer of the AI-assisted conda-forge packaging factory. The migration re-shaped a 10k-LOC procedural orchestrator into declarative Kedro dataflow — 23 phases as pure nodes in seven fixed pipelines over a declared Data Catalog — executed wave-by-wave by an agent workforce under graduated autonomy, and **shipped 2026-07-18** (PRs #58–#105, all 32 stories done).

---

## Why it matters — three outcomes

**Agents can extend it without hand-wiring**
The load-bearing journey: declare the dataset, write the pure node, contract it — checkpointing, IO, timeouts, lineage are all inherited. New signals B8–B10 landed exactly this way, with zero hand-written checkpoint code.

**The gates never bent**
Frozen exit-code convention, six deterministic gates (each a wave's first deliverable), verify-first discipline. ~21 of 32 stories ran loop-drivable — and no gate was ever weakened to raise that share.

**The read surface inverted**
One semantic interface (the BSL) feeds every consumer — Vizro pages, Vizro-AI, MCP tools, A2A, CLI — plus a DuckDB query surface, a universe SBOM, and agent-legible feeds. Feeds beat pages.

---

## The numbers

| Metric | Value |
| --- | --- |
| Stories shipped (8 waves, 22 FRs) | **32 / 32** |
| Merged PRs (bmad-loop, graduated autonomy) | **#58–#105** |
| Domain pipelines owning all 23 phases | **7** |
| Hand-wired checkpoints in the new DAG | **0** |

---

<!-- _class: lead -->

## The promise

The real deliverable is not speed — it is a DAG an autonomous agent can extend without hand-wiring a single checkpoint.

**Declare the node. Inherit the machinery.**

Atlas · pyforge family · Dream to Code
