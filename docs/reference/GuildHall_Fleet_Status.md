# BMAD Complete Tracking Dashboard

**Last refreshed:** 2026-08-08, against `main` @ `774acc7e13` (Herald Epic 12 merge, PR #316). Nothing is
currently running — no open PRs, no active bmad-loop sessions, no in-flight worktrees. Figures below are
read live from each project's `sprint-status-ledger.yaml`, not carried over from the prior (2026-08-02)
revision of this table.

## PyForge Guild — Dream-to-Code Pipeline State

### Fleet Status: 8 Stations + Infrastructure (16-Stage Pipeline)

**Pipeline stages:** Dream · Deck · Spec · Rsch · Brief · PRD · UX · Arch · Context · Epics · Sprint · TEA · Gates · Code · Tested · Retro

| **Station** | **Dream** | **Deck** | **Spec** | **Rsch** | **Brief** | **PRD** | **UX** | **Arch** | **Context** | **Epics** | **Sprint** | **TEA** | **Gates** | **Code** | **Tested** | **Retro** | **Status** |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| **🎺 Herald** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ◯ | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ◯ | ✅ Done — 47/47 stories (Epics 6-12 merged, PRs #307-#316) |
| **⚔️ Marshal** | 🚀 | 📋 | ✅ | ✅ | 🏗️ | ✅ | ◯ | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | 🚀 | 🚀 | ◯ | 🚀 In progress — 50/86 stories (Epics 1-6 done; 7-9 backlog, 17 stories) |
| **🗺️ Atlas** | 🚀 | ⏳ | ✅ | ✅ | ✅ | ✅ | ◯ | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ◯ | ✅ Done — 7/7 stories, epics 0-9 shipped |
| **🛡️ Warden** | 🚀 | ⏳ | ✅ | ✅ | ✅ | ✅ | ◯ | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ◯ | ✅ Done — 31/31 stories |
| **🧱 Mason** | 🚀 | 🎯 | ✅ | ✅ | ✅ | ✅ | ◯ | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | 🎯 | 🎯 | ◯ | 🎯 Early — 4/38 stories (Epic 1 stories 1.1-1.4 done; 1.5 onward + Epics 2-5 backlog, 34 stories) |
| **🏥 Doctor** | 🚀 | 📋 | ✅ | ✅ | ✅ | ✅ | ◯ | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ◯ | ✅ Done — 16/16 stories |
| **📖 Scribe** | 🚀 | 🎯 | ✅ | ✅ | ✅ | ✅ | ◯ | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ◯ | ✅ Done — 9/9 stories |
| **👑 Steward** | 🚀 | 🎯 | ✅ | ✅ | ✅ | ✅ | ◯ | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ◯ | ✅ Done — 18/18 stories |

---

### BMAD Workflows (Infrastructure & Execution) — FULL EXPANSION

**Official BMAD Workflows (Upstream) — Three-Level View:**


| **SDLC-Phase **         |                                                                                                      **ANALYSIS**                                                                                                      |                      **PLANNING**                      |                                                                           **SOLUTIONING**                                                                           |                                                                                       **IMPLEMENTATION**                                                                                       |
| ----------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :-----------------------------------------------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
|                         |                                                                                                                                                                                                                        |                                                        |                                                                                                                                                                      |                                                                                                                                                                                                |
| **Activities**          |                                                                         **research** ✓, **brief** ✓, PRFAQ ◯, brainstorm ◯, forge-idea ◯                                                                         |           **Create PRD** ✓, validate-prd ◯           |                                    **Create architecture** ✓, **Create epics** ✓, **Create story specs** ✓, readiness-check ◯                                    |                                                                **Per-story dev** ✓, **retro** ✓, code-review ◯, e2e-tests ◯                                                                |
| **BMAD Agents**         |                                                                                               Mary (Analyst), John (PM)                                                                                               |                        John (PM)                        |                                                         John (PM), Winston (Architect), Sally (UX Designer)                                                         |                                                                            Amelia (Developer), Paige (Tech Writer)                                                                            |
| **BMAD Skills**         | Mary:**bmad-domain-research** ✓; Mary: **bmad-market-research** ✓; Mary: **bmad-technical-research** ✓; John: **bmad-product-brief** ✓; John: bmad-prfaq ◯; Mary: bmad-brainstorming ◯; John: bmad-forge-idea ◯ | John:**bmad-create-prd** ✓; John: bmad-validate-prd ◯ | John:**bmad-create-epics-and-stories** ✓; John: **bmad-create-story** ✓; Winston: **bmad-create-architecture** ✓; Winston: bmad-check-implementation-readiness ◯ | Amelia:**bmad-sprint-planning** ✓; Amelia: **bmad-dev-story** ✓; Amelia: **bmad-retrospective** ✓; Amelia: bmad-code-review ◯; Amelia: bmad-qa-generate-e2e-tests ◯; Paige: documentation |
| **BMAD-Artifacts**      |                                **research-domain.md** ✓, **research-market.md** ✓, **research-tech.md** ✓, **product-brief.md** ✓, prfaq.md ◯, brainstorm.md ◯, forged-idea.md ◯                                |         **PRD.md** ✓, validation-report.md ◯         |                                          **architecture.md** ✓, **epics.md** ✓, **specs/*.md** ✓, readiness-report.md ◯                                          |                                  **sprint-status.yaml** ✓, **code** ✓, **tests** ✓, **PR** ✓, **merged code** ✓, **retro-findings.md** ✓, e2e-tests. ◯                                  |
| **BMAD-full**           |                                                         **research-domain.md** ✅, **research-market.md** ✅, **research-tech.md** ✅, **product-brief.md** ✅                                                         |                      **PRD.md** ✅                      |                                                      **architecture.md** ✅, **epics.md** ✅, **specs/*.md** ✅                                                      |                                         **sprint-status.yaml** ✅, **code** ✅, **tests** ✅, **PR** ✅, **merged code** ✅, **retro-findings.md** ✅                                         |
| **BMAD-quick-dev**      |                                                                                                           —                                                                                                           |                           —                           |                                                                          **specs/*.md** ✅                                                                          |                                         **sprint-status.yaml** ✅, **code** ✅, **tests** ✅, **PR** ✅, **merged code** ✅, **retro-findings.md** ✅                                         |
| **PyForge-Guild-Fleet** |                   **DREAMS** 🚀, research-domain.md ✅, research-market.md ✅, research-tech.md ✅, product-brief.md ✅, prfaq.md ◯, brainstorm.md ◯, forged-idea.md ◯, **PITCH-DECKS** 🚀                   |           PRD.md ✅, validation-report.md ◯           |                                                architecture.md ✅, epics.md ✅, specs/*.md ✅, readiness-report.md ◯                                                |                                     sprint-status.yaml ✅, code ✅, tests ✅, PR ✅, merged code ✅, retro-findings.md ✅, e2e-tests ◯,**TESTS-ARCH** 🚀                                     |

**Legend:** ✓ = Required | ◯ = Optional (run when additional pressure-testing or validation is needed; not required for all projects)

**Workflow Artifact Production:**


| **Workflow**                   | **ANALYSIS Input** | **ANALYSIS Output**                                | **PLANNING Input** | **PLANNING Output** | **SOLUTIONING Input** | **SOLUTIONING Output**                | **IMPLEMENTATION Input** | **IMPLEMENTATION Output**                                           |
| ------------------------------ | ------------------ | -------------------------------------------------- | ------------------ | ------------------- | --------------------- | ------------------------------------- | ------------------------ | ------------------------------------------------------------------- |
| **quick-dev**                  | —                 | —                                                 | —                 | —                  | —                    | —                                    | story spec ✅            | code, tests, PR, retro                                              |
| **bmad-full**                  | —                 | research-{domain,market,tech}.md, product-brief.md | analysis output    | PRD.md              | PRD + brief           | architecture.md, epics.md, specs/*.md | story-*.md               | sprint-status.yaml, code, tests, PR, merged code, retro-findings.md |
| **PyForge Guild** (8 stations) | —                 | ✅ research/, briefs/                              | ✅ analysis output | ✅ prds/            | ✅ PRD + brief        | ✅ architecture/, epics.md, specs/    | ✅ story specs           | 🚀 (Herald coding; 8/8 have 1–22 code artifacts)                   |

**Local-Recipes Customization (Extends bmad-full with 16-stage tracking):**

**Note:** The columns below show sub-components of the full 16-stage pipeline (dream, deck, spec, research, brief, prd, ux, arch, context, epics, sprint, tea, gates, code, tested, retro). This table focuses on key planning + research disciplines. For the full pipeline status, see the phase-grouped view below.


| **Station** | **DREAM** | **SPEC** | **Domain-Res** | **Market-Res** | **Tech-Res** | **BRIEF** | **PRD** | **ARCH** | **EPIC** | **STORY-SPECS** | **DEV** | **TEST** | **DELIVERY** | **RETRO** | **Status**          |
| ----------- | :-------: | :------: | :------------: | :------------: | :----------: | :-------: | :-----: | :------: | :------: | :-------------: | :-----: | :------: | :----------: | :-------: | ------------------- |
| **Herald**  |    ✅    |    ✅    |       ✅       |       ✅       |      ✅      |    ✅    |   ✅   |    ✅    |    ✅    |       ✅       |   ✅   |    ✅    |      ✅      |    ⏳    | Done — 47/47 stories; no tracked retro |
| **Marshal** |    ✅    |    ✅    |       ✅       |       ✅       |      ✅      |   🏗️   |   ✅   |    ✅    |    ✅    |       ✅       |   🚀   |    ✅    |      🚀      |    ⏳    | 50/86 stories; epic retros exist but only in gitignored implementation-artifacts (4 found), not promoted to a tracked doc |
| **Atlas**   |    ✅    |    ✅    |       ✅       |       ✅       |      ✅      |    ✅    |   ✅   |    ✅    |    ✅    |       ✅       |  ✅  |    ✅    |      ✅      |    ✅    | Done — 7/7 stories; **only station with tracked retros** (`planning-artifacts/retros/`, 10 epics) |
| **Warden**  |    ✅    |    ✅    |       ✅       |       ✅       |      ✅      |    ✅    |   ✅   |    ✅    |    ✅    |       ✅       |  ✅  |    ✅    |      ✅      |    ⏳    | Done — 31/31 stories; epic retros exist but only in gitignored implementation-artifacts (8 found), not promoted to a tracked doc |
| **Mason**   |    ✅    |    ✅    |       ✅       |       ✅       |      ✅      |    ✅    |   ✅   |    ✅    |    ✅    |       ✅       |   🎯   |    ✅    |      ⏳      |    ⏳    | 4/38 stories; earliest-stage station          |
| **Doctor**  |    ✅    |    ✅    |       ✅       |       ✅       |      ✅      |    ✅    |   ✅   |    ✅    |    ✅    |       ✅       |  ✅  |    ✅    |      ✅      |    ⏳    | Done — 16/16 stories; no tracked retro |
| **Scribe**  |    ✅    |    ✅    |       ✅       |       ✅       |      ✅      |    ✅    |   ✅   |    ✅    |    ✅    |       ✅       |   ✅   |    ✅    |      ✅      |    ⏳    | Done — 9/9 stories; no tracked retro |
| **Steward** |    ✅    |    ✅    |       ✅       |       ✅       |      ✅      |    ✅    |   ✅   |    ✅    |    ✅    |       ✅       |   ✅   |    ✅    |      ✅      |    ⏳    | Done — 18/18 stories; no tracked retro |

**Retro gap (found 2026-08-08):** 6 of 8 stations have zero tracked retrospective. Atlas is the only
station with retros promoted to a tracked doc (`planning-artifacts/retros/`). Marshal and Warden ran
per-epic retros, but they live only in each project's gitignored `implementation-artifacts/` — Tier-3
scratch that never gets promoted, so from the repo's point of view they don't exist. Herald, Doctor,
Scribe, Steward have none at all, tracked or otherwise. This mirrors CLAUDE.md's Rule 2 (every
conda-forge-touching BMAD effort must close with a retro that updates `conda-forge-expert`) but there is
no equivalent always-on rule yet for non-recipe PyForge station epics — closing that gap (promote
Marshal/Warden's existing retros, backfill one for Herald/Doctor/Scribe/Steward, and decide whether a
retro becomes a required per-epic gate) is unscheduled backlog, not yet actioned.

---

## COMMAND CENTER: PyForge Guild Fleet — Phase-Grouped View

**Overview:** 8 stations tracked across 4 SDLC phases with required exit artifacts marked ✓.

**Phase Exit Criteria:** A phase is complete when all ✓ marked artifacts exist and have the required status (✅ = delivered). Optional artifacts (unmarked) may be deferred.

### ANALYSIS Phase (Dream → Product Brief ✓ required)

| **Station** | **DREAMS** | **res-domain** | **res-market** | **res-tech** | **prod-brief** ✓ | **prfaq** | **brainstorm** | **forge-idea** | **PITCH-DECKS** | **Status** |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| **🎺 Herald** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | Moments 2–4 coding |
| **⚔️ Marshal** | 🚀 | ✅ | ✅ | ✅ | 🏗️ | ◯ | ◯ | ◯ | 🚀 | Ready for DEV |
| **🗺️ Atlas** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | Ready for DEV |
| **🛡️ Warden** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | Ready for DEV |
| **🧱 Mason** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | Queued |
| **🏥 Doctor** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | Ready for DEV |
| **📖 Scribe** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | Queued |
| **👑 Steward** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | Queued |

---

### PLANNING Phase (PRD ✓ required; validation optional)

| **Station** | **PRD** ✓ | **valid-report** | **Status** |
| --- | :---: | :---: | --- |
| **🎺 Herald** | ✅ | ◯ | Moments 2–4 coding |
| **⚔️ Marshal** | ✅ | ◯ | Ready for DEV |
| **🗺️ Atlas** | ✅ | ◯ | Ready for DEV |
| **🛡️ Warden** | ✅ | ◯ | Ready for DEV |
| **🧱 Mason** | ✅ | ◯ | Queued |
| **🏥 Doctor** | ✅ | ◯ | Ready for DEV |
| **📖 Scribe** | ✅ | ◯ | Queued |
| **👑 Steward** | ✅ | ◯ | Queued |

---

### SOLUTIONING Phase (Arch + Epics + Specs ✓ required; readiness optional)

| **Station** | **arch** ✓ | **epics** ✓ | **specs** ✓ | **ready-report** | **Status** |
| --- | :---: | :---: | :---: | :---: | --- |
| **🎺 Herald** | ✅ | ✅ | ✅ | ◯ | Moments 2–4 coding |
| **⚔️ Marshal** | ✅ | ✅ | ✅ | ◯ | Ready for DEV |
| **🗺️ Atlas** | ✅ | ✅ | ✅ | ◯ | Ready for DEV |
| **🛡️ Warden** | ✅ | ✅ | ✅ | ◯ | Ready for DEV |
| **🧱 Mason** | ✅ | ✅ | ✅ | ◯ | Queued |
| **🏥 Doctor** | ✅ | ✅ | ✅ | ◯ | Ready for DEV |
| **📖 Scribe** | ✅ | ✅ | ✅ | ◯ | Queued |
| **👑 Steward** | ✅ | ✅ | ✅ | ◯ | Queued |

---

### IMPLEMENTATION Phase (Tested ✓ required; e2e optional)
**Tested = Code + Tests (per TEA) + PR + Merged + Retro**

| **Station** | **sprint-status** | **TEA** | **code** ✓ | **tests** ✓ | **PR** | **merged** ✓ | **retro** ✓ | **e2e-tests** | **Status** |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| **🎺 Herald** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ◯ | Done, no tracked retro |
| **⚔️ Marshal** | ✅ | ✅ | 🚀 | 🚀 | 🚀 | 🚀 | ⏳ | ◯ | 50/86 stories in progress |
| **🗺️ Atlas** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ◯ | Done, retros tracked |
| **🛡️ Warden** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ◯ | Done, no tracked retro |
| **🧱 Mason** | ✅ | ✅ | 🎯 | 🎯 | 🎯 | 🎯 | ⏳ | ◯ | 4/38 stories, earliest-stage |
| **🏥 Doctor** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ◯ | Done, no tracked retro |
| **📖 Scribe** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ◯ | Done, no tracked retro |
| **👑 Steward** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ◯ | Done, no tracked retro |

Per this table's own exit criterion ("Tested = Code + Tests + PR + Merged + **Retro**"), only Atlas
actually clears IMPLEMENTATION in full — the other 5 finished stations are done on every axis except
retro.

---

### COMMAND CENTER Summary

| **Phase** | **Status** |
| --- | --- |
| **ANALYSIS** (Dream → Pitch) | ✅ Complete (8/8) |
| **PLANNING** (PRD) | ✅ Complete (8/8) |
| **SOLUTIONING** (Arch → Epics) | ✅ Complete (8/8) |
| **IMPLEMENTATION** (Code → Retro) | 6/8 stations done on code+tests+PR+merged; 1/8 (Atlas) also has a tracked retro; Marshal in progress (50/86), Mason early (4/38) |

---

Here is the PyForge Guild Fleet sequence expanded out with columns matching the specific artifacts and workflows you listed.

### PyForge Guild Fleet Execution Sequence (Detailed Artifact Matrix)

| **Station** | **DREAMS** | **res-domain** | **res-market** | **res-tech** | **prod-brief** | **prfaq** | **brainstorm** | **forge-idea** | **PITCH-DECKS** | **PRD** | **valid-report** | **arch** | **epics** | **specs** | **ready-report** | **sprint-status** | **code** | **tests** | **PR** | **merged** | **retro** | **e2e-tests** | **TESTS-ARCH** | **Status** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Herald** | ✅ | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 47/47, no tracked retro |
| **Marshal** | 🚀 | ✅ | ✅ | ✅ | 🏗️ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | 🚀 | 🚀 | 🚀 | 🚀 | ⏳ | ✅ | ✅ | 50/86 in progress |
| **Atlas** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Done — 7/7, retros tracked |
| **Warden** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 31/31, no tracked retro |
| **Mason** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | 🎯 | 🎯 | 🎯 | 🎯 | ⏳ | ✅ | ✅ | 4/38, earliest-stage |
| **Doctor** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 16/16, no tracked retro |
| **Scribe** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 9/9, no tracked retro |
| **Steward** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 18/18, no tracked retro |


### BMAD System Infrastructure

It looks like the platform you are using stripped out the HTML table I used to merge the top headers.

Standard Markdown doesn't support merged columns (colspans), so to ensure you can see the table perfectly, I have added the **SDLC Phase** as a dedicated mapping row directly beneath the headers using strict, standard Markdown formatting.

| **Station** | **DREAMS** | **res-domain** | **res-market** | **res-tech** | **prod-brief** | **prfaq** | **brainstorm** | **forge-idea** | **PITCH-DECKS** | **PRD** | **valid-report** | **arch** | **epics** | **specs** | **ready-report** | **sprint-status** | **code** | **tests** | **PR** | **merged** | **retro** | **e2e-tests** | **TESTS-ARCH** | **Status** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **SDLC PHASE** | *ANALYSIS* | *ANALYSIS* | *ANALYSIS* | *ANALYSIS* | *ANALYSIS* | *ANALYSIS* | *ANALYSIS* | *ANALYSIS* | *ANALYSIS* | *PLANNING* | *PLANNING* | *SOLUTIONING* | *SOLUTIONING* | *SOLUTIONING* | *SOLUTIONING* | *IMPLEMENT* | *IMPLEMENT* | *IMPLEMENT* | *IMPLEMENT* | *IMPLEMENT* | *IMPLEMENT* | *IMPLEMENT* | *IMPLEMENT* | *IMPLEMENT* |
| **Herald** | ✅ | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 47/47, no tracked retro |
| **Marshal** | 🚀 | ✅ | ✅ | ✅ | 🏗️ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | 🚀 | 🚀 | 🚀 | 🚀 | ⏳ | ✅ | ✅ | 50/86 in progress |
| **Atlas** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Done — 7/7, retros tracked |
| **Warden** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 31/31, no tracked retro |
| **Mason** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | 🎯 | 🎯 | 🎯 | 🎯 | ⏳ | ✅ | ✅ | 4/38, earliest-stage |
| **Doctor** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 16/16, no tracked retro |
| **Scribe** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 9/9, no tracked retro |
| **Steward** | 🚀 | ✅ | ✅ | ✅ | ✅ | ◯ | ◯ | ◯ | 🚀 | ✅ | ◯ | ✅ | ✅ | ✅ | ◯ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ✅ | ✅ | Done — 18/18, no tracked retro |



| **Component**            | **Available** | **Status** | **Details**                                                                                                                                      |
| ------------------------ | :-----------: | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **BMAD-Agents**          |      ✅      | Stable     | 6 agents: Analyst, PM, Architect, Dev, Tech-Writer, UX-Designer; persona-driven personas loaded per skill                                        |
| **BMAD-Skills**          |      ✅      | Stable     | 20+ skills:`bmad-spec`, `bmad-prd`, `bmad-architecture`, `bmad-create-epics-and-stories`, `bmad-quick-dev`, `bmad-dev-auto`, research trio, etc. |
| **Multi-Project Wiring** |      ✅      | Complete   | 9 projects (8 Smiths + Genesis) under one BMAD installation; per-project config layers; marker + symlink synchronization                         |
| **Conformance Checker**  |      ✅      | Stable     | `scripts/dream_chain_check.py` + `scripts/bmad_drift_check.py`; INV-0 thru INV-3 automation; gated CI                                            |
| **Test Automation**      |      ✅      | Complete   | `bmad_tea_playwright.py`: generates test-architecture.md + playwright.config.ts + pytest.ini + tests/ scaffold in 30s per station                |
| **Sync Reconciler**      |      ✅      | Active     | Two-layer drift detection + skill-driven reconciliation;`bmad-document-project`, `bmad-generate-project-context`, `bmad-correct-course`, etc.    |

---

## Symbol Legend


| Symbol | Meaning                           | Usage                                                                  |
| ------ | --------------------------------- | ---------------------------------------------------------------------- |
| ✅     | Complete / Exists / Stable        | Artifact delivered; feature ready; no blockers                         |
| 🚀     | In Progress / Actively Coding     | Development ongoing; expected completion this sprint                   |
| 🏗️   | Ready / Staged / Prepared         | All inputs ready; waiting for execution/resources                      |
| 📋     | Queued / Documented / Next Sprint | Design complete, queued for implementation; documented but not started |
| 🎯     | Prioritized / High Priority       | Next in line; operator committed; scheduled near-term                  |
| ⏳     | Pending / Blocked / Waiting       | Waiting on predecessor; documented but not started; external blocker   |

---

## Key Metrics

### Fleet-Wide Coverage (8 Stations)


| Artifact                             | Status      |              Stations              | Gap                        |
| ------------------------------------ | ----------- | :--------------------------------: | -------------------------- |
| DREAM (Tier 0)                       | ✅ Complete |                8/8                | 0                          |
| SPEC (bmad-spec)                     | ✅ Complete |                8/8                | 0                          |
| PRD (bmad-prd)                       | ✅ Complete |                8/8                | 0                          |
| ARCH (bmad-architecture)             | ✅ Complete |                8/8                | 0                          |
| EPIC (bmad-create-epics-and-stories) | ✅ Complete |                8/8                | 0                          |
| STORY (per-story specs)              | ✅ Complete |                8/8                | 0 (2 stations still finishing implementation) |
| **TEST** (bmad-tea-playwright)       | ✅ Complete |     8/8 (`test-architecture.md` present for every station)     | 0                 |
| **Decks** (Herald family)            | 🏗️ Ready  | 8/8 (all designed; some in flight) | 0 (execution ongoing)      |
| **RETRO** (tracked, `planning-artifacts/retros/`) | ⏳ Pending | 1/8 (Atlas ✅; Marshal/Warden have retros but only gitignored; Herald/Doctor/Scribe/Steward have none) | 7 stations |

### Development Status (Code Implementation)


| Status        | Count | Stations                                      | Notes                                              |
| ------------- | :---: | ---------------------------------------------- | -------------------------------------------------- |
| ✅**Done**    |   6   | Herald, Atlas, Warden, Doctor, Scribe, Steward | All stories merged (Atlas also has tracked retros; the other 5 don't) |
| 🚀**In progress** |   1   | Marshal                | 50/86 stories done; Epics 7-9 (17 stories) backlog |
| 🎯**Early**   |   1   | Mason                  | 4/38 stories done; Epic 1 story 1.5 onward + Epics 2-5 (34 stories) backlog |

---

## Next Actions (Sequenced)

### Immediate

1. **Marshal Epics 7-9** 🚀

   - Skill: `bmad-create-story` → `bmad-quick-dev` (no story specs written yet for 7-1 onward)
   - Owner: Marshal
   - Remaining: 17 stories (extraction manifest, marker/region substitution engine, findings/inventory scanner)
2. **Mason Epic 1 (story 1.5 onward) + Epics 2-5** 🎯

   - Skill: `bmad-create-story` → `bmad-quick-dev` (no story specs written yet)
   - Owner: Mason
   - Remaining: 34 stories (CFE root resolution through ship targets, package builds, lock/environment mgmt)
   - Independent package from Marshal — safe to run in parallel, worktree-isolated

### Backlog (Conformance Debt)

**Resolved 2026-08-08** (kept here for the record, not because they're still open):
- Retro gap for the 6 fully-done stations — Warden's 8 epic retros promoted from gitignored
  `implementation-artifacts/` to tracked `planning-artifacts/retros/`; Herald/Doctor/Scribe/Steward
  each got a first-ever grounded retro. Atlas already had tracked retros. Only **Marshal**
  (in-progress, 50/86) still has zero tracked retros — reasonable to defer until closer to done.
- `planning-artifacts/README.md` — was missing for Herald and Warden, now present for all 8.
- Dream status stuck at `specified` for Herald/Doctor/Scribe/Steward despite being fully
  shipped — flipped to `realized`.
- Story-spec promotion gaps — Doctor's `spec-2-1` and Scribe's `spec-1-4`/`spec-1-5` were never
  promoted; recovered as honest Tier-3 `epics.md`-derived contracts with real Delivery Records.
- **The "reshard flat PRD/ARCH" claims below were themselves wrong**, found while re-verifying
  this list 2026-08-08: Warden has zero flat PRD/architecture files (already fully sharded, this
  entry never should have existed). Marshal's flat `PRD.md`/`architecture*.md` files are not
  unsharded debt — they're deliberately-maintained "living" factory-documentation, explicitly
  tracked by `scripts/bmad_drift_check.py` (`tracked:living`/`tracked:plan`/`snapshot`
  classifications) as a *separate* doc genre from Marshal-the-CLI's own sharded BMAD Spec chain.
  Confirmed by reading the drift-checker's own docstring before acting, not by assumption.
- Genesis — the BMAD project dissolved 2026-08-02; its constitutive Dreams moved to
  `docs/governance/`, no longer applicable.

**Still open:**
- `planning-artifacts/specs/README.md` missing for **Marshal** and **Mason** (present for the
  other 6 — this is the newer, warden-driven convention documenting spec-recovery provenance).
- Dream-chain INV-1 backlog — was 16 findings as of 2026-08-08 morning, closed to 0 the same day
  (10 real `dreamt`-status Dreams each got a `status: draft` Spec; see
  `_bmad-output/DREAM-TRIAGE-2026-08-08.md` for the fold-in-vs-archive triage of each).

---

## How to Use This Table

**For operators:**

- Scan the Status column to find 🚀 (active) and 🎯 (queued) items
- Use rows to track cross-station readiness (e.g., are all Specs complete? Yes → ready for PRD)
- Monitor TEST column for fleet test deployment progress (currently 1/8 ✅)

**For contributors:**

- Find your station row to see what you're working on next
- Check BMAD Workflows row to see if planning infrastructure needs work
- Use symbol legend to understand what each status means

**For audits:**

- Run `pixi run -e local-recipes python scripts/dream_chain_check.py` to get authoritative state
- Run `pixi run -e local-recipes python scripts/bmad_drift_check.py` to detect local-recipes-scoped drift
- Compare results against this table; table is manually updated, detector output is ground truth

---

## Workflow Reference

### Dream-to-Code Flow (Tier 0 → Tier 3)

```
Tier 0 (User creates)
  ↓
Dream (docs/dreams/<slug>.md)
  ↓
Tier 2 (BMAD skills produce, tracked git)
  ├─ bmad-spec → SPEC.md + companions
  ├─ bmad-prd → prd.md + .memlog.md
  ├─ bmad-architecture → ARCHITECTURE-SPINE.md + .memlog.md
  ├─ bmad-create-epics-and-stories → epics.md + spec-<story-id>.md × N
  ├─ (research trio) → research/ docs
  ├─ bmad-product-brief → brief.md
  ├─ bmad-tea-playwright → test-architecture.md + scaffold
  └─ bmad-document-project → README.md + overview docs
  ↓
Tier 3 (Implementation, gitignored until story merges)
  ├─ bmad-quick-dev → code + tests
  ├─ bmad-dev-story → code + tests + delivery record
  └─ (user) → manual PR + review + merge
  ↓
Tier 2 (After merge, specs promoted)
  └─ spec-<story-id>.md moves to planning-artifacts/specs/ (durable)
```

### Quick-Dev vs Full BMAD


| Aspect             | Quick-Dev                | Full BMAD                                                              |
| ------------------ | ------------------------ | ---------------------------------------------------------------------- |
| **Entry**          | Story spec exists        | Dream exists                                                           |
| **Skills**         | 1 (`bmad-quick-dev`)     | 8 planning + 3 execution (13 stages total)                             |
| **Planning touch** | None (reads only)        | All tiers (specs/, prds/, architecture/, epics.md, research/, briefs/) |
| **Time**           | 15–90 min/story         | 40–80 hrs planning + 20–200 hrs implementation                       |
| **Use case**       | Execute existing stories | Start new projects or replanning                                       |

---

## Official BMAD Workflows (Upstream)

### **quick-dev** (Entry: Story spec exists)

Implements a **single story** from existing specification:

- Entry: Story spec file with requirements + acceptance criteria
- Skills: `bmad-quick-dev`
- Produces: Code + unit tests + PR ready for merge
- Timeline: 15–90 min per story
- Use: Execute pre-planned stories in isolation

### **bmad-full** (Entry: Dream document exists)

Orchestrates the **complete Dream→Code pipeline**:

- Entry: Dream document (`docs/dreams/<slug>.md`)
- Planning phase: Clarification, research, business case, requirements, architecture, epics/stories
- Implementation phase: Per-story implementation → integration testing → merged code
- Post-merge: Retrospective + learned findings → skill/process improvements
- Timeline: 40–80 hrs planning + 20–200 hrs implementation
- Use: Start new projects, major features, organizational processes

---

## Local-Recipes Customization: Herald & PyForge Fleet

Local-recipes extends official BMAD with a **13-stage explicit pipeline** for Tier-0→Tier-3 tracking:

### Planning Phase (Tier-2, tracked)

1. **DREAM** → `docs/dreams/<slug>.md`
2. **SPEC** → `bmad-spec` → five-field contract + companions
3. **Domain-Research** → `bmad-domain-research`
4. **Market-Research** → `bmad-market-research`
5. **Tech-Research** → `bmad-technical-research`
6. **BRIEF** → `bmad-product-brief`
7. **PRD** → `bmad-prd` → full requirements
8. **ARCH** → `bmad-architecture` → architecture spine
9. **EPIC** → `bmad-create-epics-and-stories` → epics + story list

### Story-Level Planning (Tier-2, tracked)

10. **STORY-SPECS** → `bmad-create-story` → per-story intent + ACs

### Execution Phase (Tier-3, gitignored until merge)

11. **DEV** → `bmad-quick-dev` / `bmad-dev-auto` → code + tests
12. **TEST** → `bmad-tea-playwright` → integration tests + scaffold
13. **DELIVERY** → PR merge → story lands on main

### Post-Merge (Continuous)

14. **REVIEW** → upstream review feedback
15. **RETRO** → `bmad-retrospective` + skill updates

---

## Workflow Routing


| When you have...           | Use this workflow             | Entry point                                        |
| -------------------------- | ----------------------------- | -------------------------------------------------- |
| Story spec ✅              | **quick-dev** (official BMAD) | Story file → code                                 |
| Dream only 🚀              | **bmad-full** (official BMAD) | Dream → full pipeline                             |
| PyForge station with Dream | **Herald** (local custom)     | Dream → stages 1–15 with cross-station reporting |
