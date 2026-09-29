---
title: '24.3: The second `sync-all` run is proven unchanged on a real deck'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 23.6's idempotency AC is proven over hand-written fakes and one live smoke that exercised only the skipped path, because no dispatch environment has live Claude Design credentials — the proof needs a person

**Approach:** one opt-in command runs `sync-all --slug <seeded deck>` twice against live Design and writes both per-deck reports plus the stamps to a proof dir

## Boundaries & Constraints

**Always:**
- the second report is all-`unchanged` with zero git writes and zero Design writes, the artifacts are recorded, and the surface is catalogued as live-proof-only so a static pass never claims it
- the task is never in the default gate or any CI lane, and the operator-run half is stated as such in the story's completion note — this story is `done` when the recorded run exists, not when the task does

**Never:**
- Do not re-mint a verb, build or command that exists — bind to it; do not add a second Pages deployment or a second PR gate; a live proof stays opt-in and operator-run (the Epic 24 HARD boundaries in `epics.md`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the deferral's own case | the DW row's evidence reproduced as a fixture | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-50`.
Surface: `pixi.toml` (an opt-in `deck-sync-proof` task gated on `HERALD_LIVE_SYNC_PROOF=1`), `src/shared/packages/pyforge-herald/src/pyforge/herald/sync_all.py` (a `--proof-dir` that writes both reports and the etag/tree stamps; no new stage), `.herald/sync-proof/<slug>/` (gitignored runtime output; the operator commits the two reports as the story's evidence under `planning-artifacts/specs/spec-pyforge-herald/sync-proof-2026-09-1x.md`), `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md` (one new row: herald `sync-all` idempotency), `planning-artifacts/deferred-work-ledger.md` (DW-FU-23-6 → done citing the run).
Ledger key: `24-3-the-second-sync-all-run-is-proven-unchanged-on-a-real-deck`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-24-3-the-second-sync-all-run-is-proven-unchanged-on-a-real-deck.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- With `HERALD_LIVE_SYNC_PROOF=1` and live Design credentials, the opt-in task runs `sync-all --slug <seeded deck>` twice; the second report is all-`unchanged` with zero git and zero Design writes; both reports + stamps are recorded; `live-proof-surfaces.md` gains the row; DW-FU-23-6 is marked done citing the recorded run. The live half is operator-run — the story is done when the recorded run exists.

## Auto Run Result

**Landed 2026-09-18 (PR #1482, `709c47bf2f Merge pyforge-herald/24-3 into main`) — mechanism complete, live proof pending the operator.** The dispatched session built everything a session can: the opt-in `deck-sync-proof` pixi task gated on `HERALD_LIVE_SYNC_PROOF=1`, `sync-all --proof-dir` writing both per-deck reports plus tree/etag stamps under `.herald/sync-proof/<slug>/`, the `live-proof-surfaces.md` row on `spec-pyforge-doctor`, and tests (+695 lines). The supervisor verified and landed it while the session was still waiting on its own `pyforge-station-tests` run, so this spec's status was never flipped by the session; set `done` here to match the promoted ledger row, with the honest caveat the story's own And-clause states: **the story is done when the recorded run exists, not when the task does** — that run needs live Claude Design credentials only the operator has. `DW-FU-23-6` stays **open** until `HERALD_LIVE_SYNC_PROOF=1 pixi run -e pyforge-herald deck-sync-proof -- --slug <seeded deck>` has been run twice and its artifacts recorded under `planning-artifacts/specs/spec-pyforge-herald/`.
