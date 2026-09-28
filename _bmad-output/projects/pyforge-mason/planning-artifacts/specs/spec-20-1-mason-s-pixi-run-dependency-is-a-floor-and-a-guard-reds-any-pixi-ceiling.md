---
title: "20.1: Mason's pixi run-dependency is a floor, and a guard reds any pixi ceiling"
type: 'fix'
created: '2026-09-28'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - scripts/pixi_version_registry.py
  - scripts/pixi_version_check.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `src/shared/packages/pyforge-mason/pixi.toml` pins `pixi = ">=0.80.0,<0.81"` in `[package.run-dependencies]`,
the only pixi upper bound in the repo (the root `pixi.toml`'s three `pixi = ">=0.80.0"` pins are floors). It is mirrored
by `PIXI_VERSION_RANGE` in `engines/__init__.py` and held equal by `tests/meta/test_engine_version_range_sync.py`, which
also asserts the window (`len(PIXI_VERSION_RANGE) == 2`, `0.81.0 not in PIXI_VERSION_RANGE`). The ceiling holds every
environment that carries `pyforge-mason` (`pyforge-mason`, `pyforge-container`, `pyforge-foundry-full`,
`pyforge-foundry-full-stack`) at pixi 0.80.0 while the rest of the workspace resolves 0.81.0, and it broke Mason's
self-hosting build twice by lagging `requires-pixi` (2026-08-21, 2026-09-11). Nothing checks the rule:
`pixi-version-check` compares its registered sites with the `requires-pixi` floor, and this run-dep is not one of them.
The operator ruled on 2026-09-28: *"we should loosen pyforge-mason to be >=0.80.0 with no cap -- we don't need to cap
pixi in any station / environment"*.

**Approach:** the pin becomes `pixi = ">=0.80.0"`, its comment stating the ruling; `PIXI_VERSION_RANGE` becomes
`_floor("0.80.0")` (the now-unused `_minor_range` helper goes, its AD-1 guard note folded into `_floor`); the sync test
checks pixi as a floor like the other four. The pin is registered as a `floor` site in
`scripts/pixi_version_registry.py`, so it tracks `requires-pixi` and `bump-pixi-version` moves it (a re-added ceiling no
longer matches the site's pattern, a `hit-count-drift`). `scripts/pixi_version_check.py` gains a `pixi-upper-bound`
finding: it parses the root `pixi.toml` and every `src/shared/packages/*/pixi.toml` and `pyproject.toml` with `tomllib`,
walks every dependency table (conda, PyPI, host, build, run, every feature and target) and every PEP 508 list, plus
`requires-pixi`, and reports any pixi spec with a clause other than a floor (`>`, `>=`), an exclusion (`!=`) or `*`.
`tests/scripts/test_pixi_version_check.py` plants capped specs and sees the check exit 1. `pixi.lock` is re-solved with
`pixi lock` (no `pixi add` / `pixi update`); if pixi keeps 0.80.0 in the Mason environments, those environments' lock
blocks are evicted and re-solved (the repo's path-dependency remedy).

Ledger key: `20-1-mason-s-pixi-run-dependency-is-a-floor-and-a-guard-reds-any-pixi-ceiling`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-30 (FR-52); CAP-6 (engine provisioning, FR-40); AD-12.
- `spec-pixi-candidate-currency` (doctor) governs `pixi.lock`; `spec-pyforge-core` (marshal) co-governs every station's
  `src/`, including `engines/__init__.py`.

## Acceptance Criteria

- Given `src/shared/packages/pyforge-mason/pixi.toml` When it is read Then its `pixi` run-dependency is `>=0.80.0` with no upper bound
- Given `test_engine_version_range_sync.py` When it runs Then `PIXI_VERSION_RANGE` equals the pixi.toml floor and every engine range, pixi's included, is a single `>=` specifier with `0.81.0` inside it
- Given the tree When `pixi run -e pyforge-guild pixi-version-check` runs Then it exits 0, with Mason's run-dep checked as a registered floor site
- Given a pixi spec with an upper bound (`<`, `<=`, `==`, `~=`, a bare or wildcard pin) in a root feature, a package `pixi.toml` or a package `pyproject.toml` When the check runs Then it exits 1 with a `pixi-upper-bound` finding naming the file and the table
- Given a floor (`>=`, `>`), an exclusion (`!=`) or `*` When the check runs Then it reports nothing
- Given `pixi.lock` When it is read Then every environment that carries `pyforge-mason` resolves pixi 0.81.x, and the `pyforge-mason` source records depend on `pixi >=0.80.0`

## Boundaries & Constraints

**Always:**
- Read every verdict from the exit code, never through a pipe.
- Keep the check stdlib-only (`tomllib`, `re`): `tests/scripts/` runs in the dependency-free `pyforge-ci` environment.
- Reconcile the owner `spec-pyforge-mason` and every co-governor `spec-surface-check` names, then stamp each scoped with
  `--spec`. The co-governors of this surface are `spec-pyforge-core` (marshal; `engines/__init__.py`) and
  `spec-pixi-candidate-currency` (doctor) with `spec-platform-image-one-pixi-env` (steward) for `pixi.lock`; another
  station's memlog is written only if the detector names it.

**Never:**
- Do not change the root `pixi.toml` or regenerate `environment.yaml` (its pins are already floors).
- Do not run `pixi add` or `pixi update`.
- Do not touch conda-lock's upstream `virtualenv <21` cap, steward Story 72.1 or its planning files, or the CFE surface.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| floor | `pixi = ">=0.80.0"` | no finding | — |
| window | `pixi = ">=0.80.0,<0.81"` | `pixi-upper-bound` (`<0.81`) | exit 1 |
| exact / wildcard | `==0.80.0`, `0.80.0`, `0.80.*`, `~=0.80` | `pixi-upper-bound` | exit 1 |
| exclusion | `>=0.80.0,!=0.80.1` | no finding | — |
| inline table | `pixi = { version = "<0.81" }` | `pixi-upper-bound` | exit 1 |
| PEP 508 | `"pixi>=0.80,<0.81"` in `[project] dependencies` | `pixi-upper-bound` | exit 1 |
| look-alike | `pixi-build-python = "0.*"` | no finding (a different package) | — |
| unreadable manifest | invalid TOML | `manifest-unreadable` | exit 1 |
| re-capped Mason pin | `">=0.80.0,<0.81"` | the registry site no longer matches (`hit-count-drift`) as well | exit 1 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-30 (FR-52).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-28 — Proposed: no station or environment caps pixi*.
Ledger key: `20-1-mason-s-pixi-run-dependency-is-a-floor-and-a-guard-reds-any-pixi-ceiling`.
Ledger status at mint: `backlog`.
Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-guild pixi-version-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (`tests/scripts/test_pixi_version_check.py` plants capped specs and sees exit 1).
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.lock` changed).

**Manual checks:**
- Read `pixi.lock`: every environment that carries `pyforge-mason` resolves pixi 0.81.x.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate); the operator reviews the branch before
  landing it as `Merge pyforge-mason/20-1-mason-s-pixi-run-dependency-is-a-floor-and-a-guard-reds-any-pixi-ceiling into main`.

## Auto Run Result

Status: done (hand-driven, 2026-09-28; not a harness run).

**Summary:** Mason's pixi run-dependency is the floor `>=0.80.0`; `PIXI_VERSION_RANGE = _floor("0.80.0")` (the unused
`_minor_range` retired); the sync meta-test checks all five engine ranges as single `>=` floors. The pin is a registered
`floor` site of `scripts/pixi_version_registry.py` (21 sites). `scripts/pixi_version_check.py` gained the
`pixi-upper-bound` / `manifest-unreadable` pass over the root `pixi.toml` and every `src/shared/packages/*/pixi.toml` and
`pyproject.toml` (30 manifests); `tests/scripts/test_pixi_version_check.py` (31 tests) plants capped specs in a root
feature, a target table, a package `pixi.toml`, a package `pyproject.toml` (`[project] dependencies`,
`optional-dependencies`, `dependency-groups`) and `requires-pixi`, and reads exit 1; with the pass stubbed out, the two
planted-cap tests fail. `pixi.lock`: pixi 0.81.0 rehashed the path dependency on its own (`pyforge-mason` records now
depend on `pixi >=0.80.0`) but kept the still-satisfying locked pixi 0.80.0, so the 10 locked pixi 0.80.0 entries in the
four Mason environments' package lists were evicted and `pixi lock` re-solved them: only pixi moved (0.80.0 → 0.81.0 in
`pyforge-mason`, `pyforge-container`, `pyforge-foundry-full` on linux-64 / osx-arm64 / win-64 and
`pyforge-foundry-full-stack` on linux-64); `pixi lock --check` is clean. Root `pixi.toml` and `environment.yaml` unchanged.

**Healed in passing:** three `ship_pypi` tests in `tests/unit/test_package.py` asked live pypi.org (no `version_exists`
patch) and redded the touched-module coverage gate once; they now patch it like the rest of the file, and the whole mason
unit suite passes with every HTTP(S) proxy pointed at a dead port.

**Verification (exit codes):** `pyforge-mason-test` 0 (1589 + 12); `pyforge-mason-test-slow` 0 (3, on pixi 0.81.0);
`pyforge-mason-coverage-gate` 0; `pixi-version-check` 0; `pyforge-doctor-scripts-test` 0 (801); `pyforge-station-tests` 0;
`detectors-ci` 0; `lint-types` 0; `spec-surface-check`, `chain-completeness-check`, `dream-chain-check`,
`dreams-hygiene-check`, `story-status-check`, `ledger-regression-check`, `governance-currency`, `capability-ledger-check`
0; `chain_currency_sweep_check.py --project pyforge-mason` current; `mason_cfe_surface_check.py` clean (no CFE surface).

**Surface reconcile:** `spec-pyforge-mason` memlog names every governed path, scoped stamp. `spec-surface-check` named no
co-governor: `engines/__init__.py` (`spec-pyforge-core`) and `pixi.lock` (`spec-pixi-candidate-currency`,
`spec-platform-image-one-pixi-env`) are cleared by co-governor memlogs that have moved since their last stamps and already
name those paths, so no other station's memlog was written.
