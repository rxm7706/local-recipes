---
title: Apply is deliberate, branched, and never clobbers custom
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: d8367f1d4a4
---

<intent-contract>

## Intent

**Problem:** After CAP-1's report-only pre-flight (Story 14.1), there is still no deliberate apply path that snapshots/branches first and never clobbers `_bmad/custom/**` (`spec-bmad-method-core-upgrade` CAP-2).

**Approach:** Given a clean tree and a CAP-1 report, the steward upgrade wrapper snapshots/branches first, runs `bmad-method install --action update -y` non-interactively (installer remains the only writer of `_bmad/bmm/**` / `_bmad/core/**`), refuses to start when legacy-name customization files would halt the shims, and lands the installer diff for review — never applied blind. `_bmad/custom/**` is byte-identical afterward or the run reports why not.

## Acceptance Criteria

- Apply path requires a clean tree and consumes CAP-1 report input (or equivalent pre-flight gate).
- Snapshots/branches before invoking the installer.
- Runs `bmad-method install --action update -y` non-interactively; steward never reimplements writing `_bmad/bmm/**` or `_bmad/core/**`.
- Refuses to start when legacy-name customization files would halt shims (names them).
- Lands installer diff for review — never applied blind to the working tree without a branch/review surface.
- `_bmad/custom/**` is byte-identical after the run, or the run reports why not.

## Boundaries & Constraints

**Never:** Implement CAP-3 re-apply of clobbered custom (Story 14.3), CAP-4 pin fan-out, or CAP-5 verification gate. Never call `scripts/bmad-switch`. Never silently overwrite `_bmad/custom/**`. Foreign-station pin sites are reported, never edited.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/` — upgrade apply duty extending 14.1 CLI
- Parent: `spec-bmad-method-core-upgrade/SPEC.md` CAP-2 + `failure-modes.md`
- Tests: branch-first, refuse-on-legacy-custom, custom byte-identical / named failure

## Verification

- `pixi run --frozen -e pyforge-steward pytest` targeting upgrade-apply tests
- Fixture proves refuse-on-legacy-custom and custom preservation
