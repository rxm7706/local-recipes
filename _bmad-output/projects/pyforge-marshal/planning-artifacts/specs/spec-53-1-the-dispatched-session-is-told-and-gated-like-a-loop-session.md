---
title: '53.1: The dispatched session is told and gated like a loop session'
type: 'feature'
created: '2026-09-20'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py'
  - '{project-root}/scripts/spec_surface_reconcile.py'
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-20 every dispatched session (doctor 26.1 and 29.1, steward 61.3 and 61.4, marshal 51.11 and 46.7) landed green and left `main` red on `spec-surface` until a human named the changed paths on the owning Spec's memlog and its co-governors. bmad-loop sessions never do this: `harness_bmadloop::render_policy_toml` appends `python scripts/spec_surface_reconcile.py` to every loop's verify commands (the S-13.7 guard, CAP-239), so a loop story cannot go green until the session reconciles. `marshal factory dispatch` has neither half — `dispatch_verify` runs only the station's `verify_commands`, and the `harness_bmadbuild` prompt says nothing about memlogs or about `location:` on deferrals (intake then refuses them by hand later).

**Approach:** the dispatch prompt states the obligation verbatim (name every governed path you change on the owning Spec's `.memlog.md` and on each co-governor `spec-surface` names; never `--write-baseline`; every `deferred:` entry cites a repo path in `location:`), and the S-13.7 guard is appended to the effective verify commands the session runs — at render, derived from the same constant the loop adapter uses, never declared per project — with `check_spec_binding` treating the derived guard as implicit so no pre-authored tracked spec changes.

## Boundaries & Constraints

**Always:**
- The guard is `python scripts/spec_surface_reconcile.py` — the one command the loop already uses (`harness_bmadloop._SURFACE_RECONCILE_COMMAND`); one constant, two adapters
- `check_spec_binding(declared, verify_commands)` returns `()` for every existing pre-authored spec unchanged — the derived guard is implicit, not a new declaration
- The loop adapter's rendered `policy.toml` is byte-identical after this story
- The prompt text is a tested constant (a test asserts the obligation, the co-governor rule, the `--write-baseline` prohibition and the `location:` rule are all present)

**Never:**
- Do not hand the session `--write-baseline` in any form (S-13.2: a producer that can stamp its own baseline launders drift)
- Do not add the guard to any station's `marshal-policy.toml` or to any tracked spec's `## Verification` (derive, don't declare)
- Do not change what the guard checks — `scripts/spec_surface_reconcile.py` is doctor's read-only verdict, untouched

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| session changes governed files and names them | memlog entries present for every changed path | verification passes | n/a |
| session changes governed files and names none | drift rows for its own paths | the guard fails the session's verification naming the paths; the session fixes it before HALT | n/a |
| session changes no governed file | nothing to name | the guard is silent (CAP-239: silence is not a finding) | n/a |
| pre-authored spec lists only station verify_commands | MRS-GATE-010 binding check | `()` — the derived guard is implicit | n/a |
| deferral without `location:` | the session writes one | the prompt's rule forbids it; the guard's output reports it when it still appears | reported, never silent |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-261` (a).
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py` (the prompt constant), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` and `cli/dispatch.py` (the derived guard appended to the effective verify commands), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py::check_spec_binding` (implicit derived guard), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` (the shared constant only; rendering unchanged), tests in `tests/unit/`.
Ledger key: `53-1-the-dispatched-session-is-told-and-gated-like-a-loop-session`.
Minted 2026-09-20 from `epics.md` so `marshal factory dispatch` can resolve this file; next marshal slot.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- Dispatch a story that changes a governed file and names nothing: the run's verification fails on the guard's verdict; dispatch one that names its paths: it lands with `spec-surface` green on `main`.
