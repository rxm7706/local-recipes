---
title: Intent-gap attempts are preserved
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-23'
shipped_ref: 'PR #687 / 5a50971409'
context: []
warnings: []
baseline_revision: 68687966e1
---

<intent-contract>

## Intent

**Problem:** An intent-gap halt reverts tracked work without a preserve artifact, so recovery needs session-transcript archaeology (FR-189 / `spec-bmad-loop-intent-gap-work-preservation` CAP-1 + CAP-2). Upstream `bmad_loop` stays untouched; Marshal-side compensation at the adapter seam must park the attempt like the deferred-story path.

**Approach:** On intent-gap halt with tracked changes, park an `attempt-preserve/*` branch (real commits) or `failed/<story>/changes.patch` (otherwise). Interception point (seam-observed vs proactive supervisor snapshot) is this story's design decision. Worktree stays reverted clean. Escalation text names the exact ref/patch so `bmad-loop resolve --restore-patch` restores without transcripts. Halt strictness unchanged; no auto-reland without the contract fix. Do not implement 20.5–20.10.

## Acceptance Criteria

- Intent-gap halt + tracked changes → preserve artifact exists (branch or patch) matching the reverted attempt; worktree clean.
- Escalation / Auto Run Result names the exact preserve ref or patch path.
- Given only that escalation text, restore is possible via named ref/`bmad-loop resolve --restore-patch` with zero session-transcript access.
- No edits to installed `bmad_loop` package.
- Does not implement 20.5 (missing-preserve detector) or later Epic 20 stories.

## Boundaries & Constraints

**Never:** Edit `bmad_loop`. Never auto-land preserved attempts. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward 16-2.

</intent-contract>

## Code Map

- `adapters/harness_bmadloop.py` / `supervisor/` (or current Marshal adapter seam equivalents)
- Deferred-story preserve path (reuse convention)
- Escalation / Auto Run Result text surface
- Tests proving preserve + named escalation; worktree clean

## Verification

- Fixture/simulated intent-gap halt → artifact present + named in escalation
- Restore path works from named ref/patch alone
- Related marshal tests green; CI detectors/linter/package tests
- No `bmad_loop` package mutations in the PR

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `5a50971409` (2026-08-23, "Merge pull request #687 from rxm7706/marshal/20-4-intent-gap-attempts-are-preserved"). Ledger row `20-4-intent-gap-attempts-are-preserved: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-20-4-intent-gap-attempts-are-preserved.md`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/intent_gap_preserve.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_run_status_snapshot.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_intent_gap_preserve.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_supervisor.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
