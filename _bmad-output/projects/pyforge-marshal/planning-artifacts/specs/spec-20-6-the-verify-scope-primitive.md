---
title: 'The verify_scope primitive'
type: feature
created: '2026-08-23'
status: in-progress
updated: '2026-08-23'
context: []
warnings: []
baseline_commit: e922ab953b2f
---

<intent-contract>

## Intent

**Problem:** FR-190 CAP-1 (`spec-bmad-switch-scope-enforcement`): callers need one cheap primitive that detects active-project marker/symlink drift (DW-1-4-2 blind spots) without inferred agreement. Story 20.7 will hard-wire guards; this story only ships the shared primitive.

**Approach:** Implement `verify_scope(root, expected_slug)` as one shared module. Placement (import path vs Genesis COPIED-MANAGED copy) is this story's design decision under never-two-parallel-copies — document it. Three file reads + string compares; no subprocess. Do not implement 20.7 guard hard-fail wiring yet.

## Acceptance Criteria

- Marker + both symlinks all at slug B → `verify_scope(root, "A")` returns `ScopeDrift` naming found-vs-expected.
- Unrecognized symlink-target shape → drift reporting `"unrecognized"` (never inferred agreement).
- All three agree on expected slug → returns `None`.
- No subprocess; cheap enough for a write-skill preflight.
- Single module home documented; no second parallel copy.
- Does not implement 20.7–20.10 (guards still soft/legacy until 20.7).

## Boundaries & Constraints

**Never:** Two parallel copies of the primitive. Never implement 20.7 hard-fail wiring in this story. Never change `scripts/bmad-switch` behavior beyond exporting/consuming the new primitive if needed for tests. Finalize marshal ledger only. Do not touch steward 16-3 / PR #688.

</intent-contract>

## Design Notes

### never-two-parallel-copies — placement decision

**Chosen home:** `pyforge.marshal.scope`
(`src/shared/packages/pyforge-marshal/src/pyforge/marshal/scope.py`)

| Option | Verdict |
|--------|---------|
| Import path under `pyforge.marshal` (this choice) | **Selected.** One module both 20.7 callers can import; monorepo already installs `pyforge-marshal` via pixi. |
| Under `pyforge.marshal.core` | **Rejected.** AD-4 forbids I/O in `core/**`; this primitive is three filesystem reads. |
| Genesis COPIED-MANAGED twin checked into this repo | **Rejected for CAP-1.** Would be a second body unless mechanically generated; violates never-two-parallel-copies *here*. Body is stdlib-only so Genesis *may* later deliver this single file alongside `bmad-switch` without forking — delivery is not a second source in this repo. |
| Standalone under `scripts/` only | **Rejected.** `cli/init.py` would either path-hack or reimplement; recreates the divergent-pair failure mode. |

**Rationale:** CAP-2 (story 20.7) must retire both `scripts/bmad-switch` and `cli/init.py` MRS-INIT-003 bodies by importing **this** module. Import-path keeps a single source of truth; stdlib-only (`dataclasses` + `pathlib`) keeps the door open for Genesis delivery without a marshal dependency in foreign checkouts — without shipping two copies today.

**Out of scope (20.7):** Do not replace `desync_warning` / MRS-INIT-003 hard-fail behavior yet. DW-1-4-2 stays open until 20.7 closes it.

## Code Map

| Path | Role |
|------|------|
| `src/shared/packages/pyforge-marshal/src/pyforge/marshal/scope.py` | **Sole** `verify_scope` + `ScopeDrift` + `UNRECOGNIZED` implementation |
| `src/shared/packages/pyforge-marshal/tests/unit/test_verify_scope.py` | Agree / A-vs-B / unrecognized / missing / no-subprocess AST matrix |
| `scripts/bmad-switch` (`desync_warning`, `read_link_slugs`) | Legacy soft guard — **unchanged** this story |
| `…/cli/init.py` (`_slug_from_symlink_target`, MRS-INIT-003) | Legacy hard guard — **unchanged** this story |
| deferred-work-ledger `DW-1-4-2` | Reference only; closeout is 20.7 |

## Tasks

- [x] Add `pyforge.marshal.scope` with `verify_scope` / `ScopeDrift` / `"unrecognized"` fail-closed parsing
- [x] Document never-two-parallel-copies placement (module docstring + this Design Notes)
- [x] Unit tests: agree → `None`; B-vs-A → `ScopeDrift`; unrecognized shapes → `"unrecognized"`
- [x] Run unit tests (pass)
- [ ] ~~Wire `bmad-switch --current` / MRS-INIT-003~~ → story 20.7
- [ ] ~~Close DW-1-4-2~~ → story 20.7

## Verification

- Unit matrix: agree→None; A-vs-B→ScopeDrift; unrecognized→`"unrecognized"`
- No subprocess in implementation (AST import/attr scan in `test_verify_scope.py`)
- Related marshal tests green; CI detectors/linter/named-module-gates as applicable
