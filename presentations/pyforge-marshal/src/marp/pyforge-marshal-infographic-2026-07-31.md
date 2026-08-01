---
marp: true
paginate: true
size: 16:9
title: Marshal — the Dream-to-Code factory line, at a glance
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:24px; }
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
  table { font-size:.68em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:5px 9px; }
---

<!-- _class: lead -->

# The factory line
## Marshal · The Commander — the Dream-to-Code operating model, at a glance

Spec in → gated loop → **validated code out**. Six commands shipped (Epic 1 · 10/10 · 2026-07-31); **the supervisor is the product**. Every run visible. Zero vibes.

---

## The Dream-to-Code pipeline, tier by tier

| Tier | Artifact | Owner | Lives at |
| --- | --- | --- | --- |
| **0 · Dream** | the why — raw aspiration | You | `docs/dreams/<slug>.md` |
| **Pitch** | exec summary · infographic · decks | Herald | `presentations/<slug>/` + Claude Design |
| **Spec** | the machine contract (5-field kernel) | **Marshal · BMAD** | `_bmad-output/…/planning-artifacts/specs/` |
| **Build** | gated story loops | **Marshal · bmad-loop** | loop homes · `Merge bmad-loop/…` |
| **Realized** | shipped + governed | the entire crew | surface manifests · `spec-surface-check` |

Marshal owns the two middle tiers — **the contract and the build**.

---

## The Guild — eight stations, one owner of execution

**Herald** the Proclaimer · **Marshal** the Commander · **Atlas** the Navigator · **Warden** the Guardian · **Mason** the Artisan Builder · **Doctor** the Physician · **Scribe** the Chronicler · **Steward** the Provisioner.

Every station renders its own verdict — **the hand that builds is never the gate that judges** — and Marshal alone owns execution, **sequencing on verdicts it never authors** (ratified 2026-07-31).

---

## One story's journey down the line

| Stage | What happens | Who decides |
| --- | --- | --- |
| **spec** | per-story intent contract drafted | dev session |
| **gate** | `per-story-spec-approval` — run PAUSES | human / scope-check |
| **build** | implementation in an isolated story worktree | dev (sonnet / opus by class) |
| **review** | multi-lens hunt (adversarial · edge-case · verification-gap), standing at every level | independent lenses |
| **verify + merge** | full suite green, then a labeled merge commit | the loop, mechanically |

---

## The stack Marshal drives — eleven packages, one install

| Package | Ver | What it is |
| --- | --- | --- |
| **bmad-method** | 6.10.0 | the method core — BMM, 51 installed skills |
| **bmad-loop** | 0.9.0 | the engine — **wrapped, never absorbed** |
| bmad-builder (BMB) | 2.1.0 | author custom agents & workflows |
| …test-architecture-enterprise (TEA) | 1.19.1 | risk-based test strategy |
| …creative-intelligence-suite (CIS) | 0.2.1 | ideation & design thinking |
| **bmad-manticore** | 2.0.0 | **AI video production pipeline — 16 mc-\* skills** |
| bmad-labs-skills | 1.0.0 | community marketplace — 21 skills |
| bmad-utility-skills | 2.0.0 | PR review · triage · changelog · RCA |
| bmad-method-wds-expansion | 0.4.3 | Web Design System — UX & strategy agents |
| bmad-dashboard | 1.2.2 | the Guildhall board |
| bmad-module-template | 0.1.0 | scaffold for new modules |

Plus **Skill Forge** (16 skf-\*) · web bundles (Gems / Custom GPTs) · **10 deterministic detectors**.

---

## Graduated autonomy — L1–L5, gates never traded away

**L1** Assistive · **L2** Task-based · **L3 Conditional / Context Gates — the production ceiling, running here today** · **L4** High-level · **L5** Self-governance.

Modes: attended wave boundaries · dev-auto for judgment-heavy work · loop-gated (the workhorse that shipped Atlas + Warden) · unattended with **the independent AI review pass still standing** and every escalation still pausing the run.

---

<!-- _class: dark -->

## Shipped — the marshal CLI · Epic 1 · 10/10

`marshal init <slug>` · `marshal preflight <slug>` · `marshal homes` · `marshal config compose` · `marshal teardown <slug>` · `marshal --version`

**785 tests** · coded `MRS-*` envelopes · frozen exit domain `{0,1,2,3,4,130}` · **one harness seam** (FR-52, import-linter-enforced) · teardown **refuses to destroy unmerged work** · **wrap, never absorb**.

---

## The Master Pipeline relay

Doctor pre-flight → **Herald** captures the Dream → **Marshal** spins the factory → **Atlas** maps → **Warden** audits → **Mason** ships → **Doctor** watches → **Herald** proclaims.

Supervised start to finish by Marshal, opened and closed by Herald.

---

## Proof the line runs

**57/57** Atlas (Kedro migration, PRs #58–#105) · **43/43** Warden (never-false-green gate) · **10/10** Marshal Epic 1 — built by the line it now runs · **128/333** fleet-wide across 8 stations · **0** frozen-surface violations reaching a merge.

---

## The frontier — the last mile lands itself

Ruled 2026-07-31: **Marshal owns the PR lifecycle** — `marshal land` opens, labels, waits, merges, retires the branch; refuses like teardown. Four Dreams seeded: **durable-runs · fidelity-enforcement · one-front-door · pr-lifecycle**. Ahead: gates as objects (E2) · the outside supervisor (E3) · landing paper trail (E4) · fleet status (E5) · portability proven (E6).

---

## The BMAD team — who decides

**Mary** Analyst · **John** PM · **Winston** Architect · **Sally** UX · **Amelia** Dev · **Paige** Tech Writer — Marshal's sub-agents on the floor.

**Human** governs intent · **Marshal** owns execution · **BMAD team** the inner workforce · **crew stations** independent verdicts.

---

## Three ways work flows

**Flow A** one attended story (judgment-heavy) · **Flow B** an epic, loop-gated — the workhorse that shipped Atlas + Warden · **Flow C** the unattended 8-home fleet, gates still on.

**Autonomy changes who approves, never what is checked.**

---

## Which verb, when

New line → `marshal init` · pre-launch → `preflight` · isolation → `homes` · policy → `config compose` · judgment story → `bmad-dev-auto` · epic → the loop · fleet → `gate_mode none` + supervisor · CI → `gate evaluate` (E2) · land → `deploy · land` (E4) · retire → `teardown`.

---

## Who it serves · where it runs

**Solo dev** a second shift · **Team lead** a review floor that never rubber-stamps · **Eng manager** a board that cannot lie · **CTO** autonomy with an audit trail.

Enterprise: three pure policy layers, site config materialized at install · internal tooling **mounts, never forks** · **local-first, offline by default**.

---

## Integration seams

**FR-52 harness seam** (import-linter-enforced) · **adapter profiles** (Claude today; Copilot/Cursor/Devin as profiles) · **the declared tool surface** (.mcp.json per home) · **verdict-artifact reads** (revision-pinned) · **10 detectors** · **machine-readable everything**.

---

## The seed — greenfield or brownfield

**Greenfield**: the factory arrives before the first feature. **Brownfield**: adopt in place — **this repository was the first patient**. Formerly Genesis's charge, now folding into Marshal (E10–12).

---

<!-- _class: lead -->

# Write the Dream. The factory does the rest.
