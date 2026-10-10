---
title: "Test Architecture — pyforge-mason"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: mason
source_fingerprint: 903737d117b5a29a
story_count: 106
test_file_count: 43
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Mason

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-mason`
- **Stories parsed:** 106
- **Epics parsed:** 28
- **Test files inventoried:** 43 under `src/shared/packages/pyforge-mason/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `903737d117b5a29a`

## Risk Assessment

### High-risk epics

- Epic 2: Author, build, and submit recipes

### Medium-risk epics

- Epic 1: Install, run, and diagnose Mason
- Epic 3: Ship a library to both ecosystems
- Epic 4: Bind environments into lockfiles
- Epic 5: Prove the seam holds
- Epic 6: The CFE rebuild — pilot slice, parallel-run, and the re-scope gate
- Epic 7: Machine-checked recipe knowledge
- Epic 8: One pixi base-layer discipline across the Containerfiles
- Epic 9: External integration seams
- Epic 10: Build-engine hook spec
- Epic 11: Mason persona and one portal job (CFE stays)
- Epic 12: The CFE rebuild continues — gate closure and slice 2
- Epic 13: Two feedstock pins admit Python 3.14 (steward 43.5 hybrid decision)
- Epic 14: The eval-quality Windows variant (spec-bmad-suite-lifecycle CAP-7 relay)
- Epic 15: Close the CFE rebuild campaign at slices 1–2
- Epic 16: Turn on what is built — mason's realization-gate and coverage residue
- Epic 17: The recipes/ fleet is stewarded (spec-fleet-stewardship fs:CAP-1..3)
- Epic 18: The recipe CI picks changed recipes from the remote-tracking ref (spec-pyforge-mason CAP-28)
- Epic 19: Mason has its own skills, and conda-forge-expert is one of them (spec-pyforge-mason CAP-29)
- Epic 20: No station or environment caps pixi (spec-pyforge-mason CAP-30)
- Epic 21: Mason packages the intake toolchain (spec-pyforge-mason CAP-31)
- Epic 22: Twelve recipes lose conda-recipe-manager's leaked sentinel key, and CFE's validation refuses the next one (spec-pyforge-mason CAP-32)
- Epic 23: CFE's generator asks instead of guessing, a mismatched copyleft licence is refused, and a negative corpus keeps each check honest (spec-pyforge-mason CAP-33)
- Epic 24: The CFE host-gate tests give the same verdict in any developer shell (spec-pyforge-mason CAP-34)
- Epic 25: The feedstock refresh campaign is Mason's: every feedstock rxm7706 can modify has a local recipe at its published version (spec-pyforge-mason CAP-35)
- Epic 26: CFE's tests never ask GitHub whether a recipe maintainer exists (spec-pyforge-mason CAP-34)
- Epic 27: Phase 4+5 of the deferral burn-down: mason's open medium and low deferrals
- Epic 28: The CFE-rebuild guard reads a SHA field whatever type YAML gives it (spec-pyforge-mason CAP-16)

### Low-risk epics

- none observed

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-mason/tests/integration/test_delegation_fidelity.py` | integration | none observed |
| `src/shared/packages/pyforge-mason/tests/integration/test_package_build.py` | integration | none observed |
| `src/shared/packages/pyforge-mason/tests/integration/test_package_ship.py` | integration | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_adapter_sole_caller.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_capability_tiers.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_cfe_import_floor_env_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_cfe_independence.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_credential_isolation.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_dependency_direction.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_engine_version_range_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_exit_code_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_namespace_is_implicit.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_no_config_file.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_no_recipe_knowledge.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_portal_last_diagnose.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_render_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_airgap_contract.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_boot_reconcile.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_build_hooks.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_cfe.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_cfe_rebuild_guard_merges.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_doctor.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_engines.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_engines_condalock.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_engines_gh.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_engines_pep517.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_engines_pixi.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_engines_twine.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_environment.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_errors.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_exit_codes.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_factory_island.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_fake_cfe_root_fixture.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_models.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_package.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_pypi_index.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_recipe.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_render.py` | unit | none observed |
| `src/shared/packages/pyforge-mason/tests/unit/test_resolve.py` | unit | none observed |

## Story Coverage Matrix

| Story | Title | Linked test files |
|-------|-------|-------------------|
| 1.1 | Workspace member scaffold and dual-artifact build | none observed |
| 1.2 | CLI noun-verb structure and global flags | none observed |
| 1.3 | Error taxonomy and exit-code contract | none observed |
| 1.4 | Dual output format with stream discipline | none observed |
| 1.5 | CFE root resolution chain | none observed |
| 1.6 | Interpreter selection and CFE import-floor probe | none observed |
| 1.7 | Degradation when CFE is unavailable | none observed |
| 1.8 | `mason doctor` | none observed |
| 1.9 | Fake CFE root fixture and test harness | none observed |
| 1.10 | Configuration surface, logging, and child-output streaming | none observed |
| 2.1 | The CFE port | none observed |
| 2.2 | The seam guard | none observed |
| 2.3 | Credential isolation | none observed |
| 2.4 | `mason recipe new` | none observed |
| 2.5 | `mason recipe validate` | none observed |
| 2.6 | `mason recipe build` | none observed |
| 2.7 | `mason recipe diagnose` | none observed |
| 2.8 | `mason recipe optimize` and `mason recipe scan` | none observed |
| 2.9 | `mason recipe submit` | none observed |
| 2.10 | `mason recipe update` | none observed |
| 3.1 | Engine protocol and provisioning | none observed |
| 3.2 | `mason package build` | none observed |
| 3.3 | Ship-target vocabulary and dry-run default | none observed |
| 3.4 | The `pypi` ship target | none observed |
| 3.5 | The `channel:<name>` ship target | none observed |
| 3.6 | The `conda-forge` ship target | none observed |
| 3.7 | Asymmetric receipts, partial failure, and idempotence | none observed |
| 3.8 | Mason ships Mason | none observed |
| 3.9 | The `ship` verb and TestPyPI rehearsal | none observed |
| 4.1 | Lock engine adapter and provenance | none observed |
| 4.2 | Manifest discovery | none observed |
| 4.3 | `mason environment lock` | none observed |
| 4.4 | `mason environment check` | none observed |
| 5.1 | CFE-independence test | none observed |
| 5.2 | Governance test | none observed |
| 5.3 | Delegation-fidelity test | none observed |
| 5.4 | Free-inheritance verification | none observed |
| 5.5 | Rule-2 conda-forge-expert retrospective | none observed |
| 6.1 | Slice map and campaign state | none observed |
| 6.2 | The divergence-and-endgame guard, proven red first | none observed |
| 6.3 | Pilot slice — recipe generation, built and parallel-validated | none observed |
| 6.4 | The re-scope gate — measured cost, recorded decision | none observed |
| 7.1 | The failure catalog derives from the skill spec | none observed |
| 7.2 | The pointers lint and the drift gates | none observed |
| 8.1 | The convention is written and guarded | none observed |
| 9.1 | The repo's CI is consumable via workflow_call | none observed |
| 9.2 | The air-gap distribution contract has a socket | none observed |
| 10.1 | Extract the build-engine hook | none observed |
| 11.1 | BMAD persona consults conda-forge-expert | none observed |
| 11.2 | First portal slice — last diagnose | none observed |
| 12.1 | Landed retros are mirrored into the pilot brief | none observed |
| 12.2 | CI enforcement for the guard and the equivalence net | none observed |
| 12.3 | The real audit tool backs the pilot zero-drift claim | none observed |
| 12.4 | The re-scope gate is machine-enforced | none observed |
| 12.5 | The ownership decision is recorded | none observed |
| 12.6 | Slice 2 brief — cross-slice dependencies re-derived first | none observed |
| 12.7 | Slice 2 compiled and equivalence-validated | none observed |
| 12.8 | The slice-2 re-scope checkpoint | none observed |
| 13.1 | langflow-base onnxruntime pin admits Python 3.14 | none observed |
| 13.2 | dbgpt-client sqlalchemy cap admits Python 3.14 | none observed |
| 14.1 | `bmad-eval-quality` builds a `__win` variant | none observed |
| 15.1 | Close the CFE rebuild campaign — cut callers over to slices 1–2 or retire the... | none observed |
| 15.2 | Rule-2 retro for Story 13.2 lands in the CFE skill | none observed |
| 16.1 | Mason's own env satisfies the CFE import floor | none observed |
| 16.2 | A first estate caller of `mason recipe` | none observed |
| 16.3 | Mason's MCP tool surface passes the CLI⇄tool parity gate | none observed |
| 16.4 | The Containerfile convention guard derives its file list | none observed |
| 17.1 | The local mirror is the source of truth | none observed |
| 17.2 | Every local recipe carries its internal metadata, stripped on push | none observed |
| 17.3 | The recurring campaigns have a home and a record | none observed |
| 18.1 | The recipe CI picks changed recipes from the remote-tracking ref | none observed |
| 19.1 | Mason's station skill is SKF-compiled, exported and consulted by the persona | none observed |
| 19.2 | The package craft skill teaches mason package build and ship | none observed |
| 19.3 | The environment craft skill teaches mason environment lock and check | none observed |
| 19.4 | The two feedstock campaigns become Mason skills | none observed |
| 19.5 | The closing Rule-2 retro teaches conda-forge-expert it is one of Mason's skills | none observed |
| 20.1 | Mason's pixi run-dependency is a floor, and a guard reds any pixi ceiling | none observed |
| 21.1 | git-pkgs builds green from source as a local recipe | none observed |
| 21.2 | forge builds green from source as a local recipe | none observed |
| 21.3 | gitgres builds green against PostgreSQL 17 from a pinned commit | none observed |
| 21.4 | opengrep is repackaged from its release binaries as a local-only recipe | none observed |
| 21.5 | pptxgenjs-plus-jsx builds green beside its pptxgenjs-plus sibling | none observed |
| 22.1 | The twelve recipes carrying conda-recipe-manager's sentinel key are repaired | none observed |
| 22.2 | CFE's validation reds a recipe with a non-string key or a Python object repr | none observed |
| 22.3 | ctng-compilers loses its sentinel key once rattler-build renders its output g... | none observed |
| 22.4 | vc loses its sentinel key once rattler-build can emit its vc14 track feature | none observed |
| 23.1 | CFE refuses a copyleft -only licence whose LICENSE grants any later version | none observed |
| 23.2 | CFE's recipe generator asks instead of guessing | none observed |
| 23.3 | A negative corpus proves each CFE check keeps rejecting its defect | none observed |
| 24.1 | CFE's host-gate tests pass in any developer shell | none observed |
| 25.1 | Track A's Wave H refreshes the sole-maintainer recipes the first waves missed | none observed |
| 25.2 | Track B refreshes the co-maintained recipes and keeps every other maintainer'... | none observed |
| 25.3 | CFE gains a tracked bulk recipe-refresh driver that the refresh waves run thr... | none observed |
| 25.4 | Wave 0's leftover recipes end repaired or carry a recorded reason | none observed |
| 25.5 | Track B batch 1 refreshes airflow-code-editor through django-countries | none observed |
| 25.6 | Track B batch 2 refreshes django-fsm-log through import-linter | none observed |
| 25.7 | Track B batch 3 refreshes jhub-apps through niquests | none observed |
| 25.8 | Track B batch 4 refreshes ocrmypdf through pysqlite3 | none observed |
| 25.9 | Track B batch 5 refreshes redshift_connector through zxing-cpp | none observed |
| 25.10 | Track B batch 6 refreshes OpenTelemetry's core packages and exporters | none observed |
| 25.11 | Track B batch 7 refreshes OpenTelemetry instrumentation from distro through h... | none observed |
| 25.12 | Track B batch 8 refreshes OpenTelemetry instrumentation from mysql through wsgi | none observed |
| 26.1 | CFE's tests never ask GitHub whether a recipe maintainer exists | none observed |
| 27.1 | Mason's package and the repo tooling it owns close their open deferrals | none observed |
| 27.2 | CFE, its failure catalog and the closed rebuild campaign's records close thei... | none observed |
| 28.1 | The rebuild guard reads a SHA field whatever type YAML gives it | none observed |

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | FR-132 |
| Story-id coverage drift | every epic story id in matrix | `--check` (CAP-5 / Story 19.4) |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-mason
python _bmad/scripts/bmad_tea_playwright.py --all
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-mason --check
python _bmad/scripts/bmad_tea_playwright.py --all --check
```
