---
marp: true
paginate: true
size: 16:9
title: Mason — Executive Summary
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

MASON · The Artisan · `docs/dreams/packaging-factory.md`
**The working forge behind the persona**

# We forge the blocks. We ship the structure.

### 769 feedstocks. One craft. Both ecosystems.

Mason binds raw software ingredients into deterministic, reproducible, cross-platform structures — PyPI for pure-Python agility, conda-forge for compiled scientific and ML/AI stacks, treated as one craft. Behind the persona stands the AI-assisted packaging factory that already runs this repo: the full recipe lifecycle from generation to merged PR, gated at every step.

---

## Why it matters — three outcomes

**Dual-ecosystem, one pipeline**
The same library ships as wheel **and** conda package from one synchronized release; one lockfile serves every platform. No more "works on pip, breaks on conda."

**Structural integrity by construction**
rattler-build + pixi, deterministic builds, per-recipe gates (validate → scan → optimize → build → verify) — brittle environments rejected at the forge, not discovered in production.

**A forge that learns**
Every build failure becomes a recorded gotcha (106 and counting) in the conda-forge-expert skill — the craft compounds; the next recipe inherits every lesson.

---

## The numbers

| Metric | Value |
| --- | --- |
| Maintained feedstocks | **769** |
| Local recipe mirrors under governance | **~900 (2,809 files)** |
| Encoded packaging gotchas (skill) | **106** |
| Platforms per expanded feedstock | **up to 5** |

---

<!-- _class: lead -->

## The promise

Anything the crew needs — PyPI, npm, CRAN, a Go binary, a Rust CLI — becomes an installable, reproducible conda artifact with a paper trail.

**We forge the blocks. We bind the environment. We ship the structure.**

Mason · the packaging factory · PyForge Guild
