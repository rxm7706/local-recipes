---
title: '59.2: Detectors read one declaration; in-progress is grandfathered'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Those modules each keep a private status set.

**Approach:** They import the CAP-1 declaration. New Specs are not written in-progress; live in-progress files stay open until next edited. Doctor subset of Warden remains declared.

## Boundaries & Constraints

**Always:**
- board.py, chain.py, and status_body_consistency.py import the CAP-1 declaration.
- Live in-progress Specs stay open until next edited.

**Never:**
- Do not rewrite live in-progress files just to retire the status.
- Do not invert Doctor subset of Warden.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new Spec | authoring a new SPEC.md | status is not in-progress | n/a |
| live in-progress | existing file already in-progress | unchanged until next edit | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-2`.
Surface: src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py, chain.py, status_body_consistency.py; exit-code domains in the same declaration file (different key; DW-VOCAB-2026-09-14-8)..
Ledger key: `59-2-detectors-read-one-declaration-in-progress-is-grandfathered`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-2-detectors-read-one-declaration-in-progress-is-grandfathered.md`.

## Verification

**Recovered and completed 2026-09-18.** `marshal factory dispatch pyforge-steward 59.2` (run
`pyforge-steward-20260918T085921623Z-b8e882a5`) implemented this story correctly and committed the
work as a series of `wip: 59.2 (auto-checkpoint)` commits, but its own verify step (`marshal-policy.toml`'s
configured `python scripts/spec_surface_reconcile.py`) hit `MRS-GATE-001` (a real, unrelated repo-wide
gate failure — 5 pre-existing spec-surface-drift findings across three *other* stations' specs, none
touching this story's own surface) and the dispatch was marked `dispatch_completion_verdict: failed`.
A separate wind-down process still merged the checkpoint commits to `main` (PR #1444) without flipping
this story's own ledger key or spec `status:` — the story's actual implementation was never at risk,
just never formally closed.

Recovered by: (1) confirming `board.py`, `chain.py`, and `status_body_consistency.py` all read the
CAP-1 declaration (`docs/governance/guild-roster.json`'s `spec_statuses`/`spec_statuses_terminal`/
`spec_statuses_ready_or_beyond`) live at call time rather than keeping a private hardcoded copy, each
degrading to a documented fallback constant (never a crash) on a read/parse failure and appending a WARN
finding-precursor for the caller to surface, matching the house pattern (`chain.py::_load_constitutive`);
(2) reconciling the 5 unrelated spec-surface-drift findings that were blocking `spec_surface_reconcile.py`
in their own owning specs' memlogs (`pyforge-mason/spec-conda-forge-expert-rebuild`,
`pyforge-mason/spec-packaging-factory`, `pyforge-marshal/spec-pyforge-core`,
`pyforge-steward/spec-pyforge-steward` — each entry names the real, already-landed, unrelated commit
that caused it) and re-stamping each scoped baseline; (3) re-running both of this story's own configured
verify commands fresh: `pixi run --frozen -e pyforge-steward pyforge-steward-test` (1280 passed, 1
skipped) and `python scripts/spec_surface_reconcile.py` (now exits 0, "OK: every tracked file governed
or allowlisted; no drift"); (4) running the full `pyforge-doctor-test` suite directly (1710 passed; the
only 2 failures are a pre-existing, unrelated `agentic-sdlc-autonomy` `DEFERRED_SPECS` fixture drift,
confirmed to fail even with this story's own changes stashed out against clean `main`).

**Residual:** this recovery pass verified the implementation is correct and its own tests pass; it did
not re-derive the dev/review session's own narrative (the checkpoint commits carry no review-triage
log, since the dispatch never reached that finalize step). If a fuller `## Auto Run Result` accounting
is wanted later, `git log` on the `wip: 59.2 (auto-checkpoint)` commit chain (`fa7a44293b`..`256d3a4a2c`,
squash-landed as `df2ead09c4`) is the source of record.
