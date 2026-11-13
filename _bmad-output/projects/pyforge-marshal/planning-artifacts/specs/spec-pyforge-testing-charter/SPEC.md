---
id: SPEC-pyforge-testing-charter
status: ready
owner-dream: archive/docs/dreams/pyforge-testing-charter.md
updated: 2026-11-12
surface:
  - _bmad/scripts/bmad_tea_playwright.py
  - scripts/fleet_scan.py    # the file doctor loads as pyforge.doctor.sources.fleet_scan (sources/board.py); re-pointed 2026-10-15
  - src/shared/packages/pyforge-testing-kit/**    # the shared testing kit every station's tests import: its source, its own suite and its package files (CAP-3, CAP-6, CAP-7)
  # scripts/coverage_gates_ci.py and scripts/run_station_coverage_gate.py (Story
  # 19.3/FR-131, added 2026-08-29) handed over 2026-09-24 (doctor Story 24.3) to
  # docs/governance/spec-coverage-gate-independence/, which now declares both
  # in its own surface: -- see this Spec's .memlog.md for the hand-over record.
companions:
  - station-tea-status.md
  - contract.md    # the testing kit's public contract (CAP-6)
  - ../../../../../../docs/reference/test-charter.md    # adopted — the Guild's per-Smith mottos, testing hierarchy, and Phase 1-4 roadmap; not duplicated here
sources:
  - ../../../../../../archive/docs/dreams/pyforge-testing-charter.md
open_questions: []
fold-exemption: cross-station-seam
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# PyForge Testing Charter — fleet-wide test architecture

## Why

A pain to solve, discovered while verifying it rather than assumed from the Dream: the Dream
claims herald and warden both have complete test architecture and that six other stations have
none. Neither is true. Every one of the 8 stations already has real pytest coverage at
`src/shared/packages/pyforge-<slug>/tests/` (measured at Spec authoring, 2026-08-02: herald 20, marshal 20,
atlas 78, warden 54, doctor 13, mason 8, steward 7, scribe 3 files — see `station-tea-status.md`,
whose live signal measures today), roughly tracking
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

- **CAP-1 — Correct fleet-wide TEA signal** (shipped 2026-08-02)
  - **intent:** An operator or the dashboard can tell, per station, whether real test coverage exists, without being misled by a planning-scaffold directory that only ever holds mocks and fixtures.
  - **success:** `scripts/fleet_scan.py`'s `tea` glob (`_stage_globs()`) points at `src/shared/packages/{slug}/tests/**/test_*.py` (the canonical location per the root `AGENTS.md`'s workspace-package conventions), not `_bmad-output/projects/<slug>/tests/`; `scan_fleet()` reports atlas and warden's `tea` stage as populated rather than pending.

- **CAP-2 — One automation path, run for real per station** (shipped 2026-08-23)
  - **intent:** `bmad_tea_playwright.py` is the single generator for a station's test-architecture document, and every station's document was actually produced by running it against that station's real epics and architecture, not hand-typed.
  - **success:** The script's output-filename convention (`test-architecture-tea.md`) is reconciled with the committed convention (`test-architecture.md`); running it against atlas, doctor, mason, scribe, steward, and warden's real epics-with-stories.md produces a document referencing actual story IDs and modules, replacing all six boilerplate stand-ins; a document still containing the literal token "TBD" after a run is a failed run, not a placeholder to fill in later.

- **CAP-3 — Shared test-support package (pyforge-testing-kit)** (shipped 2026-11-12)
  - **intent:** A station author does not hand-roll CLI runner fixtures, DB factories, or mocks another station already wrote.
  - **success:** A `pyforge-testing-kit` package exists under `src/shared/packages/` with five families — CLI runner, web page-object, DB factory and auth/HTTP/time mocks, seeded from Marshal's four already-real mocks (`mock_github_api.py`, `mock_worktree.py`, `mock_supervisor.py`, `mock_runner.py`) rather than rewritten from scratch, and the feature-flag fixture (`flags`, spec-feature-flag-governance:CAP-4) — plus `branch_diff_guard` and `cfe_surface`; its run-dependencies are `pyforge-core` and `openfeature-sdk` (the stdlib-leaf premise was retired 2026-09-30); all eight stations' tests import it instead of a local duplicate; its public surface is written in `contract.md` (CAP-6). The lane runs the package half and the live-tree half of the kit's suite (CAP-7; mechanism spec-pyforge-steward:CAP-175), `pyforge-testing-kit-test` stays the whole suite (`pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test` exits 0), and the kit's lane-wired meta-test (`tests/meta/test_testing_kit_lane_wired.py`) reds a wiring that drops a half.

- **CAP-4 — Coverage gate enforced, not just measured** (shipped 2026-08-23)
  - **intent:** A PR cannot merge with unit coverage under 80% or integration coverage under 70% for the package it touches, matching the fleet's own stated targets.
  - **success:** Each station's `pyforge-<slug>-test` pixi task runs its unit suite under `--cov`, and its `pyforge-<slug>-coverage-gate` task runs `scripts/coverage_gates_ci.py` over the modules a branch touches against that station's floor (fleet defaults unit 80%, integration 70%, in `docs/governance/coverage-thresholds.toml`); CI runs the same gate in that station's `pyforge-station-tests.yml` job; a station under threshold fails the build naming the specific uncovered module, not a bare percentage. The gate's scripts and thresholds are governed by `docs/governance/spec-coverage-gate-independence/` since 2026-09-24. The gate judges the eight stations: `pyforge-core` and the testing kit carry no floor (DW-marshal-118-2-1).

- **CAP-5 — Test architecture stays current as stories land** (shipped 2026-08-23)
  - **intent:** Herald's and Marshal's existing real test-architecture documents do not freeze at today's snapshot while more stories ship.
  - **success:** Re-running `bmad_tea_playwright.py` (or its manual-equivalent process) against Marshal's epics after each epic completes regenerates the story-coverage table without hand-editing; a story that shipped without its test-architecture row updated is a detectable drift, not a silent gap.

- **CAP-6 — the kit's public surface is written down, and its suite reds what it lacks** ← Dream entry 2026-11-10 (The shared floor says what it is: core and the testing kit before the cutover); decision D1 of the 2026-11-10 design pass (shipped 2026-11-12)
  - **intent:** A companion `contract.md` beside this Spec names every module of `pyforge.testing_kit`, every public name (the package's `__all__` and each submodule's), the pytest fixtures and markers it provides, its run-dependencies, its Python floor, and which members are bound to this estate (`cfe_surface`), so a second root can rebuild the kit that eight stations' tests import.
  - **success:** `pixi run --frozen -e pyforge-testing-kit pytest src/shared/packages/pyforge-testing-kit/tests/meta/test_public_contract.py -q` exits 0; that module (marked `live_tree`) exits 1 naming the item when the kit has a module or public name `contract.md` lacks, or `contract.md` names one the kit lacks, proven on synthetic input in the same module.

- **CAP-7 — the kit's own suite runs without the host** ← Dream entry 2026-11-10 (The shared floor says what it is: core and the testing kit before the cutover); decision D2 of the 2026-11-10 design pass; mechanism spec-pyforge-steward:CAP-175 (shipped 2026-11-12)
  - **intent:** The package half of the kit's suite imports no `django` and no `django_pyforge` and reads nothing outside the kit; the portal-and-CLI header contract, the lane wiring, the comparison with the platform flag tree and the contract check are the live-tree half, marked `pytest.mark.live_tree`. (How the lane runs the halves is CAP-3's.)
  - **success:** `pixi run --frozen -e pyforge-testing-kit pytest src/shared/packages/pyforge-testing-kit/tests -q -m "not live_tree" --strict-markers` exits 0 with no django-pyforge on `PYTHONPATH`, and again from a copy of the package alone with the working directory outside the repository; `-m live_tree` exits 0 on the repository with django-pyforge on the path; only live-tree modules name `django`; steward's trigger-map derivation finds no outside read in an unmarked kit module.

## Constraints

- No manual re-work per station — `test-architecture.md` is machine-generated by `bmad_tea_playwright.py` from epics and architecture, never hand-typed; a hand-typed one is exactly the failure mode this Spec exists to close.
- One framework, not many — Playwright for CLI/web/integration, pytest for unit, already proven by Herald and Marshal (20 real test files each at Spec authoring, 2026-08-02); no station introduces a second test framework.
- No fake passes — a generated document or scaffold that does not reflect real, runnable code is worse than an honestly-absent one, because it reads as done to both the dashboard and a future agent. A `test-architecture.md` containing the literal token "TBD" fails validation.

## Non-goals

- Retroactively writing missing unit or integration tests for every uncovered module across all 8 stations in one pass. This Spec fixes the signal (CAP-1), the generator (CAP-2), the shared primitives (CAP-3), and the gate (CAP-4); closing individual per-story coverage gaps remains each station's own story-level work.
- Building a new test framework or methodology. Playwright + pytest + BMAD TEA is already chosen and proven twice over (Herald, Marshal); this Spec scales the existing pattern, it does not replace it.
- Retroactively migrating Herald's or Marshal's already-real tests onto the shared `pyforge-testing-kit`. CAP-3 seeds the kit from Marshal's existing mocks for stations built from here forward; rewriting two stations' already-working test suites to consume it is not required.

## Success signal

`scan_fleet()` in `scripts/fleet_scan.py`, after CAP-1's glob fix, reports atlas and warden's
`tea` stage as populated, not pending. All 8 stations' `planning-artifacts/test-architecture.md` was produced by
`bmad_tea_playwright.py` and contains zero "TBD" tokens. `pyforge-testing-kit` is importable
from at least one station's tests other than the one it was seeded from. A PR that drops a
touched package's coverage below its station's gate fails CI, naming the uncovered module.

## Assumptions

- Marshal's four mocks (then under `_bmad-output/projects/pyforge-marshal/tests/mocks/`, archived 2026-08-02 to `archive/_bmad-output/projects/pyforge-marshal/tests/mocks/`) were taken as the `pyforge-testing-kit` seed on their content (real, domain-specific: GitHub API, worktree, supervisor, runner), before any second station had tried to consume them. It held: Story 19.2 seeded the kit from them (landed 2026-08-23), and all eight stations' tests import the kit.
- The boilerplate six stations' real story-proportional test counts (atlas 78 down to scribe 3 at Spec authoring, 2026-08-02) are assumed adequate as a baseline signal of "material coverage exists" for CAP-1's purposes; this Spec does not assert those counts meet the 80%/70% targets CAP-4 gates on — that measurement is CAP-4's gate, run on the modules each pull request touches.
