---
title: The dispatch verb launches one governed, isolated story session
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 7d1e1e1a30
---

<intent-contract>

## Intent

**Problem:** The fastest story-landing pattern (one worktree-isolated `bmad-build-auto` per story) exists only as a hand ritual — no marshal verb provisions, launches, journals, or surfaces dispatched runs (FR-193 CAP-1, spec-marshal-single-story-dispatch).

**Approach:** Add a marshal factory subcommand (provisional name: `marshal factory dispatch`) that provisions a fresh isolated worktree, launches exactly one detached `bmad-build-auto` session with `BMAD_ACTIVE_PROJECT` per-invocation and physical artifact paths (never `scripts/bmad-switch`), journals the launch (AD-25/AD-28/AD-30), and surfaces the run in `marshal status` / fleet-picture. Harness goes through the FR-52 adapter seam (second engine), never scattered subprocess calls. Plain background agent only — never fork-style subagents. Deps: none. Do not implement completion detection (22.2), verification (22.3), landing (22.4), overlap guard (22.5), or attach/resume (22.6).

## Acceptance Criteria

- Dispatching a backlog story provisions a fresh isolated worktree and launches one detached `bmad-build-auto` session.
- `BMAD_ACTIVE_PROJECT` is passed per-invocation; artifact paths are physical (`_bmad-output/projects/<slug>/…`), never via `scripts/bmad-switch`.
- Launch is journaled with intent/outcome discipline; run appears in `marshal status` and fleet-picture.
- Launched session demonstrably receives policy-resolved model/budget parameters (or documents enforceable subset).
- Harness uses one adapter seam (FR-52 extended), not ad-hoc subprocess sprawl.
- Does not implement CAP-2..CAP-6 (Stories 22.2–22.6).

## Boundaries & Constraints

**Never:** Replace `marshal factory spin`/`resume` or bmad-loop. Never busy-wait in foreground. Never fork-style agent launch. Finalize marshal ledger only. Do not touch steward 17-2.

</intent-contract>

## Code Map

- Parent: `spec-marshal-single-story-dispatch/SPEC.md` (CAP-1)
- `src/shared/packages/pyforge-marshal/` — `cli/factory.py` (new subcommand), `core/`, FR-52 adapter seam
- Journal + status surfaces for dispatched runs
- Tests: launch provisions worktree, journals entry, status/fleet-picture visibility

## Verification

- Unit/integration tests for dispatch launch path (worktree provision, journal row, status output)
- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Manual smoke: dispatch records a run without blocking the caller

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/701
Merge: 94708563fd9d3d4fea867a67b6aac428506ff7a3
Merge policy: admin merge (`gh pr merge 701 --merge --admin --repo rxm7706/local-recipes`) — GitHub Actions billing blocks CI; local tests green before merge.
Summary: Added `marshal factory dispatch` (Story 22.1, FR-193 CAP-1): provisions an isolated worktree from `origin/main`, launches one detached `cursor agent` session via `BuildHarnessPort`/`BmadBuildHarness` with per-invocation `BMAD_ACTIVE_PROJECT` and physical artifact paths, journals `dispatch-launch` intent/outcome under Tier-3 `dispatch-runs/`, and surfaces live dispatch in `marshal status` / fleet-picture via dispatch overlay on `FleetHomeFacts`.
Files:
- `cli/dispatch.py`, `core/dispatch.py` — dispatch verb, path helpers, model/budget resolution
- `ports/build_harness.py`, `adapters/harness_bmadbuild.py` — FR-52 second engine seam
- `cli/spin.py`, `cli/status.py`, `core/status.py` — factory subcommand wiring + fleet overlay
- `core/findings.py`, `core/verdict.py`, `core/egress.py` — MRS-DISP-001..010, BuildHarnessPort registry
- `tests/unit/test_dispatch.py` — launch/journal/status unit coverage
Verification: `pixi run -e pyforge-marshal pyforge-marshal-test` — **6066 passed**, 12 deselected.
Out of scope (Stories 22.2–22.6): completion detection, verification gate, landing, overlap guard, attach/resume.
