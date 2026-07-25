---
marp: true
paginate: true
size: 16:9
title: Unity Data Stack — the platform, at a glance
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

# Unity Data Stack
## The enterprise innersource platform — at a glance

Standards **chosen once and machine-enforced**. Native and Python dependencies resolved **together**, offline, on every declared platform. Evidence emitted by construction.

---

## The problem, and two clocks

Every team re-solves the same **six problems** — native + Python resolution, offline reproducibility, supply-chain compliance, OpenShift deployment, cross-platform testing, cross-team contribution — and the organization pays for the difference forever.

**EU CRA:** in force 2024-12-10 · **reporting obligations 2026-09-11** · main obligations 2027-12-11.
**Artifact decay:** a 37 KB Constitution, a **1,726-line** pixi root and a 12 KB toolchain spec, authored 2026-01 → 05 and never landed.

---

## The requirement spine

| Article | Subject | Disposition in v1 |
| --- | --- | --- |
| **II** | Pixi-first package management | Carried — FR-1 · 10 · 14 · 27 |
| **VII** | Data mesh | Carried — FR-48–52 |
| **XI** | Performance and scalability | **Not carried** — guidance, no mechanism |
| **XII** | Security and compliance | Carried — FR-39–47 · 57 · 58 |
| **XIV** | Python version support | **Revised** |

**8 amendments** required before re-ratification — including MCP → **Model Context Protocol** and naming the Trusted Committer.

---

## The honest findings

**The flagship command does not exist.** `pdm export` has no `--override-platform` flag (verified 2026-07-25); platform targeting lives on `pdm lock --platform`.

**The format never promised it either.** **PEP 751 does not guarantee multi-platform lockfiles** — it uses environment markers.

Hence **AD-2** (one authoritative Workspace Lock, every derived artifact from one pinned SHA) and **AD-3** (coverage **materialized** per platform, never inferred).

---

## Governed, not imposed

**AD-8** — every mandate is machine-classified as **platform-invariant** (no override) or **domain-default** (overridable with a linked decision record). An unclassified mandate fails the gate.

**FR-33** — the Constitution required "at least one human approval" and never said whose. Every Package names a **Trusted Committer**.

**SM-2 must rise while SM-C1 falls** — a contribution rate that climbs while internal forks do not fall is not measuring what it claims.

---

<!-- _class: dark -->

## The contract

**9** capabilities · **60** requirements · **23** architecture decisions · **8** accountable stations · **0** epics.

# One workspace. One lock. One gate.

PRD + architecture depth by design — stories decompose fresh when this Dream is scheduled.
