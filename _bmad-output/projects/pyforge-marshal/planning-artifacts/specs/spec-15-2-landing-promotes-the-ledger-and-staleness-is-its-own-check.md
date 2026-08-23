---
title: Landing promotes the ledger, and staleness is its own check
type: feature
created: '2026-08-23'
status: in-review
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 3cd7abf25bd60a1c4b714af152d45dbc95f31842
---

<intent-contract>

## Intent

**Problem:** Ledger promotion after a story lands still depends on operator memory; ledger-vs-git drift (landed-but-unpromoted) is not a standalone check with direction (FR-136–FR-139, AD-71).

**Approach:** Wire mechanical ledger promotion into the landing path (deterministic trigger). Add a standalone check that reports ledger-vs-git drift per key WITH DIRECTION, reading merge history never the Tier-3 feed. Serialize concurrent promotions on the existing `FsPort.acquire_advisory_lock` (AD-42 — never a second lock). Regression-pin the already-shipped downgrade refusal.

## Acceptance Criteria

- Ledger promotion runs from landing itself (deterministic, never memory).
- Standalone check reports ledger-vs-git drift per key with direction (landed-but-unpromoted covered).
- Check reads merge history, never the feed.
- Concurrent promotions serialize on `FsPort.acquire_advisory_lock` (AD-42).
- Downgrade refusal remains regression-pinned (not rebuilt).

## Boundaries & Constraints

**Never:** Second lock implementation. Never `scripts/bmad-switch`. Surface: `cli/land.py`, `scripts/promote_sprint_status.py`, `pyforge.doctor.sources` (ledger direction).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py`
- `scripts/promote_sprint_status.py`
- Doctor ledger-direction source under `pyforge.doctor.sources`
- Tests under marshal / doctor packages as appropriate

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- Relevant doctor source tests if ledger-direction lands there

## Auto Run Result

Status: in-review
Verification: `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 5746 passed, 12 deselected.
Doctor: ledger-staleness + dispatch/registry/independence — 108 passed (focused).
promote_sprint_status regressions — 4 passed.
Changed: `cli/land.py` `_promote_sprint_ledger` (MRS-LAND-011); `promote_sprint_status.py` LocalFs advisory lock; doctor `LEDGER_STALENESS` / `gather_ledger_staleness`.
