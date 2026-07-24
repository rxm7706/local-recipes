---
marp: true
paginate: true
size: 16:9
title: Steward — the estate, at a glance
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

# The estate
## Steward · The Provisioner — at a glance

Before anything runs: **provisioned**. After everything ships: **operated**. In between: keys, budgets, uptime.

---

## The four duties

| Duty | Today (by hand) | With the Steward |
| --- | --- | --- |
| **Provision** | pixi envs + `environment.yaml` sync | runners + envs ready before pre-flight |
| **Deploy** | Pages console via `dashboard-gen` + push | services on platforms, hardened |
| **Hold the keys** | JFROG chain in env vars | audit · rotate · revoke, lifecycle-owned |
| **Enforce ceilings** | numbers in wikis | machine-readable budgets with alerts |

---

## The boundary with Mason

**Mason's job ends when the artifact reaches the registry.**
**Steward's job starts there** — the service on the platform: budgeted, keyed, observed, answered-for when it breaks.

---

## The live case

The JFROG API key attaches to **every outbound request regardless of host** — a cross-resolver credential leak. Doctor diagnosed it; the airgap kernel names it as an open deviation; **Steward owns the remediation** and the key lifecycle after it. No privilege outlives its deployment.

---

<!-- _class: dark -->

## The creed

Budgets are governance. Keys are lifecycle. Uptime is a duty, not luck.

# Provision the line. Hold the keys. Keep the lights on.
