---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/test-design-architecture.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/test-design-qa.md'
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-09-07'
projectName: 'pyforge-steward'
---

# TEA → BMAD Integration Handoff

## Purpose

This document bridges TEA's test design outputs with BMAD's epic/story decomposition workflow (`create-epics-and-stories`). It provides structured integration guidance so that quality requirements, risk assessments, and test strategies flow into implementation planning for pyforge-steward's remaining/future epics.

## TEA Artifacts Inventory

| Artifact | Path | BMAD Integration Point |
| --- | --- | --- |
| Test Design (Architecture) | `test-design-architecture.md` | Epic quality requirements, story acceptance criteria, testability blockers |
| Test Design (QA) | `test-design-qa.md` | Story test requirements, coverage plan, execution strategy |
| Risk Assessment | Embedded in both documents (R-1..R-19) | Epic risk classification, story priority |
| Coverage Strategy | Embedded in `test-design-qa.md` (P0-P3, ~34 scenarios) | Story test requirements |

## Epic-Level Integration Guidance

### Risk References

P0/P1 risks that should appear as epic-level quality gates:

- **Epic 8 (Two boards, one truth)** — R-9 (zero-loop guard under baseline drift, score 6) should gate stories 8.4/8.5 before they unblock from NEEDS-RESPEC.
- **Epic 9 (Secure live dashboards)** — R-3 (isolation proof non-vacuousness, score 6) should gate any future dashboard adopter beyond Atlas's Vizro board.
- **Epic 14 (BMAD core upgrades)** — R-13 (shim-retirement coverage, score 6) should gate Stories 14.9/14.10 closure.
- **Epic 42 (Agent and bus containment)** — R-16 (MCP transport authorization cross-station gap, score 6) should gate Epic 42's own "done" declaration.
- **Epic 44 (Cutover to python-foundry)** — R-14 (artifact-loss failure mode, score 6, echoing this repo's own prior incident) should gate Story 44.3 ("open the foundry") — the rehearsal drill must run first.
- **Epic 46/47 (bmad-suite lifecycle / cutover-ready estate)** — R-10 (readiness-gate false-positive risk, score 6) should gate treating Story 47.1's readiness checklist as sufficient before Epic 44's flag flips.
- **Container/Helm work (Epics 7, 12)** — R-6 (secret material in image layers/Pod specs, score 6) and R-15 (base-install dashboard-import isolation, score 4) should gate the next story that touches the container build or a Helm/OCP overlay.

### Quality Gates

Recommended per-epic quality gates based on this risk assessment:

- No epic touching secret/credential handling (Epics 1, 7, 9, 26, 41, 42) should be marked "done" while any of R-4, R-5, R-6, R-16 lack a confirmed passing test in the relevant CI matrix cell.
- Epic 44 (cutover) should not execute Story 44.3 until the R-14 rehearsal drill has a documented result.
- Epic 8's remaining stories (8.4/8.5) should not unblock from NEEDS-RESPEC until R-9's baseline-drift scenario is confirmed or added.

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Story Acceptance Criteria

Critical test scenarios that should become explicit acceptance criteria for their owning stories:

- Story 8.2 ("Zero-loop guarantee") / 8.4-8.5 — add "the guard holds when the baseline has drifted from both synced systems' current state" as an explicit AC (P0-004).
- Story 9.6 ("Isolation proven by tests that cannot pass vacuously") — add "the mutation-proof case is re-run for every new `[dashboard]` adopter, not only at initial authorship" as an explicit AC (P0-002).
- Story 44.3 ("Open the foundry") — add "a rehearsal restore from the archive has produced a reconciled tree before this story executes against the real repo" as a precondition AC (P0-007).
- Story 47.1 ("The readiness checklist is live...") — add "the gate reports NOT-READY when a known-broken suite member is injected" as an explicit AC (P0-005).
- Stories 14.9/14.10 (deprecation-shim retirement) — add "shim removal is proven landed via the existing `test_upgrade_*` pattern" as an explicit AC (P0-006).

### Data-TestId Requirements

Not applicable — `pyforge-steward` is a CLI + backend package with no primary HTML/UI surface of its own; the one UI surface it hosts (`[dashboard]` extra, Epic 9) is governed by the secure-live-dashboards spine's own component conventions, outside this handoff's scope.

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic | Test Level |
| --- | --- | --- | --- | --- |
| R-1 | TECH | 2×3=6 | Epic 1 (Story 1.1, `interfaces.py`/`cli.py` origin) — ongoing for every new duty module | Unit |
| R-3 | TECH | 2×3=6 | Epic 9, Story 9.6 | Unit/Meta |
| R-6 | SEC | 2×3=6 | Epic 7 (Story 7.3) / Epic 12 (Helm/OCP overlay stories) | Meta |
| R-9 | DATA | 2×3=6 | Epic 8, Stories 8.2/8.4/8.5 | Conformance |
| R-10 | BUS | 2×3=6 | Epic 46/47, Story 47.1 | Unit/Meta |
| R-13 | OPS | 1×3=3(→6*) | Epic 14, Stories 14.9/14.10 | Unit |
| R-14 | DATA | 2×3=6 | Epic 44, Story 44.3 (gated by 44.12/44.13/44.14) | Manual drill |
| R-16 | SEC | 2×3=6 | Epic 42, Stories 42.1/42.2 | Conformance (cross-station) |
| R-2 | TECH | 1×3=3 | Epic 3/5 (provisioning boundary) | Meta |
| R-4 | SEC | 1×3=3 | Epic 1, Story 1.2 (FR-7) | Conformance |
| R-5 | SEC | 1×3=3 | Epic 1, Story 1.5 (NFR-7) | Meta |
| R-7 | PERF | 2×2=4 | Epic 34/36 | k6 (blocked) |
| R-8 | OPS | 2×2=4 | Epic 17 | CI (ephemeral runner) |
| R-12 | DATA | 2×2=4 | Epic 34/36 (unifying AD-6) | Config review |
| R-15 | TECH | 2×2=4 | Epic 7/12 (uc:AD-4) | Meta |
| R-17 | BUS | 1×2=2 | Epic 4, Story 4.3 | Conformance |
| R-18 | OPS | 1×2=2 | Epic 1, Story 1.3 | Monitor |
| R-19 | TECH | 1×2=2 | Epic 1, Story 1.3 | Monitor |

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (`TD`) → produced this handoff document (system-level, this run).
2. **BMAD Create Epics & Stories** → for any *new* epic (e.g., a future Epic 48+), consume this handoff and embed the relevant risk/quality-gate language directly into new story ACs.
3. **TEA Epic-Level Test Design** → recommended specifically for Epic 44 (cutover), given R-14's severity and the historical incident it echoes — run this same workflow in Epic-Level mode scoped to Epic 44 for a deeper, story-by-story drill-down before the flag flips.
4. **TEA ATDD** (`AT`) → not yet run for this project; would generate acceptance tests per the new ACs listed above.
5. **BMAD Implementation** → developers implement the recommended new tests (R-2, R-6, R-10, R-15, plus R-9/R-13 extensions) per the QA document's Implementation Planning Handoff table.
6. **TEA Trace** (`TR`) → recommended once the new tests land, to validate P0/P1 coverage completeness against this risk register.

## Phase Transition Quality Gates

| From Phase | To Phase | Gate Criteria |
| --- | --- | --- |
| Test Design | Epic/Story Creation | All P0 risks (R-1, R-3, R-6, R-9, R-10, R-13, R-14, R-16) have a mitigation strategy on record (done — see `test-design-architecture.md` § Risk Mitigation Plans) |
| Epic/Story Creation | ATDD | New/extended stories (8.4/8.5, 14.9/14.10, 44.3, 47.1, next container-build story) carry the acceptance criteria listed above |
| ATDD | Implementation | Failing acceptance tests exist for R-2, R-6, R-10, R-15 before implementation starts |
| Implementation | Test Automation | All new/extended tests (P0-003 through P0-006, P1-002, P2-001) pass |
| Test Automation | Release | R-14's rehearsal drill has a documented result; no OPEN score-9 risk exists |
