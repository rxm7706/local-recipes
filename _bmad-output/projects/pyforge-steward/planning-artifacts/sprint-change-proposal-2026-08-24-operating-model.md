---
title: Sprint Change Proposal — operating-model Q1–Q8 into the Canopy chain
date: 2026-08-24
project: pyforge-steward
chain: pyforge-unifying-strategy
status: approved
trigger: docs/dreams/pyforge-unifying-strategy.md Grounding Q1–Q8
mode: batch
---

# Sprint Change Proposal — Operating model into the Canopy chain

## 1. Issue summary

The Unifying Strategy Dream is `specified` and this chain is `ready` (CAP-1..17, Epics 18–30).
On 2026-08-24 the operator bound an **estate-wide operating model** (sourced from
OpenTeams-WFT-CDO `pyforge-operation.md`, adapterizing WFT tool names) into Dream
**Grounding Q1–Q8**. The SPEC kernel has footnotes and a few Always/Never lines. The
**PRD, architecture spine, and Epics 18–30 still state the pre-Q2 completeness rule**
(“a station is unfinished on fewer than five tiers”) and are silent on Golden Path,
owner/`work_class` discovery, generic traceability, Tachyon-as-provider, Lane 2 HTMX,
and Warden-as-sole-gate.

This is a **new requirement / strategic bind**, not a failed implementation. Scorecard
**numbers are deferred** (human + agent + team; do not invent measures).

Evidence: Dream Grounding bullets Q1–Q8; SPEC notes on CAP-1/3/8/15/16; companions
updated in this pass (`convergence.md` residual 20, `architecture-diagrams.md`,
`stack.md`). PRD §3 glossary + §4.13 FR-37/38/39 + SM-5; `epics.md` Epic 29 title and
Story 29.3.

## 2. Impact analysis

### Checklist (batch)

| ID | Status | Finding |
|---|---|---|
| 1.1 | N/A | Not a story-triggered defect. Trigger is Dream Grounding Q1–Q8. |
| 1.2 | Done | Type: new requirement / strategic bind. Problem: ready plan contradicts Grounding. |
| 1.3 | Done | Evidence as §1. |
| 2.1 | Done | No in-flight canopy story is the trigger. Epic 29 is the epic that cannot ship as written. |
| 2.2 | Done | **Modify** Epic 29 (and small AC adds on 18, 19, 24). **No new epic in this OM pass.** Scorecard is not CAP-18. **Superseded later the same day:** hook-spec implementation is CAP-18 / Epic 32 (`sprint-change-proposal-2026-08-24-hook-specs.md`). |
| 2.3 | Done | Epics 18–28, 30 stay scoped; wording only where they assert five-tier-for-all-work or a second PR gate. |
| 2.4 | Done | No epic obsolete. No new epic for scorecard (sibling Dream). Warden hooks are a **Warden-station** story, not Epic 31. |
| 2.5 | Done | Do not resequence. Packaging gates (26.3, 27.1) unchanged. |
| 3.1 | Done | PRD glossary “Five-tier symmetry”, FR-37/38/39, SM-5, SM-C3 conflict with Q2. FR-1/2 miss owner/`work_class`. Event FRs miss `spec_id`. |
| 3.2 | Done | Spine has no “five-tier” string; add a short AD note pointing at Grounding/SPEC. No stack swap. |
| 3.3 | N/A | No UX artifact (readiness report already recorded this). |
| 3.4 | Done | Warden station spec + optional CI “Warden verdict is the gate” later. `test-architecture.md` only if FR-39 check changes. |
| 4.1 | Viable | Direct Adjustment. Effort: Medium. Risk: Low. |
| 4.2 | Not viable | Nothing to roll back; canopy implementation not started on these FRs. |
| 4.3 | Not viable | MVP stays the eight 03 stations + Canopy residual. Do not shrink CAP-15/16. |
| 4.4 | Done | **Option 1 — Direct Adjustment.** |

### Epic impact

| Epic | Change |
|---|---|
| **18** Chrome and trusted client | Story 18.x / FR-1–2: registration seam carries owner slug, backup, `work_class`, promotion date. SLA body is **not** an AppConfig field. |
| **19** Eight portals | No URL-scheme change. AC: Guildhall/switcher does not tile `work_class` 01/02 as a station. |
| **21** Agents survive | No Tasks/MCP change. Note Path B = canopy + CAP-16; Tachyon is not this epic. |
| **24** Stations tell each other | Story 24.1 envelope: `spec_id`, git sha, SBOM purl, optional work-item id. **Never** require Jira. |
| **29** Every station is five tiers | **Rename/scope:** five tiers are the **03 station** shape. FR-39 check: fail if an **03** station misses a tier; do **not** fail 01/02 work. FR-37/38 stay “each of the eight stations” (they are 03). |
| 20, 22, 23, 25–28, 30 | No scope change. |
| New | None. Scorecard board = sibling Dream. Warden hook plugins = Warden correct-course, not a steward epic. |

### Story impact

Current stories 29.1–29.3 remain; ACs get the 03 qualifier. 24.1 gains identity fields.
No story deleted. No story added in this proposal.

### Artifact conflicts

- PRD: §3, §4.1 (FR-1/2), §4.13, SM-5 / SM-C3.
- Architecture spine: one AD/note; no pattern change (modular monolith stands).
- UX: none.
- SPEC companions: **done this pass**.
- Eight 2026-08-24 canopy station proposals: see §6.

### Technical impact

None on running code this sprint. Future: AppConfig metadata; CloudEvents fields;
Warden hook specs (Warden package). Golden Path is a CI/policy invariant, not a new
service.

## 3. Recommended approach

**Direct Adjustment** of existing PRD FRs and Epic 18/19/24/29 stories.

Rationale: Grounding does not add a capability; it **scopes** CAP-15/16 and adds
invariants the plan already had seams for (registration, CloudEvents, Warden).
Rollback is empty. MVP review would wrongly drop agent tiers.

Effort: one steward edit pass after approval. Risk: low if FR-39’s check is rewritten
before anyone implements Story 29.3.

**Eight station runs:** **not all eight.** See §6.

## 4. Detailed change proposals

### PRD

**§3 Five-tier symmetry**

OLD: a station is complete when it has all five … Fewer than five means unfinished.

NEW: an **03** station capability is complete when it has all five … 01/02 work is
complete at spec+script or spec+skill. The eight stations are 03.

**§4.1 FR-1/FR-2** — add consequences: registration includes owner, backup,
`work_class`, promotion date; 01/02 must not appear as station tiles; SLA text is
not a chrome field.

**§4.13 / FR-37–39 / SM-5** — prefix “each **03** station”; FR-39 check denominator
remains 8×5 for the eight stations; **Never** count 01/02 tasks in that check.
SM-C3 unchanged (do not optimize for shallow skill count).

**Events (FR-17 area)** — add `spec_id` + git sha + SBOM purl; Jira optional.

**Glossary** — add `work_class` 01/02/03; Tachyon = production LLM provider adapter;
Path B = Agent Canopy + persona.

### Epics (`epics.md`)

**Epic 29 title** OLD: “Every station is five tiers”
NEW: “Every 03 station is five tiers”

Story 29.3 Given/Then: “all eight **03** stations” / missing tier on an 03 station
fails; 01/02 fixtures must not fail the check.

**Story 24.1** And: envelope carries `spec_id`, git sha, SBOM purl; optional
work-item id; missing Jira key is not a fail.

**Epic 18 / 19** ACs as PRD FR-1/2/19 tile rule.

### Architecture spine

Add a dated note under canopy ADs: operating-model Q1–Q8 bind; pointer to Dream
Grounding and this proposal. No AD reversal.

### SPEC

Kernel footnotes + Always/Never already landed. Companions landed this pass.
No further SPEC edit required for approval of this proposal.

### UX

None.

## 5. Implementation handoff

**Scope: Moderate** — backlog wording / FR text, not a fundamental replan.

| Who | Does |
|---|---|
| Operator | Approve or revise this proposal (correct-course step 5). |
| Steward / PO-DEV | Apply §4 edits to PRD + `epics.md` + spine note; append realization log. |
| Developer | Do not implement Story 29.3 until FR-39 text is applied. |
| Eight station correct-courses | Record OM Nevers + AD-21 (hooks/plugins as replaceable layers) on every spoke. Warden owns PR-gate hook *specs*; plugins implement them. Not a Kedro re-template of any station. |
| Scorecard sibling | Later; human + agent + team; no unpublished metrics. |

Success: PRD/epics/SPEC/Dream agree that five-tier completeness is 03-only; one
Warden verdict; generic traceability; no CAP-18; **all eight stations** carry
the operating-model block.

## 6. Do all eight station runs? — **REVISITED (operator, 2026-08-24)**

**First recommendation (Warden-only) is withdrawn.** It treated hooks as a
scanner-implementation detail. **Hooks and plugins are an architecture
principle** (canopy:AD-21): as far as possible every layer is replaceable —
process-owned hook specs, plugins that implement or replace a layer without a
fork. Kedro *names* the split; it does not require a Kedro project. Atlas
already *is* Kedro (pipeline hooks = one instantiation, not Warden's PR-gate
book). **Warden owns** PR-gate hook specifications; scanners implement them
(Q8). Other stations own their process hooks and must not grow a second PR
gate.

| Station | Record OM SCP? | Station-local hook surface |
|---|---|---|
| **warden** | Yes | Owns PR-gate hook specs; scanner plugins |
| **atlas** | Yes | Already a Kedro project; pipeline hooks = reference shape, not Warden's PR-gate book; DRF only on data-models |
| **mason** | Yes | Build-engine plugins; build ≠ Warden verdict |
| **marshal** | Yes | Loop/runner plugins; loop pass ≠ PR gate |
| **doctor** | Yes | Remedy/linter hooks; findings are Warden inputs or advisory |
| **herald** | Yes | Export-format plugins |
| **scribe** | Yes | Store/recall plugins |
| **steward** | Yes | Deploy-profile adapters (Harness, Splunk, Tachyon, Jira) |

Landed the same day: each station
`change-history/sprint-change-proposal-2026-08-24-operating-model.md`,
`epics.md` § Operating-model obligations, `DW-OM-2026-08-24`. No new station epics.

## 7. Approval

Status: **approved** (operator, 2026-08-24). PRD, `epics.md`, and architecture
spine edits from §4 applied the same day. Companions were already applied.
§6 revisited the same day: **all eight stations**, not Warden-only.
