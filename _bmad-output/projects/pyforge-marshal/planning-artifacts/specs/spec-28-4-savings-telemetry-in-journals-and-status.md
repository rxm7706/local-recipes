---
title: 'Savings telemetry in journals and status (Story 28.4, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** The supervisor tallies weighted spend but nothing records what the
token-economy layers *saved* — so the operator cannot see economy mid-run (the standing
`DW-FU-3-6-6` mid-session-blindness finding), and ceilings cannot be recalibrated on
evidence.

**Approach:** The supervisor's tick gathers per-layer savings (wire-compression stats,
output-compression delta, graph-hit vs file-read counts where available) and journals them
alongside the existing weighted-spend tally; `marshal status` renders spend and savings for
the running story.

## Acceptance Criteria

- Given a live run with layers enabled, when the supervisor ticks, then journal entries
  carry per-layer savings fields next to the weighted spend tally (a new journal kind or
  extended payload, folded like existing kinds).
- Given a running story, when `marshal status` renders it, then spend and savings are both
  visible mid-run.
- Given a layer that exposes no stats (disabled or degraded), when the tick gathers, then
  its savings field is explicitly absent/null — never fabricated.
- Given any savings number, when verdicts are computed, then it feeds no pass/fail verdict
  and no exit-code change (advisory only).

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-4-savings-telemetry-in-journals-and-status`.

**Block If:** A change would turn savings telemetry into a gate, or break the supervisor's
prompt-cache-aware polling cadence (NFR-14, poll ≤60s) to gather stats.

**Never:** A second PR-gate verdict. Blocking the tick on a slow/unavailable stats source.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/` + `core/supervise.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/journal.py` (entry kinds, fold)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` (rendering)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(journal payload shape, status rendering, absent-not-fabricated, advisory-only). Land this
spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.4 and spec-marshal-token-economy CAP-7. Journals are the source of
truth for status (never a hand-maintained feed) — extend that pipeline, don't bypass it.
This story chips at `DW-FU-3-6-6` (token ceilings dark mid-session) but does not claim to
close it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-09-01: status → `done` (ledger + PR #973); SCP cross-ref `sprint-change-proposal-2026-09-01-dispatch-autonomy-hotfixes.md`

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `951eddb6b7` (2026-09-01, "Merge pull request #973 from rxm7706/dispatch/pyforge-marshal/28.4"). Ledger row `28-4-savings-telemetry-in-journals-and-status: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_savings_telemetry.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
