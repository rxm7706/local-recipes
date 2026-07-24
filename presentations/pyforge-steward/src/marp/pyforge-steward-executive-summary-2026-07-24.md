---
marp: true
paginate: true
size: 16:9
title: Steward — Executive Summary
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

STEWARD · The Provisioner · `docs/dreams/pyforge-steward.md`
**The estate the factory stands on**

# Provision the line. Keep the lights on.

### Mason stops at the registry. Steward starts there.

Steward owns Deployment & Operations — the SDLC stage that fell between chairs until the 2026-07-23 ownership audit. It provisions runners and environments before anything runs, deploys services (not just artifacts), owns the credential lifecycle end-to-end, and enforces resource ceilings as machine-readable governance. Incident response rides on all four.

---

## Why it matters — three outcomes

**No privilege outlives its deployment**
Keys are audited, rotated, revoked — the live case: the JFROG API key attaching to every outbound request, found by Doctor, remediated and lifecycle-owned by Steward.

**Budgets as governance, not hope**
Machine-readable ceilings enforced with alerts — the difference between "locked at $1,500/month" and a number in a wiki nobody reads.

**Services answered-for**
The Pages console, the pixi estate, the air-gap routing — deployed, hardened, observed, and owned when they break. Today done by hand; now with a name and a chair.

---

## The numbers

| Metric | Value |
| --- | --- |
| Duties consolidated (provision · deploy · keys · budgets) | **4** |
| Live credential-leak case on the desk | **1 (JFROG key, remediation owned)** |
| Pixi environments in the estate | **12** |
| Privileges that should outlive their deployment | **0** |

---

<!-- _class: lead -->

## The promise

Nothing the factory needs is missing — and nothing it no longer needs stays privileged.

**Provision the line. Hold the keys. Keep the lights on.**

Steward · pyforge crew · Dream to Code
