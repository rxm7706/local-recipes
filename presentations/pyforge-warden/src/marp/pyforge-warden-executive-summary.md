---
marp: true
paginate: true
size: 16:9
title: PyForge-Warden — Executive Summary
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  a { color:#c22a10; }
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

PYFORGE-WARDEN · `pyforge-warden`
**Six-axis dependency governance gate**

# Catch risky dependencies before they ship.

### One gate. Both Python ecosystems.

A single CI gate for both Python worlds — **PyPI** applications and the **conda / conda-forge** scientific, analytics and ML/AI data stacks. It checks every dependency across six axes — from unused code to unpatched CVEs, risky licenses and unmaintained upstreams — and blocks risky merges automatically.

<!-- Executive one-slide summary. PyForge-Warden is a CI dependency-trust gate covering both Python ecosystems. -->

---

## Why it matters — three outcomes

**Cover both worlds · PyPI + conda-forge**
Application Python **and** the scientific / ML / AI data stack — one gate covers both, with pluggable engines (deptry + osv-scanner) behind one report.

**Six axes · every dependency risk**
Hygiene, security, license, currency, provenance and maintenance — checked in one pass, blocked before merge, never silently green.

**Trust at scale · auditable, fleet-wide**
Schema-validated reports and expiring, recorded waivers across a 20,000+ repo fleet — without ever mutating your source.

---

## The numbers

| Metric | Value |
| --- | --- |
| Governance axes | **6** |
| Python ecosystems, one gate | **2** |
| Consolidated report + SBOM | **1** |
| Changes to your host or source | **0** |

---

<!-- _class: lead -->

## Honest by design — no false greens

PyForge-Warden refuses to fake a pass. If it can't prove your dependencies are safe, it fails — until you pin them, formally accept the risk, or explicitly run `--warn-only`.

**An honest "not verified" beats a false "all clear."**

PyForge-Warden · module `pyforge.warden` · dist `pyforge-warden`
