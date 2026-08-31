---
title: 'Auto-derived effective surface, no manual per-story widening (Story 28.14, Epic 28)'
type: 'feature'
created: '2026-08-31'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings:
  - Operational stopgap on 2026-08-31 widened pyforge-marshal `[epic_surfaces]."28"` to a
    station-wide wildcard — this story ships the real auto-derive mechanism to replace that
    stopgap; do not rely on the hand-widened entry as the long-term design.
---

<intent-contract>

## Intent

**Problem:** When a story spec declares no `surface:` globs, `MRS-GATE-007` falls back to
policy `[epic_surfaces]` entries that must be hand-widened per epic/story before dispatch
can land legitimate within-station work — the Aug 31 live drain stalled atlas 21.7 and
marshal 28.2 for over an hour each until an operator manually patched `marshal-policy.toml`.

**Approach:** At `spin`/`dispatch` policy composition, auto-derive a safe per-station default
effective surface feeding AD-27's existing narrow-only `compute_effective_surface`
combinator (unchanged): the station's own package tree
(`src/shared/packages/pyforge-<slug>/**`), its planning/implementation-artifact trees, and
the common bookkeeping paths (`.gitignore`, `pixi.toml`, `pixi.lock`, `environment.yaml`,
`scripts/.spec-surface-baseline.json`). An explicit `[epic_surfaces]` entry still narrows
further via intersection when an operator wants tighter containment.

## Acceptance Criteria

- Given a story touching only files under its own station's package tree and the common
  bookkeeping paths, when verification runs with zero `[epic_surfaces]` entry declared, then
  `MRS-GATE-007` passes.
- Given a story touching a different station's package, or repo config outside the computed
  default, when verification runs, then `MRS-GATE-007` still fails — cross-station
  containment is preserved.
- Given an existing `[epic_surfaces]` entry that narrows further than the auto-derived
  default, when verification runs, then behavior is byte-identical to today (intersection-only
  combinator unchanged).
- Given spin and dispatch, when policy is composed, then both engines receive the same
  auto-derived default (Story 28.1's one-composition-site discipline).

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-14-auto-derived-effective-surface-no-manual-per-story-widening`.

**Block If:** A change would weaken cross-station containment, rewrite AD-27's
intersection-only combinator, or remove the ability to narrow further via explicit
`[epic_surfaces]`.

**Never:** A per-story hand-maintained surface list as the steady-state operator workflow.
Replacing `MRS-GATE-007`/`008` with a different gate.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (surface resolution; `compute_effective_surface` consumer)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` (`MRS-GATE-007` scope check)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` + `cli/dispatch.py` (policy composition at launch)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(within-station pass with no epic_surfaces, cross-station fail, explicit narrow unchanged,
spin/dispatch agreement). Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.14 and spec-marshal-token-economy CAP-16. Deps: —. Operator
decision 2026-08-31: automate surface derivation so dispatch never blocks on manual
`[epic_surfaces]` widening (paired with Story 28.15's warn-mode default).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-31: drafted from live MRS-GATE-007 dispatch stall (CAP-16; operator fold-in same session)
