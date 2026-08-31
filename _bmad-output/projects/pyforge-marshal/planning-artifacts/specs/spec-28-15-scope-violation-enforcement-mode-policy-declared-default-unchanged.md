---
title: 'Scope-violation enforcement mode, policy-declared, default unchanged (Story 28.15, Epic 28)'
type: 'feature'
created: '2026-08-31'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
baseline_revision: '7a13ea55d5ca052cab79edc498afa56fc8716453'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings:
  - pyforge-marshal is set to `off` immediately as an operational stopgap (2026-08-31) to
    unblock the live Epic 28 drain — this story ships the real `hard`/`warn`/`off`
    mechanism; the stopgap is not the long-term design.
---

<intent-contract>

## Intent

**Problem:** `MRS-GATE-007`/`008` scope violations are non-waivable refuses today — an
unattended drain campaign deadlocks permanently on the first out-of-surface file with no
self-service recovery, while the operator still wants violations visible (not silently
landed).

**Approach:** Add a policy-declared, per-station scope-violation enforcement mode with
three values: `hard` (today's non-waivable refuse), `warn` (findings journaled and surfaced
in `marshal status`/`fleet-picture`, landing not blocked), `off` (check skipped entirely).
Default is `warn`, not `hard`. One station's declared mode never changes another's.

## Acceptance Criteria

- Given no scope-violation mode declared for a station, when a scope violation occurs,
  then it lands as a named, journaled advisory finding and does not refuse landing (`warn`
  default).
- Given `hard` declared for a station, when a scope violation occurs, then behavior
  reproduces today's non-waivable refuse exactly.
- Given `off` declared for a station, when files change outside surface, then
  `MRS-GATE-007`/`008` are not evaluated — zero findings, zero journal entries.
- Given `warn` mode and a violation, when `marshal status` or `fleet-picture` renders, then
  the finding is visible — not journal-only.
- Given two stations with different declared modes, when each violates scope, then each
  station's mode applies independently.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-15-scope-violation-enforcement-mode-policy-declared-default-unchanged`.

**Block If:** A change would make `warn` silently equivalent to `off`, or apply one
station's mode fleet-wide.

**Never:** Removing scope containment checks entirely as the fleet default. A second
scope-gate mechanism outside Epic 2's gate objects.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` (`MRS-GATE-007`/`008` verdict shaping)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (per-station mode key + validator)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` (render warn-mode findings)
- `scripts/fleet_picture.py` (fleet-wide visibility of warn-mode violations)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(default warn, hard reproduces refuse, off skips, status visibility, per-station isolation).
Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.15 and spec-marshal-token-economy CAP-17. Deps: —. Pairs with
Story 28.14 (CAP-16 auto-derive reduces how often violations fire; CAP-17 ensures the
remainder never deadlocks an autonomous drain). Operator decision 2026-08-31: visible but
non-blocking is the steady state once auto-derivation is trusted.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-31: drafted from live MRS-GATE-007 dispatch stall (CAP-17; operator fold-in same session)
