---
title: Test architecture stays current as stories land
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 18221846fd
---

<intent-contract>

## Intent

**Problem:** Station `test-architecture.md` files freeze at generation time; a story that ships without an updated coverage-table row is a silent gap (FR-193 / testing-charter CAP-5).

**Approach:** Re-running S-19.1's generator (`scripts/bmad_tea_playwright.py` or successor) against a station's own epics regenerates its story-coverage table without hand-editing. Drift between shipped stories and the table is detectable (fail or report), not silent — so Herald's and Marshal's real documents do not freeze at their generation snapshot.

## Acceptance Criteria

- Re-run of the 19.1 generator regenerates each station's story-coverage table from that station's epics (no hand-edit required for normal epic completion).
- A story that shipped without its `test-architecture.md` row updated is detectable drift (CI or CLI gate), not a silent gap.
- Idempotent re-run; existing real Herald/Marshal architecture docs remain regenerable.
- Does not implement Epic 20 baseline-drift / intent-gap stories.

## Boundaries & Constraints

**Never:** Implement 20.x. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward 15-3.

</intent-contract>

## Code Map

- `scripts/bmad_tea_playwright.py` (or successor) — re-run / drift path
- Per-station `test-architecture.md` under planning-artifacts
- Meta tests for drift detection + idempotence

## Verification

- Generator re-run regenerates tables; drift fixture fails when a shipped story lacks a row
- `pixi run --frozen -e pyforge-marshal` related tests green
- CI: detectors, linter, package tests
