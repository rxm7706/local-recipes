---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/test-design-architecture.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/test-design-qa.md
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-09-07'
projectName: 'pyforge-doctor'
---

# TEA → BMAD Integration Handoff — pyforge-doctor

## Purpose

Bridges TEA's system-level test design outputs with BMAD's own epic/story tracking for
`pyforge-doctor`. Since Epics 1–19 (108 stories) are already `done`, this handoff is
scoped to what is actually actionable: **Epic 20** (5 stories, the fleet's only
undelivered surface for this station), plus 3 carried-debt regression items the
architecture doc named. It is not a retroactive handoff for already-shipped epics.

## TEA Artifacts Inventory

| Artifact | Path | BMAD Integration Point |
| --- | --- | --- |
| Test Design (Architecture) | `_bmad-output/projects/pyforge-doctor/planning-artifacts/test-design-architecture.md` | Epic 20 quality requirements; 3 pre-implementation decisions (R-4, R-9, R-6) |
| Test Design (QA) | `_bmad-output/projects/pyforge-doctor/planning-artifacts/test-design-qa.md` | Story-level acceptance-criteria candidates for Stories 20.1–20.5 |
| Risk Assessment | embedded in both above | Epic 20 risk classification; 1 HIGH (R-4), 6 MEDIUM, 2 LOW |
| Coverage Strategy | embedded in `test-design-qa.md` | ~13 new test items mapped to Stories 20.1–20.5 |

## Epic-Level Integration Guidance

### Risk References

**P0/P1 risks that should appear as Epic 20 quality gates:**

- **R-4 (score 6, HIGH)** — Story 20.2 must not be marked done without its AD-13-style
  conformance test (render-HALT simulation ≡ `render_skill.py`'s real merge behavior).
  Recommend this as an explicit acceptance criterion on Story 20.2, not left implicit.
- **R-9 (score 4)** — the `DoctorReport.schema_version` bump-policy decision is a
  one-time architecture call that should be made and recorded (e.g. in Story 20.1's
  own commit or a short architecture note) before any of Epic 20's 3 new finding
  shapes ship, since it affects all of Stories 20.1–20.3 equally.
- **R-6 (score 4)** — Story 20.3's acceptance criteria should explicitly separate
  "ledger absent" (ok) from "ledger present but malformed" (should NOT silently be ok)
  — the epic's current Given/When/Then only names the absent case.

### Quality Gates

Recommended quality gates per Epic 20, derived from the risk assessment:

1. No source added by Story 20.2 or 20.3 joins `detectors`/`detectors-ci` until its
   fail-open behavior is fixture-proven (this is already the epic's own stated
   boundary — this handoff reinforces it as a formal gate, not a new requirement).
2. `test_check_speed_budget.py` is re-run and green after Epic 20 lands (R-5) — add as
   a gate on the epic's own retrospective/closeout, mirroring Story 6.1's precedent.
3. Every new finding Epic 20 introduces stays `warn`-at-most (never widens Doctor's
   `{0,2,130}` exit-code domain) — verified by extending, not replacing,
   `test_verdict_narrows_warden.py`'s existing coverage.

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Story Acceptance Criteria

- **Story 20.1**: P1-001/P1-004 (13/13 `packages_checked`, the 2026-08-21 lag fixture,
  fail-open on unreachable registry) should be the story's acceptance criteria
  verbatim — they already are, per `epics.md`'s own Given/When/Then; this handoff
  confirms no gap between the epic text and the test plan.
- **Story 20.2**: P0-001 (conformance test) is a **new** acceptance criterion this test
  design adds beyond the epic's current text — recommend folding it in before dispatch.
- **Story 20.3**: P0-003/P1-003 — recommend splitting the epic's current single
  "absent ledger → ok" criterion into two explicit criteria (absent vs. malformed) per
  R-6.
- **Story 20.4**: P2-001 stays blocked until steward 46.2 lands — no change to the
  story's own text needed, only a sequencing note.
- **Story 20.5**: P2-002 — docs-only, no test-design gap.

### Data-TestId Requirements

N/A — Doctor is a non-interactive backend CLI (no UI surface to instrument with
`data-testid` attributes).

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic | Test Level |
| --- | --- | --- | --- | --- |
| R-4 | TECH | 2×3=6 | Story 20.2 | Unit/meta (conformance) |
| R-1 | TECH | 2×2=4 | Epic 20 (monitor only, no code change) | N/A (process) |
| R-2 | TECH | 2×2=4 | Epic 20 (opportunistic refactor) | Unit/meta |
| R-3 | TECH | 2×2=4 (upgraded from carried-debt baseline given Epic 20's 3 new remote-coupled sources) | Epic 20 (follow-up) | Unit |
| R-5 | OPS/PERF | 2×2=4 | Epic 20 (closeout) | Unit (benchmark) |
| R-6 | OPS | 2×2=4 | Story 20.3 | Unit |
| R-9 | DATA | 2×2=4 | Stories 20.1–20.3 (shared decision) | Unit (schema round-trip) |
| R-7 | SEC | 1×2=2 | Monitor only (no Epic 20 story) | — |
| R-8 | BUS | 1×2=2 | Story 20.4 | Meta (sequencing) |

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (this handoff) → produced this document, scoped to Epic 20.
2. **BMAD epic/story refinement** → fold R-4's conformance-test requirement and R-6's
   absent-vs-malformed split into Stories 20.2/20.3's acceptance criteria before
   dispatch (`marshal factory spin pyforge-doctor` or direct `bmad-build`/
   `bmad-build-auto`, matching every prior epic's own dispatch convention).
3. **Implementation** (`bmad-build-auto` / `marshal factory spin`) → developers
   implement Stories 20.1–20.3/20.5 now, 20.4 once steward 46.2 unblocks.
4. **`bmad-testarch-test-review` / `bmad-testarch-trace`** (not run in this session —
   out of scope for `bmad-testarch-test-design`) → validate coverage once Epic 20's
   implementation evidence exists.

## Phase Transition Quality Gates

| From Phase | To Phase | Gate Criteria |
| --- | --- | --- |
| Test Design | Story Dispatch | R-4/R-9/R-6 decisions recorded; Stories 20.2/20.3's acceptance criteria updated per this handoff |
| Story Dispatch | Implementation | Fixtures for 20.1/20.2/20.3 constructed (all three already named concretely in `epics.md`) |
| Implementation | Detector Membership | Fail-open fixture-proven for each new source (Epic 20's own stated boundary) |
| Detector Membership | Epic Closeout | `test_check_speed_budget.py` re-profiled green; retrospective records R-1/R-2/R-3's disposition (fixed, deferred, or monitored) |
