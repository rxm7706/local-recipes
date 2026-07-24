---
marp: true
paginate: true
size: 16:9
title: Marshal — the factory line, at a glance
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

# The factory line
## Marshal · The Commander — at a glance

Spec in → gated loop → **validated code out**. Every run visible. Zero vibes.

---

## One story's journey down the line

| Stage | What happens | Who decides |
| --- | --- | --- |
| **spec** | per-story intent contract drafted (`bmad-dev-auto`) | dev session |
| **gate** | `per-story-spec-approval` — run PAUSES | human / scope-check |
| **build** | implementation in an isolated story worktree | dev (sonnet / opus by class) |
| **review** | multi-lens hunt (adversarial · edge-case · verification-gap) | independent lenses |
| **verify** | deterministic project-scoped test gate | the harness, not a skill |
| **merge** | `Merge bmad-loop/<run>/<story>` — the ledger entry | orchestrator |

---

## The doctrine

**Skills are the unit of execution** — BMM's 34+ workflows, community plugins, forged skills.
**The harness is the unit of governance** — bmad-loop, sandboxes, verify gates: deliberately **not** a skill.
**Stations own verdicts; Marshal owns the loop** — the hand that builds must not be the gate that judges it.

---

## Proof the line runs

**32/32** Atlas stories (waves 0–H, PRs #58–#105) · **26/31** Warden stories with the never-false-green gate · **2 loops concurrently** on one machine (loop-home isolation, proven live) · **0** escalations guessed.

---

<!-- _class: dark -->

## The toolkit

**BMM · BMB · TEA · BMGD · CIS** + web bundles for flat-rate planning + community plugins + `bmad-loop` / `bmad-dev-auto` for gated autonomy.

# What ships is what was specified.
