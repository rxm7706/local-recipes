---
title: '27.3: A station''s legacy-template history stays attributed after its template changes'
type: 'fix'
created: '2026-09-18'
status: 'in-review'
baseline_revision: '76905db53a99c882398a4412ffa0548984760b46'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 27.1 made Doctor's merge-history sources read each station's *current* `merge_subject_template`. Marshal landed `34-3` on 2026-09-12 as `Merge 34-3 into main` under the then-default template; the moment marshal's policy moved to `Merge pyforge-marshal/{key} into main` (PR #1467), `story-status` on `main` reports `marshal/34-3: reads done in the sprint feed, but the harness says 'deferred' with no commit and no merge commit anywhere` — a `done` story orphaned by its own station's template move.

**Approach:** A bare legacy-form subject (`Merge {key} into main`) is attributed to the querying station only when that station's tracked ledger knows the key (Story 35.1's corroboration), implemented once and used by both `marshal.py::gather_story_status` and `ledger.py::gather_direction`. The scoped form keeps attributing; a bare subject naming a key the station does not know attributes nothing.

## Boundaries & Constraints

**Always:**
- Marshal `34-3` reads as merged and `story-status` on `main` reports no finding for it; a bare subject naming an unknown key attributes nothing; the scoped form still attributes; CAP-78's PR #1465 replay stays `ok`.
- One function, both sources; exit-code domain `{0, 2, 130}` untouched.

**Never:**
- Do not attribute a bare subject to a station whose ledger does not know the key — that is the cross-station poison CAP-78 closed.
- Do not import `pyforge.marshal`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| own legacy landing | `Merge 34-3 into main`; marshal ledger knows 34-3; policy now scoped | attributed to marshal | n/a |
| sibling's bare subject | `Merge 13-5 into main`; atlas ledger does not know 13-5 | nothing | n/a |
| scoped form | `Merge pyforge-marshal/50-1 into main` | attributed | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-80`.
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py`; `.../sources/ledger.py`; tests.
Ledger key: `27-3-a-stations-legacy-template-history-stays-attributed`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-27-3-a-stations-legacy-template-history-stays-attributed.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild story-status-check` on `main` reports no `marshal/34-3` finding.
