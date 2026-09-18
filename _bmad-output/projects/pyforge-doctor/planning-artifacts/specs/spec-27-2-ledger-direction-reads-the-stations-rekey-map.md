---
title: '27.2: `ledger-direction` reads the station''s rekey map'
type: 'fix'
created: '2026-09-18'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `gather_direction` compares keys parsed from merge history straight against the tracked ledger, so a station that renumbered its stories (atlas, `rekey-2026-09-17.md`: 13-5 → 12-5-…, 14-4 → 13-4-…, 15-3 → 14-3-…) reads its own bmad-loop merges as `landed-but-unpromoted` — three live rows on today's `main`. `gather()` has applied the rekey maps since Story 25.3; `gather_direction` never did.

**Approach:** Pass every merge-history key through the station's `rekey-*.md` maps (via `pyforge.doctor.rekey.parse_rekey`, the reader `gather()` uses) before the ledger comparison; an unreadable or malformed map is a WARN naming the file.

## Boundaries & Constraints

**Always:**
- `ledger-direction-check` on today's `main` reports no atlas `landed-but-unpromoted` row; a fixture with a rekey map and a merge naming the old key reports nothing; the same fixture without the map reports the row (mutation test).
- An unreadable or malformed rekey map is a WARN that names the file — never a silent pass, never a crash; the exit-code domain `{0, 2, 130}` is untouched.

**Never:**
- Do not re-implement rekey parsing — reuse `pyforge.doctor.rekey.parse_rekey` and the `_rekey_paths` discovery `gather()` already has.
- Do not soften any other `ledger-direction` verdict; every other source stays advisory.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| renumbered station | merge names old key; map says old → new; new is done | no finding | n/a |
| no map | same merge, no rekey-*.md | `landed-but-unpromoted` | n/a |
| broken map | rekey-*.md unparseable | WARN `rekey-map-unreadable` naming the file | never crash |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-79`.
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py` (`gather_direction`); `tests/unit/test_sources_ledger_direction.py`.
Ledger key: `27-2-ledger-direction-reads-the-stations-rekey-map`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-27-2-ledger-direction-reads-the-stations-rekey-map.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild ledger-direction-check` on `main` exits 0 with no `pyforge-atlas/13-5`, `14-4` or `15-3` row.
