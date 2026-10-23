---
title: "37.8: The export-purls lists the PURL artifacts"
type: 'feature'
created: '2026-10-23'
status: 'done'
baseline_revision: 'de4b8cd0800577adc11aa7c8e0e86d3a0b96b0be'
flag:
  key: pyforge.atlas.board_projections            # existing; minted by Story 37.4, extended to this board
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the export-purls reads primary/purl_export_manifest as before, which nothing writes, and renders empty'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - .claude/skills/conda-forge-expert/scripts/export_purls.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/purl_exports.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the export-purls board reads `primary/purl_export_manifest/`, and no node writes it (DW-atlas-37-8-1).
`derived_purl_exports` holds only Artifactory's `artifactory_downloads.tsv`. Legacy `export_purls.py`'s six artifacts
are not ported:
1. `purls_conda-forge.txt`: one conda purl per active package;
2. `purls_conda-forge_versioned.txt`: the same, at the latest version;
3. `purls_pypi.txt`: the PyPI universe, G98-normalized;
4. `purls_conda-pypi_mapped.tsv`: the conda-to-PyPI mapping, with provenance;
5. `recipe-purl-exceptions.txt`: the pending or blocked local recipes that are missing from the exports;
6. `purls_conda-upstream_mapped.tsv`: each PyPI-unmapped package's non-PyPI upstream purl.

**Approach:**
1. **A read-only dataset,** `RecipeExtrasDataset` (new, `datasets/recipe_extras.py`), as `discovery_recipe_extras_raw`
   over `paths.local_recipes_dir`. It reads each `recipes/*/recipe.yaml`'s conda-forge-expert stamps, as legacy does:
   - `extra.cfe-on-conda-forge-status`;
   - the conda name: `cfe-conda-name`, else `package.name`, else the directory;
   - `cfe-upstream-registry` and `cfe-upstream-name`.
2. **A node,** `export_purl_artifacts` (new module `derived_artifacts/purl_exports.py`, a port of legacy's functions).
   - It reads `core_packages_enumerated`, `core_latest_status`, `pypi_conda_mapping`, `pypi_universe`, the recipe
     stamps, and `core_cf_graph_raw` with `core_feedstock_attribution` (`package_recipe_fields`: each package's recipe
     URLs).
   - It writes the six artifacts as text partitions of `derived_purl_artifacts`, and a manifest,
     `derived_purl_export_manifest`: `artifact_name`, `regenerated_at` and `row_count` (lines, a TSV's header not
     counted).
   - Legacy's ordering contract and purl conventions hold: C-locale by name for 1, 2 and 4; a full-line sort for 3;
     G98 PyPI names; a fold for membership only.
3. **The board,** behind `pyforge.atlas.board_projections` as Stories 37.4–37.10's boards are: on, export-purls reads
   the manifest; off, it reads `primary/purl_export_manifest/` as before.

**Deviations from legacy:**
- Artifact 6 reads each package's recipe URLs (`repo_url`, `source_url`, `dev_url`, `home_url`), classified by host
  (github, gitlab, codeberg, npm, crates, rubygems, maven). Legacy reads `upstream_versions`' (source, url) rows, which
  atlas's VCS stores do not keep. A field can list several URLs (split on commas and spaces), and a GitLab or
  Codeberg URL is cut to its `<namespace>/<project>` (an archive, tree or release path is not the project), as
  legacy's Phase K builds its URLs before `upstream_purl`. It emits one row per package and source, from the first
  URL that parses.
- Artifact 4 lists every mapping row of an active package (`pypi_conda_mapping` can hold several PyPI names for one
  package), one line per G98-normalized name; legacy's `packages` table holds one. `match_confidence` is empty: the
  mapping has no such column.
- `derived_purl_exports` keeps Artifactory's TSV, and its one writer. The six artifacts go to a dataset of their own.

Ledger key: `37-8-the-export-purls-lists-the-purl-artifacts`.
Type / Effort / Deps: feature / M / Story 37.1 (the data root).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77, the boards no pipeline feeds). **AD-2/AD-13** (the dataset owns the recipe
  reads; a missing tree degrades to empty), **AD-8** (BSL over DuckDB; no metric computed in the app), **AD-14** (a new
  rider, not parity-gated), **AD-17** (the page's stamp from the dataset it reads).

## Acceptance Criteria

- **AC1 — Conda purls.** One per active package, in C-locale name order (never a full-line sort); the versioned file
  has the same rows, unversioned when the version is unknown.
- **AC2 — PyPI purls.** The universe G98-normalized, deduplicated, full-line sorted.
- **AC3 — Mapping TSV.** A header, then each active package's mapping rows with their provenance.
- **AC4 — Exceptions.** A `pending-` or `blocked-` recipe whose conda name is not active reads `not-on-cf`; one whose
  PyPI upstream is not in the PyPI export (folded) reads `not-in-pypi-export`; no other recipe appears.
- **AC5 — Upstream TSV.** A header, then each active, PyPI-unmapped package's upstream purl per source, from its recipe
  URLs, by legacy `upstream_purl`.
- **AC6 — Manifest and board.** The manifest has the six artifacts with their row counts. With the flag on, the board
  reads it and its AD-17 stamp names it; off, it reads `primary/purl_export_manifest/` as before.

## Boundaries & Constraints

**Always:** read-only over the recipes tree and the data root; never reach the network beyond what the cf-graph
dataset already fetches.

**Never:** change `derived_purl_exports` or its writer.

**Residual risk:**
- Artifact 6 covers what each recipe names as its URLs. An upstream that only the VCS refresh knows does not appear.
- Artifact 5 depends on the recipes tree, which the Pages runner checks out; a run without it lists no exceptions.

## I/O & Edge-Case Matrix

| Input | Result |
|-------|--------|
| inactive package | in no artifact |
| no `core_latest_status` | every enumerated package is active |
| a mapping row with an empty PyPI name | not in the TSV |
| a recipe with status `built` | never an exception |
| a pending recipe on conda-forge whose PyPI name folds into the universe | no exception |
| a mapped package with a GitHub repo URL | not in the upstream TSV |
| nothing in | header-only TSVs, empty text files, a manifest of zeros |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-19 entry (the Vizro boards read their data).
- Epic: Epic 37 (in progress). Closes DW-atlas-37-8-1.
- Ledger key: `37-8-the-export-purls-lists-the-purl-artifacts`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass.
- From the repo root: `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_purl_exports.py`,
  `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_recipe_extras.py` and
  `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` (both flag states) — expected: pass.

## Run results

Run 2026-10-23 in the landing worktree on `de4b8cd080`, every verdict read from its exit code; the numbers are those
after the review fixes.

- **AC1–AC6, tests:** `test_purl_exports.py` (23), `test_recipe_extras.py` (4) and `test_board_projections.py` pass;
  `pyforge-atlas-test` gives 3,221 passed and 20 skipped, then 103 passed (exit 0).
- **Pins moved:** `derived_artifacts` has 12 nodes (11), the combined DAG 71 (70), the catalog 142 entries (139); the
  node has a timeout (600 s).
- **Mutations**, each restored, each failing a named test (17 of 17):
  - conda purls: a full-line conda sort; inactive packages kept;
  - PyPI purls: no G98 normalization; PyPI purls not deduplicated;
  - mapping TSV: an empty PyPI name mapped; inactive mapping rows kept; the mapping deduplicated on the raw name;
  - exceptions: non-pending recipes excepted; the PyPI side not folded;
  - upstream TSV: mapped packages in it; one source per package only; recipe URLs not split; a project path not cut;
  - manifest and inputs: a TSV header counted; `cfe-conda-name` ignored; `meta.yaml` scanned;
  - board: the board path not switched.
- **Real data:** over Story 37.2's live data root (its cf-graph `last_good.parquet`, 359,049 rows) and this checkout's
  7,561 `recipe.yaml` files (0 parse errors):
  - the recipes load in 13.0 s (31 s under a concurrent preflight, the review measured) and the node runs in 2.2 s;
  - 34,720 conda purls (and as many versioned) and 919,975 PyPI purls;
  - 22,454 mapping rows, 0 of them duplicates;
  - 2,498 recipe exceptions, mostly `pending-submission-to-conda-forge` recipes not yet on conda-forge;
  - 8,030 upstream purls: 7,558 GitHub, 163 rubygems, 143 npm, 140 GitLab, 17 Codeberg, 9 crates. None is malformed
    (no comma, space or archive file in a purl).
  - `load_export_purls` reads the manifest's 6 rows.

## Spec Change Log

- 2026-10-23, independent review (FAIL, 1 blocker), fixed on the same branch:
  - B1: raw recipe URLs went straight into `upstream_purl`, which legacy only ever fed URLs its Phase K had built.
    150 of 8,032 upstream rows were malformed: 130 GitHub purls from comma-joined URL fields
    (`pkg:github/krlmlr/bindr, https:`) and 20 GitLab purls named by a tarball or a tree path. A field is now split
    into its URLs, and a GitLab or Codeberg URL is cut to its project before `upstream_purl`.
  - Should-fix: the mapping TSV deduplicated before G98 normalization, so 186 lines repeated
    (`alibabacloud_credentials_api` and `alibabacloud-credentials-api`). It now deduplicates on the normalized name.
  - Nits: the node's timeout sits in the derived_artifacts block; `derived_purl_artifacts` has `overwrite: true`, so
    no partition from an earlier run survives; the run times are re-measured above.
- 2026-10-23: drafted from Story 37.8 and DW-atlas-37-8-1.

## Review Triage Log

- 2026-10-23, review 1 (independent subagent, read the diff against this spec): FAIL, with 1 blocker, 1 should-fix and
  3 nits, all addressed (Spec Change Log).
  - Its in-memory reproduction against Story 37.2's live root matched these, byte for byte, in content and order:
    - `purls_pypi.txt` and legacy `pypi_purl_lines`;
    - the exceptions and legacy `recipe_exception_lines`;
    - the conda order and SQLite's BINARY collation.
  - It confirmed that the cf-graph is fetched once per session, and that Kedro makes the recipes path absolute.
  - The reviewer left a scratch directory, `tmp_6wpmxjz/`, inside that data root and could not remove it; it is the
    operator's to delete. Nothing reads it.
