---
title: Both guards hard-fail on drift
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 049c416ca6
---

<intent-contract>

## Intent

**Problem:** CAP-2 + CAP-3 of `spec-bmad-switch-scope-enforcement` (FR-190): `scripts/bmad-switch --current` still exits 0 with advisory stderr on marker/symlink drift, and `marshal init` may silently reconcile a home whose triangle agrees on the wrong project. DW-1-4-2 stays open until both guards consume the ONE S-20.6 `verify_scope` primitive and hard-fail.

**Approach:** Wire both call sites to S-20.6 `verify_scope` / `ScopeDrift`. Retire per-caller check bodies (no shadow copies). Deliberately desynced tree → non-zero `bmad-switch --current` naming the drift; `marshal init` refuses wrong-project agreement instead of reconciling. Close DW-1-4-2 against this story. Do not implement 20.8–20.10.

## Acceptance Criteria

- Desynced tree → `scripts/bmad-switch --current` exits non-zero and names the drift (no advisory-at-exit-0).
- `marshal init` refuses a home whose marker/symlinks agree on a different project than requested (no silent reconcile).
- Both consume the single S-20.6 primitive; old per-caller check bodies removed / not shadowed.
- DW-1-4-2 (`deferred-work-ledger` entry) closes against this story.
- Does not implement landing-evidence grammar (20.8+) or steward work.

## Boundaries & Constraints

**Never:** Second copy of `verify_scope`. Never edit steward 16-4. Never `scripts/bmad-switch` beyond hard-fail wiring. Finalize marshal ledger only.

</intent-contract>

## Code Map

- S-20.6 `verify_scope` / `ScopeDrift` module (already shipped)
- `scripts/bmad-switch` (`--current` path)
- `src/shared/packages/pyforge-marshal/.../cli/init.py` (MRS-INIT-003)
- DW-1-4-2 ledger entry
- Tests for desync → non-zero / refuse init

## Verification

- Fixture desync → bmad-switch --current ≠ 0 + named drift
- Init with wrong agreed slug → refuse
- Happy path still succeeds
- Related marshal tests + CI green
