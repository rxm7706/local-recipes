---
title: '74.1: The testing kit runs a story in both flag states through one fixture'
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: '7151e3d2653a6289c4f01a4ac17f8514aee3247a'
flag-exempt: flag-infrastructure   # the rule's own test infrastructure (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-testing-kit/README.md
  - src/platform/tests/test_openfeature_file_flags.py
  - src/platform/config/flags.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-4: every flagged story is tested in both states, and its Verification
names such a test. `pyforge-testing-kit`, the test-support seam every station already imports (FR-130 / Story 19.2,
governed by `spec-pyforge-testing-charter`, `fold-exemption: cross-station-seam`), has four mock families and no flag
fixture. The only ON/OFF tests in the repository write two flagd trees by hand (`src/platform/tests/test_openfeature_file_flags.py`).
The intake's own pattern (mocking `waffle.flag_is_active`, injecting flags through `sessionStorage`) breaks canopy:AD-11:
one provider (OpenFeature), one tree, no egress, evaluated on the server.

**Approach:** a fifth family, `pyforge.testing_kit.flags`:
- a pytest fixture that installs OpenFeature's `InMemoryProvider` (`openfeature.provider.in_memory_provider`) with the
  test's flag values and restores the prior provider afterwards, so no provider state leaks between tests;
- `flag_states(key)`, an ON/OFF parametrize helper whose ids read `on` and `off`, so one decorated test runs twice;
- `flagd_tree(tmp_path, {key: variant})`, which writes a temporary flagd FILE tree in the shape of
  `src/platform/config/flags.json` (`flags` → key → `state`, `variants`, `defaultVariant`) for integration tests and for
  Playwright against a server started on it; it writes JSON only and imports no provider;
- a CLI helper for the OFF case the Spec's Q3 rules: the verb is still listed in `--help`, marked disabled, and refuses
  with the station's usage exit code; it builds on the kit's CLI-runner family and takes the station's usage code as an
  argument, so every station's OFF test is one call.
`openfeature-sdk` (conda-forge, as the platform features already resolve it) becomes the kit's one new dependency,
declared in `pyproject.toml`, the package `pixi.toml` and the root `pixi.toml` `[feature.pyforge-testing-kit.dependencies]`
(`environment.yaml` regenerated, `pixi.lock` re-solved). The README's family table gains the row.

Ledger key: `74-1-the-testing-kit-runs-a-story-in-both-flag-states-through-one-fixture`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-feature-flag-governance` CAP-4, the kit half (Guild-owned; Marshal's stories per the Spec's table). Its gate
  clause is doctor Story 34.5, minted `blocked` behind this story. No marshal CAP or FR (PRD § 31.11).
- `spec-pyforge-testing-charter` (the kit's governing Spec; FR-130's four families gain a fifth).
- Kinship: doctor Story 34.5; marshal Story 74.3 (the TEA mandate names this family).

## Acceptance Criteria

- Given a unit test decorated with `flag_states("pyforge.example.thing")` When the suite runs Then it runs twice, with ids `on` and `off`, and the key resolves ON then OFF through the OpenFeature client API
- Given two tests in sequence, the first setting the key ON When the second runs without the fixture Then the prior provider is back in place (no leak)
- Given `flagd_tree(tmp_path, {"pyforge.example.thing": "off"})` When the written file is loaded Then it has the tree's shape, the key's `defaultVariant` reads `off`, and its `variants` carry `on` and `off`
- Given a fixture CLI whose verb is listed in `--help` as disabled and exits with the given usage code When the CLI helper runs Then it passes; given a verb absent from `--help`, or one that exits 0, Then it fails
- Given the kit's module-level imports When `pyforge-deps-test` runs Then `openfeature-sdk` is declared in both `pyproject.toml` and the package `pixi.toml`
- Given the change When `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci pyforge-deps-test` run Then both pass

## Boundaries & Constraints

**Always:**
- Use OpenFeature's API and `InMemoryProvider` only; the tree shape is `src/platform/config/flags.json`'s.
- Keep the kit a test-support leaf: it imports no station and no `django_pyforge` at module level.
- Reconcile the kit's surface: `spec-pyforge-testing-charter` governs `src/shared/packages/pyforge-testing-kit/**` —
  append a `.memlog.md` entry naming each changed path (`uv run _bmad/scripts/memlog.py append --workspace
  _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter --type event --text
  "Surface reconcile …"`), `git add`, then a scoped stamp `python scripts/spec_surface_check.py --write-baseline --spec
  pyforge-marshal/spec-pyforge-testing-charter`, plus every co-governor the detector names.
- A `pixi.toml` change regenerates `environment.yaml` in the same change (`pixi project export conda-environment -e build
  > environment.yaml`).

**Never:**
- Do not add Waffle, LaunchDarkly, flagd as a daemon, or an environment variable as a flag source.
- Do not add a flag to the tree or change any station's code or tests.
- Do not run a live `pixi add` / `pixi update`; edit the manifests and re-solve the lock.
- Do not edit `SPEC.md` or `sprint-status-ledger.yaml`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| parametrized test | `flag_states(key)` | two runs, `on` and `off` | — |
| nested use | fixture inside a test that already set a provider | prior provider restored after | — |
| tree writer | `{key: "on"}` | a flags.json-shaped file | a non-dict mapping raises `ValueError` |
| CLI OFF, correct | listed-disabled, usage code | pass | — |
| CLI OFF, absent from help | verb missing | fail naming the verb | — |
| CLI OFF, exits 0 | refusal missing | fail naming the exit | — |

</intent-contract>

## Code Map

Kit root `K` = `src/shared/packages/pyforge-testing-kit`; modules `M` = `K/src/pyforge/testing_kit`.

- `M/cli_runner.py` -- the CLI-runner family (`MockRunner`, alias `CliRunner`); no real CLI invoker yet, so the OFF helper needs one here
- `M/branch_diff_guard.py:50-67` -- precedent: `import pytest` inside the function keeps the kit a stdlib leaf
- `M/__init__.py` -- family re-exports and sorted `__all__`; no test pins the family count
- `K/pyproject.toml`, `K/pixi.toml` -- `dependencies = []` and header comments say "stdlib leaf / zero third-party run-deps"; both change
- `K/README.md` -- family table (four rows) gains the fifth
- `K/tests/unit/test_families.py`, `K/tests/conftest.py` -- test style and the Django settings bootstrap; new tests sit beside them
- `pixi.toml:3044` `[feature.pyforge-testing-kit.dependencies]` -- root declaration site; `openfeature-sdk >=0.10.0` already pinned at `pixi.toml:242` and `:496`
- `src/platform/config/flags.json` -- read-only: the tree shape (`flags` → key → `state`, `variants`, `defaultVariant`)
- `src/platform/tests/test_openfeature_file_flags.py:73` -- read-only: the hand-written `_flagd_tree` this family replaces (no station test changes here)
- `tests/packaging/test_dependency_completeness.py:82,389,547` -- read-only: hard imports must map to a declared dist; `openfeature` → `openfeature-sdk` needs a `MODULE_ALIASES` entry, and this file is outside the Epic 74 surface, so kit imports of `openfeature` stay function-scoped (deferred)
- OpenFeature SDK 0.10.0 (read from the `platform-ci-test` env): `openfeature.api.set_provider_and_wait`, `api.get_client().provider` (the default-domain provider, public), `openfeature.provider.in_memory_provider.InMemoryProvider` / `InMemoryFlag(default_variant, variants)`; `set_provider` shuts the replaced provider down, so restore re-sets the prior one
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md` -- owning Spec's memlog for the surface reconcile

## Tasks & Acceptance

**Execution:**
- `M/cli_runner.py` -- add `CliResult` (frozen: `exit_code`, `output`) and `invoke_cli(main, argv)`: run `main(list(argv))`, capture stdout and stderr, take the exit code from the return value or `SystemExit` -- the invoker the OFF helper builds on
- `M/flags.py` (new) -- `installed_flags(values)` context manager (InMemoryProvider, prior default provider restored, `openfeature` imported inside), `make_flag_provider_fixture()` (pytest fixture `flag_provider`, `pytest` imported inside), `flag_states(key)`, `flagd_tree(tmp_path, flags)`, `assert_flag_off_verb(main, verb, usage_code)`
- `M/__init__.py` -- export the new names, docstring "five families"
- `K/pyproject.toml`, `K/pixi.toml` -- declare `openfeature-sdk>=0.10.0` / `">=0.10.0"` in `[project] dependencies` and `[package.run-dependencies]`; fix the leaf comments
- `pixi.toml` -- add `openfeature-sdk = ">=0.10.0"` to `[feature.pyforge-testing-kit.dependencies]`; re-solve `pixi.lock` (`pixi lock`), regenerate `environment.yaml`
- `K/README.md` -- family table row for `pyforge.testing_kit.flags`
- `K/tests/unit/test_flags.py` (new) -- unit-test every I/O Matrix row and the four kit ACs below
- `spec-pyforge-testing-charter/.memlog.md` and each co-governor `spec_surface_reconcile.py` names -- one `Surface reconcile` entry naming every changed governed path; never `--write-baseline` in this run

**Acceptance Criteria:**
- Given the kit gains `openfeature-sdk`, when `pixi run --frozen -e pyforge-ci pyforge-deps-test` runs, then pyproject and package pixi.toml agree on the pin and the gate passes
- Given the changed paths, when `python scripts/spec_surface_reconcile.py` runs, then it exits 0 with every governed path named on its Spec's `.memlog.md`

## Spec Change Log

- 2026-09-30 -- operator ruling, unblocked (contract widened; recorded on `spec-feature-flag-governance`, `spec-pyforge-core` and `epics.md` Story 74.1, PR `unblock-wave1-2026-09-30` on `origin/main`): **migrate, as the leaf pin's own docstring prescribes -- do not retarget or loosen the pin.** Q-26's stdlib-leaf premise retires.
  - The kit declares its real runtime dependencies: `openfeature-sdk>=0.10.0` (already added) and `pyforge-core` (the kit's pyproject, its package `pixi.toml`, and the root `pixi.toml` feature, then `pixi lock`; regenerate `environment.yaml`). pyforge-core does not depend on the kit, so there is no cycle.
  - `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py`: move its nine `subprocess` `run`/`check_output` version-control call sites onto `pyforge.core.process.PosixProcess.run` (behaviour unchanged; its own tests stay green).
  - `src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py` (now inside `[epic_surfaces]` `"74"` on `origin/main`): remove `branch_diff_guard.py` from `_EXEMPT_RELATIVE_PATHS`, delete `test_branch_diff_guard_is_excluded_from_the_scan`, `test_branch_diff_guard_would_fire_if_it_were_not_excluded` and `test_branch_diff_guard_exemption_rests_on_the_kits_leaf_declaration`, and add one test that the file is scanned and has no violations.
  - Reconcile `spec-pyforge-core` (governs that test) and `spec-pyforge-testing-charter` (governs the kit): memlog first naming each path, then their scoped stamps at landing.
  - First bring `origin/main` into this branch (merge, never rebase) so the widened policy and the rulings are present. Then the Verification commands, `pixi run -e pyforge-guild pyforge-station-tests` (every leg, pyforge-core included) and `pyforge-testing-kit-test` must exit 0. The flags work already done is kept, not redone.
- 2026-09-29 (implementation, no change to the contract): the mandated `dependencies = ["openfeature-sdk>=0.10.0"]` reds one
  test outside this story's surface, `pyforge-core`'s
  `tests/meta/test_process_sole_ownership.py::test_branch_diff_guard_exemption_rests_on_the_kits_leaf_declaration`
  (line 368, `assert ['openfeature-sdk>=0.10.0'] == []`), which pins the kit's `[project] dependencies` to `[]`. The pin
  stands in for the Q-26 premise behind `branch_diff_guard.py`'s sanctioned `subprocess` opt-out, that the kit does not depend on
  `pyforge-core`; that premise still holds. Left alone because `marshal-policy.toml` `[epic_surfaces]` `"74"` does not admit
  it (MRS-GATE-007). `pyforge-core-test` and the core leg of `pyforge-station-tests` stay red until it changes: widen the
  entry to that one file, then have the test assert no `pyforge-core` dependency instead of an empty list. Also in the
  charter Spec's `.memlog.md` (the 2026-09-29 Surface reconcile entry).

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-4 and the Q3 ruling (memlog 23), the
Dream's *What the intake gets right, and what does not transfer*, and `spec-pyforge-testing-charter` (the kit), decomposed
2026-09-28 (night) as Epic 74's mint.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-4 (Guild-owned; the kit half is
Marshal's).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `74-1-the-testing-kit-runs-a-story-in-both-flag-states-through-one-fixture`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"74"` admits the testing kit, the testing-charter memlog and the
`_bmad/custom/` overrides beside the default surface.

## Design Notes

- One fixture: `flag_provider` reads `request.param` (a `{key: bool}` mapping, empty when unparametrized). `flag_states(key)` returns a decorator that parametrizes `flag_provider` indirectly with ids `on` / `off` and adds `usefixtures("flag_provider")`, so a test needs no argument to be run twice. A station binds the fixture with `flag_provider = make_flag_provider_fixture()` in its `conftest.py`; the factory is what keeps `pytest` out of the kit's module-level imports.
- `openfeature` is imported inside `installed_flags`, not at module level: a module-level import makes `pyforge-deps-test` require a `MODULE_ALIASES` entry in `tests/packaging/`, outside the Epic 74 surface. The dependency is still declared in both manifests (AC 5), so the gate's parity checks bind it.
- A dispatch run may not stamp its own baseline. This run reconciles through the memlogs only; the scoped `--write-baseline` clause in *Boundaries* is the landing step, not this run's.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- `pixi run -e pyforge-testing-kit pyforge-testing-kit-test` — expected: pass (the kit's own suite, both states).
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (a `pixi.toml` / `pixi.lock` change fires every station suite in CI).
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamp.

## Review Triage Log

## Auto Run Result

Status: blocked
Blocking condition: implementation verification failed. The spec's manual check `pixi run -e pyforge-guild pyforge-station-tests` (expected: pass) cannot pass. Its `pyforge-core` leg fails on `src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py::test_branch_diff_guard_exemption_rests_on_the_kits_leaf_declaration` (`assert ['openfeature-sdk>=0.10.0'] == []`). The story's own contract causes the failure: the intent contract requires `openfeature-sdk` in the kit's `[project] dependencies`, and that test pins the list to `[]`. The fix is a one-file edit to a test outside this story's writable surface, and no change inside the surface can clear it.

Evidence, re-run by the reviewing session against this worktree's manifest (`--manifest-path`, `--frozen`), exit codes read directly:
- `pyforge-marshal-test` (`-e pyforge-marshal`): exit 0, 8905 passed.
- `pyforge-deps-test` (`-e pyforge-ci`): exit 0, 130 passed, 3 skipped.
- `pyforge-testing-kit-test` (`-e pyforge-testing-kit`): exit 0, 60 passed (32 of them the new `test_flags.py`).
- `python scripts/spec_surface_reconcile.py`: exit 0, "every tracked file governed or allowlisted; no drift".
- `src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py`: exit 1, 1 failed and 316 passed. The one failure is the test named above. The implementation subagent saw the same result in the full `pyforge-core` suite (1 failed, 1988 passed).
- Not run: the full `pyforge-station-tests` and the other stations' suites, because their environments are not built in this worktree. Stations do not import the new module.

Why it is not fixed here: `marshal-policy.toml` `[epic_surfaces]` `"74"` does not admit `src/shared/packages/pyforge-core/**`, so editing that test would draw an MRS-GATE-007 scope violation at landing. Widening the surface from inside the run that needs it would launder its own scope check. The test's docstring already names the sanctioned resolution: when the kit's declaration changes, loosen the pin in the same change. The premise behind the pin, that the kit does not depend on `pyforge-core`, still holds.

Operator decision to unblock: widen the `"74"` entry to that one file (and reconcile `spec-pyforge-core`, which governs it), then change the test to assert "no `pyforge-core` dependency in the kit's `[project] dependencies`" instead of an empty list. Then re-dispatch this story; the kit implementation below is complete and does not need redoing.

What is done (kit root `src/shared/packages/pyforge-testing-kit`):
- `src/pyforge/testing_kit/flags.py` (new): `installed_flags`, `make_flag_provider_fixture`, `flag_states`, `flagd_tree`, `assert_flag_off_verb`; `openfeature` and `pytest` are imported inside the functions.
- `src/pyforge/testing_kit/cli_runner.py`: `CliResult` and `invoke_cli`, the in-process CLI invoker the OFF helper builds on.
- `src/pyforge/testing_kit/__init__.py`, `README.md`, `pyproject.toml`, `pixi.toml`, `tests/unit/test_flags.py` (new).
- Root `pixi.toml` gains `openfeature-sdk = ">=0.10.0"`; `pixi.lock` re-solved (only `openfeature-sdk` and the kit's own entries moved); `environment.yaml` regenerated byte-identical, so unchanged.
- `spec-pyforge-testing-charter/.memlog.md` carries the `Surface reconcile 2026-09-29` entry naming every changed governed path and the known conflict above. No `--write-baseline` was run; the scoped stamp is the landing step.

Review (step 4) did not run: verification blocks first, and a review cannot cure an out-of-surface failure.
