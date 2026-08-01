---
marp: true
paginate: true
size: 16:9
title: Marshal — enforce the spec. run the line.
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
  table { font-size:.68em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:5px 9px; }
---

<!-- _class: lead -->

# enforce the spec. run the line.
## Marshal · The Commander — the Dream-to-Code factory, 26-slide chapter deck

Six commands shipped (Epic 1 · 10/10 · 2026-07-31) · **the supervisor is the product** · bmad-loop 0.9, wrapped never absorbed.

---

<!-- _class: dark -->

## Act I — The Commander

Eight stations, one Guild — and **one owner of execution**. While Atlas charts the map, Warden secures the perimeter, and Mason binds the packages, Marshal runs the heavy automated machinery.

---

## Autonomy fails two ways

**Unattended** → plausible-but-wrong code, discovered in production. **Over-supervised** → the speed evaporates into meetings.

Marshal's answer is **structural**: spec gates before merge · scope checks on frozen surfaces · independent verification — gates never weakened to raise the autonomy share. **128** stories shipped · **0** frozen-surface violations reaching a merge.

---

## Mindsets: anti-vibe · context containment

**Anti-vibe pragmatism** — strict structural inputs only; deviation from the spec is flagged instantly and corrected. "Close enough" does not compile.
**Ruthless context containment** — each sub-agent gets exactly the context its task requires: **Exact · Clean · Fast**.

---

## Dream to Code, tier by tier

| Tier | Artifact | Owner | Lives at |
| --- | --- | --- | --- |
| **0 · Dream** | the why | You | `docs/dreams/<slug>.md` |
| **Pitch** | decks · infographics | Herald | `presentations/<slug>/` |
| **Spec** | 5-field machine contract | **Marshal · BMAD** | `…/planning-artifacts/specs/` |
| **Build** | gated story loops | **Marshal · bmad-loop** | loop homes |
| **Realized** | shipped + governed | the crew | `spec-surface-check` |

---

<!-- _class: dark -->

## Act II — The Guild & the armory

Eight stations with independent verdicts · six sub-agents on the floor · eleven packages, one install.

---

## The Guild (1/2)

**01 Herald** the Proclaimer — decks, telemetry, broadcasts, video scripts · *"Capture the dream. Illustrate the telemetry. Proclaim the release."* · 4/27
**02 Marshal** the Commander — the BMAD orchestrator; owns the PR lifecycle · *"Enforce the spec. Guard the boundaries. Run the line."* · **Epic 1 · 10/10**
**03 Atlas** the Navigator — PyPI + conda graphed together · *"Chart the dependencies. Map the world. Define the floor."* · **57/57 COMPLETE**
**04 Warden** the Guardian — six axes, one verdict, hard CI gate · *"Halt the threat. Clear the axes. Protect the perimeter."* · **43/43 COMPLETE**

---

## The Guild (2/2)

**05 Mason** the Artisan Builder — wheels + conda-forge, one pass; 769 feedstocks · *"We forge the blocks. We bind the environment. We ship the structure."* · 4/48
**06 Doctor** the Physician — pre-flight, fleet vitals; judges Marshal's own row · *"Check the vitals. Diagnose the fault. Keep the ecosystem alive."* · 5/18
**07 Scribe** the Chronicler — team memory, the knowledge graph · *"Capture the decision. Keep the graph. Answer from memory."* · 2/13
**08 Steward** the Provisioner — runners, keys, budgets, the pager · *"Provision the line. Hold the keys. Keep the lights on."* · 3/26

---

## The BMAD team — Marshal's sub-agents

**Mary** Analyst · **John** PM · **Winston** Architect · **Sally** UX · **Amelia** Dev · **Paige** Tech Writer.

Who decides: the **Human** governs intent and answers escalations · **Marshal** owns execution · the **BMAD team** is the inner workforce · **crew stations** hold independent verdicts.

---

## The armory

**Five official modules:** BMM (51 skills) · BMB (builder) · TEA (test architect) · BMGD (game dev) · CIS (creative intelligence) + web bundles (Gems / Custom GPTs) + community plugins.

**The wider bmad-code-org stack:** **bmad-manticore 2.0 — AI video production, 16 mc-\* skills** · bmad-dashboard · bmad-labs-skills (21) · bmad-utility-skills · WDS expansion · module-template · **bmad-loop 0.9, wrapped**. Plus Skill Forge (16 skf-\*) and 10 detectors. **One install yields the whole stack.**

---

<!-- _class: dark -->

## Act III — Running the line

From one story's journey to the whole relay — every step gated, every failure contained, every run visible.

---

## One story's journey · three flows

**spec** → **gate** (run PAUSES) → **build** (isolated worktree) → **review** (adversarial · edge-case · verification-gap) → **verify + merge** (mechanical, full suite green).

**Flow A** one attended story · **Flow B** an epic, loop-gated (shipped Atlas + Warden) · **Flow C** the unattended 8-home fleet. **Autonomy changes who approves, never what is checked.**

---

## Graduated autonomy — L1–L5

L1 Assistive · L2 Task-based · **L3 Conditional / Context Gates — the production ceiling, running today** · L4 High-level · L5 Self-governance.

The supervisor watches **from outside** — idle strands in minutes, ceilings with named stops, journal-before-the-act. Paid for in production: 25.8M tokens · 3 lost attempts · 13/31 lost specs. **Every failure is a requirement now.**

---

## The SDLC, staffed

Dream & Pitch (Human · Herald) → Plan & Spec (Marshal + Mary·John·Winston·Sally) → Build (Marshal + Amelia·Paige — **the marshal CLI, shipped**) → Map (Atlas 57/57) → Audit (Warden 43/43) → Package & Ship (Mason) → Deploy & Operate (Steward) → Monitor & Heal (Doctor) → Proclaim (Herald) → Remember (Scribe, throughout).

---

## The Master Pipeline relay

✓ Doctor pre-flight → 1 Herald captures the Dream → **2 Marshal spins the factory** → 3 Atlas maps → 4 Warden audits → 5 Mason ships → 6 Doctor watches → 7 Herald proclaims.

Supervised start to finish by Marshal — **sequencing on verdicts it never authors**; every hand-off a durable, revision-pinned verdict artifact.

---

<!-- _class: dark -->

## Act IV — The product

What shipped, the law it obeys, and how to hold it.

---

## Shipped — the marshal CLI · Epic 1 · 10/10

`marshal init <slug>` · `preflight <slug>` · `homes` · `config compose` · `teardown <slug>` · `--version`

**785 tests** · coded `MRS-*` envelopes · frozen exit domain `{0,1,2,3,4,130}` · **one harness seam** (FR-52, import-linter-enforced) · teardown refuses unmerged work · **wrap, never absorb**.

---

## The doctrine + which verb when

**Skills execute · the harness governs (not a skill) · verdicts stay independent** — and Marshal **sequences on verdicts it never authors** (ratified 2026-07-31).

New line → `init` · pre-launch → `preflight` · isolation audit → `homes` · judgment story → `bmad-dev-auto` · epic → the loop · fleet → `gate_mode none` + supervisor · CI gate → `gate evaluate` (E2) · land a wave → `deploy · land` (E4) · retire → `teardown`.

---

## Every run stays visible

Sprint feeds through gates · the console regenerated from ledgers, **never hand-trusted** · ten deterministic detectors — a false green is caught by **machinery, not luck**. The board renders scope faithfully; it would be easier to look at if it lied.

---

## Who it serves, where it runs

**Solo dev** — a second shift · **Team lead** — a review floor that never rubber-stamps · **Eng manager** — a board that cannot lie · **CTO** — autonomy with an audit trail.

Enterprise: three pure policy layers (site config materialized at install) · internal tooling **mounts, never forks** (adapter profiles + declared tool surface) · **local-first, offline by default**.

---

## Proof & road

**57/57** Atlas · **43/43** Warden · **10/10** Marshal Epic 1 — built by its own line · **128/333** fleet-wide.

Next: gates as objects (E2) · the outside supervisor (E3) · landing paper trail (E4) · fleet status (E5) · portability (E6). Later: **pr-lifecycle** (`marshal land`, ruled 2026-07-31) · durable-runs · fidelity-enforcement · one-front-door · the installer fold (E10–12).

---

<!-- _class: lead -->

# The Dream deserves better than vibes.
## Write the Dream. The factory does the rest.
