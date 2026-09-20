---
title: 'Wave probe A (baseline drift script surface)'
status: done
surface: ["scripts/bmad_loop_baseline_drift_check.py"]
---

Minimal wave-probe spec for Story 33.8 — disjoint surface declaration only.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `052d259a51` (2026-09-10, "Merge pull request #1107 from rxm7706/dispatch/pyforge-marshal/33.8"). Ledger row `33-8-the-first-live-fan-out-wave-on-a-real-dispatch-max-parallel-key: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-8-the-first-live-fan-out-wave-on-a-real-dispatch-max_parallel-key.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-8-wave-probe-a.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-9-wave-probe-b.md`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/config.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/policy.json`, `src/shared/packages/pyforge-marshal/tests/unit/test_cli.py` (+4 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `backlog` → `done` (ledger row `33-8-the-first-live-fan-out-wave-on-a-real-dispatch-max-parallel-key: done`).
- `## Auto Run Result` reconstructed from git (none survived).
