---
title: "Story 13.1: A drafting session surfaces matching deferred-work entries for an epic"
type: "feature"
created: "2026-08-21"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-09-18"
---

<!-- MINTED 2026-09-18 from epics.md Intent + ACs (Story 13.1). No Tier-3 draft was
     present under planning-artifacts/specs/ as spec-<ledger-key>.md. -->

## Intent

A drafting session surfaces matching deferred-work entries for a named epic or story.
Decomposes `spec-backlog-intake-check` CAP-1. Trigger is a `pyforge.doctor.sources`
detector / `doctor` CLI verb invoked manually by a drafting session — matching every
other Doctor capability's shape, not a hook into `bmad-create-story` (retired in 6.11)
or `bmad-create-epics-and-stories` prompt instructions.

Scan is a parsed id token, never a bare string-contains check (avoids repeating
`DW-CHAIN-COMPLETENESS-1` / Story 12.3). Nothing is auto-written into the story/spec.

**Deps:** —

## Acceptance Criteria

- **Given** an epic or story identifier named at invocation, **When** the new
  detector/verb runs, **Then** it scans tracked `deferred-work-ledger.md` files
  fleet-wide for entries whose `owner:`/prose precisely names that epic or story id —
  a parsed id token, never a bare string-contains check — **And** surfaces each match
  as a candidate acceptance criterion with its source ledger, entry id, and summary,
  for the drafting session to accept, reject, or reword. Nothing is auto-written into
  the story/spec (CAP-1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station verify
  suite; contract mint, no new per-story claim).
