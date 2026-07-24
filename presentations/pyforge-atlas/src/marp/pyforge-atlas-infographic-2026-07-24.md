---
marp: true
paginate: true
size: 16:9
title: Atlas — the migration, at a glance
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
  table { font-size:.74em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- _class: lead -->

# The migration
## Atlas · cf_atlas → Kedro DAG — at a glance

A 10k-LOC procedural monolith, re-shaped into **pure nodes · declared catalog · seven pipelines** — built by an agent workforce, **shipped 2026-07-18**.

---

## The shape

| Before | After |
| --- | --- |
| 10k-LOC procedural orchestrator | pipes-and-filters over a **declared Data Catalog** |
| hand-wired checkpoints per phase | **inherited** checkpointing, IO, timeouts, lineage |
| 23 ad-hoc phases | 23 nodes in **7 fixed pipelines**, producer owns the dataset |
| pages for humans | **agent-legible feeds** + DuckDB + universe SBOM |

---

## The execution model

**Graduated autonomy, gates first**: 6 attended · 4 dev-auto · 22 loop-driven stories — **~21 of 32 loop-drivable**, and the six deterministic gates were never weakened to raise that share. Eight waves (0, A–H); legacy retired only after parity.

---

## The proof

**Phase 24 needs no hand-wiring.** Declare, write the node, contract it — B8–B10 (Basilisk, velocity, readiness) landed through exactly that path with **zero hand-written checkpoint code**. Evidence: PRs **#58–#105 merged**, all 32 stories done.

---

<!-- _class: dark -->

## The creed

The DAG is the deliverable. The gates are the law. The agents do the wiring — because there isn't any.

# Never hand-wire story 33.
