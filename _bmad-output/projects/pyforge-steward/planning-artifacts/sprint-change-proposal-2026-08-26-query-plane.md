---
title: Sprint Change Proposal — evergreen Unifying Strategy; bind the query plane
date: 2026-08-26
project: pyforge-steward
chain: pyforge-unifying-strategy
status: approved
trigger: Operator ruling — Dream stays evergreen; SPEC may return in-progress; rebuild of shipped stores is in scope
mode: batch
scope: major
operator: Rxm7706
---

# Sprint Change Proposal — Query plane (CAP-19)

## 1. Issue summary

Canopy CAP-1..18 closed 2026-08-26. The operator then ruled the Unifying Strategy is the
**evergreen** Dream: new estate contracts land here, not on sibling Dreams. They accept
`spec-pyforge-unifying-strategy` returning to `in-progress` and accept rebuilding Atlas RAG,
Scribe semantic recall, and agent DSNs so one HTAP query plane is the read path.

Type: **new capability on a shipped chain** — not a rollback of 18–32, not a ninth station.

## 2. Impact analysis

| ID | Status | Finding |
|---|---|---|
| 1.1 | Done | Trigger is operator evergreen ruling, not a red story. |
| 2.1 | Done | Epics 18–32 stay `done`. New **Epic 34**. |
| 2.2 | Done | No rewrite of 18–32 stories. |
| 3.1 | Done | SPEC CAP-19 + constraints + OQs. PRD canopy:FR-46..50. Spine canopy:AD-22. Dream status `specified`. |
| 4.1 | Viable | Direct Adjustment. Risk: medium (rebuild of private stores is explicit). |

## 3. Recommended approach

**Direct Adjustment.** Apply in this session. Do not mint `spec-htap-query-plane`.

## 4. Applied

- SPEC `shipped` → `in-progress`; CAP-19; Why / Always / Non-goals / success signal.
- PRD `shipped` → `in-progress`; canopy:FR-46..50; FR-27 note; traceability.
- `epics.md` Epic 34 (34.1–34.5).
- Architecture spine canopy:AD-22.
- Dream Grounding: evergreen; CAP-19 now on the SPEC.
- `htap-query-plane.md` pointer updated (CAP lives here).
- Hygiene 2026-08-26 (same session, later): PRD counts 16/19; UJ-6; JTBD query row;
  glossary; spine binds CAP-1..19 / `updated: 2026-08-26`; stack.md DuckDB rows.
