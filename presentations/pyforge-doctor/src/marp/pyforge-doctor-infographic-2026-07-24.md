---
marp: true
paginate: true
size: 16:9
title: Doctor — the practice, at a glance
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
  table { font-size:.76em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- _class: lead -->

# The practice
## Doctor · The Physician — at a glance

Pre-flight before the run. **Pulse after the ship.** Prescriptions, never bare findings.

---

## The patient chart — what Doctor watches

| Vital | Instrument | Signal |
| --- | --- | --- |
| **Machinery** | engine self-check | envs, engines, configs sound before the loop |
| **Freshness** | `staleness-report` · `behind-upstream` | who lags upstream, by how much |
| **Health** | `feedstock-health` | stuck bots, red CI, open issues |
| **Threat** | `cve-watcher` + KEV/EPSS/CWE | new advisories, exploited-in-wild first |
| **Lifecycle** | `release-cadence` · `adoption-stage` | acceleration, silence, abandonment |

---

## Triage order — prescriptions ranked

**1 · exploited-in-wild** (KEV-listed) → patch now · **2 · high-EPSS criticals** → this week · **3 · EOL / abandoned** → plan replacement (`find-alternative`) · **4 · stale-but-healthy** → routine refresh waves.

Every prescription names the root cause and the order of work — a worklist, not a report.

---

## Consolidation, not invention

The instruments already beat inside the factory — atlas health surface, advisory watch, Warden's self-check pattern. **Doctor is one bedside manner over all of them**: one chart, one triage, one voice to Marshal's line and Herald's briefs.

---

<!-- _class: dark -->

## The creed

A fault caught in triage costs seconds. The same fault in production costs an outage.

# Check the vitals. Diagnose the fault. Keep the ecosystem alive.
