---
marp: true
paginate: true
size: 16:9
title: Scribe — what the team knows, every agent knows
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

SCRIBE · The Chronicler · pyforge crew chapter · Dream: `docs/dreams/pyforge-scribe.md`

# what the team knows,<br>every agent knows.

Scribe is the **inward voice** of the factory — where Herald tells the world, Scribe tells the team. Every decision **captured, curated, compiled** into a knowledge graph, and **answerable from memory**. Adopted 2026-07-23, when the ownership audit found the knowledge station unowned.

| Role | Motto | Owns | Ancestor |
| --- | --- | --- | --- |
| The inward voice | "Capture the decision. Keep the graph. Answer from memory." | team-memory · the graph | Sentinel (2026-04) |

---

<!-- _class: dark -->

## Act I

# The Chronicler

The eighth chair existed before anyone sat in it — the knowledge station was **unowned** until the 2026-07-23 audit.

---

## Knowledge is lossy

The disease, diagnosed by the Sentinel ancestor: an engineer touches **six tools in the first hour**; the knowledge the team runs on is scattered across them, a dozen threads, and whoever was on call.

Every handoff drops context. **AI without the graph hallucinates — hallucination is a context problem, not a model problem.**

---

## The compile loop

The cure: index sources into raw, then **incrementally compile a wiki** — markdown with summaries, backlinks, concepts, articles.

Scribe industrializes that personal loop for a team: **capture → curate → compile → answer.**

---

<!-- _class: dark -->

## Act II

# The practice

What Scribe does, and the CLI it will grow.

---

## What Scribe owns

**team-memory** — the shared `.claude/memory` layer: what the team knows, every agent knows.

**Sentinel's unbuilt core** — the knowledge graph compiled nightly from real tools.

**The curation surfaces** — the Dreams index, ADRs, wikis, catalogs.

```
scribe capture --decision "…" --link dream:pyforge-atlas
scribe compile --graph nightly
scribe answer "why did we pin conda-smithy <4?"
```

---

<!-- _class: dark -->

## Act III

# Already beating

The Scribe habit already exists in the factory — it just didn't have a name.

---

## Scribe-shaped machinery

**The memlog discipline** — append-only decision logs; derived artifacts re-render from the log, never hand-patched.

**The auto-memory pipeline** — thirty-plus curated entries; the single-operator prototype of team memory.

**Dream realization logs** — decisions recorded where the aspiration lives.

---

## Memory that stays true

The differentiator: **curation**. A memory that only accumulates becomes a landfill that misleads.

Scribe **supersedes, dedups, links** — and a wrong memory gets corrected at the source.

---

<!-- _class: lead -->

## The creed

# What the team knows, every agent knows.

The graph is the product. The Scribe keeps it.

Scribe · pyforge crew · Dream to Code
