---
title: An UNSUPERVISED row has a cheap documented double-check
type: docs+feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: 39cee7530c
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

## Auto Run Result

Status: done
Reconciled 2026-09-20: `shipped` is the Spec-level word; a story's terminal state is `done` (ledger row `24-3-an-unsupervised-row-has-a-cheap-documented-double-check: done`).
PR: https://github.com/rxm7706/local-recipes/pull/720 (admin merge — GitHub Actions billing blocker; local tests green: meta 13 passed)
Merge SHA: `39cee7530c16ac3d17aeb031e726c4a877097e4b`
Implementation: CAP-3 UNSUPERVISED section in `fleet-landing-pass-liveness.md`; fleet-picture ATTENTION split for unsupervised vs stopped; `marshal status --help` cites follow-up; 3 new meta tests in `test_operator_liveness_instructions.py`. `derive_home_state` unchanged.
Completes Epic 24 (FR-195 CAP-1/CAP-2/CAP-3 all shipped via Stories 24.1–24.3).
Finalize SHA: `122b1299a3b16ae5f7daadc013d66440ab92706e`

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `24-3-an-unsupervised-row-has-a-cheap-documented-double-check: done`).
- Auto Run Result `Status: shipped` → `done` (see the reconcile line under it).
