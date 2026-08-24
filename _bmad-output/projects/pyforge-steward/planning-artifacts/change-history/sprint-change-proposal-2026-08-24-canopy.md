---
name: sprint-change-proposal-2026-08-24-canopy
type: sprint-change-proposal
status: approved
created: '2026-08-24'
scope: spec-pyforge-unifying-strategy Canopy (pyforge-steward Epics 18–30)
---

# Sprint Change Proposal — 2026-08-24 (Canopy)

## Issue Summary

**Trigger:** Phase 5 of `spec-pyforge-unifying-strategy` (the Canopy). The Dream is approved;
`bmad-spec`, PRD, architecture spine, and epic decomposition are complete. Steward already
shipped Epics 1–17 (host, engines, deploy, bootstrap) under `spec-python-agent-platform`.
This proposal records how the Canopy chain **adjusts interpretation of shipped work** and
**appends** Epics 18–30 — it does not reopen completed engine-integration stories.

**Category:** Strategic extension / inherited-conflict reconciliation.

**Problem statement:** Shipped steward work assumed parent AD-5 (`RunSQL` / Django migrations as
production schema authority for `langflow_schema` / `dbgpt_schema`) and a static
`docs/dashboard/` front door. The Canopy spec binds CAP-9 (Liquibase-governed DDL, canopy
AD-9), CAP-2 (Wagtail Lane 1), CAP-1..17 (chrome, portals, MCP, events, flags, supervisor),
and FR-22 (app role cannot DDL). Without an explicit course correction, reviewers could treat
FR-22 as undoing Stories 11.1/11.2 or as requiring immediate rollback of Epic 11 isolation.

**Operator decision (bound):** proceed. Status **approved** 2026-08-24.

**What this proposal does:** documents the steward-side Phase 5 pass — obligations on shipped
artifacts, append-only epic chain, packaging gates, and handoff to Epics 18–30 implementation.
Peer stations receive their own Phase 5 proposals; Marshal additionally retires
`spec-factory-console`.

## Impact Analysis

### Epic impact — shipped (Epics 1–17)

- **Epic 11 (done, 4/4):** **Not reopened.** Stories 11.1–11.4 remain `done`. Schema
  isolation (`langflow_schema`, `dbgpt_schema`, `search_path`, ORM never crosses schemas,
  Pattern A/B per parent AD-17) is still the binding invariant. FR-22 / canopy AD-9 changes
  only the **producer** of production DDL (Liquibase pre-upgrade Job + DML-only app role) —
  superseding the mechanism in **Epic 27**, not rolling back Epic 11.
- **Epic 10 (done):** Host image, factory-sourced environment, and sidecar wiring remain
  valid. Canopy stories may extend `INSTALLED_APPS`, URLconf, and redis split (Epics 18–20,
  24) without revisiting 10.1–10.5 acceptance criteria.
- **Epic 12 (done except skipped 12-7):** Vanilla chart and air-gap parity remain the
  substrate. Canopy adds redis-cache vs redis-broker (canopy AD-10), Wagtail media PVC (canopy
  AD-13), Liquibase hook Job (Epic 27), and OpenFeature FILE mount (Epic 26) as **forward
  work**, not edits to merged 12.1–12.3 stories.
- **Epics 1–9, 13–17 (done):** Unaffected except citation hygiene — new work cites **parent
  AD-n** vs **canopy AD-n**; bare `AD-n` in Canopy epics is review-blocking.

### Epic impact — appended (Epics 18–30)

- **Epics 18–30:** The steward build for the Canopy. No duplicate implementation stories
  beyond what `epics.md` already lists. Packaging stories **26.3** (OpenFeature) and **27.1**
  (Liquibase) stay **blocked** until operator-owned feedstocks land on the platform channel
  (canopy AD-16).
- **Epic 19 → Epic 27 sequencing:** S-19.1 (warden reusable-app triple + URL move) must
  complete before any Epic 27 story revokes app-role DDL (FR-9b / canopy AD-4).

### Artifact conflicts

- **`architecture/.../ARCHITECTURE-SPINE.md` (Canopy):** documents inherited conflicts with
  parent AD-5 (DDL producer), parent AD-1/AD-6 (Lane 1 media), RFC-1 (single ASGI pool).
  Isolation from parent AD-5 **still binds**; schema count amends to four (+ `liquibase`).
- **`specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md`:** parent AD-n remain read-only;
  cite as **parent AD-n** when Canopy work references them.
- **`epics.md`:** Epics 18–30 appended 2026-08-24; this proposal adds the Canopy obligations
  block and does not rewrite Epic 11 story text.
- **Open question `lane1-serves-dw-h3`:** joint steward/atlas; **not answered here** — stays
  out of stories until resolved (see deferred-work ledger `DW-CANOPY-2026-08-24`).

### Out of scope (this station)

- Recipe authoring for Liquibase, OpenFeature, cachebox (operator-owned).
- Peer-station Phase 5 proposals (atlas, marshal, warden, …).
- New stories duplicating Epics 18–30 content.

## Recommended Approach

**Direct Adjustment (selected).** Keep all shipped Epic 1–17 stories `done`. Append Epics
18–30 as the sole new build surface. Treat Epic 27 as the forward path for production DDL
governance; do not re-run 11.1/11.2. Record packaging gates and the `lane1-serves-dw-h3`
deferral in the ledger.

**Effort: Moderate** — artifact and obligation updates plus a large appended backlog; no
rollback of merged code.

**Rollback: not applicable.** Nothing in Epic 11 is invalidated; Canopy extends the host.

**MVP review: not needed.** CAP-1..17 goals are additive over the shipped platform.

## Detailed Change Proposals

**Epic 11 — status interpretation (no story text change):**
```
OLD: parent AD-5 — Django RunSQL/data migrations provision langflow_schema and dbgpt_schema;
     production schema authority is Django migrate.

NEW: Epic 11 stories 11.1–11.4 remain done. Isolation, search_path, and engine patterns
     unchanged. Production DDL authority moves to Epic 27 (canopy AD-9, FR-21–FR-25, FR-22).
     Existing RunSQL migrations remain until Liquibase changesets are extracted and the
     pre-upgrade Job + DML-only app role land — not a reopen of 11.1/11.2.
```

**`epics.md` — append Canopy obligations block (2026-08-24):**
```
NEW: ## Canopy obligations (2026-08-24) — steward owns the Canopy; Epics 18–30 are the build;
     Epic 11 isolation remains done; Epic 27 supersedes production DDL mechanism; Phase 5
     peer stations get their own proposals.
```

**`deferred-work-ledger.md` — append `DW-CANOPY-2026-08-24`:**
```
NEW: Ledger entry recording 11.1/11.2 NOT reopened; Epic 27 is superseding work;
     lane1-serves-dw-h3 remains open (joint atlas).
```

**Citation convention — all Canopy epics/stories/reviews:**
```
OLD: Bare AD-n references (ambiguous between parent and Canopy spines).

NEW: Cite parent AD-n (spec-python-agent-platform spine) vs canopy AD-n
     (architecture-pyforge-unifying-strategy-2026-08-24). Bare AD-n is review-blocking.
```

**Packaging gates — Stories 26.3, 27.1 (unchanged blocked state):**
```
OLD: (implicit) platform stories could start before conda packages exist.

NEW: Explicit hold per canopy AD-16 — S-26.3 and S-27.1 do not start until Liquibase
     ≥5.0.4 (+ vendored PostgreSQL JDBC) and OpenFeature FILE provider packages are on the
     channel the platform env consumes. Recipe work is operator-owned, not steward stories.
```

**No changes proposed to:** Epic 11 story bodies, sprint-status entries for 11.1–11.4
(remain `done`), shipped Epic 10/12 story acceptance criteria, or peer-station planning
artifacts.

## Implementation Handoff

**Scope classification: Moderate.**

**Routed to:** Steward implementation via `bmad-build` / `bmad-dev-auto` on Epics 18–30
stories, sequenced by epic dependencies (18 before 19/20/21; 19.1 before Epic 27 DDL revoke;
20.2 before 24.1; 27.1 operator gate before 27.2).

**Action items (approved 2026-08-24):**
1. ✅ This sprint-change-proposal (approved).
2. ✅ Append `## Canopy obligations (2026-08-24)` to `epics.md`.
3. ✅ Append `DW-CANOPY-2026-08-24` to `deferred-work-ledger.md`.
4. Implement Epics 18–30 per existing story decomposition — **no new stories** beyond
   `epics.md`.
5. Hold S-26.3 and S-27.1 until operator packaging clears.
6. Do not reopen or re-queue 11.1/11.2; route DDL governance to Epic 27.
7. Peer stations: run their own Phase 5 `bmad-correct-course` (physical paths, pinned
   `BMAD_ACTIVE_PROJECT`).

**Success criteria:** Canopy build proceeds from Epics 18–30 without Epic 11 regression;
Epic 27 lands Liquibase + DML-only app role after S-19.1; reviews enforce parent vs canopy
AD citation; `lane1-serves-dw-h3` stays tracked until atlas/steward joint resolution.
