---
title: "Story 12.1: The hygiene/verification catalog stays a maintained, current artifact"
type: "chore"
created: "2026-08-21"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-09-18"
---

<!-- MINTED 2026-09-18 from epics.md Intent + ACs (Story 12.1). No Tier-3 draft was
     present under planning-artifacts/specs/ as spec-<ledger-key>.md. -->

## Intent

Keep the hygiene/verification catalog a maintained, current artifact: newly discovered
"nothing actually checks for X" gaps are checked against the catalog's six categories,
and items stay cross-referenced as they move from cataloged to specced to shipped
(`spec-fleet-hygiene-verification-exemplar-program` CAP-1).

**Deps:** —

## Acceptance Criteria

- **Given** a newly-discovered "nothing actually checks for X" gap, **When** it is
  checked against the catalog's six categories, **Then** it returns a match or confirms
  genuine novelty, **And** the catalog stays cross-referenced with which items moved
  from cataloged to specced to shipped (CAP-1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station verify
  suite; contract mint, no new per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `6bdcb5df34` (2026-08-21, "Merge pull request #588 from rxm7706/doctor/12-1-hygiene-catalog-status"). Ledger row `12-1-the-hygiene-verification-catalog-stays-a-maintained-current-artifact: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-fleet-hygiene-verification-exemplar-program/hygiene-gap-catalog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
