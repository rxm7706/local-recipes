---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/test-design-architecture.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/test-design-qa.md
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-09-07'
projectName: 'pyforge-atlas'
---

# TEA → BMAD Integration Handoff

## Purpose

This document bridges TEA's test design outputs with pyforge-atlas's existing epic/story backlog
(`epics.md`, 24 epics / 91 stories). **Retrofit note:** unlike the workflow's normal green-field
sequence, this backlog already exists — this handoff maps TEA's risk findings onto the *existing*
epics rather than feeding a not-yet-run `create-epics-and-stories` pass. Use it to prioritize
remediation stories, not to re-derive the backlog.

## TEA Artifacts Inventory

| Artifact                | Path                                                                                    | BMAD Integration Point                               |
| -------------------------| -------------------------------------------------------------------------------------------| ------------------------------------------------------|
| Test Design (Architecture) | `planning-artifacts/test-design-architecture.md`                                       | Epic quality requirements, blocker ownership          |
| Test Design (QA)        | `planning-artifacts/test-design-qa.md`                                                  | Story-level acceptance-criteria candidates            |
| Risk Assessment          | Embedded in both test design docs (R-001..R-010)                                       | Epic risk classification, story priority              |
| Coverage Strategy        | Embedded in `test-design-qa.md` § Test Coverage Plan                                    | Remediation-story test requirements                   |

## Epic-Level Integration Guidance

### Risk References

- **R-002 (B4 parity pending) / R-005 (MCP-cutover unowned)** map to **Epic 10 (Post-Audit
  Remediation)**'s territory — both are legacy-retirement-readiness gaps in the same spirit as
  Epic 10's existing I0–I5 stories. Recommend a new remediation story (or an Epic-10 follow-on) to
  charter R-005's ownership explicitly.
- **R-003 (AD-23 lock-release asymmetry)** relates to **Epic 4 (Wave C — Orchestration)**'s C1/C2
  scope and to Story 10.6's prior `DW-AD23-1` closure — recommend a follow-on story against the same
  `tests/test_admission.py` gate for the multiprocess-drop path (`DW-AD23-2`).
- **R-007 (F1 threshold unset)** belongs to **Epic 7 (Wave F — DuckDB Singularity)**'s F1 story —
  recommend fixing the numeric threshold in that story's spec before its attended benchmark reruns.
- **R-006 (PyPI-sourced exceptions)** is a candidate CFE packaging task, not an atlas epic — track
  outside this backlog per the architecture doc's own recommendation.

### Quality Gates

- No epic should claim "legacy retired" status until R-002 and R-005 are both resolved (recorded
  evidence + an owner for the MCP-cutover story).
- No epic should enable a persistent Dagster daemon (Wave-C / Wave-G sensor work) until R-003's
  multiprocess-drop path is either tested or explicitly accepted as a documented availability
  boundary.

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Acceptance-Criteria Candidates

- **P0-001** (admission-lock multiprocess-drop regression) — recommend as an explicit acceptance
  criterion on whichever story implements the Wave-C persistent daemon (currently deferred, Q2).
- **P0-002/P1-001** (B4 parity / `dagster-dryrun`) — already acceptance criteria on existing stories
  B4 and C1 respectively; no new story needed, only the attended-event scheduling itself.
- **P3-001** (GX-ceiling static guard) — low priority; suitable as a small opportunistic task rather
  than a chartered story.

### Data-TestId Requirements

Not applicable — this station has no HTML/DOM-testid surface in scope for these scenarios (the Vizro
dashboard's own agent-legibility bar, semantic HTML + ARIA, is governed separately by AD-8 and the
existing `tests/dashboard/` suite, which already exists and is out of this handoff's remediation set).

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic                                              | Test Level            |
| ------- | -------- | --- | -----------------------------------------------------------------------| ------------------------ |
| R-001   | TECH     | 6   | Epic 4 (Wave C) — Q2 Dagster re-verify checkpoint                    | Integration (existing) |
| R-002   | OPS      | 6   | Epic 10 (Post-Audit Remediation) — B4 attended sign-off               | Integration (existing) |
| R-003   | TECH     | 6   | Epic 4 (Wave C) follow-on / `DW-AD23-2` — new admission-lock test    | Integration (net-new)  |
| R-005   | OPS      | 4   | New remediation story (unowned today) — charter the MCP-cutover work | N/A (ownership gap)    |
| R-006   | TECH     | 4   | Candidate CFE packaging task (outside this backlog)                  | Static/CI (existing)   |
| R-007   | PERF     | 4   | Epic 7 (Wave F) — F1 story spec threshold fix                        | Manual/attended         |
| R-008   | SEC      | 3   | Epic 2 (Wave A) — FR-1 credential-scoping regression watch           | Integration (existing) |
| R-009   | OPS      | 2   | Epic 9 (Wave H) — MinIO server provisioning precondition             | Integration (existing) |
| R-010   | DATA     | 2   | Epic 7 (Wave F) — GX-ceiling policy (AD-9)                            | Static (net-new, low)  |

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (`TD`) → produced this handoff document (this run).
2. **Existing epics/stories** (already created, not re-derived) → the 3 blockers above should land as
   either new remediation stories or acceptance-criteria amendments to their mapped epics.
3. **TEA ATDD** (`AT`) → optional, only for the net-new P0-001/P3-001 items if a red-phase fixture is
   wanted before implementation.
4. **Implementation** → developers close R-002/R-003/R-005/R-007 per their owners above.
5. **TEA Trace** (`TR`) → re-run after closure to confirm the 3 blockers now show PASS/mitigated.

## Phase Transition Quality Gates

| From Phase          | To Phase            | Gate Criteria                                                                |
| ---------------------| ---------------------| ---------------------------------------------------------------------------------|
| Test Design          | Remediation Stories | R-002/R-003/R-005 each have an assigned owner and a recorded plan             |
| Remediation Stories  | Implementation       | Acceptance criteria drawn from P0-001/P3-001 where applicable                |
| Implementation       | Test Automation      | P0-001's admission-lock regression test passes                               |
| Test Automation      | Legacy Retirement    | B4 sign-off recorded AND the MCP-cutover story (R-005) is either closed or explicitly deferred with an owner |
