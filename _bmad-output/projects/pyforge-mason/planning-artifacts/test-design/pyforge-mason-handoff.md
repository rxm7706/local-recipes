---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/test-design-architecture.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/test-design-qa.md'
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-09-07'
projectName: 'pyforge-mason'
---

# TEA → BMAD Integration Handoff — pyforge-mason

## Purpose

Bridges TEA's system-level test design with BMAD's epic/story tracking for pyforge-mason. Unlike
a typical greenfield handoff (feeding a not-yet-decomposed PRD into `create-epics-and-stories`),
pyforge-mason's epics and stories **already exist and are 60/61 `done`** (`epics.md`,
`sprint-status-ledger.yaml`). This handoff instead functions as a **retrospective cross-check**:
it maps the 12 newly-identified risks onto the existing epic chain so a future story (or a
correct-course pass) can pick them up as tracked work, and it flags the one still-open epic
(Epic 14 / Story `14-1`).

## TEA Artifacts Inventory

| Artifact | Path | BMAD Integration Point |
|---|---|---|
| Test Design (Architecture) | `test-design-architecture.md` | Risk register, ADR-checklist testability review, mitigation plans |
| Test Design (QA) | `test-design-qa.md` | Coverage plan (P0–P3), NFR plan, execution strategy |
| Risk Assessment | embedded in both documents above | Candidate `deferred-work-ledger.md` entries / future story ACs |
| Coverage Strategy | embedded in `test-design-qa.md` | 15 recommended test scenarios, 10 net-new |

## Epic-Level Integration Guidance

### Risk References

- **R-001 (seam erosion) / R-002 (credential leak)** are already load-bearing invariants of
  **Epic 5** ("Prove the seam holds", Stories 5.1–5.3) and **Epic 2** (Story 2.2 seam guard,
  Story 2.3 credential isolation) — no new epic needed; recommend a regression-lock policy note
  on those stories rather than new work.
- **R-003 (`environment check` swallows failure)** maps to **Epic 4** (Story 4.4, `mason
  environment check`) — recommend a follow-up story or a `deferred-work-ledger.md` promotion of
  `DW-4-4-3` to an active fix.
- **R-004 (CFE-rebuild guard soft spots)** maps to **Epic 12** (Stories 12.1/12.2/12.4, the
  guard's own clauses) — recommend closing before **Story 12.8**'s slice-3 go/adjust/stop
  decision; this is already `deferred-work-ledger.md` entries `DW-12-1-1`/`DW-12-1-2`, not a new
  finding.

### Quality Gates

- Epic 12 (CFE-rebuild continuation): recommend R-004's closure as an explicit pre-condition
  alongside the four pre-conditions Story 12.4 already machine-enforces, following that story's
  own precedent of turning session-discipline gates into code.
- Epic 4 (environments): recommend R-003's closure before any future story proposes `mason
  environment check` as a CI-blocking gate for a consuming project.

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Candidate Acceptance Criteria (for a future hardening story)

- P0-003 (environment check surfaces real failures) → AC candidate for a `DW-4-4-3` fix story.
- P0-004/P0-005 (guard content-validation + staleness check) → AC candidates for a story
  preceding Story 12.8.
- P1-003/P1-004 (concurrent-ship race, `~`-path expansion) → AC candidates for one combined
  hardening story (both are small, DW-3-7-1 + DW-3-6-2/3).

### Data-TestId Requirements

Not applicable — pyforge-mason has no UI surface of its own (see Not in Scope, `test-design-qa.md`).

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic | Test Level |
|---|---|---|---|---|
| R-001 | TECH | 2×3 | Epic 5 (Stories 5.1–5.3) — regression-lock, no new story | Meta |
| R-002 | SEC | 2×3 | Epic 2 (Story 2.3) — regression-lock + widen verbosity coverage | Unit/Meta |
| R-003 | OPS/DATA | 3×2 | Epic 4 (Story 4.4) — new fix story recommended | Unit |
| R-004 | TECH | 2×3 | Epic 12 (Stories 12.1/12.2/12.4, before 12.8) — new fix story recommended | Unit/Meta |
| R-005 | BUS | 2×2 | Epic 3 (Story 3.6/3.7) — regression-lock | Unit |
| R-006 | TECH | 2×2 | Epic 5 (Story 5.4/FR-46) — nightly-lane scheduling only | Integration |
| R-007 | DATA | 2×2 | Epic 3 (Story 3.7) — new hardening item | Unit |
| R-008 | TECH | 2×2 | Epic 3 (Story 3.6) — new hardening item | Unit |
| R-009 | SEC | 1×2 | Epic 2 (Story 2.5) / Epic 3 (Story 3.5) — new hardening item | Unit |
| R-010 | TECH | 1×2 | Workspace-wide (Story 1.1 precedent) — monitor only | N/A |
| R-011 | TECH | 1×2 | Epic 1 (Stories 1.6/1.8) — regression-lock | Unit |
| R-012 | OPS | 1×1 | Epic 14 (Story 14-1) — already tracked, `backlog` | N/A |

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (this document's source) → produced this handoff.
2. **BMAD correct-course / a new hardening story** → consumes the Risk-to-Story Mapping above to
   decide whether R-003/R-004 (the two 🚨 must-close items) become tracked stories or stay
   `deferred-work-ledger.md` entries pending an operator decision.
3. **TEA ATDD** (`bmad-testarch-atdd`) → if a hardening story is minted, generate acceptance tests
   for its P0 scenarios (not auto-run by this workflow).
4. **TEA Trace** (`bmad-testarch-trace`) → validate coverage completeness once the hardening story lands.

## Phase Transition Quality Gates

| From Phase | To Phase | Gate Criteria |
|---|---|---|
| Test Design | Hardening story creation | R-003/R-004 explicitly triaged (fixed, deferred with a dated decision, or accepted) |
| Story creation | ATDD | Story has acceptance criteria drawn from the P0/P1 rows above |
| ATDD | Implementation | Failing acceptance tests exist for R-003/R-004 before the fix lands |
| Implementation | Regression | `pyforge-mason-test` (fast lane) stays green; `pyforge-mason-test-slow` run at least once |
| Regression | Release | No open P0/P1 finding remains in `deferred-work-ledger.md` for R-001–R-004 |
