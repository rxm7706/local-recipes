---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/test-design-architecture.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/test-design-qa.md
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-09-07'
projectName: 'pyforge-scribe'
---

# TEA → BMAD Integration Handoff — pyforge-scribe

## Purpose

This document bridges TEA's test design outputs for **pyforge-scribe** with BMAD's epic/story decomposition workflow (`bmad-create-epics-and-stories`). Scribe's epics are already fully decomposed and 18/19 stories are `done` (see `epics.md`), so this handoff's practical use is: (a) informing the one remaining open story (7.1, currently `blocked`), and (b) informing any follow-up story minted to close the 4 high-priority risks below, rather than a pre-implementation gate for net-new epics.

## TEA Artifacts Inventory

| Artifact | Path | BMAD Integration Point |
|---|---|---|
| Test Design — Architecture | `_bmad-output/projects/pyforge-scribe/planning-artifacts/test-design-architecture.md` | Risk register, testability concerns, mitigation plans for Scribe maintainer review |
| Test Design — QA | `_bmad-output/projects/pyforge-scribe/planning-artifacts/test-design-qa.md` | P0-P3 coverage plan, ~45 test scenarios, NFR validation plan |
| Risk Assessment | Embedded in both documents above | Story priority informed by R-001..R-009 |
| Coverage Strategy | Embedded in QA doc | Test-authoring backlog, ~34-57 hours |

## Epic-Level Integration Guidance

### Risk References

- **R-001 (score 9, DATA)** — `promote.py` never adversarially reviewed. No existing epic owns this; if a remediation story is minted, it should sit under Epic 1 (Team Memory — Capture & Promotion), the epic that owns `promote.py`.
- **R-002 (score 6, DATA)** — `recall`'s tie-break can serve a superseded fact as current. Belongs under Epic 2 (Knowledge Graph — Compile & Recall), the epic that owns `recall.py`, or Epic 3 if scoped specifically to transcript-sourced supersession (the surface that makes it bite per DW-FU-3-2-4).
- **R-003 (score 6, TECH)** — no standing air-gap regression beyond Story 2.1. Cross-cutting; the natural owner is whichever epic next adds a `GraphStore` driver or `compile_surface` extra (most recently Epic 4/Epic 6).
- **R-006 (score 6, TECH)** — 87/88 memlog nodes titled `---`. Belongs under Epic 2 (`compile.py` ownership).

### Quality Gates

- No epic should ship a new `GraphStore` driver or `compile_surface` extra without re-running R-003's air-gap regression check (recommend adding this as a standing AC template for any future Epic 4/6-shaped story).
- Any story touching `recall.py`'s ranking/tie-break logic should carry R-002's regression test as an explicit acceptance criterion, not an implicit expectation.

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Story Acceptance Criteria

If a remediation story is minted for any of the 4 high-priority risks, these P0/P1 scenarios (full detail in `test-design-qa.md`) should become that story's acceptance criteria directly, not be re-derived:

- **P0-001, P0-002** (promote.py write-boundary + concurrency) → acceptance criteria for an R-001 remediation story.
- **P0-003** (recall tie-break correctness) → acceptance criterion for an R-002 remediation story.
- **P0-004, P0-005** (air-gap regression + import-lint) → acceptance criteria for an R-003 remediation story.
- **P2-006** (no memlog node titled `---`) → acceptance criterion for an R-006 remediation story.

### Data-TestId Requirements

N/A — Scribe is a backend CLI/library with no UI surface; there are no `data-testid`-shaped testability hooks to request from architecture.

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic | Test Level |
|---|---|---|---|---|
| R-001 | DATA | 3×3=9 | New remediation story under Epic 1 | Unit |
| R-002 | DATA | 2×3=6 | New remediation story under Epic 2 or 3 | Unit |
| R-003 | TECH | 2×3=6 | Standing AC on the next Epic 4/6-shaped story | Unit (meta/offline harness) |
| R-006 | TECH | 3×2=6 | New remediation story under Epic 2 | Unit |
| R-004 | OPS | 2×2=4 | Small remediation story or folded into R-005's fix | Meta |
| R-005 | OPS | 2×2=4 | Small remediation story (can close R-004 and R-005 together) | Meta |
| R-007 | OPS | 3×1=3 | Not a Scribe story — bmad-loop-level, out of this project's epics | N/A |
| R-008 | DATA | 1×2=2 | Monitor only; no story needed unless the scanner becomes recursive | N/A |
| R-009 | OPS | 1×1=1 | Not a story — a scoped spec-surface `--write-baseline` operation | N/A |

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (`TD`) → this handoff document (produced 2026-09-07, post-ship review since all epics but 7 are `done`).
2. **BMAD Correct-Course or a new story** → if the Scribe maintainer decides to remediate R-001/R-002/R-003/R-006, mint stories under the epics named above using this handoff's P0/P1 scenarios as acceptance criteria.
3. **TEA ATDD** (`AT`) → generate acceptance tests per remediation story, if minted (separate workflow, not auto-run).
4. **Implementation** → developer implements against the P0-001..P0-009 scenarios.
5. **TEA Automate** (`TA`) → extend the existing pytest suite per the QA doc's Appendix A pattern.
6. **TEA Trace** (`TR`) → validate coverage completeness once remediation stories land.

## Phase Transition Quality Gates

| From Phase | To Phase | Gate Criteria |
|---|---|---|
| Test Design | Remediation Story Creation | R-001/R-002/R-003/R-006 have an owner and timeline (all currently "Scribe maintainer," no date fixed) |
| Story Creation | ATDD | Remediation story's acceptance criteria are copied verbatim from the P0/P1 scenarios above |
| ATDD | Implementation | Failing regression tests exist for the risk being fixed before the fix lands |
| Implementation | Test Automation | New tests pass; existing `pyforge-scribe-test` suite (~19 files) stays green |
| Test Automation | Release | `coverage-gates.yml` still passes repo-wide after the new tests land |
