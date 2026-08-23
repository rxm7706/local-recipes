---
title: The shared test-support kit
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: 98cc782aa485a2f52a35bf2ac9ee7098ec2db173
deferred:
  - summary: >-
      Seeded mock edge-case hardening (recreate-after-delete, negative clock
      advance, journal reload from disk) remains identical to archive seeds.
    evidence: |-
      Edge-case hunter listed lifecycle/input guards that the archived Marshal
      mocks also lack; Story 19.2 seeds without rewriting those behaviors.
    location: >-
      src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/
    severity: low
  - summary: >-
      docs/reference/library-llms-full.md still reports broad pin/undocumented-dep
      drift beyond the new pyforge-testing-kit env row.
    evidence: |-
      llms-full-check reports dozens of pre-existing undocumented deps and pin
      mismatches; this story only added the testing-kit env row.
    location: >-
      docs/reference/library-llms-full.md
    severity: low
---

<intent-contract>

## Intent

**Problem:** Marshal's CLI-runner / page-object / DB-factory / auth-HTTP-time mocks are station-local; other stations reimplement them (FR-130). Q-26 (own leaf vs pyforge-core module) must be decided here.

**Approach:** Ship Marshal's four real mocks as a shared kit (`pyforge-testing-kit` or `pyforge.core.testing`), seeded not rewritten, and have at least one other station import from it. Record the Q-26 leaf-vs-core decision in a dated Spec Change Log entry.

## Acceptance Criteria

- Shared kit exposes Marshal's four mock families (CLI-runner, page-object, DB-factory, auth-HTTP-time), seeded from existing Marshal tests.
- At least one other station imports from the kit (not a copy).
- Q-26 decided with a dated Spec Change Log entry (own leaf vs `pyforge.core.testing`).
- Fixture-covered; does not implement 19.3 coverage gates.

## Boundaries & Constraints

**Never:** Rewrite mocks from scratch when seeding is possible. Never implement 19.3/19.4. Never `scripts/bmad-switch`. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Own-leaf package: `src/shared/packages/pyforge-testing-kit` (`pyforge.testing_kit`) — Q-26 decided (see Spec Change Log)
- Four family modules: `cli_runner`, `page_object`, `db_factory`, `auth_http_time`
- Marshal re-export: `tests/support/testing_kit.py`
- Consumer: `pyforge-doctor` `tests/unit/test_testing_kit_import.py`
- Spec Change Log for Q-26

## Verification

- Kit importable; second-station import test green
- `pixi run --frozen -e pyforge-marshal` (+ consumer station env) relevant tests green
- CI: detectors, linter, package tests

## Spec Change Log

### 2026-08-23 — Q-26 decision: own leaf `pyforge-testing-kit`

**Decision:** ship as own leaf package `pyforge-testing-kit` (`pyforge.testing_kit`), **not** as `pyforge.core.testing`.

**Rationale:**
- Charter CAP-3 / FR-130 / SPEC surface already name `pyforge-testing-kit` under `src/shared/packages/`.
- `pyforge-core` is the pure-stdlib *runtime* leaf every station depends on; folding test-only fixtures into it would couple test helpers into every station's runtime install (the open risk named in `spec-pyforge-core` Q2).
- Own leaf keeps the leaf constraint honest: core stays runtime primitives; the kit stays test-time-only and is an optional feature-level path dep for consuming stations (doctor + marshal), never a package run-dep.

**Seed mapping (not rewritten):**
| Family | Module | Seed |
|--------|--------|------|
| CLI-runner | `cli_runner` | `mock_runner.py` |
| page-object | `page_object` | `mock_worktree.py` |
| DB-factory | `db_factory` | `mock_supervisor.py` + LoopHome/RunJournal from archived conftest |
| auth/HTTP/time | `auth_http_time` | `mock_github_api.py` + supervisor timing as `FrozenClock` |

**Consumer:** `pyforge-doctor` tests import the kit (`tests/unit/test_testing_kit_import.py`). Marshal re-exports via `tests/support/testing_kit.py`.

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 2: (high 0, medium 0, low 2)
- reject: 20+
- addressed_findings:
  - `[medium]` `[patch]` Marshal support re-export was AST-only — replaced with live `importlib` load + identity asserts against `pyforge.testing_kit`
  - `[low]` `[patch]` Code Map outside intent-contract updated to the decided own-leaf surface
  - `[low]` `[patch]` Added `py.typed` and a `library-llms-full.md` env row for the new lean kit env

## Auto Run Result

Status: done

Summary: Shipped own-leaf `pyforge-testing-kit` (`pyforge.testing_kit`) with four seeded mock families; doctor imports the kit; Marshal re-exports via `tests/support/testing_kit.py`; Q-26 recorded in Spec Change Log.

Files changed:
- `src/shared/packages/pyforge-testing-kit/` — new leaf package (four families + tests)
- `pixi.toml` / `pixi.lock` — feature env + marshal/doctor path deps
- `pyforge-doctor/.../test_testing_kit_import.py` — second-station consumer
- `pyforge-marshal/tests/support/testing_kit.py` + re-export tests — seed-station shim
- `docs/reference/library-llms-full.md` — kit env catalog row
- story spec — Code Map, Spec Change Log, review/finalize

Review findings: 3 patches applied; 2 deferred; remaining edge-case/hardening and intent-contract wording findings rejected (seed fidelity / out of AC / parent finalize owns ledger).

Follow-up review recommendation: true (patched medium=1, low=2 → score 5).

Verification:
- `pixi run -e pyforge-testing-kit pyforge-testing-kit-test` — 8 passed
- `pixi run -e pyforge-doctor pytest …/test_testing_kit_import.py -q` — 2 passed
- `pixi run -e pyforge-marshal pytest …/test_testing_kit_reexport.py -q` — 3 passed
- `pixi project export conda-environment -e build` vs `environment.yaml` — identical (no commit)

Residual risks: Marshal's pre-existing tests do not yet migrate onto the shim (AC only requires kit + one importer); seeded edge-case gaps preserved intentionally.
