---
marp: true
paginate: true
size: 16:9
title: Scribe — Executive Summary
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

SCRIBE · The Chronicler · `docs/dreams/pyforge-scribe.md`
**The inward voice — team knowledge, kept true**

# What the team knows, every agent knows.

### Hallucination is a context problem, not a model problem.

Scribe owns the factory's memory: every decision captured where it happens, curated so the record stays true, compiled into a knowledge graph, and answerable — by humans and agents alike. Where Herald tells the world, Scribe tells the team. It inherits Sentinel's founding insight ("the graph is the product") and industrializes the compile loop for a whole crew.

---

## Why it matters — three outcomes

**Handoffs stop dropping context**
Decisions live in append-only logs at the source — memlogs, Dream realization logs, ADRs — and derived artifacts re-render from the record instead of drifting from it.

**Agents answer from memory, not vibes**
The shared memory layer means every agent session starts already knowing what the team knows — pins, conventions, past incidents, why things are the way they are.

**Curation keeps it true**
Accumulation without curation is a landfill. Scribe supersedes, dedups and links — and a wrong memory is corrected at the source, on the record.

---

## The numbers

| Metric | Value |
| --- | --- |
| Curated auto-memory entries (single-operator prototype) | **30+** |
| Append-only memlogs across spec kernels | **10+** |
| Dreams with realization logs on the board | **25** |
| Handoffs where context is lost, by design | **0** |

---

<!-- _class: lead -->

## The promise

Six months from now, "why did we do it this way?" has an answer in seconds — sourced, dated, and linked to the decision that made it so.

**Capture the decision. Keep the graph. Answer from memory.**

Scribe · pyforge crew · Dream to Code
