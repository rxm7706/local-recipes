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

**Problem:** Detector blind spots still degrade silently or lack fixtures — unparseable frontmatter does not surface as a finding (FR-144 residual), and several bmad-drift cases lack fixture pins plus a tracked incident log (FR-145/146).

**Approach:** Change unparseable frontmatter to a finding (re-pin tests that currently assert degrade-to-owner-none). Add fixtures for bmad-drift pin-missing / archive-misplaced / stray-file / spec-status-stale. Create a tracked detector-incident log with mandatory-entry rule when a detector fix lands.

## Acceptance Criteria

- Unparseable frontmatter surfaces as a finding (not silent degrade); re-pin opposite tests.
- Fixtures for pin-missing, archive-misplaced, stray-file, spec-status-stale (live-repo integrity tests stay).
- Tracked incident log (date, detector, wrong claim, true value, root cause, fixing commit, pinning fixture) with mandatory-entry rule on detector fixes.

## Boundaries & Constraints

**Never:** Weaken live-repo integrity tests. Doctor package surface under `src/shared/packages/pyforge-doctor/tests/` + tracked incident log companion. Never `scripts/bmad-switch`.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/tests/`
- Tracked detector-incident log companion (path per existing doctor docs conventions)

## Verification

- Doctor/marshal test tasks as established for detector fixtures
