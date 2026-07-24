---
marp: true
paginate: true
size: 16:9
title: Doctor — check the vitals, keep the ecosystem alive
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

DOCTOR · The Physician · pyforge crew chapter · Dream: `docs/dreams/pyforge-doctor.md`

# check the vitals.<br>keep the ecosystem alive.

Doctor is the **health and diagnostics authority** of the factory — sound machinery before the run, a finger on the fleet's pulse after the ship. Its instruments already exist across atlas and warden; **Doctor is the consolidation.**

| Role | Motto | Before | After |
| --- | --- | --- | --- |
| Health authority | "Check the vitals. Diagnose the fault. Keep the ecosystem alive." | pre-flight diagnostics | continuous fleet monitoring |

---

<!-- _class: dark -->

## Act I

# The Physician

Verify the machinery is sound **before** the factory runs; keep monitoring the shipped estate **afterward** — diagnosing faults early, prescribing the fix before an outage.

---

## Preventive vigilance

A fault caught in triage is **cheaper than one caught in production**.

The self-check runs before the factory spins — a missing engine or broken config **fails fast**, never mid-build.

---

## Continuous pulse

Never one-and-done. Once packages ship, Doctor keeps watching — **freshness and drift, new advisories, abandonment signals** — surfacing regressions the moment they appear.

---

<!-- _class: dark -->

## Act II

# The practice

The three duties and their CLI.

---

## The three duties

| Duty | When | What |
| --- | --- | --- |
| **Pre-flight diagnostics** | before Marshal spins the factory | envs, engines, configs verified sound |
| **Fleet monitoring** | continuously, post-ship | health, staleness, advisories across the estate |
| **Remediation guidance** | on every finding | findings → prioritized, ordered worklists |

```
doctor check --env --engines
doctor monitor --fleet
doctor prescribe --priority critical
```

---

<!-- _class: dark -->

## Act III

# Organs that already beat

Doctor is the **consolidation of instruments the factory already runs** — not an invention from scratch.

---

## Existing instruments

**The atlas health surface** — `feedstock-health` · `staleness-report` · `behind-upstream`.
**The atlas advisory watch** — `cve-watcher` · `release-cadence` · adoption signals.
**The engine self-check pattern** — from Warden's pre-flight discipline.

One bedside manner over all of them.

---

## Prescriptions, not reports

Doctor never stops at a finding. Every diagnosis names the **root cause** and comes with an **ordered remediation plan** — what to patch, upgrade or retire, in what order.

---

<!-- _class: lead -->

## The creed

# Check the vitals. Diagnose the fault. Keep the ecosystem alive.

The factory only stays autonomous if something is always watching its health.

Doctor · pyforge crew · Dream to Code
