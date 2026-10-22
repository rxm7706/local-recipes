---
title: "37.4: Behind-upstream, whodepends, live-catalog coverage and the universe SBOM boards fill"
type: 'feature'
created: '2026-10-22'
status: 'done'
baseline_revision: 'a81732d0a3'
flag:
  key: pyforge.atlas.board_projections            # new; minted by this story
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the four boards read as before: behind-upstream and whodepends are shells, the two coverage boards read the paths nothing writes'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 2
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
     component names its PyPI project (`cfe:pypi_name`), else `unmapped` (not legacy's `--conda-only`, which is the
     BOM without its PyPI side); `with_vulns_count` null, since the BOM carries no vulnerability data (legacy adds
     it only under `--with-vulns`).
2. **Two models** (`semantic/models.py`): `build_behind_upstream_model` over the projection, and
   `build_whodepends_model` over `core_dependencies`: per `depends_on` and `dep_type`, the count of distinct
   packages that depend on it (legacy `whodepends --reverse`, for every package at once). The two coverage models
   keep their dimensions and measures.
3. **The flag** decides each board at build time: `dashboard.data.board_projections()` reads it, and
   `app.page_inventory()` returns `PAGE_INVENTORY` with the four boards' projected definitions when it is on.
   `build_dashboard` and the static export use the same inventory and one read of the flag; `vizro-static-export
   --flags-path` reads this flag from the same tree as `pyforge.atlas.vizro_static_boards`.
4. **Charts.** Behind-upstream counts packages per lag label; whodepends sums each package's dependents over its
   dependency types, so the static export's table lists the most depended-on packages first (Story 37.2's cap).

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
- **AC5 — SBOM.** The node writes one row per component, its slice (`mapped` / `unmapped`) from the PyPI property,
  `with_vulns_count` null.
- **AC6 — Flag.** On, the four boards read the above and each is stamped from the file it reads; off, behind-upstream
  and whodepends are shells and the two coverage boards read their earlier paths. The dashboard, the static export
  and the export task each follow the flag. Tested in both states.
- **AC7 — Empty.** Each node writes a typed empty table for an empty or malformed input, and each board reads it.
- **AC8 — Gates.** `pyforge-atlas-test`, the dashboard integration suite, `kedro-catalog-check`, the coverage gate,
  `lint-types`, `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` (the flag's tree
  entry and both states, the three nodes, the two models, the loaders on frames shaped like the produced datasets,
  and the inventory, stamps and static export each state builds) and
  `src/shared/packages/pyforge-atlas/tests/unit/test_board_wiring.py` (the new paths against the catalog).
- **Live, 2026-10-22,** over a scratch copy of the inputs Story 37.2's public run wrote (no credentials, no switch,
  no token): `pyforge atlas run --pipelines derived_artifacts --nodes project_behind_upstream,
  project_live_catalog_coverage,project_universe_sbom_summary` exit 0.
  - live-catalog-coverage: 17 flags over the export's 871 rows, e.g. `PyPI_Verified` 854, `CondaForge_Verified` 868,
    `in_basilisk` 868, `in_nixpkgs` 285; `in_bioconda`, `in_pytorch`, `in_nvidia`, `in_robostack` 0.
  - universe-sbom: 34,720 components, 22,358 mapped and 12,362 unmapped; the board reads all 34,720.
  - whodepends: 314,317 edges of `core_dependencies` give 21,406 rows; `python` (run) has 21,269 dependents.
  - behind-upstream: that root's `vcs_upstream_versions` was empty (the run predates Story 35.4), so the board read
    no rows. A public GitLab/Codeberg fetch over the same root (`--nodes refresh_vcs_host_stores,
    track_upstream_versions,project_behind_upstream`, 243 s, no token pattern in the log) wrote 435 upstream rows
    (404 GitLab, 31 Codeberg; 389 with a version), and the node found 95 packages behind: 15 major, 23 minor, 16
    patch, 41 unknown (tags such as `bzip2-1.0.8` that are not PEP 440, which legacy also keeps as `unknown`).

## Boundaries & Constraints

**Never:** a value invented for a column the input lacks; a board's existing dimension or measure renamed; a network
read (the nodes are pure).

**Residual risk:**
- **Behind-upstream reads VCS hosts only.** Legacy also compares PyPI's version for a package whose source is PyPI;
  atlas holds that in `pypi_current_versions`, which this story does not read.
- **Whodepends has no `pin_spec`:** `core_dependencies` does not carry the pin.
- **Universe-sbom's `with_vulns_count` stays null** until a story joins the vulnerability store to the BOM, and
  DESIGN.md § 4.3's summary cards are not built: the board is one row per component, and its static page shows the
  first 5,000 in column order.
- **Behind-upstream without the credentialed run** shows GitLab and Codeberg only; GitHub's versions need Story
  35.3's opt-in. Its `package_count` is 1 per row (the chart's count), so its static table is in column order.
- **Archived packages:** legacy's query drops inactive and archived packages; this node relies on the enumeration
  (active packages) and Story 35.2's batches, which leave archived feedstocks out.
- **The live whodepends chart draws every bar** (16,004 packages on a public root, in query order); the static page
  keeps the 5,000 largest, sorted. Its sum over dependency types can exceed the package count (python: 42,899), as
  Approach 4 says.
- **Unparsed dependency names:** 76 `depends_on` values are requirement specs (`boost>=1.67`), which split counts on
  whodepends; the core node is parity-gated, so the fix is deferred (DW-atlas-37-4-1).

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
| a zero-row export with its columns | typed empty table |
| component with `cfe:pypi_name` | `mapped`; otherwise `unmapped` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-19.
- Epic 37 / Story 37.4 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-22, review round 2 (PASS), should-fix applied:
  - S1: with the flag on, nothing tested the projected definitions or their charts, so swapping in `PAGE_INVENTORY`,
    dropping the whodepends chart (and with it the static table's sort) or pointing a chart at another column
    survived. Tests now pin both charts, the built pages' Graph and note, and the static whodepends order.
  - S2: the page swap replaced a page's whole definition and dropped its `access_column`, so the static export would
    not refuse a projected board that declared one (latent; no page declares one). `page_inventory` now keeps the
    base page's `access_column`; a test checks the refusal in both states.
  - Nits: a long docstring line wrapped; the SBOM model's docstring says what the board reads; residual risks for the
    live whodepends chart and the unparsed dependency names (DW-atlas-37-4-1).
- 2026-10-22, review round 1 (FAIL), fixed:
  - B1: `board_projections`' `flags_path` was typed `str | os.PathLike[str]`, which `read_boolean` does not take;
    mypy failed `lint-types`. It is `Path | str | None`.
  - Should-fix: tests for each board's flag-on stamp, the dashboard reading the flag when not told, the static
    export following the tree it is given, and the export task passing `--flags-path` through (it did not:
    `export_boards` now takes `flags_path`); an unparseable upstream kept as `unknown`; a zero-row export with its
    columns. Whodepends declares a chart, so its static table sorts by its dependents.
  - Nits: the SBOM slice reads `unmapped`, not `conda-only` (legacy's `--conda-only` means something else); the
    universe-sbom note no longer calls the board a summary; residual risks for the archived filter, the constant
    `package_count` and the 5,000-row SBOM page.
- 2026-10-22: written with the implementation (branch `atlas-37-4-board-projections`, cut from `main` at
  `a81732d0a3`).
