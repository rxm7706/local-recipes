---
id: SPEC-pyforge-testing-charter
status: ready
owner-dream: docs/dreams/pyforge-testing-charter.md
surface:
  - _bmad/scripts/bmad_tea_playwright.py
  - docs/dashboard/generate.py
  - src/shared/packages/pyforge-testing-kit/**    # net-new, not yet created
companions:
  - station-tea-status.md
  - ../../../../../../docs/reference/test-charter.md    # adopted — the Guild's per-Smith mottos, testing hierarchy, and Phase 1-4 roadmap; not duplicated here
sources:
  - ../../../../../../docs/dreams/pyforge-testing-charter.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# PyForge Testing Charter — fleet-wide test architecture

## Why

A pain to solve, discovered while verifying it rather than assumed from the Dream: the Dream
claims herald and warden both have complete test architecture and that six other stations have
none. Neither is true. Every one of the 8 stations already has real pytest coverage at
`src/shared/packages/pyforge-<slug>/tests/` (herald 20, marshal 20, atlas 78, warden 54,
doctor 13, mason 8, steward 7, scribe 3 files — see `station-tea-status.md`), roughly tracking
each station's story completion. What is actually missing is narrower and more mechanical than
"build test architecture from scratch": six of eight stations' `planning-artifacts/test-architecture.md`
are boilerplate (created in the 2026-08-02 bulk commit later found to contain other fabricated
content — a false migration note, since removed), the automation script that should have produced
them for real (`bmad_tea_playwright.py`) has only ever been run or hand-adapted for two stations,
the dashboard's own completeness signal for this stage reads the wrong directory and so
under-reports every station's real coverage, no shared fixtures package exists despite Marshal
having already hand-rolled four reusable mocks, and no station's coverage is gated in CI. This
Spec closes those five gaps — it does not re-derive test architecture the fleet already has.

## Capabilities

- **CAP-1 — Correct fleet-wide TEA signal**
  - **intent:** An operator or the dashboard can tell, per station, whether real test coverage exists, without being misled by a planning-scaffold directory that only ever holds mocks and fixtures.
  - **success:** `generate.py`'s `tea` glob points at `src/shared/packages/pyforge-<slug>/tests/test_*.py` (the canonical location per `project-context.md`'s workspace-package convention), not `_bmad-output/projects/<slug>/tests/`; re-running `dashboard-gen` reports atlas and warden's `tea` stage as populated rather than pending.

- **CAP-2 — One automation path, run for real per station**
  - **intent:** `bmad_tea_playwright.py` is the single generator for a station's test-architecture document, and every station's document was actually produced by running it against that station's real epics and architecture, not hand-typed.
  - **success:** The script's output-filename convention (`test-architecture-tea.md`) is reconciled with the committed convention (`test-architecture.md`); running it against atlas, doctor, mason, scribe, steward, and warden's real epics-with-stories.md produces a document referencing actual story IDs and modules, replacing all six boilerplate stand-ins; a document still containing the literal token "TBD" after a run is a failed run, not a placeholder to fill in later.

- **CAP-3 — Shared test-support package (pyforge-testing-kit)**
  - **intent:** A station author does not hand-roll CLI runner fixtures, DB factories, or mocks another station already wrote.
  - **success:** A `pyforge-testing-kit` package exists under `src/shared/packages/` with CLI runner, web page-object, DB factory, and auth/HTTP/time mock primitives; Marshal's four already-real mocks (`mock_github_api.py`, `mock_worktree.py`, `mock_supervisor.py`, `mock_runner.py`) are evaluated as the seed rather than rewritten from scratch; at least one station other than the one it was seeded from imports from the shared kit instead of a local duplicate.

- **CAP-4 — Coverage gate enforced, not just measured**
  - **intent:** A PR cannot merge with unit coverage under 80% or integration coverage under 70% for the package it touches, matching the fleet's own stated targets.
  - **success:** Each station's existing `pyforge-<slug>-test` pixi task (or a new `-test-coverage` task) runs with `--cov` and a `--cov-fail-under` threshold; CI invokes it; a station under threshold fails the build naming the specific uncovered module, not a bare percentage.

- **CAP-5 — Test architecture stays current as stories land**
  - **intent:** Herald's and Marshal's existing real test-architecture documents do not freeze at today's snapshot while more stories ship.
  - **success:** Re-running `bmad_tea_playwright.py` (or its manual-equivalent process) against Marshal's epics after each epic completes regenerates the story-coverage table without hand-editing; a story that shipped without its test-architecture row updated is a detectable drift, not a silent gap.

## Constraints

- No manual re-work per station — `test-architecture.md` is machine-generated by `bmad_tea_playwright.py` from epics and architecture, never hand-typed; a hand-typed one is exactly the failure mode this Spec exists to close.
- One framework, not many — Playwright for CLI/web/integration, pytest for unit, already proven by Herald (20 real tests) and Marshal (20 real tests); no station introduces a second test framework.
- No fake passes — a generated document or scaffold that does not reflect real, runnable code is worse than an honestly-absent one, because it reads as done to both the dashboard and a future agent. A `test-architecture.md` containing the literal token "TBD" fails validation.

## Non-goals

- Retroactively writing missing unit or integration tests for every uncovered module across all 8 stations in one pass. This Spec fixes the signal (CAP-1), the generator (CAP-2), the shared primitives (CAP-3), and the gate (CAP-4); closing individual per-story coverage gaps remains each station's own story-level work.
- Building a new test framework or methodology. Playwright + pytest + BMAD TEA is already chosen and proven twice over (Herald, Marshal); this Spec scales the existing pattern, it does not replace it.
- Retroactively migrating Herald's or Marshal's already-real tests onto the shared `pyforge-testing-kit`. CAP-3 seeds the kit from Marshal's existing mocks for stations built from here forward; rewriting two stations' already-working test suites to consume it is not required.

## Success signal

`dashboard-gen`, after CAP-1's glob fix, reports atlas and warden's `tea` stage as populated,
not pending. All 8 stations' `planning-artifacts/test-architecture.md` was produced by
`bmad_tea_playwright.py` and contains zero "TBD" tokens. `pyforge-testing-kit` is importable
from at least one station's tests other than the one it was seeded from. A PR that drops a
touched package's coverage below its station's gate fails CI, naming the uncovered module.

## Assumptions

- Marshal's four existing mocks under `_bmad-output/projects/pyforge-marshal/tests/mocks/` are suitable as the `pyforge-testing-kit` seed based on their content (real, domain-specific: GitHub API, worktree, supervisor, runner) — not independently confirmed reusable by another station's author, since no second station has attempted to consume them yet.
- The boilerplate six stations' real story-proportional test counts (atlas 78 down to scribe 3) are assumed adequate as a baseline signal of "material coverage exists" for CAP-1's purposes; this Spec does not assert those counts meet the 80%/70% targets CAP-4 will gate on — that measurement happens when CAP-4 ships.
