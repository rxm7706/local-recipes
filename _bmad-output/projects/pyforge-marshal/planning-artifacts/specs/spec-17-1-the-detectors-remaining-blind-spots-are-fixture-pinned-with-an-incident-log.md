---
title: The detectors' remaining blind spots are fixture-pinned, with an incident log
type: test
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: c3e8af1f2b3
---

<intent-contract>

## Intent

**Problem:** Doctor detector suites largely cover FR-144, but unparseable frontmatter still degrades silently (today pinned as the opposite in `test_sources_chain_dream_chain.py`), and bmad-drift pin-missing / archive-misplaced / stray-file / spec-status-stale lack dedicated fixture pins. Detector regressions have no tracked incident log.

**Approach:** Change unparseable-frontmatter behaviour to surface a finding (re-pin tests). Add fixture pins for each bmad-drift blind spot (live-repo integrity tests stay). Introduce a tracked detector-incident log companion (date, detector, wrong claim, true value, root cause, fixing commit, pinning fixture) with a mandatory-entry rule whenever a detector fix lands in the same change.

## Acceptance Criteria

- Unparseable frontmatter surfaces as a finding — not silent degrade-to-owner-none (replaces opposite pin at `test_sources_chain_dream_chain.py:682`).
- `covers-dreams:` path remains pinned (existing coverage at `:147/:164/:657` — do not regress).
- bmad-drift pin-missing, archive-misplaced, stray-file, and spec-status-stale each have a dedicated fixture test.
- Tracked detector-incident log exists with mandatory entry when a detector is fixed in the same PR.

## Boundaries & Constraints

**Never:** Second parser for frontmatter. Never weaken live-repo integrity tests. Surface: `src/shared/packages/pyforge-doctor/tests/` + tracked incident log companion under doctor planning or package docs.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/tests/` — fixture pins + behaviour change tests
- `test_sources_chain_dream_chain.py` — unparseable frontmatter re-pin
- bmad-drift detector fixture tests (pin-missing, archive-misplaced, stray-file, spec-status-stale)
- Tracked detector-incident log companion (new file under doctor package or planning-artifacts)

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` (or established doctor test task)
- Incident log entry present when a detector behaviour changes

## Auto Run Result

Status: done — merged PR #661 as 208093926d3
Verification:
- `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dream_chain.py src/shared/packages/pyforge-doctor/tests/unit/test_detector_incident_log.py -q` — 39 passed
- CI detectors + linter green on PR #661
Implemented:
- `chain.py::_frontmatter_parse` surfaces `unparseable-frontmatter` WARN (FR-144 residual)
- `docs/detector-incident-log.md` with mandatory-entry rule + four seed entries (FR-146)
- `test_detector_incident_log.py` cross-checks FR-145 factory fixture pins
