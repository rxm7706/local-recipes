---
title: Missing-preserve detector
type: test
created: '2026-08-23'
status: done
shipped_ref: 'PR #689 / 7fd89e4294'
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: ee39a97fcf
---

<intent-contract>

## Intent

**Problem:** CAP-3 of `spec-bmad-loop-intent-gap-work-preservation` needs a post-hoc detector so an intent-gap halt without a preserve artifact (seam bypass or upstream shift) cannot pass silently. Story 20.4 shipped the preserve convention (proactive supervisor snapshot); this story only detects missing preserves.

**Approach:** Add a detector following `story-status-check` / `loop-stall-check` precedent that reads the S-20.4 preserve convention. Simulated intent-gap halt with no artifact → finding; halt with artifact present → clean. No edits to `bmad_loop`. Do not implement 20.6–20.10.

## Acceptance Criteria

- Simulated intent-gap halt **without** preserve artifact → detector trips a finding (non-silent).
- Halt **with** artifact present (branch or patch per 20.4 convention) → detector passes clean.
- Follows local detector precedent (runtime scope / placement documented like peer detectors).
- No mutations to installed `bmad_loop` package.
- Does not implement 20.6+ (verify_scope, etc.).

## Boundaries & Constraints

**Never:** Edit `bmad_loop`. Never re-implement 20.4 preserve path beyond reading its convention. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward 16-3.

</intent-contract>

## Code Map

- S-20.4 preserve convention (`attempt-preserve/*`, `failed/<story>/changes.patch`, supervisor `intent_gap_preserve`)
- New detector under `scripts/` or `pyforge.doctor.sources` (peer: loop-stall / story-status) — placement is this story's decision; document it
- Fixtures + unit/meta tests for missing vs present artifact

## Verification

- Missing-artifact fixture → finding; present-artifact fixture → clean
- Related marshal / detector tests green; CI detectors/linter/named-module-gates as applicable
- Confirm not silently no-op when preserve missing

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9ad3509c96` (2026-08-23, "Merge pull request #690 from rxm7706/marshal/20-5-finalize"); also `7fd89e4294` (2026-08-23, "Merge pull request #689 from rxm7706/marshal/20-5-missing-preserve-detector"). Ledger row `20-5-missing-preserve-detector: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.cursor/pyforge-fleet-drain/STATUS.md`, `.cursor/pyforge-fleet-drain/queues.yaml`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-20-5-missing-preserve-detector.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
