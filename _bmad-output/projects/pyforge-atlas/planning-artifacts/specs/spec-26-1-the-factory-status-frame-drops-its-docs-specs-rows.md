---
title: "26.1: The factory-status frame drops its docs/specs rows"
type: 'chore'
created: '2026-09-29'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/factory_status.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
  - src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_factory_status.py
  - src/shared/packages/pyforge-atlas/tests/integration/dashboard/conftest.py
  - src/shared/packages/pyforge-atlas/tests/integration/dashboard/test_dashboard_dryrun.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-one-chain-per-station:CAP-11` (operator ruling 2026-09-29) retires the legacy intake-spec tier:
`docs/specs/` empties and goes in doctor Story 37.1. Atlas's factory-status frame (`dashboard/factory_status.py`) reads
it: `read_spec_statuses` globs `docs/specs/*.md` and emits one `source="docs/specs"` row per file, and the page text in
`dashboard/app.py` (~line 519) names `docs/specs/*.md`. An empty directory is a silent no-op. However,
`tests/integration/dashboard/test_dashboard_dryrun.py` (~line 297) asserts `(frame["source"] == "docs/specs").sum() >= 1`,
so it fails on any local checkout once the directory empties. It is skipped on a fresh clone and in CI, where the
gitignored `sprint-status.yaml` is missing. CHAIN-STANDARD §11 requires every reader to follow before the PR that empties
the directory.

**Approach:** remove the `docs/specs` source from the frame: `read_spec_statuses`, the `specs_dir` default and parameter,
and the rows. The page text stops naming `docs/specs/*.md`. Tests that inject a `specs_dir` or build a temporary
`docs/specs` drop it. The dry-run assertion becomes "no `docs/specs` row", which holds before and after the directory
empties. Everything else in the frame is unchanged.

Ledger key: `26-1-the-factory-status-frame-drops-its-docs-specs-rows`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-one-chain-per-station:CAP-11` (the Guild's; Atlas mints no CAP and no FR, the relay shape doctor's Epics 24, 25,
  32, 34 and 36 use); CHAIN-STANDARD §11.
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.
- Siblings: doctor Story 37.1 (the move; blocked on this story), steward Story 77.1, herald Story 34.1, marshal Story 76.1.

## Acceptance Criteria

- Given today's tree When the factory-status frame is built Then it has the build-stamp row, the `sprint-status.yaml` rows
  and the `epics.md` row, and no `docs/specs` row
- Given `build_factory_status_frame` When it is called Then it takes no `specs_dir` argument
- Given the factory-status page When it renders Then its text names no `docs/specs/` path
- Given `test_dashboard_dryrun.py` When it runs with `docs/specs/` present or absent Then it passes
- Given the atlas suite When `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check` run
  Then both exit 0

## Tasks

1. Read `dashboard/factory_status.py`, `dashboard/app.py` and the three test files.
2. Remove `read_spec_statuses`, the `specs_dir` default and parameter, and the `docs/specs` rows; update the page text and
   the module docstring.
3. Update the unit tests and the integration conftest that build a temporary `docs/specs`, and change the dry-run
   assertion to "no `docs/specs` row".
4. Run `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check`, and read each exit code.
5. Reconcile every Spec `spec-surface-check` names for the edited files: memlog first, `git add`, then a scoped
   `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Keep the frame's other rows and its column order unchanged.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not move or edit anything under `docs/specs/` in this story.
- Do not add a catalog dataset.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| today's tree | five files in `docs/specs/` | no `docs/specs` row | — |
| after the move | `docs/specs/` absent | no `docs/specs` row; the page renders | — |
| no sprint feed | fresh clone or CI | the dry-run test skips as before | — |

</intent-contract>

## Binding

Parent capability: `spec-one-chain-per-station:CAP-11` (Guild relay; no atlas CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `26-1-the-factory-status-frame-drops-its-docs-specs-rows`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
