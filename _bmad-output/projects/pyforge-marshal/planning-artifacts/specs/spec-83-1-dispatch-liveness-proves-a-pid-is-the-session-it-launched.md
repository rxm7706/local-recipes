---
title: '83.1: Dispatch liveness proves a pid is the session it launched'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `cli/dispatch.py::_live_dispatch_story_keys` walks every dispatch run and counts one LIVE when `resolve_dispatch_session_verdict` finds its recorded session pid alive, through `pyforge.core.process.PosixProcess.is_alive`, a bare `kill(pid, 0)`. That call succeeds for any process or thread that now holds the number. On 2026-10-02 two 2026-08-31 runs of done Story 28.4 had no completion entry; pid allocation had wrapped (`pid_max` 4194304), and their session pids 600353 and 600354 were Firefox thread ids, so the campaign reported `wave in flight: 28.4` and dispatched nothing until the two run directories were moved aside.

**Approach:** `PosixProcess.is_alive` answers for a process, as its docstring promises: a number that names a thread but not a thread-group leader is not alive. The dispatch verdict also proves identity: a session whose process started more than a bounded tolerance after the run's journaled launch is not that run's session. The start time comes from a ProcessPort read; a host that cannot answer degrades to today's behaviour.

Ledger key: `83-1-dispatch-liveness-proves-a-pid-is-the-session-it-launched`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- Story 28.16 (the live dispatch story keys a wave reads) and `spec-pyforge-core`'s ProcessPort. A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a run with no completion entry whose session pid names another process's thread When its liveness is judged Then it is not live
- Given a run whose session pid names a process that started well after the run's journaled launch When its liveness is judged Then it is not live
- Given the session a dispatch launched, still running When its liveness is judged Then it is live
- Given either check removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where the shipped behaviour lives, and pin it with a test that fails without the fix.

**Never:** Do not kill, signal or rename any process. Do not change how a completed or terminal run is judged.

</intent-contract>

## Binding

Parent: Story 28.16 (the live dispatch story keys a wave reads) and `spec-pyforge-core`'s ProcessPort.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 (night) entry.
Ledger key: `83-1-dispatch-liveness-proves-a-pid-is-the-session-it-launched`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 at the operator's request to chain the defects found landing Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks:**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (the ProcessPort change; not in marshal's
  `verify_commands`, so run it by hand until Story 83.2 folds it into every station's verification).

## Review Triage Log

- No review has run yet.
