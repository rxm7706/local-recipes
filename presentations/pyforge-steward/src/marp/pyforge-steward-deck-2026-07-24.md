---
marp: true
paginate: true
size: 16:9
title: Steward — provision the line, keep the lights on
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

STEWARD · The Provisioner · pyforge crew chapter · Dream: `docs/dreams/pyforge-steward.md`

# provision the line.<br>keep the lights on.

Steward runs **the estate the factory stands on** — Mason ships artifacts and stops at the registry, Doctor observes and prescribes, **Steward deploys, provisions, and operates**. Adopted 2026-07-23, when the ownership audit found Deployment & Operations orphaned between stations.

| Role | Motto | Owns | Rides on |
| --- | --- | --- | --- |
| The estate | "Provision the line. Hold the keys. Keep the lights on." | deploys · keys · budgets | incident response |

---

<!-- _class: dark -->

## Act I

# The Provisioner

The Implementation view names **Deployment & Operations** a first-class SDLC stage — in the crew it fell between two chairs, until the Steward sat down.

---

## Privilege drift

**No privilege outlives its deployment.**

The live case on the desk: the JFROG API key that attaches to every outbound request regardless of host — Doctor finds it, **Steward remediates it** and owns the key lifecycle from then on.

---

## Budgets are governance

The Taxonomy view's resource governance, made real: **machine-readable ceilings** — lock infrastructure at $1,500/month — enforced with alerts, **not hoped about in a wiki**.

---

<!-- _class: dark -->

## Act II

# The duties

Four duties, and the CLI they will grow.

---

## The four duties

| Duty | What it means |
| --- | --- |
| **Provision** | runners + environments ready before Doctor's pre-flight ever runs |
| **Deploy** | services, not just artifacts — hardened, on the platform |
| **Hold the keys** | audit, rotate, revoke; credential lifecycle owned |
| **Enforce ceilings** | budgets as machine-readable governance |

```
steward provision --runners ci --envs pixi
steward deploy --service console --target pages
steward keys rotate --scope jfrog
steward budget enforce --ceiling 1500usd/mo
```

Incident response rides on all four.

---

<!-- _class: dark -->

## Act III

# Already steward-shaped

The duties are already being done — **by hand, without a name.**

---

## The estate today

**The Pages console deploys** — today a hand-run `dashboard-gen` + push.
**The pixi environment estate** — with its `environment.yaml` sync discipline.
**The air-gap routing machinery** — truststore + JFrog chains, awaiting an operator.

All Steward duties, done manually. The chair now has an owner.

---

## Deploy services, not artifacts

The differentiator versus Mason: **Mason's job ends when the artifact reaches the registry. Steward's job starts there** — the service on the platform, hardened, budgeted, keyed, observed, and answered-for when it breaks.

---

<!-- _class: lead -->

## The creed

# Nothing the factory needs is missing. Nothing it no longer needs stays privileged.

Provision the line. Hold the keys. Keep the lights on.

Steward · pyforge crew · Dream to Code
