---
marp: true
paginate: true
size: 16:9
title: Genesis — the Dream-to-Code factory, at a glance
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

# The Dream-to-Code factory
## PyForge · Genesis — at a glance

One pipeline: **Dream → Deck → Spec → Code → Proclaim.**
Eight Forgemasters. One design system. Zero vibes.

---

## The pipeline, tier by tier

| Tier | Artifact | Owner | Lives at |
| --- | --- | --- | --- |
| **0 · Dream** | the why — raw aspiration | you | `docs/dreams/<slug>.md` |
| **deck** | visual alignment | Herald | `presentations/<slug>/` + Claude Design |
| **spec** | the machine contract (5-field kernel) | Marshal · BMAD | `_bmad-output/…/planning-artifacts/specs/` |
| **build** | gated story loops | Marshal · bmad-loop | loop homes · `Merge bmad-loop/…` |
| **realized** | shipped + governed | crew | surface manifests · `spec-surface-check` |

Every Dream shows at its **furthest stage** on the live console — with its chain (▤ deck · § spec · ⚙ project · n/n build) on the chip.

---

## The crew — stations and their verdicts

| | | |
| --- | --- | --- |
| **Herald** — decks, bridge, proclamations | **Marshal** — the loop, gates, escalation | **Atlas** — the dependency map |
| **Warden** — never false-green | **Mason** — forge, bind, ship | **Doctor** — vitals + diagnosis |
| **Scribe** — the team's memory | **Steward** — keys, budgets, uptime | *stations own verdicts; Marshal owns the loop* |

---

## The autonomy gradient — how far the leash goes

Autonomy is a **gradient, not a leap of faith** — personas + skills + a deterministic harness carry the SDLC at every level, up to fully autonomous when a human so chooses.

| Level | Mode | Who drives |
| --- | --- | --- |
| **L1** Assistive | AI support | human is the primary driver |
| **L2** Task-based | discrete tasks under approvals (per-story **ATTENDED**) | human approves each |
| **L3** Conditional · context gates | **the ceiling running here today** — unattended loops in machine-readable bounds; unsafe calls escalate | agent, gated |
| **L4** High-level | human sets governance + policy | human governs |
| **L5** Self-governance | full autonomy | human governs intent alone |

**Live L3 evidence:** 32/32 Atlas stories shipped unattended-with-gates · CRITICAL escalation via `bmad-loop-resolve` · a real context-gate escalation 2026-07-23 · model-tier policy per story.

---

## The SDLC, staffed — phase × persona × skills

Every stage has an owner and a skill set. **Deployment & Operations was the one orphaned stage** until Steward joined the crew.

| Phase | Personas | Skills — today |
| --- | --- | --- |
| **Dream & Pitch** | Human · Herald | `docs/dreams/`; the Design bridge (`deck seed`/`pull`); decks, infographics, exec summaries |
| **Plan & Spec** | Marshal + BMAD (Mary · John · Winston · Sally) | `bmad-spec` 5-field kernel; BMM planning workflows |
| **Build** | Marshal + BMAD (Amelia · Paige) | `bmad-loop` + `bmad-dev-auto` gated loops; TEA; `skill-forge` |
| **Map** | Atlas | `atlas map` dual-ecosystem; Kedro / Dagster / DuckDB (waves 0–H) |
| **Audit** | Warden | `warden audit` — six axes, one verdict, hard CI gate |
| **Package & Ship** | Mason | `mason recipe / package / lock`; the CFE skill — 769 feedstocks |

A **frontier** column (specced or dreamed, not yet built) rides the same table.

---

## The Master Pipeline relay

**One automation loop** — the crew hands configs and assets down the line, supervised start to finish by **Marshal**, opened and closed by **Herald**.

| # | Step | Persona | Command |
| --- | --- | --- | --- |
| ✓ | **Pre-flight** | Doctor | `doctor check --env --engines` |
| 1 | **Capture** | Herald | `herald deck generate` |
| 2 | **Build** | Marshal | `marshal factory spin --method bmad` |
| 3 | **Map** | Atlas | `atlas map --ecosystem dual` |
| 4 | **Audit** | Warden | `warden audit --axes …` |
| 5 | **Ship** | Mason | `mason package --ship conda-forge` |
| 6 | **Watch** | Doctor | `doctor monitor --fleet` |
| 7 | **Proclaim** ⟲ | Herald | `herald updates compile · broadcast` |

---

## Proof the model runs

**32/32** Atlas stories shipped by bmad-loop · **26/31** Warden stories with an honest gate · **10** decks in one Modernist system · **25** Dreams on the board · **0** manual Design↔repo transfers · **9 kernels** governing 4,000+ files with drift detection.

---

<!-- _class: dark -->

## Genesis is also the seed

**Greenfield**: init a repo Dream-first — tiers, crew, BMAD wiring, deck family from day zero.
**Brownfield**: adopt in place without disturbing what runs — *this repo was the first*.

# Write the Dream. The factory does the rest.
