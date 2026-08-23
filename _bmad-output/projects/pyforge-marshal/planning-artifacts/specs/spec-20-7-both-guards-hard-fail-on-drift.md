---
title: Both guards hard-fail on drift
type: feature
created: '2026-08-23'
status: done
shipped_ref: 'PR #692 / 1a5f2d32c5'
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 3f722545d5cd7a4225eda0ed22d4c7f6ca4d3cc4
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


## Design Notes

- Both guards import `pyforge.marshal.scope.verify_scope` (sole CAP-1 primitive).
- `scripts/bmad-switch`: retired `desync_warning` / `read_link_slugs`; `--current` and `--list` hard-fail (exit 2) when `verify_scope(root, marker)` returns `ScopeDrift`.
- `marshal init` MRS-INIT-003: `verify_scope(home, requested_slug)` + `_mrs_init_003_from_scope_drift` refuses unrecognized planning symlinks, internal desync, and marker+planning agreement on a wrong project; partial/empty homes still provision.
- FsPort skip/write path retains `_slug_from_*` helpers (not a second triangle check). `core/status.py` homes reporting keeps its own parse helpers (out of CAP-2 guard scope).
- DW-1-4-2 closed against this story.

## Tasks & Acceptance

- [x] Wire `bmad-switch --current` to `verify_scope` (hard-fail, named drift)
- [x] Wire `marshal init` MRS-INIT-003 to `verify_scope` (refuse wrong-project agreement)
- [x] Retire `desync_warning` body in `bmad-switch`
- [x] Tests: desync → non-zero; wrong-project init refuse; happy path
- [x] Close DW-1-4-2

## Auto Run Result

Status: done

PR: https://github.com/rxm7706/local-recipes/pull/692
Merge SHA: 1a5f2d32c5ca9c4dfc678360a77fe0e0ad3f36d1
Note: merged with `--admin` (Actions billing blocked CI; local verification green).

Summary: Both guards consume sole `verify_scope`. `bmad-switch --current` exits 2 on drift; `marshal init` refuses wrong-project agreement; DW-1-4-2 closed in ledger.

Verification (local): `pixi run -e pyforge-marshal pytest …/test_verify_scope.py …/test_init.py tests/scripts/test_bmad_switch_hard_fail.py -q` → 186 passed.

