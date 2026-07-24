---
marp: true
paginate: true
size: 16:9
title: Doctor — Executive Summary
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

DOCTOR · The Physician · `docs/dreams/pyforge-doctor.md`
**One bedside manner over the fleet's vitals**

# Check the vitals. Keep the ecosystem alive.

### Sound machinery before the run. A finger on the pulse after the ship.

Doctor is the health and diagnostics authority of the factory: pre-flight checks so the loop never starts on broken machinery, continuous monitoring so shipped packages never rot silently, and prescriptions — not just reports — so every finding arrives with its ordered fix. It consolidates instruments the factory already runs across atlas and warden.

---

## Why it matters — three outcomes

**Fail fast, not mid-build**
A missing engine or broken config is caught in triage — before Marshal spins the factory — where it costs seconds instead of a wasted run.

**Nothing rots silently**
Freshness, drift, new advisories, abandonment signals — watched continuously across 769 feedstocks; regressions surface the moment they appear, not when a user hits them.

**Prescriptions, not reports**
Every diagnosis names the root cause and an ordered remediation plan: what to patch, upgrade or retire, in what order — findings become worklists, not noise.

---

## The numbers

| Metric | Value |
| --- | --- |
| Feedstocks under continuous watch | **769** |
| Atlas instruments consolidated | **6+ CLIs** (health · staleness · upstream · CVE · cadence · adoption) |
| Advisory overlays feeding triage | **KEV + EPSS + CWE** |
| Cost of a fault caught pre-flight vs production | **seconds vs outages** |

---

<!-- _class: lead -->

## The promise

The factory only stays autonomous if something is always watching its health — and knows what to do when it falters.

**Check the vitals. Diagnose the fault. Keep the ecosystem alive.**

Doctor · pyforge crew · Dream to Code
