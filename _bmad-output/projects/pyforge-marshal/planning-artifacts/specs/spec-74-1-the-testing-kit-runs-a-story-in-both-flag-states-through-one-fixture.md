---
title: '74.1: The testing kit runs a story in both flag states through one fixture'
type: 'feature'
created: '2026-09-28'
status: 'backlog'
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

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- `pixi run -e pyforge-testing-kit pyforge-testing-kit-test` — expected: pass (the kit's own suite, both states).
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (a `pixi.toml` / `pixi.lock` change fires every station suite in CI).
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamp.

## Review Triage Log
