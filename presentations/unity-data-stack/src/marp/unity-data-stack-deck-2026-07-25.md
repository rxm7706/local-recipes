---
marp: true
paginate: true
size: 16:9
title: Unity Data Stack — one workspace, one lock, one gate
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
  table { font-size:.72em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- 01 · Cover -->

UNITY DATA STACK · the enterprise innersource platform · PyForge · Dream: `docs/dreams/unity-data-stack.md`

# one workspace.<br>one lock. one gate.

Open-source culture **inside** the enterprise: an opinionated, conda-native, air-gap-first, spec-governed monorepo where teams co-contribute templates, libraries, services and Data Products on **one python-first toolchain** — standards chosen once and machine-enforced, not written on a wiki page.

| Model | Substrate | Contract | Depth |
| --- | --- | --- | --- |
| Inner-Source | pixi orchestrator root | 9 CAP · 60 FR · 23 AD | PRD + architecture |

---

<!-- _class: dark -->

## Act I

# Six problems, solved once

Native + Python resolution · offline reproducibility · supply-chain compliance · OpenShift deployment · cross-platform testing · **letting another team contribute without breaking anything.**

Every team solves them slightly differently — and the organization pays for the difference forever, in onboarding time, duplicated internal libraries, audits measured in weeks, and the quiet conclusion that sharing code is not worth the trouble.

---

## Two clocks, both running

**The regulatory clock — EU CRA.** In force 2024-12-10. **Vulnerability-reporting obligations begin 2026-09-11**; main obligations 2027-12-11. Obligations propagate through the value chain, so an internal platform feeding EU-market products inherits the evidentiary burden.

**The artifact decay clock.** A 37 KB Constitution, a **1,726-line** working pixi root and a 12 KB toolchain spec, authored 2026-01 → 2026-05 and never landed. Verified drift: `requires-pixi = "==0.59.0"` **blocks every current install** (0.73.0); Python 3.12 has gone security-phase; 3.15 first-releases 2026-10-01; the Constitution's own review lapsed 2026-02-20.

---

## The Constitution is the requirement spine

| Article | Subject | Disposition in v1 |
| --- | --- | --- |
| **II** | Pixi-first package management | Carried — FR-1 · 10 · 14 · 27 |
| **VII** | Data mesh | Carried — FR-48–52 (principles 1 and 2 faithfully implemented) |
| **XI** | Performance and scalability | **Not carried** — guidance with no platform mechanism |
| **XII** | Security and compliance | Carried — FR-39–47 · 57 · 58 |
| **XIV** | Python version support | **Revised** — the 2-year rule expires its own baseline |

**Eight amendments before re-ratification** — including correcting MCP to **Model Context Protocol**, naming whose approval Art. VIII § 8.3 demands, and re-ratifying the overdue governance review.

---

<!-- _class: dark -->

## Act II

# One authoritative lock

A pixi orchestrator root resolves native and Python packages **together**. The PEP 751 `pylock.toml` export and the offline bundle are **derived** — never a second resolution input.

---

## The flagship command does not exist

```
pdm export --format pylock --override-platform=linux --override-platform=macos …
```

Verified 2026-07-25: **`pdm export` has no `--override-platform` flag.** Platform targeting lives on `pdm lock --platform`.

And the format never promised it either: **PEP 751 does not guarantee multi-platform lockfiles** — it uses environment markers, not a cross-compilation guarantee. The "Cryptographic Predictability" outcome the intake spec promised had **no verified mechanism at all**.

**AD-2** — exactly one authoritative Workspace Lock; every derived artifact generated from one pinned commit SHA and drift-checked against it.
**AD-3** — for every platform × every deployable Environment, a gate **materializes** it from the lock. Coverage per platform, never one boolean.

---

## Governed, not imposed

**AD-8 — every mandate machine-classified.** The Constitution declares itself uniformly "immutable" and "non-negotiable", which collapses federated governance into central imposition. Each mandate now carries exactly one classification: **platform-invariant** (no override) or **domain-default** (overridable with a linked decision record). An unclassified mandate fails the gate.

**FR-33 — the social layer, supplied.** The Constitution required "at least one human approval" and **never said whose**. Every Package now names a **Trusted Committer**. SM-2 (cross-team merged PRs) must rise *while* SM-C1 (internal forks) falls — otherwise SM-2 is not measuring what it claims.

---

## Three planes, one paradigm, one owner each

**Declarative Reconciliation:** every plane declares a desired state and materializes it. Nothing is mutated in place; drift is a defect with a detector.

| Plane | Declared | Materialized | Station |
| --- | --- | --- | --- |
| Workspace | manifests → Workspace Lock | an Environment on disk | **Marshal** |
| Data | Asset definitions + contracts | a Data Product in a Layer | **Atlas** |
| Delivery | git-tracked desired state | running workloads | **Steward** |

**AD-17:** every plane resolves to exactly one station of the PyForge Guild. The intake spec's five roles mapped onto the eight Smiths and left **three unmapped** — Herald, Doctor, Scribe: communication, diagnostics, memory. It covered *doing*, not observing, explaining or remembering.

---

## Compliance is a build artifact

**SBOM (AD-11)** — generated inside the built artifact with populated dependency edges, not from a lock. A flat inventory answers "do we ship X?" but never "what reaches X?". CycloneDX 1.7 is **ECMA-424**; the version is pinned, never implicit.

**Provenance (AD-12)** — entirely absent from the intake set. SLSA Build L1 floor, L2 goal; an **unattested artifact does not deploy** to any Stage whose promotion policy requires approval.

**The gate (AD-6)** — PyForge Warden already ships a strict superset, so Unity **consumes it as a CLI** in its own lean Environment. Never a library import, never CI-only; the exit code derives from the report **file**.

---

<!-- _class: lead -->

## The measured promise

# Six problems solved once — and if cross-team reuse never rises, the platform failed at its premise regardless of technical quality.

**< 1 hr** clone to a passing test, docs only (SM-1) · **100%** platform + air-gap parity, materialized (SM-4 / SM-6) · **minutes** from publication to estate-impact determination (SM-5) · **no epics** — PRD + architecture depth by design; stories decompose when scheduled.

Unity Data Stack · PyForge · Dream to Code
