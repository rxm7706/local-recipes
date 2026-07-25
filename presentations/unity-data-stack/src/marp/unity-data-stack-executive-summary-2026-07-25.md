---
marp: true
paginate: true
size: 16:9
title: Unity Data Stack — Executive Summary
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

UNITY DATA STACK · the enterprise innersource platform · `docs/dreams/unity-data-stack.md`
**Six problems solved once, not once per team**

# Open-source culture, inside the enterprise.

### One workspace. One lock. One gate.

An opinionated, conda-native, air-gap-first, spec-governed monorepo where teams co-contribute templates, libraries, services and Data Products on one python-first toolchain. Native and Python dependencies resolve together, offline, on every declared platform — and the platform emits the compliance evidence to prove what it resolved.

---

## Why it matters — three outcomes

**The Constitution becomes enforceable**
14 Articles are the requirement spine: every FR traces to an Article or its explicit disposition. Article XI is not carried in v1 — it is guidance with no mechanism. Eight amendments are required before re-ratification, and the governance review has been overdue since 2026-02-20.

**Reproducibility is proven, not claimed**
One authoritative Workspace Lock; the PEP 751 export and offline bundle derived from it and drift-checked against one pinned commit SHA. Coverage is proven by materializing every Environment on every declared platform — never inferred from a format claim.

**Compliance becomes a build artifact**
SBOM with populated dependency edges generated from the built artifact, provenance at SLSA L1 floor / L2 goal, and PyForge Warden consumed as the gate — ahead of the EU CRA's 2026-09-11 reporting-obligation date.

---

## The honest findings

| Intake claim | Verified reality |
| --- | --- |
| `pdm export --format pylock --override-platform=…` | **The flag does not exist.** Platform targeting lives on `pdm lock --platform` |
| PEP 751 "tracks multi-platform targets" | **It does not guarantee them** — environment markers express intent, not coverage |
| `requires-pixi = "==0.59.0"` | **Blocks every current install** — 0.73.0 is current (2026-07-15) |
| Python 3.12 as the legacy baseline | **Security-phase upstream**; 3.15 first-releases 2026-10-01 |
| Provenance | **Entirely absent** from the intake set |

---

## The numbers

| Metric | Value |
| --- | --- |
| Capabilities · requirements · architecture decisions | **9 · 60 · 23** |
| Constitution Articles carried, and amendments required | **14 · 8** |
| SM-1 · clone to a passing test, written docs only | **under 1 hour** |
| SM-4 / SM-6 · platform and air-gap parity, materialized | **100%** |
| Epics — PRD + architecture depth by design | **0** |

---

<!-- _class: lead -->

## The premise

If cross-team reuse never rises, the platform has failed at its premise — regardless of technical quality.

**One workspace. One lock. One gate.**

Unity Data Stack · PyForge · Dream to Code
