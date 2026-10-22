---
title: "37.4: Behind-upstream, whodepends, live-catalog coverage and the universe SBOM boards fill"
type: 'feature'
created: '2026-10-22'
status: 'in-progress'
baseline_revision: 'a81732d0a3'
flag:
  key: pyforge.atlas.board_projections            # new; minted by this story
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the four boards read as before: behind-upstream and whodepends are shells, the two coverage boards read the paths nothing writes'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/nodes.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** four boards render no rows from a public run:
- behind-upstream and whodepends are shells: a Card states the gap, and no data function is registered.
- live-catalog-coverage reads `derived/live_catalog_coverage/`, and universe-sbom reads
  `primary/universe_sbom_summary/`. No node writes either path.

The data exists. `vcs_upstream_versions` (Story 35.3/35.4) and `core_packages_enumerated` hold both versions, and
`core_dependencies` holds the dependency graph. `identity_complete_export` holds the inventory flags, and
`derived_universe_sbom` holds the CycloneDX BOM.

**Approach** (each behind `pyforge.atlas.board_projections`; off, the four boards read as before):
1. **Three pure projection nodes** (`derived_artifacts`), each writing a typed table even when its input is empty:
   - `project_behind_upstream`: per enumerated package, its upstream version from `vcs_upstream_versions` (one row
     per package, hosts in legacy's order for a package with no source registry: GitHub, GitLab, Codeberg; a row with
     no version or with an error is skipped). The package is classified against its enumerated `latest_version` with
     legacy's `_classify_lag` (`packaging.version`): `major`, `minor`, `patch`, or `unknown` for a version that does
     not parse. A package whose upstream is not newer (`current`) is left out, as legacy leaves it out. Version order
     needs PEP 440 parsing, which SQL cannot express, so this board gets a node where the epic named a model only.
   - `project_live_catalog_coverage`: one row per inventory flag of `identity_complete_export`
     (`PyPI_Verified` and `CondaForge_Verified`, "Yes" counting true, and the 15 `in_*` booleans):
     `field_name`, `true_count`, `total_count`.
   - `project_universe_sbom_summary`: one row per BOM component: `component_purl`; `slice`, `mapped` when the
     component names its PyPI project (`cfe:pypi_name`), else `conda-only`; `with_vulns_count` null, since the BOM
     carries no vulnerability data (legacy adds it only under `--with-vulns`).
2. **Two models** (`semantic/models.py`): `build_behind_upstream_model` over the projection, and
   `build_whodepends_model` over `core_dependencies`: per `depends_on` and `dep_type`, the count of distinct
   packages that depend on it (legacy `whodepends --reverse`, for every package at once). The two coverage models
   keep their dimensions and measures.
3. **The flag** decides each board at build time: `dashboard.data.board_projections()` reads it, and
   `app.page_inventory()` returns `PAGE_INVENTORY` with the four boards' projected definitions when it is on.
   `build_dashboard` and the static export use the same inventory.

Ledger key: `37-4-behind-upstream-whodepends-live-catalog-coverage-and-the-universe-sbom-boards-fill`.
Type / Effort / Deps: feature / M / Story 37.1 (the data root).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77). **AD-8** (BSL over DuckDB; no metric computed in the app), **AD-14** (the
  projection nodes are new riders, not parity-gated), **AD-17** (each page's stamp from the dataset it reads).

## Acceptance Criteria

- **AC1 — Paths.** Each new constant is the `filepath` of the catalog dataset a node writes, or of `core_dependencies`.
- **AC2 — Behind-upstream.** The node classifies as legacy `_classify_lag` does, drops `current`, takes one upstream
  per package in host order, skips rows with no version or with an error; the board reads its rows.
- **AC3 — Whodepends.** The board reads `core_dependencies`: per depended-on package and type, its dependents' count.
- **AC4 — Coverage.** The node counts each flag's true values over the export's rows; the board reads them.
- **AC5 — SBOM.** The node writes one row per component, its slice from the PyPI property, `with_vulns_count` null.
- **AC6 — Flag.** On, the four boards read the above; off, behind-upstream and whodepends are shells and the two
  coverage boards read their earlier paths. Tested in both states.
- **AC7 — Empty.** Each node writes a typed empty table for an empty or malformed input, and each board reads it.
- **AC8 — Gates.** `pyforge-atlas-test`, the dashboard integration suite, `kedro-catalog-check`, the coverage gate,
  `lint-types`, `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` (the flag's tree
  entry and both states, the three nodes, the two models, the loaders on frames shaped like the produced datasets,
  and the inventory each state builds) and `src/shared/packages/pyforge-atlas/tests/unit/test_board_wiring.py` (the
  new paths against the catalog).

## Boundaries & Constraints

**Never:** a value invented for a column the input lacks; a board's existing dimension or measure renamed; a network
read (the nodes are pure).

**Residual risk:**
- **Behind-upstream reads VCS hosts only.** Legacy also compares PyPI's version for a package whose source is PyPI;
  atlas holds that in `pypi_current_versions`, which this story does not read.
- **Whodepends has no `pin_spec`:** `core_dependencies` does not carry the pin.
- **Universe-sbom's `with_vulns_count` stays null** until a story joins the vulnerability store to the BOM.

## I/O & Edge-Case Matrix

| Input | Result |
|---|---|
| upstream `1.2.0`, conda `1.1.9` | `minor` |
| upstream `2.0`, conda `1.9` | `major` |
| upstream `1.0.1`, conda `1.0.0` | `patch` |
| upstream equal or older | left out (`current`) |
| a version that does not parse | `unknown` |
| GitHub and GitLab rows for one package | GitHub's |
| a package not enumerated | left out |
| `PyPI_Verified` "Yes"/"No", null | "Yes" counts true; null counts in the total, not as true |
| BOM with no `components` | typed empty table |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-19.
- Epic 37 / Story 37.4 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-22: written with the implementation (branch `atlas-37-4-board-projections`, cut from `main` at
  `a81732d0a3`).
