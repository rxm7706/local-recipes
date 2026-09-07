---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/test-design-architecture.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/test-design-qa.md
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-09-07'
projectName: 'pyforge-warden'
---

# TEA → BMAD Integration Handoff

## Purpose

This document bridges TEA's test design outputs with BMAD's epic/story decomposition workflow (`create-epics-and-stories`). pyforge-warden's v1-through-Epic-10 stories are already `done`; the primary consumer of this handoff today is Epic 11 (advisory lenses, currently `blocked`/`backlog`) and any future epic touching the false-green triad, the manifest extractor, or the baseline/waiver suppression engine.

## TEA Artifacts Inventory

| Artifact | Path | BMAD Integration Point |
|---|---|---|
| Test Design — Architecture | `_bmad-output/projects/pyforge-warden/planning-artifacts/test-design-architecture.md` | Epic quality requirements, story acceptance criteria for triad-touching work |
| Test Design — QA | `_bmad-output/projects/pyforge-warden/planning-artifacts/test-design-qa.md` | Story test-level assignments, coverage plan |
| Risk Assessment | embedded in both documents above (R-001 through R-014) | Epic risk classification, story priority |
| Coverage Strategy | embedded in the QA doc's Test Coverage Plan | Story test requirements |

## Epic-Level Integration Guidance

### Risk References

P0/P1 risks that should appear as epic-level quality gates for any future epic touching `extract/`, `engines.py`, `verdict.py`, `feeds.py`, or `waiver.py`:

- **R-001** (score 9): the adversarial fixture corpus (0 exit-0) must stay green — treat as a non-negotiable epic exit gate.
- **R-002** (score 6): corpus-oracle + differential-oracle CI wiring is a prerequisite for any epic that changes the E1 extractor.
- **R-003** (score 6): the 2027-07-24 baseline expiry cliff should be resolved (staggered) before any epic that would make the resulting red run harder to distinguish from a real regression.
- **R-004** (score 6): the offline-DB content pre-flight must remain independently tested before any epic that touches `engines.py`'s DB-loading path.
- **R-005** (score 6): differential-oracle coverage is the detection mechanism for extractor regressions — same prerequisite as R-002.

### Quality Gates

- No story that touches a false-green-triad module (`extract/`, `engines.py`, `verdict.py`, `feeds.py`, `waiver.py`) may merge without the adversarial fixture corpus and the relevant meta-tests (`test_extract_no_execution.py`, `test_socket_deny_alive.py`, `test_verdict_sole_ownership.py`) passing.
- Epic 11 (advisory lenses) should re-run this test design's epic-level companion once its stories move out of `blocked`/`backlog`, since it adds a new advisory-finding surface (`tea-test-review is a warden advisory finding`, story 11.2) that this system-level pass does not cover in depth.

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Story Acceptance Criteria

Critical scenarios that should become acceptance criteria for any story touching the named area:

- Any story touching `extract/*`: must not regress P0-003 (corpus-conformance, 0 uncaught exceptions) or P0-004 (differential-oracle ⊇ authoritative renderer).
- Any story touching `verdict.py`: must not regress P0-005 (pinned 7→4 exit projection).
- Any story touching `waiver.py`: must not regress P0-006 (baseline/waiver expiry re-block, applied-entry echo).
- Any story touching `engines.py`'s DB-loading path: must not regress P0-002 (DB content pre-flight).
- Any story adding forge-egress code: must satisfy P1-005's constraints (opt-in, post-verdict, never mutates scanned tree).

### Data-TestId Requirements

Not applicable — pyforge-warden is a non-interactive CLI with no UI surface in its core gate path. (The Epic-8 Django portal has its own UI-testability surface, out of this handoff's scope.)

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic | Test Level |
|---|---|---|---|---|
| R-001 | SEC | 9 | Any story touching `extract/`, `engines.py`, `verdict.py`, `feeds.py` | Conformance |
| R-002 | OPS | 6 | A new CI/infra story (Platform/Marshal-owned, not a Warden-package story) | CI wiring |
| R-003 | DATA | 6 | Story 6.8 follow-up (baseline-ID/expiry scheme) | Conformance |
| R-004 | SEC | 6 | Story 1.4 follow-up (DB loader hardening) | Conformance |
| R-005 | TECH | 6 | Any story touching `extract/*` (same prerequisite as R-002) | Conformance |
| R-006 | TECH | 4 | Story 6.6 follow-up (version-range widening) | Meta/Conformance |
| R-007 | DATA | 4 | Story 6.8 follow-up | Unit |
| R-008 | BUS | 4 | Story 2.1 follow-up | Unit |
| R-009 | PERF | 4 | A new CI/infra story (perf-trend tracking) | Performance |
| R-010 | OPS | 4 | Story 6.4/6.7 follow-up (feed refresh-job ownership) | OPS |

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (`TD`) → produced this handoff document.
2. **BMAD Create Epics & Stories** → for Epic 11 (currently `blocked`), consume this handoff when re-scoping.
3. **TEA ATDD** (`AT`) → generate acceptance tests per new story, if any new stories are opened against the R-002/R-003/R-009 gaps.
4. **BMAD Implementation** → developers implement with test-first guidance for any triad-touching change.
5. **TEA Trace** (`TR`) → validate coverage completeness once R-002's CI wiring lands.

## Phase Transition Quality Gates

| From Phase | To Phase | Gate Criteria |
|---|---|---|
| Test Design | Epic/Story Creation (Epic 11 re-scope) | All P0 risks (R-001 through R-005) have a documented mitigation strategy (done, this pass) |
| Epic/Story Creation | ATDD | Any new story touching a triad module has acceptance criteria drawn from this handoff's Story-Level Integration Guidance |
| ATDD | Implementation | Failing acceptance tests exist for P0/P1 scenarios tied to the story's touched modules |
| Implementation | Test Automation | The adversarial fixture corpus and relevant meta-tests pass |
| Test Automation | Release | Corpus-oracle CI wiring (R-002) is confirmed before an extractor-touching release |
