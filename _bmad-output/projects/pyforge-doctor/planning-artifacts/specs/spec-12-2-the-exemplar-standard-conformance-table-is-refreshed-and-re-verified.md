<!-- MINTED 2026-09-18 from epics.md Intent + ACs (Story 12.2). No Tier-3 draft was
     present under planning-artifacts/specs/ as spec-<ledger-key>.md. -->
---
title: "Story 12.2: The exemplar standard conformance table is refreshed and re-verified"
type: "chore"
created: "2026-08-21"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-09-18"
---

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
