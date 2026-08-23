---
title: The pin fan-out is enumerated, not discovered by red tests
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: ed2b1fe6c05d1ef870d452b757f82fd53ae39aed
---

<intent-contract>

## Intent

**Problem:** When bmad-method or bmad-loop versions change, pin sites are still discovered by red tests (trap 5 from 2026-08-21) instead of an enumerated report (spec-bmad-method-core-upgrade CAP-4).

**Approach:** Extend the steward upgrade duty with a report-only command that, given a version change in bmad-method or bmad-loop, enumerates every known pin site with moved/not-moved status — root `pixi.toml` floors, marshal's pyproject + package `pixi.toml` + `HARNESS_VERSION_RANGE_TEXT` + seed manifest and its drift-test map, loop-home hook relays — exactly the sites the 2026-08-21 session had to touch. Foreign-station sites are reported, never edited.

## Acceptance Criteria

- Report-only enumeration of known pin sites with moved/not-moved status for a bmad-method or bmad-loop version change.
- Covers: root `pixi.toml` floors; marshal pyproject + package `pixi.toml` + `HARNESS_VERSION_RANGE_TEXT` + seed manifest + drift-test map; loop-home hook relays.
- Foreign-station sites are reported, never edited.
- Fixture-covered against the 2026-08-21 trap-5 site list.

## Boundaries & Constraints

**Never:** Edit foreign-station pin sites. Never implement 14.5 prove-landed. Never `scripts/bmad-switch`. Steward 12-7 remains skipped. Finalize steward ledger only.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py` — pin fan-out report
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — report verb
- Known pin-site inventory (constants or catalog)
- Unit tests under `pyforge-steward/tests/`

## Verification

- `pixi run --frozen -e pyforge-steward pytest …` green
- Fixture enumerates expected sites with moved/not-moved
- CI: detectors, linter, package tests

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/670
Merge SHA: b9f1000a671c94266a72d487b2b10ae0935752d1
Tests: 33 upgrade unit tests passed; CI green on #670
