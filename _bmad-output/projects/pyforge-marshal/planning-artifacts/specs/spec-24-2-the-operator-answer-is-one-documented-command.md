---
title: The operator answer is one documented command
type: docs+feature
created: '2026-08-24'
status: ready
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: ae09a259fa
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
