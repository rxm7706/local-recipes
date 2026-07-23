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
  a { color:#c22a10; }
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

ATLAS · `pyforge-atlas`
**cf_atlas Kedro / Dagster / DuckDB migration — built to be maintained by agents**

# Turn a 10k-LOC monolith into a DAG agents can extend.

### One intelligence layer for the whole conda-forge channel.

`cf_atlas` builds a database over **19,726 feedstocks** — versions, downloads, maintainers, vulnerabilities, readiness. The migration replaces the hand-rolled orchestrator with **Kedro nodes + Dagster orchestration + DuckDB compute**, a Boring Semantic Layer, a Vizro / Vizro-AI read surface, and MCP / A2A agent interfaces — so an autonomous agent workforce can safely maintain and extend it.

<!-- Executive one-slide summary. The load-bearing justification is agent-maintainability. -->

---

## Why it matters — three outcomes

**Agent-maintainable by construction**
Small, pure, contract-guarded nodes with declared inputs/outputs. A new signal lands as node + catalog + contract — inheriting checkpoint, TTL, backoff and observability for free.

**Honest, incremental performance**
Only affected nodes re-materialize; DuckDB adds query-time analytics, graph traversal and vector search. The cold rebuild stays network-bound — no engine-swap miracle claimed.

**Feeds, not just pages**
A BSL semantic graph powers dashboards, a natural-language query path, and MCP / A2A surfaces the recipe-authoring agents consume. The productizable value is machine-consumable data.

---

## The numbers

| Metric | Value |
| --- | --- |
| Domain pipelines (was 23 phases) | **7** |
| Waves · stories | **8 + 0 · 32** |
| Deterministic verify gates | **6** |
| New signal sources (Basilisk · velocity · readiness) | **3** |
| Feedstock population | **19,726** |

---

<!-- _class: lead -->

## Built to be maintained by agents

The real deliverable isn't speed — the cold rebuild is network-bound. It's a DAG small enough, pure enough and contract-guarded enough that an agent can add **phase 24** without hand-wiring a single checkpoint.

**The price of never hand-wiring story 33.**

Atlas · module `pyforge.atlas` · dist `pyforge-atlas`
