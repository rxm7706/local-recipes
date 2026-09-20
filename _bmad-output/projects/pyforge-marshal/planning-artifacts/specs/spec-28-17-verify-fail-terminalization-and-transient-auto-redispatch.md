---
title: 'Verify-fail terminalization and transient auto-redispatch (Story 28.17, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-verify-fail-terminalization/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-13-sanctioned-retry-after-an-operator-initiated-stop.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** After independent verify refuses (`MRS-GATE-001` etc.) and the build
session is dead, git-fact progress keeps `judge_dispatch_completion()` at
**`LIVE`**. The dispatch supervisor heartbeats indefinitely; preserve never
runs; fleet `--stories` drains freeze until an operator manual preserve/kill/
reset/redispatch (atlas 23.1, 2026-09-01).

**Approach:** In the dispatch supervisor, when `session_alive == false`, verify
outcome is `refused`, and git shows progress — **terminalize as `failed`**:
journal completion, capture `failed/<story>/changes.patch`, exit supervisor.
Rely on existing `classify_dispatch_block` **TRANSIENT** classification so the
next `factory drain --once` cycle redispatches the same backlog story without
`MRS-DRAIN-005` permanent block.

## Acceptance Criteria

- Given a dispatch whose session is dead, verify outcome is `refused`, and git
  shows progress beyond baseline, when the supervisor ticks, then it journals
  `dispatch-completion` with verdict `failed`, captures preserve patch, and exits
  (no further heartbeats as LIVE).
- Given the same story with verify `refused` but the session process still
  alive, when the supervisor ticks, then verdict remains `LIVE` (unchanged).
- Given a CAP-1 terminalized run with `MRS-GATE-001`, when the next fleet
  `drain --once` cycle runs on that station, then the story is not permanently
  blocked by `MRS-DRAIN-005` and a new dispatch may launch (transient retry).
- Given verify passes, when the supervisor runs, then CAP-1 terminalization does
  not fire (landing path unchanged).

## Boundaries & Constraints

**Always:** Pure helper `should_terminalize_verify_refusal` in
`dispatch_supervisor_state.py`; supervisor imports it — no change to global
22.2 judge.

**Block If:** CAP-1 weakens live-session refusal or skips preserve on
terminalized verify-fail.

**Never:** Silent auto-apply of preserve patch; replacing **28.13** stopped
taxonomy.

Ledger key `28-17-verify-fail-terminalization-and-transient-auto-redispatch`.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_supervisor_state.py` — `should_terminalize_verify_refusal`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` — LIVE-loop terminalization + existing preserve on FAILED exit
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py` — transient gate set (unchanged; CAP-2 compose)
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_hotfix.py` — CAP-1 unit tests

## Tasks & Acceptance

**Execution:** CAP-1 shipped in supervisor + pure helper + tests. CAP-2 verified
by existing transient classification + drain cycle (document in Dev Notes).
CAP-3 optional journal field — defer if not needed for v1.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Sibling to **28.13** (sanctioned retry / SIGTERM). Motivating incident:
`docs/dreams/marshal-dependency-aware-dispatch.md` addendum E; live atlas 23.1
verify-fail zombie 2026-09-01.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`

## Spec Change Log

- 2026-09-01: drafted via bmad-spec; CAP-1 implemented same session (P0)

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9541dc6f80` (2026-09-01, "feat(marshal): Story 28.17 verify-fail terminalization (P0)"). Ledger row `28-17-verify-fail-terminalization-and-transient-auto-redispatch: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/fleet-drain-queue.yaml`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-17-verify-fail-terminalization-and-transient-auto-redispatch.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-verify-fail-terminalization/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-verify-fail-terminalization/SPEC.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `docs/dreams/marshal-dependency-aware-dispatch.md`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_supervisor_state.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_hotfix.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `28-17-verify-fail-terminalization-and-transient-auto-redispatch: done`).
- `## Auto Run Result` reconstructed from git (none survived).
