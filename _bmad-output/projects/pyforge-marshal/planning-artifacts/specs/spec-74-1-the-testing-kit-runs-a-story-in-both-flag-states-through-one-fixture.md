---
title: '74.1: The testing kit runs a story in both flag states through one fixture'
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: '7151e3d2653a6289c4f01a4ac17f8514aee3247a'
flag-exempt: flag-infrastructure   # the rule's own test infrastructure (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: true
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-testing-kit/README.md
  - src/platform/tests/test_openfeature_file_flags.py
  - src/platform/config/flags.json
deferred:
  - summary: >-
      No CI lane or pr-preflight leg runs the pyforge-testing-kit suite, so the flags family, invoke_cli and the
      branch_diff_guard loud-failure tests are guarded only by the manual `pyforge-testing-kit-test` command.
    evidence: |-
      The only definition of `pyforge-testing-kit-test` is the pixi task at pixi.toml:3060; .github/workflows/pyforge-station-tests.yml
      has `core-test` plus the eight station jobs and no kit job, and the `pyforge-station-tests` task depends on
      `pyforge-core-test` and the eight station tasks only. The gap pre-dates this story (the kit's existing
      test_branch_diff_guard.py was never in a lane either). Fixing it needs a new job in that workflow and a matching
      `depends-on` entry, both outside marshal-policy.toml `[epic_surfaces]` "74" (MRS-GATE-007), plus the workflow's
      trigger-companion meta-tests, so a run inside this story cannot land it.
    location: >-
      .github/workflows/pyforge-station-tests.yml
    severity: medium
  - summary: >-
      spec-pyforge-core's SPEC.md still calls the testing kit "a stdlib leaf by Q-26" and lists "Not pyforge-testing-kit" as a
      non-goal, after the 2026-09-30 operator ruling retired that premise.
    evidence: |-
      SPEC.md:152 reads "a stdlib leaf by Q-26" and SPEC.md:217 reads "Not `pyforge-testing-kit`". The supersession is recorded on
      the .memlog.md of spec-pyforge-core, spec-pyforge-testing-charter and spec-feature-flag-governance (the sanctioned reconcile
      path), but this story's Never clause and AGENTS.md forbid a hand edit of SPEC.md; it is re-derived with bmad-spec.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md:152
    severity: low
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

### 2026-09-29 — Review pass
- verdicts: 35 findings — high 0, medium 5, low 20, false 10, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter 1, stale "leaf" wording — confirmed at `testing_kit/__init__.py:5`, `pixi.toml:1008` and `pixi.toml:3045` (root env and feature comments); reworded, comments and the docstring only. The pyproject "imports no station" wording stays true (`pyforge.core` is the kernel, not a station). Grouped with Edge Case Hunter 11.
  - `[low]` `[defer]` Blind Hunter 2, Q-26's supersession only in memlogs — `spec-pyforge-core/SPEC.md` still says "a stdlib leaf by Q-26" (`:152`) and keeps the "Not pyforge-testing-kit" non-goal (`:217`); real, but the fix is a re-derive of a SPEC.md, which the intent's Never clause and AGENTS.md forbid here, and the memlog entries on the core, charter and flag-governance Specs are the sanctioned reconcile. Recorded in `deferred`. No spec-19-2 Change Log entry is needed (that story is done).
  - `[medium]` `[patch]` Blind Hunter 3, nothing replaces the deleted premise pin — with `test_branch_diff_guard_exemption_rests_on_the_kits_leaf_declaration` gone and `tests/packaging` skipping the `pyforge` namespace, nothing pins that the kit declares the `pyforge-core` and `openfeature-sdk` it imports; added one kit test reading both manifests. Grouped with Edge Case Hunter 10.
  - `[low]` `[reject]` Blind Hunter 4, memlog dating — the 2026-09-30 entries name the operator ruling's own date (the story spec's Change Log), `memlog.py` stamps `updated:` from the wall clock, and memlogs are append-only; editing them is churn with no reader harm.
  - `[false]` `[reject]` Blind Hunter 5, the changed exception contract — no caller in `src/` or any station `tests/meta` catches `FileNotFoundError` from these guards (grep), both errors are loud, and a failing git exit still raises `CalledProcessError` (`_git_out`).
  - `[low]` `[reject]` Blind Hunter 6, restore only tested against `NoOpProvider` — same root cause as Edge Case Hunter 2: the registry shuts the replaced provider down asynchronously and the restore re-initialises it, so a provider whose `shutdown()` outlasts its `initialize()` ends registered but shut down. Reproduced with a synthetic slow-shutdown provider (6/6 rounds), but 5/5 rounds against the estate's only real prior, `FlagdProvider` in FILE mode (`django_pyforge.flags.configure_file_provider`), stayed `READY` and read the flag. The fix (holding the prior under a nesting-aware private domain) is more than a direct correction for a defect no provider in the estate shows; revisit if a slow-shutdown provider is ever installed.
  - `[low]` `[reject]` Blind Hunter 7, the leak test depends on execution order — `test_installed_flags_restores_the_prior_provider_even_when_the_body_raises` and the nested-use test check restoration inside one test, order-independent, and no random-order plugin is installed (`pytest-xdist` splits by process).
  - `[low]` `[patch]` Blind Hunter 8, the tree-shape test indexes the production flag `pyforge.three_surfaces` by name, so retiring that flag breaks the kit suite; now compares against any one entry and asserts the tree is non-empty. Grouped with Edge Case Hunter 9.
  - `[low]` `[patch]` Blind Hunter 9, `flagd_tree` is annotated `Mapping[str, str]` but refuses a non-dict (the I/O matrix row), so a `MappingProxyType` passes the type checker and fails at runtime; annotation now `dict[str, str]`. Grouped with Edge Case Hunter 3.
  - `[low]` `[reject]` Blind Hunter 10, `flag_states` is single-key and the fixture needs a `conftest.py` binding — the contract prescribes `flag_states(key)` and one `flag:` key per story, a multi-key API is new public surface, and the Design Notes prescribe the factory; the binding is now documented by the README patch (Blind Hunter 13).
  - `[low]` `[reject]` Blind Hunter 11, `assert_flag_off_verb` gaps (no flag key, one verb token, substring marker) — as the contract prescribes (verb, usage code, "marked disabled"); the alias and prose cases fail loudly, never pass falsely.
  - `[false]` `[reject]` Blind Hunter 12, `openfeature-sdk` is a hard dependency imported lazily — the contract mandates the hard dependency in `pyproject.toml`, the package `pixi.toml` and the root feature, and the Design Notes give the reason for the function-local import.
  - `[low]` `[patch]` Blind Hunter 13, thin docs — a station author reading only the README is never told `flag_provider` must be bound in `conftest.py`, and the CLI-runner row omits `invoke_cli` / `CliResult`; README gains a short usage block and the row names both. The mark-internals assertion and the module-level `PosixProcess()` parts are not acted on (the behavioural test covers the first; the guard tests use real git repos). Grouped with Intent Alignment 1.
  - `[medium]` `[patch]` Edge Case Hunter 1, ANSI colour breaks `assert_flag_off_verb` — argparse on Python 3.14 colours `--help` under `FORCE_COLOR=1` or `PYTHON_COLORS=1`; reproduced (`FAIL` under both, `PASS` plain). `invoke_cli` now strips ANSI SGR sequences, with a test that sets both variables.
  - `[low]` `[reject]` Edge Case Hunter 2, provider shutdown race — same root cause and evidence as Blind Hunter 6.
  - `[low]` `[patch]` Edge Case Hunter 3, `flagd_tree` refuses a `MappingProxyType` and raises `TypeError` on an unhashable variant — the annotation half is patched with Blind Hunter 9; the `TypeError` half is unlikely and its fix adds a guard.
  - `[low]` `[reject]` Edge Case Hunter 4, `flagd_tree(name=...)` accepts a path separator — the parameter is a literal the test author writes; writing there is the caller's own path.
  - `[low]` `[reject]` Edge Case Hunter 5, a bare `str` for `argv`/`args` splits into characters — annotated `Sequence[str]`, callers pass lists; a guard for a misuse nothing shows.
  - `[low]` `[reject]` Edge Case Hunter 6, `assert_flag_off_verb` misses `thing, t` alias lines and never checks the `--help` exit — the alias case fails loudly rather than passing falsely, and a broken `--help` fails the verb-present check.
  - `[low]` `[reject]` Edge Case Hunter 7, `_exit_code` does not mask to 0-255 or coerce a bool — not a shape any station `main` returns; the fix adds a branch for an unlikely case.
  - `[low]` `[reject]` Edge Case Hunter 8, stacked `flag_states` decorators collide — one `flag:` key per story is the contract; a multi-key form is new public surface.
  - `[low]` `[patch]` Edge Case Hunter 9, the shape test hardcodes `pyforge.three_surfaces` — patched with Blind Hunter 8.
  - `[medium]` `[patch]` Edge Case Hunter 10, the deleted premise-pin test leaves the `pyforge-core` declaration unpinned — patched with Blind Hunter 3.
  - `[low]` `[patch]` Edge Case Hunter 11, `__init__.py:5` and root `pixi.toml` still say "own leaf" — patched with Blind Hunter 1.
  - `[false]` `[reject]` Edge Case Hunter 12, "one new dependency" versus the two declared — the story spec's 2026-09-30 Spec Change Log widens the contract to `openfeature-sdk` and `pyforge-core`.
  - `[medium]` `[defer]` Verification Gap 1, no CI lane or `pr-preflight` leg runs the kit suite — verified (`pyforge-testing-kit-test` is defined only at `pixi.toml:3060`; the workflow has no kit job). It pre-dates this story, and the fix (a job in `.github/workflows/pyforge-station-tests.yml` plus a `depends-on`) is outside marshal-policy `[epic_surfaces]` "74" (MRS-GATE-007). Recorded in `deferred`.
  - `[medium]` `[patch]` Verification Gap 2, `_git_out`'s "a failing git raises" contract is pinned at one of seven call sites (`commit_subject`); swapping any other site to the non-raising `_git` would return an empty result and stay green. Added a parametrized test, one row per call site: six sites fail through a real git failure (a bad pathspec, a bad sha, a corrupt index) and the `ls-files` call in `changed_paths_since`, where git only warns, fails through the process seam. Mutation-checked: swapping `changed_paths_since`'s `diff` call to the non-raising `_git` turns exactly that row red.
  - `[false]` `[reject]` Verification Gap, other finding (`pixi.lock` not checked) — `pixi run --locked -e pyforge-testing-kit` exits 0, so the lock satisfies the manifests, and `environment.yaml` regenerates byte-identical.
  - `[low]` `[patch]` Intent Alignment 1, the consumer must bind `flag_provider` in `conftest.py` and no test covers that path — the Design Notes prescribe the factory; the discoverability gap is closed by the README patch (Blind Hunter 13).
  - `[false]` `[reject]` Intent Alignment 2, `flagd_tree` is tested with `json.loads`, not a flagd file provider — the criterion reads "when the written file is loaded, it has the tree's shape", and the contract says `flagd_tree` "writes JSON only and imports no provider".
  - `[false]` `[reject]` Intent Alignment 3, the OFF helper is tested on a synthetic argparse CLI — the criterion says "Given a fixture CLI".
  - `[false]` `[reject]` Intent Alignment 4, function-local imports mean `pyforge-deps-test` checks manifest parity only — stated in the Design Notes; declared-in-both-manifests is what it binds.
  - `[false]` `[reject]` Intent Alignment 5, scope beyond the verbatim contract and a `pyforge-core` import at module level — the story spec's 2026-09-30 Spec Change Log widens the contract by operator ruling and `[epic_surfaces]` "74" admits each path; "imports no station" still holds.
  - `[false]` `[reject]` Intent Alignment 6, the scoped `--write-baseline` stamp was not run — the Design Notes and this run's instructions reserve it for landing; the memlog reconcile is done.
  - `[false]` `[reject]` Intent Alignment 7, the spec's `## Auto Run Result` still reads `Status: blocked` — Finalize rewrites that section this pass, and a finding whose fix edits this spec's text is rejected.

## Auto Run Result

Status: done
Blocking condition: none. This run supersedes the earlier `blocked` result (the `pyforge-core` test pin): the 2026-09-30 operator ruling in the Spec Change Log widened the contract, and the work below carries it out.

### Summary of implemented change

The kit gains its fifth family, `pyforge.testing_kit.flags`: `installed_flags` and `make_flag_provider_fixture` (OpenFeature's `InMemoryProvider`, the prior default provider set again afterwards), `flag_states(key)` (ids `on` and `off`), `flagd_tree` (a flagd FILE tree in the shape of `src/platform/config/flags.json`) and `assert_flag_off_verb` (the Q3 OFF case), built on a new in-process `invoke_cli` / `CliResult` in the CLI-runner family. Per the ruling, the kit declares `openfeature-sdk>=0.10.0` and `pyforge-core`; `branch_diff_guard.py` runs its nine git calls through `pyforge.core.process.PosixProcess.run` (`_git_out` keeps the `CalledProcessError` on a non-zero exit); and `pyforge-core`'s `test_process_sole_ownership.py` drops the exemption and its premise pin and gains `test_branch_diff_guard_is_scanned_and_clean`. `origin/main` was merged in (twice; merge, never rebase).

### Files changed

- `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/flags.py` (new): the flags family.
- `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/cli_runner.py`: `CliResult`, `invoke_cli` (strips ANSI colour from the captured output).
- `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py`: git calls moved onto `PosixProcess.run`; one mypy finding fixed and its override dropped.
- `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/__init__.py`: exports, "five families", leaf wording corrected.
- `src/shared/packages/pyforge-testing-kit/pyproject.toml`, `pixi.toml`: `openfeature-sdk` and `pyforge-core` declared; leaf comments corrected.
- `src/shared/packages/pyforge-testing-kit/README.md`: family row, a feature-flag usage block, `invoke_cli` / `CliResult` named.
- `src/shared/packages/pyforge-testing-kit/tests/unit/test_flags.py` (new), `test_branch_diff_guard.py`: every I/O Matrix row, the guard's loud-failure contract at all seven call sites, and a pin that both manifests declare the two dependencies.
- `src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py`: exemption, three exemption tests and the unused `tomllib` import removed; one scanned-and-clean test added.
- `pixi.toml`: `openfeature-sdk = ">=0.10.0"` in `[feature.pyforge-testing-kit.dependencies]`; two kit comments reworded. `pixi.lock` re-solved (only the kit's own entries moved); `environment.yaml` unchanged.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md`, `spec-pyforge-core/.memlog.md` and `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md`: `Surface reconcile` entries naming every governed path changed. No `--write-baseline` was run.

### Review findings

- 35 findings from four layers (Blind Hunter 13, Edge Case Hunter 12, Verification Gap 3, Intent Alignment 7): high 0, medium 5, low 20, false 10, maybe-false 0.
- Patches applied: 12 findings in 7 entries. Medium: the deleted premise pin (a kit test that both manifests declare `pyforge-core` and `openfeature-sdk`), ANSI colour breaking `assert_flag_off_verb` (`invoke_cli` strips it), and `_git_out`'s loud-failure contract pinned at one of seven sites (a seven-row parametrized test). Low: stale "leaf" wording, the shape test's hardcoded production flag name, the `flagd_tree` annotation, and the README usage gap.
- Deferred: 2, both in the spec's `deferred` list. No CI lane runs the kit suite (medium); `spec-pyforge-core/SPEC.md` still says "a stdlib leaf by Q-26" (low).
- Rejected: 21, each with its reason:
  - Blind Hunter 4, memlog dating — the 2026-09-30 entries name the operator ruling's own date (the story spec's Change Log), `memlog.py` stamps `updated:` from the wall clock, and memlogs are append-only; editing them is churn with no reader harm.
  - Blind Hunter 5, the changed exception contract — no caller in `src/` or any station `tests/meta` catches `FileNotFoundError` from these guards (grep), both errors are loud, and a failing git exit still raises `CalledProcessError` (`_git_out`).
  - Blind Hunter 6, restore only tested against `NoOpProvider` — same root cause as Edge Case Hunter 2: the registry shuts the replaced provider down asynchronously and the restore re-initialises it, so a provider whose `shutdown()` outlasts its `initialize()` ends registered but shut down. Reproduced with a synthetic slow-shutdown provider (6/6 rounds), but 5/5 rounds against the estate's only real prior, `FlagdProvider` in FILE mode (`django_pyforge.flags.configure_file_provider`), stayed `READY` and read the flag. The fix (holding the prior under a nesting-aware private domain) is more than a direct correction for a defect no provider in the estate shows; revisit if a slow-shutdown provider is ever installed.
  - Blind Hunter 7, the leak test depends on execution order — `test_installed_flags_restores_the_prior_provider_even_when_the_body_raises` and the nested-use test check restoration inside one test, order-independent, and no random-order plugin is installed (`pytest-xdist` splits by process).
  - Blind Hunter 10, `flag_states` is single-key and the fixture needs a `conftest.py` binding — the contract prescribes `flag_states(key)` and one `flag:` key per story, a multi-key API is new public surface, and the Design Notes prescribe the factory; the binding is now documented by the README patch (Blind Hunter 13).
  - Blind Hunter 11, `assert_flag_off_verb` gaps (no flag key, one verb token, substring marker) — as the contract prescribes (verb, usage code, "marked disabled"); the alias and prose cases fail loudly, never pass falsely.
  - Blind Hunter 12, `openfeature-sdk` is a hard dependency imported lazily — the contract mandates the hard dependency in `pyproject.toml`, the package `pixi.toml` and the root feature, and the Design Notes give the reason for the function-local import.
  - Edge Case Hunter 2, provider shutdown race — same root cause and evidence as Blind Hunter 6.
  - Edge Case Hunter 4, `flagd_tree(name=...)` accepts a path separator — the parameter is a literal the test author writes; writing there is the caller's own path.
  - Edge Case Hunter 5, a bare `str` for `argv`/`args` splits into characters — annotated `Sequence[str]`, callers pass lists; a guard for a misuse nothing shows.
  - Edge Case Hunter 6, `assert_flag_off_verb` misses `thing, t` alias lines and never checks the `--help` exit — the alias case fails loudly rather than passing falsely, and a broken `--help` fails the verb-present check.
  - Edge Case Hunter 7, `_exit_code` does not mask to 0-255 or coerce a bool — not a shape any station `main` returns; the fix adds a branch for an unlikely case.
  - Edge Case Hunter 8, stacked `flag_states` decorators collide — one `flag:` key per story is the contract; a multi-key form is new public surface.
  - Edge Case Hunter 12, "one new dependency" versus the two declared — the story spec's 2026-09-30 Spec Change Log widens the contract to `openfeature-sdk` and `pyforge-core`.
  - Verification Gap, other finding (`pixi.lock` not checked) — `pixi run --locked -e pyforge-testing-kit` exits 0, so the lock satisfies the manifests, and `environment.yaml` regenerates byte-identical.
  - Intent Alignment 2, `flagd_tree` is tested with `json.loads`, not a flagd file provider — the criterion reads "when the written file is loaded, it has the tree's shape", and the contract says `flagd_tree` "writes JSON only and imports no provider".
  - Intent Alignment 3, the OFF helper is tested on a synthetic argparse CLI — the criterion says "Given a fixture CLI".
  - Intent Alignment 4, function-local imports mean `pyforge-deps-test` checks manifest parity only — stated in the Design Notes; declared-in-both-manifests is what it binds.
  - Intent Alignment 5, scope beyond the verbatim contract and a `pyforge-core` import at module level — the story spec's 2026-09-30 Spec Change Log widens the contract by operator ruling and `[epic_surfaces]` "74" admits each path; "imports no station" still holds.
  - Intent Alignment 6, the scoped `--write-baseline` stamp was not run — the Design Notes and this run's instructions reserve it for landing; the memlog reconcile is done.
  - Intent Alignment 7, the spec's `## Auto Run Result` still reads `Status: blocked` — Finalize rewrites that section this pass, and a finding whose fix edits this spec's text is rejected.

### Follow-up review recommendation

`followup_review_recommended: true`. Three medium entries were patched, and the patches have had no independent review pass. The specific unverified risks: `invoke_cli` strips SGR sequences only (`\x1b[...m`), not other CSI escapes; the seven-row failure test depends on git's own error behaviour (a bad pathspec exits 128; a corrupt index fails `git diff HEAD`), and its `ls-files` row uses a patched process seam because no real input makes that call fail; the dependency pin reads both manifests with `tomllib` and would need updating if the package layout changes.

### Verification performed

Exit codes read from files, on the final tree, worktree manifest, `--frozen`:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: exit 0, 8939 passed.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`: exit 0, 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test`: exit 0, 70 passed.
- `pixi run --frozen -e pyforge-guild pyforge-station-tests` (every leg, `pyforge-core` included): exit 0, 2123 passed in the last leg.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0, all ten packages.
- `python scripts/spec_surface_reconcile.py`: exit 0, "every tracked file governed or allowlisted; no drift".
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0.
- `pixi run --locked -e pyforge-testing-kit`: exit 0 (the lock satisfies the manifests).
- Reproduced before and after: the ANSI failure (`FORCE_COLOR=1` and `PYTHON_COLORS=1` failed, now pass); the provider-restore hazard (kept as a residual risk, below).
- Mutation check by the reviewer: swapping `changed_paths_since`'s `diff` call to `_git` turns exactly that parametrized row red.
- Matrix audit: every I/O Matrix row is covered by a test that ran and passed in the verbose listing of `test_flags.py` (parametrized ids `on` and `off`, nested use, the tree writer and its `ValueError`, the three OFF-helper rows).

### Residual risks

- Landing still needs the scoped stamps, from a clean tree after `git add`: `--write-baseline --spec pyforge-marshal/spec-pyforge-testing-charter`, `pyforge-marshal/spec-pyforge-core` and `pyforge-steward/spec-pyforge-unifying-strategy`. A stamp is valid only until the next edit of any file in that Spec's surface.
- `installed_flags` restores the prior provider by setting it again, and the OpenFeature registry shuts a replaced provider down asynchronously, so a provider whose `shutdown()` outlasts its `initialize()` can end registered but shut down. Reproduced with a synthetic provider (6 of 6 rounds); the estate's real prior, `FlagdProvider` in FILE mode, stayed ready in 5 of 5 rounds. Revisit if a slow-shutdown provider is ever installed.
- `PosixProcess.run` raises `ProcessError` for a missing `git` (previously `FileNotFoundError`) and decodes git output as UTF-8 with `errors="replace"`; no caller in the repository distinguishes them.
- The kit suite is not in any CI lane (deferred above), so the flags family is guarded in CI only indirectly until a lane is added.
