---
title: An UNSUPERVISED row has a cheap documented double-check
type: docs+feature
created: '2026-08-24'
status: ready
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: d7047f4c68
---

<intent-contract>

## Intent

**Problem:** When `marshal status` / fleet-picture reports `UNSUPERVISED` for a run Marshal did not spawn, operators have no documented cheap follow-up for "is the engine actually alive?" — the 2026-08-15 raw-`bmad-loop run` incident (FR-195 CAP-3; spec-bmad-loop-liveness-footgun).

**Approach:** Wherever UNSUPERVISED is explained (fleet-picture output docs, marshal status help/runbooks, team-memory carriers), name the CAP-2 one-command follow-up (`bmad-loop status <run_id> --json` + `list --json`, per `.claude/memory/reference/fleet-landing-pass-liveness.md`) and/or reference `HarnessPort.engine_liveness`. Do not alter `derive_home_state` row derivation (Story 5.8 territory). Deps: 24.1 done (#718); 24.2 done (#719). Completes Epic 24.

## Acceptance Criteria

- UNSUPERVISED explanation surfaces include the documented engine-liveness follow-up command.
- 2026-08-15 scenario (raw `bmad-loop run`, no sidecar) resolves in one command per docs.
- `derive_home_state` / fleet row derivation unchanged.
- Meta gate extended or new test if repo pattern exists (mirror 24.2's operator-instruction gate).

## Boundaries & Constraints

**Never:** Re-mint CAP-1/CAP-2. Never add per-row probe to fleet sweep. Finalize marshal ledger only. **maintenance label** on PR.

</intent-contract>

## Code Map

- Parent: `spec-bmad-loop-liveness-footgun/SPEC.md` (CAP-3)
- Surfaces: fleet-picture docs/help, marshal status docs, `.claude/memory/` carriers, any UNSUPERVISED user-facing strings
- Follow-up: `.claude/memory/reference/fleet-landing-pass-liveness.md` (24.2)

## Verification

- `test_operator_liveness_instructions.py` or sibling gate green
- grep: UNSUPERVISED docs cite follow-up command
