---
title: "Story 12.2: The exemplar standard conformance table is refreshed and re-verified"
type: "chore"
created: "2026-08-21"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-09-18"
---

<!-- MINTED 2026-09-18 from epics.md Intent + ACs (Story 12.2). No Tier-3 draft was
     present under planning-artifacts/specs/ as spec-<ledger-key>.md. -->

## Intent

Refresh and re-verify the exemplar standard conformance table. The DW-ledger column
currently shows only `pyforge-atlas` compliant while 7 other projects now carry real,
git-tracked `deferred-work-ledger.md` files. Correct that column to the live state and
check every other column (companions, story specs, delivery records, README) for the
same staleness (`spec-fleet-hygiene-verification-exemplar-program` CAP-2).

**Deps:** —

## Acceptance Criteria

- **Given** the DW-ledger column currently shows only `pyforge-atlas` compliant while 7
  other projects now carry real, git-tracked `deferred-work-ledger.md` files, **When**
  the refresh runs, **Then** the table is corrected to the live state, **And** every
  other column (companions, story specs, delivery records, README) is checked for the
  same staleness (CAP-2).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station verify
  suite; contract mint, no new per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `f0cca9e262` (2026-08-21, "Merge pull request #590 from rxm7706/doctor/12-2-exemplar-standard-refresh"). Ledger row `12-2-the-exemplar-standard-conformance-table-is-refreshed-and-re-verified: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/EXEMPLAR-STANDARD.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-fleet-hygiene-verification-exemplar-program/hygiene-gap-catalog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
