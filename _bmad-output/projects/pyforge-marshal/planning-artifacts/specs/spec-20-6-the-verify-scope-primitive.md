---
title: The verify_scope primitive
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 9ad3509c96
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

**Never:** Two parallel copies of the primitive. Never implement 20.7 hard-fail wiring in this story. Never `scripts/bmad-switch` behavior change beyond exporting/consuming the new primitive if needed for tests. Finalize marshal ledger only. Do not touch steward 16-3 / PR #688.

</intent-contract>

## Code Map

- Active-project marker + planning/implementation artifact symlink pair (BMAD multi-project pattern)
- New shared module (placement TBD this story) exporting `verify_scope` + `ScopeDrift`
- Unit tests covering agree / mismatch / unrecognized shapes
- DW-1-4-2 reference in deferred-work ledger (closeout stays for 20.7)

## Verification

- Unit matrix: agree→None; A-vs-B→ScopeDrift; unrecognized→"unrecognized"
- No subprocess in implementation
- Related marshal tests green; CI detectors/linter/named-module-gates as applicable
