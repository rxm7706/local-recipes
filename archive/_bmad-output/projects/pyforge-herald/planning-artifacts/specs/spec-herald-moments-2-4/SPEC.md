---
title: Herald's Proclamation Surfaces — Moments 2–4
slug: herald-moments-2-4
owner-dream: herald-moments-2-4-missing-surface
status: draft
created: 2026-08-02
updated: 2026-08-02
spec_version: 1.0
companions:
  - epic-structure.md
sources:
  - ../../../../docs/dreams/herald-moments-2-4-missing-surface.md
---

# Herald's Proclamation Surfaces — Moments 2–4

**SPEC.md** — Five-field kernel for completing Herald's Four Moments of Proclamation framework.

---

## Why

Herald is the factory's voice and visibility surface. Its Four Moments guide all proclamation:

1. **Moment 1: Pitch** — Launch an idea with narrative force ✅ READY (deck family spec complete)
2. **Moment 2: Progress** — Make shipping motion visible and explainable
3. **Moment 3: Success** — Claim completion with evidence attached
4. **Moment 4: Operations** — Announce deprecations, fixes, end-of-life proactively

Moment 1 is production-ready. **This spec addresses Moments 2–4**, creating missing surfaces that close the proclamation cycle and ensure no work ships silently.

---

## Capabilities

### CAP-1: Progress Visibility Surface (Moment 2)

**Intent:** Make factory motion visible — what shipped, what it cost, what it unblocked.

**What it does:**
- **Weekly/milestone summary** showing station updates, new capabilities, closed gates.
- **Cost transparency** — compute hours, token spend, wall-clock time per effort.
- **Unblock narrative** — what downstream work did this unlock.
- **Automation trigger** — weekly schedule OR manual on shipping milestone.
- **Integration** — Herald CLI `herald progress <station>`, Herald web surface widget.

**Success:** Progress surface renders weekly; cost data is accurate (derived from sprint-status + bmad-loop journals); every shipped effort has an unblock narrative.

---

### CAP-2: Success Proclamation Surface (Moment 3)

**Intent:** Shipping ≠ being known to ship. Create a public claim backed by retrievable evidence.

**What it does:**
- **Release claim** — structured statement: "Project X shipped. Thesis: [what we proved]. Proof: [links to tests, metrics, adoption data]."
- **Evidence integration** — automatic link to: CI test results, dashboard metrics, user adoption counts, upstream PRs merged.
- **Automation trigger** — on PR close to main + passing gate-suite.
- **Integration** — Herald CLI `herald success <project>`, Herald web release archive.

**Success:** Every closed project has a success claim with ≥1 evidence link; claims are retrievable and dated; no claims exist without proof.

---

### CAP-3: Operations Proclamation Surface (Moment 4)

**Intent:** Deprecations, security fixes, end-of-life notices — the unglamorous tail that protects users but nobody announces.

**What it does:**
- **Notice authoring** — structured template for deprecation/fix/EOL notices (what changed, why, migration path, deadline).
- **Archive & redirect** — notices are permanent and indexed by date/category; old URLs redirect to archive.
- **Automation trigger** — manual on notice author; no auto-generation.
- **Integration** — Herald CLI `herald notice author|list|archive`, Herald web notice board.

**Success:** Every deprecated feature has a notice; every notice links to proof/reason; archive is indexed and searchable; all links are permanent.

---

## Constraints

**Integration**: All three Moments must integrate with Herald CLI and Herald web surface. No separate platforms; unified UI surface.

**Automation triggers**: Moment 2 weekly/on-ship, Moment 3 on-PR-close, Moment 4 on-notice-author. Each must have explicit automation rule.

**Evidence requirement**: Moment 3 and 4 claims must be backed by retrievable evidence. No claims without proof links.

**No silent shipping**: Every completed project must have a Moment 3 claim. This is enforced by a pre-ship gate.

---

## Non-goals

**Replacing Herald Moment 1** — Pitch/deck family already complete; this effort completes the remaining Moments, not reimplements the existing one.

**Rebuilding existing Moment 2 & 3 specs** — Moment 2 & 3 specs exist in archive. This effort audits them, incorporates proven patterns, and surfaces them. Not a redesign from scratch.

**Implementing automation yet** — This spec designs the surfaces and automation triggers. Implementation (CI hooks, scheduler rules, CLI commands) happens in separate stories.

**Marketing proclamation** — Moments 2–4 are internal visibility (what we shipped, what changed, what's deprecated). Not external marketing content. Herald Moment 1 (Pitch) is separate and handles that.

---

## Success Signal

**Spec completion**
- [ ] Three Moment surface specs drafted and reviewed
- [ ] Automation triggers defined for each Moment (schedule, event, gate)
- [ ] Entry points identified in Herald CLI and web surface

**Specification readiness**
- [ ] Moment 2 & 3 archived specs audited and adapted patterns identified
- [ ] Moment 4 notice template drafted
- [ ] Surface integration points mapped to existing Herald infrastructure

**Decision readiness**
- [ ] Unified orchestration strategy decided (3 separate stories vs. coordinated epic)
- [ ] Automation implementation approach decided (CI hooks, scheduler, manual + CLI)

---

## Decisions Made (All Three Locked ✅)

1. **Orchestration**: Coordinated epic with 6–7 sub-stories (not independent stories). Rationale: shared CLI/web/automation infrastructure, integration correctness prioritized, Herald precedent (Moment 1 unified).

2. **Moment 2 Automation**: Trigger on-ship webhook + weekly cron Thursday 2300 UTC (fallback). Rationale: immediate visibility on shipping + guaranteed weekly cadence.

3. **Moment 3 Automation**: Auto-extract on PR-close + passing gates (test results, metrics, adoption). Operator review gate before publish. Rationale: reproducibility, deterministic claims, quality gate.

4. **Moment 4 Archive**: Simple date/category index (YYYY-MM folders + tags). No full-text backend. Rationale: <100 notices expected; date/category dominant query; manual search acceptable; full-text addable later without migration.

See `epic-structure.md` for story breakdown, dependencies, and automation rules.

---

## Status

**Created**: 2026-08-02  
**Status**: Draft — memlog complete, ready for PRD + Architecture decomposition.  
**Next**: Feed to `bmad-prd` and `bmad-architecture` to flesh out product requirements and technical approach.

---

*SPEC.md is derived from `.memlog.md`. Hand-edits to SPEC.md are not supported.*
