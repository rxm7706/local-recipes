---
title: "83.23: Dispatch verification runs the cross-station meta-tests that read the story's station"
type: 'fix'
created: '2026-10-04'
status: 'in-progress'
baseline_revision: fead184902fc8554365dd1274b77b5e16865f248
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-2-every-station-s-dispatch-verification-runs-the-checks-that-read-the-whole-tree.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-12-dispatch-verification-runs-the-coverage-gate-of-every-station-the-story-touches.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-steward/tests/meta/test_no_station_assumes_local_recipes.py
  - src/shared/packages/pyforge-doctor/tests/meta/test_coverage_gate_stays_outside_every_station.py
  - src/shared/packages/pyforge-doctor/tests/meta/test_flag_gate_stays_outside_every_station.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a story can break another station's meta-test, the kind that reads every station's `src/`, and still land.

- **Seen on 2026-10-04:** atlas Story 27.3 landed `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/scan_submit.py`, which shelled `pixi run -e local-recipes env-inspect`. Main went red on steward's `tests/meta/test_no_station_assumes_local_recipes.py` (steward CAP-152), which reads every `src/shared/packages/pyforge-*/src/` (`_station_src_dirs`, :90-91). Hotfix #1840 (`bb3f979308`) fixed it.
- **Why dispatch passed it:** atlas's dispatch verification ran atlas's `verify_commands` plus the derived set in `dispatch_verify.py::_verify_commands_with_surface_guard` (:413-470): the surface guard, `lint-types`, `pyforge-core-test`, `deferred-work-check` (Story 83.2) and the touched stations' coverage gates (Story 83.12). None of these runs a steward test.
- **Why CI passed it:** 27.3's PR touched no steward path, so `.github/workflows/pyforge-station-tests.yml` never started `steward-test`.
- **The same exposure:** a measured sweep of every package's `tests/meta/` for a scan of all `pyforge-*` package trees found three tests outside pyforge-core:
  - steward `tests/meta/test_no_station_assumes_local_recipes.py`, which reads every `pyforge-*/src/`, pyforge-core and the testing kit included;
  - doctor `tests/meta/test_coverage_gate_stays_outside_every_station.py` (`_station_dirs` / `_station_source_files`, :124-141), which reads every station's `src/pyforge/<station>/`;
  - doctor `tests/meta/test_flag_gate_stays_outside_every_station.py` (:68-83), with the same scan.
  pyforge-core's own sole-ownership meta-tests also scan every station (`tests/meta/conftest.py::sibling_station_dirs`), but Story 83.2 already derives `pyforge-core-test`.

**Approach:**
- In `dispatch_verify.py`, beside the coverage-gate derivation, declare one constant naming each cross-station meta-test: its owning station's environment and its repo-relative test path. Seed it with the three files above.
- When `changed_files` contains any `src/shared/packages/pyforge-*/src/` path, append one command per owning station after the dedupe, in sorted order: `pixi run --frozen -e pyforge-<owner> python -m pytest -q <paths>`. That same `changed_files` gate already decides the coverage gates; widen its match to pyforge-core and the testing kit, because steward's test reads those trees too.
- Add these commands to the derived set that the 28.22 pre-existing reclassifier skips, as Story 83.2 did for its whole-tree checks. Their failures read the whole tree, so they must refuse.
- Add a test that every path in the constant exists, so a renamed or moved test fails loudly instead of running nothing.

Ledger key: `83-23-dispatch-verification-runs-the-cross-station-meta-tests-that-read-the-story-s-station`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 83.2 (dispatch verification runs the checks that read the whole tree), Story 83.12 (the touched stations' coverage gates) and Story 53.1 (the derived guard). This is a defect of shipped behaviour, so it mints no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given a story whose diff adds a `pixi run -e local-recipes` shell-out under `src/shared/packages/pyforge-atlas/src/` When its dispatch verifies Then steward's `test_no_station_assumes_local_recipes.py` runs, fails, and verification refuses (MRS-GATE-001 naming the command). A fixture replay of 27.3's `scan_submit.py` change pins it.
- Given a story whose diff adds a module named `coverage_gate.py` or `flag_gate.py` under any station's `src/pyforge/<station>/` When its dispatch verifies Then the matching doctor contract runs, fails and refuses
- Given a story that touches only planning artifacts or tests When its dispatch verifies Then no cross-station meta-test command is derived
- Given a story that touches `src/shared/packages/pyforge-core/src/` or `src/shared/packages/pyforge-testing-kit/src/` When its dispatch verifies Then steward's test is derived
- Given a station whose own `verify_commands` already lists one of these commands When its dispatch verifies Then the command runs once
- Given a failing cross-station meta-test whose output names only paths outside the story's blast radius When the 28.22 reclassifier runs Then the failure still refuses and never downgrades to MRS-GATE-014
- Given a path in the constant that does not exist When the marshal suite runs Then a test fails naming it
- Given the derivation removed, or the reclassifier exemption removed When the new tests run Then they fail (mutation)

## Boundaries & Constraints

**Always:**
- Derive at use time, in `_verify_commands_with_surface_guard`, the one place the derived commands are folded in.
- Run each test in its owning station's environment, because the doctor contracts import doctor-only fixtures.

**Never:**
- Never write these commands into any station's `marshal-policy.toml` `verify_commands`.
- Never run a station's whole suite in place of its cross-station meta-tests. A full `pyforge-steward-test` would cost minutes on every story.
- Never edit the steward or doctor tests in this story.
- Never change the CI trigger rules here. Widening `pyforge-station-tests.yml`'s path filters is CI work that needs its own story.

</intent-contract>

## Binding

- Parent: Story 83.2 and the 2026-10-04 atlas 27.3 main-red (#1840).
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (cross-station meta-tests) entry.
- Epic: Epic 83.
- Ledger key: `83-23-dispatch-verification-runs-the-cross-station-meta-tests-that-read-the-story-s-station`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Minted 2026-10-04 at the operator's request after hotfix #1840.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-steward python -m pytest -q src/shared/packages/pyforge-steward/tests/meta/test_no_station_assumes_local_recipes.py` and `pixi run --frozen -e pyforge-doctor python -m pytest -q src/shared/packages/pyforge-doctor/tests/meta/test_coverage_gate_stays_outside_every_station.py src/shared/packages/pyforge-doctor/tests/meta/test_flag_gate_stays_outside_every_station.py` — expected: pass on main. These are the derived commands, run by hand.

## Review Triage Log

- No review has run yet.
