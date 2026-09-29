---
title: Marshal gains the missing liveness primitive
type: feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: 4f978f3213b
---

<intent-contract>

## Intent

**Problem:** Operators and Marshal lack a supported way to answer "is run X's engine alive?" — hand-parsing `engine.pid` is silently wrong (pid + start-time float), and spec-3-7's deferred double-drive fix names the missing `HarnessPort` counterpart as its blocker (FR-195 CAP-1; spec-bmad-loop-liveness-footgun).

**Approach:** Add a Marshal-side liveness primitive that shells out to `bmad-loop status <run_id> --json` (the versioned public CLI) — never reads `engine.pid`, never imports `bmad_loop` internals. Returns honest tri-state: `alive` / `dead` / `unknown`. Primitive home is the story's design decision (`HarnessPort` method vs `scripts/*.py` helper vs `pyforge.doctor` source — pick one seam-consistent home). Update spec-3-7 deferred entry to cite the primitive as existing. Deps: none. Epic 23 done (#716/#717). Does not implement CAP-2/CAP-3 (Stories 24.2–24.3) or consume at resume preflight (spec-3-7's own deferred fix).

## Acceptance Criteria

- Given live, stopped, and absent/unreadable run dirs → returns `alive`, `dead`, `unknown` respectively.
- Zero reads of `engine.pid`; zero `bmad_loop` imports (assertable in tests / import-linter).
- `unknown` stays `unknown` — never coerced to alive/dead.
- On-demand only — not wired into `marshal status` fleet sweep (NFR-14).
- spec-3-7 deferred-work entry updated to name primitive as existing.

## Boundaries & Constraints

**HARD:** No in-place `bmad_loop` edits. No private-API dependency. **Never:** per-home probe in fleet sweep. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-bmad-loop-liveness-footgun/SPEC.md` (CAP-1)
- Surfaces: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py`, adapter, tests
- Deferred cite: `spec-3-7-escalation-deferral-and-resume.md` (live-engine double-drive entry)

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Unit tests: live/stopped/absent → alive/dead/unknown; no engine.pid read; no bmad_loop import

## Auto Run Result

Status: done
Reconciled 2026-09-20: `shipped` is the Spec-level word; a story's terminal state is `done` (ledger row `24-1-marshal-gains-the-missing-liveness-primitive: done`).
PR: https://github.com/rxm7706/local-recipes/pull/718 (admin merge — GitHub Actions billing blocker; local tests green: 6291 passed)
Merge SHA: `67ae6237a4d731da2ca4a039fdf9e647f9730e0e`
Implementation: `HarnessPort.engine_liveness` + `BmadLoopHarness.engine_liveness` via `bmad-loop status <run_id> --json` gate + `list --json` liveness-aware status mapping; spec-3-7 deferred entry updated.
Spec change: `list --json` carries `discover_runs`' engine liveness tri-state; `status --json` alone is run-state-only.

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `24-1-marshal-gains-the-missing-liveness-primitive: done`).
- Auto Run Result `Status: shipped` → `done` (see the reconcile line under it).
