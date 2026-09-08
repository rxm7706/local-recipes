---
title: "Test Architecture — pyforge-mason"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: mason
source_fingerprint: 44291bfab689964e
story_count: 61
test_file_count: 39
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Mason

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-mason`
- **Stories parsed:** 61
- **Epics parsed:** 14
- **Test files inventoried:** 39 under `src/shared/packages/pyforge-mason/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `44291bfab689964e`

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
| `src/shared/packages/pyforge-mason/tests/meta/test_cfe_independence.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_credential_isolation.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_dependency_direction.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_engine_version_range_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_exit_code_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_namespace_is_implicit.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_no_config_file.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_no_recipe_knowledge.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_portal_last_diagnose.py` | meta | none observed |
| `src/shared/packages/pyforge-mason/tests/meta/test_render_ownership.py` | meta | none observed |
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
