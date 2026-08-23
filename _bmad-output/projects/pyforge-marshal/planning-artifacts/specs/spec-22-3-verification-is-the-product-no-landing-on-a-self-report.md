---
title: Verification is the product — no landing on a self-report
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: c23116e064
---

<intent-contract>

## Intent

**Problem:** Dispatched sessions can self-report shipped while gates fail or diff exceeds frozen surface — no independent verification before landing (FR-193 CAP-3; doctor-12.3 never-false-green trap).

**Approach:** Before any landing on a dispatched story, the driver runs the story's real verify commands via Epic 2 gate objects and reads diff against the story's frozen surface. Session self-report is input only, never the verdict (unevaluable ≠ pass). Failing gates or out-of-surface diff → loud non-landing verdict naming the failed gate. Deps: 22.1 done. Do not implement landing (22.4), overlap guard (22.5), or attach/resume (22.6).

## Acceptance Criteria

- Dispatched completion triggers independent verification via Epic 2 gate objects (not self-report).
- Diff read against story frozen surface; out-of-surface changes block landing with named verdict.
- Failing gates block landing with named failed gate (doctor-12.3 refusal fixture shape).
- Self-report alone never produces a landing verdict in any test path.
- Does not implement CAP-4..CAP-6 (Stories 22.4–22.6).

## Boundaries & Constraints

**Never:** Land on harness self-report. Never-false-green lattice (unevaluable ≠ pass). Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-marshal-single-story-dispatch/SPEC.md` (CAP-3)
- Composition over Epic 2 standalone gate objects; frozen-surface diff read
- `src/shared/packages/pyforge-marshal/` — dispatch verify path wired into supervisor/completion flow
- Tests: gate-fail refusal, out-of-surface diff refusal, doctor-12.3 canonical fixture

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Regression: self-reported shipped + failing gates → non-landing verdict

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/703
Merge: dc56f55e6b8c8958fe9a7953cace6a86b9760d9e
Merge policy: admin merge (`gh pr merge 703 --merge --admin --repo rxm7706/local-recipes`) — GitHub Actions billing blocks CI; local tests green before merge.
Summary: Story 22.3 (FR-193 CAP-3) wires independent Epic 2 gate verification into the dispatch supervisor before any landing: verify commands run in the dispatch worktree, frozen-surface scope check reads diff against policy seed, and session self-report is never the verdict. Doctor-12.3 refusal fixture regression-pinned (self-reported shipped + MRS-GATE-001 gate fail + MRS-GATE-007 out-of-surface).
Files:
- `core/dispatch_verification.py` — pure verification judge (self-report never verdict)
- `dispatch_verify.py` — impure gate runner (AD-9: outside cli for supervisor import)
- `dispatch_supervisor/__main__.py` — runs verification when session dead with git progress
- `cli/dispatch.py`, `cli/status.py`, `core/status.py` — verification verdict journal + fleet overlay
- `tests/unit/test_dispatch_verification.py` — doctor-12.3 fixture + self-report regression pins
Verification: `pixi run -e pyforge-marshal pyforge-marshal-test` — **6135 passed**, 12 deselected.
Out of scope (Stories 22.4–22.6): landing, overlap guard, attach/resume.
