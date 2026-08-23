---
title: The detectors' remaining blind spots are fixture-pinned, with an incident log
type: test
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 3c0d74fa09
---

<intent-contract>

## Intent

**Problem:** Doctor detector blind spots remain — unparseable frontmatter degrades silently (FR-144 residual); pin-missing/archive-misplaced/stray-file/spec-status-stale lack fixture pins; no tracked incident log when a detector wrong-claim is fixed (FR-145, FR-146).

**Approach:** Change unparseable frontmatter to surface as a finding (update/re-pin `test_sources_chain_dream_chain.py` away from degrade-to-owner-none). Add live-repo integrity fixtures for each listed detector gap. Add tracked detector-incident log with mandatory entry rule in the same change that fixes a detector.

## Acceptance Criteria

- Unparseable frontmatter surfaces as a finding (not silent degrade).
- `bmad-drift` pin-missing, archive-misplaced, stray-file, spec-status-stale each have fixture coverage.
- Tracked incident log exists (date, detector, wrong claim, true value, root cause, fixing commit, pinning fixture).
- Mandatory-entry rule: fixing a detector requires a log entry in the same change.

## Boundaries & Constraints

**Never:** Second detector implementation outside doctor sources. Surface: `pyforge-doctor/tests/`, tracked incident log companion doc.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/tests/` — fixture pins
- Tracked detector-incident log (planning-artifacts or doctor package docs per sibling pattern)
- `pyforge.doctor.sources` — unparseable frontmatter behaviour change

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` (or established doctor test task)
