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
projectName: 'pyforge-marshal'
---

# TEA → BMAD Integration Handoff

## Purpose

This document bridges TEA's test design outputs with BMAD's epic/story decomposition workflow
(`create-epics-and-stories`). pyforge-marshal's epics/stories already exist (37 epics / 208
stories in `epics.md`), so this handoff is used retroactively here — to recommend which *existing*
epics should carry the new risk-driven test items, rather than to seed brand-new epics.

## TEA Artifacts Inventory

| Artifact | Path | BMAD Integration Point |
|----------|------|--------------------------|
| Test Design Document (Architecture) | `../test-design-architecture.md` | Epic quality requirements, testability blockers (B-1/B-2/B-3) |
| Test Design Document (QA) | `../test-design-qa.md` | Story-level test requirements, P0-P3 coverage plan |
| Risk Assessment | embedded in `test-design-architecture.md` | Epic risk classification, story priority |
| Coverage Strategy | embedded in `test-design-qa.md` | Story test requirements |

## Epic-Level Integration Guidance

### Risk References

P0/P1 risks that should appear as epic-level quality gates:

- **R-1, R-2, R-5, R-6, R-8** (all score 6) → recommended as quality gates on **Epic 31** ("TEA
  replaces the generator, and marshal's own estate is cutover-ready") before Story 31.2 deletes
  the generator, since the verdict-projection (R-2) and durability (R-5) properties are exactly
  what an equivalence check needs to trust.
- **R-1** (region-engine corruption) also relates to **Epic 8** ("The Managed-Region Engine"),
  where the risk originates.
- **R-6** (landing-evidence grammar) also relates to **Epic 4** ("Landing with a durable paper
  trail") and **Epic 20** ("The loop cannot lose work, and a landing is always recognizable") —
  both already flagged as high-risk epics in the existing `test-architecture.md`.

### Quality Gates

Recommended per-epic gates based on this risk assessment:

- **Epic 31**: do not execute Story 31.2 (generator deletion) until R-2 and R-5 have passing
  adversarial fixtures (B-1/B-2 also resolved — see architecture doc Quick Guide).
- **Epic 8**: region-unit-test share of the suite should not shrink (P2-003) as a standing early
  warning for R-1.
- **Epic 4/Epic 20**: the lived landing-evidence incident (R-6) should be a permanent fixture, not
  reviewed away as a one-off.

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Story Acceptance Criteria

<!-- Populated from test-design-qa.md's Test Coverage Plan -->

- P0-001 (crash/hang/garbage-exit → FAIL) and P0-005 (poll-interval derivation) are strong
  candidates for acceptance criteria on whichever story in Epic 31 formalizes the verdict/
  supervisor properties TEA-equivalence depends on.
- P0-003 (kill-mid-run durability) maps naturally to Epic 3 ("Supervised unattended runs") /
  Epic 20, both of which already own the durability narrative in `epics.md`.
- P0-004 (landing-grammar regression) maps to Epic 4/Epic 20 as above.

### Data-TestId Requirements

Not applicable — no UI surface (`detected_stack = backend`).

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic | Test Level |
|---------|----------|-----|--------------------------|------------|
| R-1 | TECH | 2×3=6 | Epic 8 (Managed-Region Engine); gate for Epic 31 | Unit |
| R-2 | OPS | 2×3=6 | Epic 31 (verdict-projection property underpins TEA equivalence) | Unit |
| R-5 | DATA | 2×3=6 | Epic 3 / Epic 20 (durable unattended runs, durable landing) | Integration |
| R-6 | TECH | 2×3=6 | Epic 4 / Epic 20 (landing evidence grammar) | Contract |
| R-8 | PERF/OPS | 2×3=6 | Epic 3 (supervisor cost/poll behavior) | Integration |
| R-3 | SEC | 1×3=3 | Epic 18 (The governed tool surface) — redaction is a boundary property | Unit/meta |
| R-4 | OPS | 2×2=4 | Epic 3 (supervisor independence) | Unit |
| R-7 | OPS | 1×3=3 | Epic 1 / policy composition surface (no single epic owns policy alone — see FR-49..FR-54, § 7.7) | Unit |
| R-9 | DATA | 1×3=3 | Part II — `marshal seed` (no dedicated epic number in `epics.md`; tracked under the PRD's § 15 satellite) | Integration |
| R-10 | SEC | 1×3=3 | Epic 8 (Managed-Region Engine) | Unit/meta |
| R-11 | TECH | 1×2=2 | Part II — `marshal seed` (accepted/monitor) | Unit |
| R-12 | OPS | 1×2=2 | Part II — `marshal seed` (accepted/monitor) | Unit |
| R-13 | BUS | 1×2=2 | Part II — `marshal seed` (accepted, no action owed) | N/A |

**Note on this table's shape vs. the existing generator's Story Coverage Matrix:** this table is
risk-driven — 13 rows, one per identified risk, recommending an epic/story to own each. It is
*not* an enumeration of all 208 stories with their linked test files (that is what
`test-architecture.md`'s Story Coverage Matrix attempts, and currently reports "none observed"
for 207 of 208 rows). The two artifacts answer different questions: this one says "which epic
should own closing this risk," the generator's says "which test file already exists for this
story" (see `test-design-architecture.md` finding B-1/B-2 for why those are not interchangeable).

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (`TD`) → produced this handoff document.
2. **BMAD Create Epics & Stories** → epics/stories already exist for pyforge-marshal; this step
   would instead be a targeted addition of the P0/P1 items above into Epic 31 / Epic 3 / Epic 4 /
   Epic 8 / Epic 20 / Epic 18, not a fresh decomposition.
3. **TEA ATDD** (`AT`) → generate acceptance tests per new story, if any new stories are opened
   against the P0/P1 risks above.
4. **BMAD Implementation** → developers implement with test-first guidance for any risk-touching change.
5. **TEA Automate** (`TA`) → generate full automated coverage for the resulting scenarios.
6. **TEA Trace** (`TR`) → recommended as the actual owner of any future "every story has a linked
   test file" artifact (see B-2), rather than re-purposing this Test Design pass for that.

## Phase Transition Quality Gates

| From Phase | To Phase | Gate Criteria |
|------------|----------|-----------------|
| Test Design | Epic/Story Creation | All P0 risks (R-1, R-2, R-5, R-6, R-8) have a named recommended epic above |
| Epic/Story Creation | ATDD | Stories opened against the P0/P1 risks have acceptance criteria from this test design |
| ATDD | Implementation | Failing acceptance tests exist for all P0/P1 scenarios |
| Implementation | Test Automation | All acceptance tests pass |
| Test Automation | Release | Trace matrix shows adequate coverage of the P0/P1 requirements |
