---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - '../test-design-architecture.md'
  - '../test-design-qa.md'
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-09-07'
projectName: 'pyforge-herald'
---

# TEA → BMAD Integration Handoff — pyforge-herald

## Purpose

This document bridges TEA's test design outputs with BMAD's epic/story decomposition
workflow. Since pyforge-herald is a **post-ship** station (47/50 stories done), the primary
integration point is not "new stories" but the **one open epic** (Epic 18) that still needs
epic-level test design once its cross-station blockers clear, plus the follow-up work items
R-001–R-004 identified in the system-level review.

## TEA Artifacts Inventory

| Artifact             | Path                                                              | BMAD Integration Point                               |
| --------------------- | -------------------------------------------------------------------- | ------------------------------------------------------- |
| Test Design Document (Architecture) | `../test-design-architecture.md`                        | Risk register, testability gaps, NFR requirements     |
| Test Design Document (QA)          | `../test-design-qa.md`                                    | Test scenario plan, execution strategy, coverage       |
| Risk Assessment      | Embedded in both documents (R-001..R-007)                           | Epic risk classification, story priority               |
| Coverage Strategy    | Embedded in `test-design-qa.md` (P0-P3, ~21 scenarios)               | Story test requirements                                 |

## Epic-Level Integration Guidance

### Risk References

- **R-001 (TECH, score 6)** and **R-002 (PERF, score 6)** are the two P0/P1-relevant
  system-level risks that should surface as quality gates on any future epic touching (a) the
  test-design generator itself, or (b) the Herald web dashboard's load characteristics.
- **Epic 18** (the only open epic) inherits no NEW risks from this review beyond what its own
  epics.md entries already record (cross-station `blocked` on Steward 46.2/46.5/46.6) — its
  test design is deliberately deferred (see `test-design-qa.md` § Not in Scope) until code
  exists to assess.

### Quality Gates

- Any story that touches `webhook.py`'s known-fields set should re-run R-004's schema check
  (once built) before merge.
- Any story that touches the web dashboard's bundle/build pipeline should re-evaluate R-002
  before claiming the `<2s` NFR is unaffected.

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Story Acceptance Criteria

The 6 P0 scenarios (etag safety, write-gate consistency, webhook auth, concurrency safety,
evidence-required-to-publish, live-ship end-to-end proof) are already satisfied by existing
stories' shipped code and tests (Stories 2.1, 6.x, 13.1/13.3/13.6, AD-15's evidence gate).
No new story is needed to *create* this coverage — only R-001's generator fix would make it
mechanically traceable.

### Data-TestId Requirements

Not applicable — this is a Python CLI + React static-snapshot dashboard, not a
data-testid-driven E2E surface; the React panel tests (Vitest) assert on rendered content and
component behavior directly.

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic                                    | Test Level          |
| ------- | -------- | --- | ---------------------------------------------------------- | ---------------------- |
| R-001   | TECH     | 6   | New follow-up story against `_bmad/scripts/bmad_tea_playwright.py` (cross-station, not a Herald epic) | N/A (tooling fix)    |
| R-002   | PERF     | 6   | New follow-up story in a future Herald web epic             | TBD (harness or decision) |
| R-003   | OPS      | 4   | Documentation-only follow-up (operator runbook)              | N/A                    |
| R-004   | OPS      | 4   | New follow-up story: static webhook schema-diff check         | Unit/CI                |
| R-005   | TECH     | 4   | Deferred — no story recommended until KPI instrumentation is prioritized | N/A               |
| R-006   | DATA     | 2   | Monitor only — no story recommended                           | N/A                    |
| R-007   | TECH     | 1   | Monitor only — no story recommended                           | N/A                    |

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (`TD`) → this handoff document (done)
2. **BMAD Correct Course / Epic Refresh** → if R-001/R-002/R-004 are prioritized, add them as
   follow-up stories in the relevant owning station's epics.md (not necessarily Herald's own,
   for R-001)
3. **TEA ATDD** (`AT`) → only needed for genuinely new stories (R-002/R-004 follow-ups), not
   for the already-shipped Epics 1–17
4. **TEA Trace** (`TR`) → re-run against `test-architecture.md` once R-001 is fixed, to
   validate the story↔test matrix actually populates

## Phase Transition Quality Gates

| From Phase          | To Phase            | Gate Criteria                                                         |
| ---------------------- | ---------------------- | -------------------------------------------------------------------------- |
| Test Design          | Follow-up Story Creation | R-001/R-002/R-004 reviewed and either accepted-as-story or explicitly deferred |
| Follow-up Stories    | Implementation         | Stories have acceptance criteria drawn from this handoff's risk-to-story mapping |
| Implementation       | Test Automation        | New/updated tests pass under the existing `pyforge-herald-test` gate       |
| Test Automation      | Epic 18 Test Design     | Steward 46.2/46.5/46.6 land → re-run this workflow in epic-level mode for Epic 18 |
