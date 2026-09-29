---
title: The operator answer is one documented command
type: docs+feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: 6e2d536f3f
---

<intent-contract>

## Intent

**Problem:** Tracked operator instructions still prescribe hand-parsed `engine.pid`, `ps -p $(cat engine.pid)`, or bare `grep 'bmad-loop run'` — missing `resume`/`resolve` argv forms (2026-08-14 mason incident). The supported answer exists but isn't the primary documented path (FR-195 CAP-2; spec-bmad-loop-liveness-footgun).

**Approach:** Update fleet landing-pass liveness step and its team/auto-memory carriers so the supported one-command check is primary: `bmad-loop status <run_id> --json` (and/or thin marshal wrapper if one-front-door warrants it — cheap once CAP-1 exists). Any surviving corroboration `ps`/`grep` must match all three engine argv forms: `bmad-loop (run|resume|resolve)`. Remove/replace prescriptions of `cat engine.pid` / `ps -p $(cat engine.pid)` / bare `grep 'bmad-loop run'`. Deps: 24.1 done (#718, `HarnessPort.engine_liveness`). Does not implement CAP-3 (Story 24.3) or resume preflight consumption (spec-3-7 deferred).

## Acceptance Criteria

- No tracked operator instruction prescribes `cat engine.pid`, `ps -p $(cat engine.pid)`, or bare `grep 'bmad-loop run'` as the liveness answer.
- Supported one-command check is the primary prescribed answer in landing-pass protocol + carriers.
- Any surviving corroboration grep matches `bmad-loop (run|resume|resolve)`.
- 2026-08-14 mason scenario (engine live under `bmad-loop resume`) resolves correctly by documented steps alone.
- Meta/drift test or grep gate optional but preferred if repo pattern exists.

## Boundaries & Constraints

**Never:** Re-mint CAP-1 primitive. Never wire liveness into fleet sweep. Finalize marshal ledger only. **maintenance label** on PR (docs/.claude/_bmad-output outside recipes/).

</intent-contract>

## Code Map

- Parent: `spec-bmad-loop-liveness-footgun/SPEC.md` (CAP-2)
- Surfaces: fleet landing-pass protocol docs, `.claude/memory/` carriers, operator runbooks (grep for `engine.pid`, `grep 'bmad-loop run'`)
- Primitive: `HarnessPort.engine_liveness` (24.1) — reference, don't reimplement

## Verification

- `git grep` / drift: no bad prescriptions in tracked operator paths
- Manual: mason resume scenario steps documented correctly

## Auto Run Result

Status: done
Reconciled 2026-09-20: `shipped` is the Spec-level word; a story's terminal state is `done` (ledger row `24-2-the-operator-answer-is-one-documented-command: done`).
PR: https://github.com/rxm7706/local-recipes/pull/719 (admin merge — GitHub Actions billing blocker; local tests green: meta 6 passed, pyforge-marshal 6291 passed)
Merge SHA: `6e2d536f3ffced7a82b5249305cd37eccc3030d9`
Implementation: `.claude/memory/reference/fleet-landing-pass-liveness.md` (STEP 2 primary check); team-memory carrier updates; `test_operator_liveness_instructions.py` meta gate.
Finalize SHA: `ff1c82c5fa5deed3d06c5045306f19a86c25e40d`

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `24-2-the-operator-answer-is-one-documented-command: done`).
- Auto Run Result `Status: shipped` → `done` (see the reconcile line under it).
