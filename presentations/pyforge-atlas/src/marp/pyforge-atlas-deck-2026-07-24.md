---
marp: true
paginate: true
size: 16:9
title: Atlas — from monolith to DAG
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
  table { font-size:.72em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- 01 · Cover -->

ATLAS · The intelligence layer · pyforge family · BMAD project: `pyforge-atlas`

# from monolith<br>to DAG.

cf_atlas is the intelligence layer of an AI-assisted conda-forge packaging factory. This deck is the migration plan that **shipped 2026-07-18**: a 10k-LOC procedural orchestrator became declarative Kedro dataflow — so an **agent workforce** can maintain it.

| Scope | Executed via | Evidence |
| --- | --- | --- |
| 8 waves · 32 stories · 22 FRs | bmad-loop, graduated autonomy | PRs **#58–#105 merged**, all epics done |

---

<!-- _class: dark -->

## Act I

# From monolith to DAG

What the legacy orchestrator costs, and what declarative dataflow replaces it with.

---

## The problem

The legacy orchestrator **ships — but the cost is chronic.** Agents cannot safely extend a 10k-line procedural monolith.

That is the load-bearing justification for the whole migration.

---

## Before and after

Same factory, re-shaped: **pipes-and-filters over a declared Data Catalog.**

**Pure nodes** · **catalog-owned IO** · **per-node timeouts** — six layers mapping every concern to exactly one place.

---

## Seven domain pipelines

The 23 phases become nodes in **exactly seven fixed pipelines**.

**Producer owns the dataset** — no two pipelines write one artifact. New signals join their assigned pipeline, never a new ad-hoc one.

---

<!-- _class: dark -->

## Act II

# Node-shaped & agent-maintainable

Why the node shape matters; what the migration buys; the verify-first gate that keeps it honest.

---

## Add phase 24 without hand-wiring

The load-bearing journey (**UJ-5**): **declare, write the node, contract it** — everything else is inherited.

The new signals B8–B10 landed through exactly this path with **zero hand-written checkpoint code.**

---

## What the migration buys

The honest wins:

- **Incremental re-materialization** (not cold-start speed)
- a **DuckDB query surface**
- a **universe SBOM**
- **agent-legible feeds** — feeds beat pages

---

## The verify-first gate

The **frozen exit-code convention** and the four-axis ComplianceReport, plus **six deterministic gates** — each a wave's first deliverable.

**Gates are never weakened to raise the autonomy share.**

---

<!-- _class: dark -->

## Act III

# An agent workforce builds it

Who runs it, the graduated-autonomy execution model, the eight-wave plan.

---

## Who runs it

Four consumers: **the operator**, **CFE authoring agents**, **BMAD execution agents**, and **CI**.

Internal and non-commercial — adoption means operator + agent usage across a **19,726-feedstock** population.

---

## Graduated autonomy

| Mode | Stories |
| --- | --- |
| Attended (wave-boundary events) | 6 |
| `bmad-dev-auto` | 4 |
| Loop · per-story-spec approval | 11 |
| Loop · per-epic approval | 11 |

**~21 of 32 loop-drivable** — but gates are never weakened to raise that share.

---

## Eight waves, 32 stories

| Wave | Delivers |
| --- | --- |
| 0 | the SKF skill |
| A | the scaffold |
| B | node ports + parity + new signals |
| C | orchestration |
| D | read surface |
| E | agent plane |
| F | DuckDB consolidation |
| G | portability |
| H | the AI factory |

Legacy retires only **after B4 parity**. Shipped: all eight waves, PRs #58–#105.

---

## Which surface, when

The **BSL is the single semantic interface** — every read surface consumes it, never raw SQL.

Vizro pages, Vizro-AI, MCP tools, A2A, three CLI-first exceptions. Public page breadth stays at **one factory-status page**.

---

<!-- _class: dark -->

## Act IV

# New signals

Three committed signal sources — and the open questions, gated by wave.

---

## Three new signals

**Basilisk** — matches by package name, not the OSV tag; `fix_available` is tri-state.
**Velocity** — restricts to releases under 90 days, computed against first availability.
**Readiness** — partitions by upstream category lists; new migrations need **no code change**.

---

## Open questions, gated

**Six open questions**, each adopted at its spec default and re-checked at its gating wave. None block earlier work.

Q5 was resolved into the AI-factory scope.

---

<!-- _class: dark -->

## Act V

# The read surface inverts

On top of the DAG: five surfaces — and the pyforge family relationship.

---

## Five surfaces

**Semantic read** via BSL · the **agent plane** over MCP/A2A · **WASM portability** · the Wave-H **AI factory** · **quality + lineage** via pandera + OpenLineage/OTel.

---

## The pyforge family

Two workspace members in one `pyforge` namespace: **Atlas provides the data; Warden uses it.**

Exactly **one optional code edge · zero cycles** — both install and run independently.

---

<!-- _class: lead -->

## The close

# Never hand-wire story 33.

The real deliverable is not speed — the cold rebuild is network-bound. It is **a DAG an autonomous agent can extend without hand-wiring a single checkpoint.**

Atlas · pyforge family · Dream to Code
