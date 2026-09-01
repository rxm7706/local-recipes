# MASTER PROMPT V3.0 — Consolidated Inventory Replay (Reusable)

**Canonical runner script:** [`scripts/conda-forge-packaging-inventory-operations_metrics.py`](../../scripts/conda-forge-packaging-inventory-operations_metrics.py)  
**Prompt:** [`docs/reference/conda-forge-packaging-inventory-operations_prompt.md`](conda-forge-packaging-inventory-operations_prompt.md)  
**Curated groups config:** [`conf/conda-forge-packaging-inventory-operations_curated_groups.json`](../../conf/conda-forge-packaging-inventory-operations_curated_groups.json)

## Prompt ↔ Script sync contract (required)

1. This prompt, the runner script, and curated config are a coupled set.
2. Any new analysis step, source, parsing rule, verification rule, status bucket, output column, or report section must update all relevant files in the same commit.
3. Do not merge prompt-only behavior changes without script implementation updates.
4. Do not merge script behavior changes without prompt updates.

---

Use the following replay prompt with your coding agent:

## Replay Prompt

Act as an Expert Python Ecosystem Analyst and Open Source Packaging Specialist.

Goal:
Build a single, consolidated, verified package inventory from the Atlas Kedro data plane (Story 23.9 workbook-free path), with PyPI + conda-forge verification, packaging status buckets, and source attribution already materialized in Parquet exports.

Local Inputs:
1. Atlas data root (`PYFORGE_ATLAS_DATA_ROOT`) — **required** for all quartet scripts.
2. OpenTeams export (`.tsv`) path (historical; universe now comes from Kedro).
3. Curated groups config (`conf/conda-forge-packaging-inventory-operations_curated_groups.json`) (historical; Kedro owns ingestion).

Historical: the analysis workbook (`docs/Analysis_Dataset-2026-08-12.xlsx`) and its tab names are retired as inputs (Story 23.9). Passing `--analysis-xlsx`, `--xlsx`, `--tab`, or `--tab-out` exits 2.

Required integrated sources:
1. Anaconda Distribution latest package table (`2026.x`).
2. Anaconda main channel package index.
3. conda-forge channel package index.
4. Basilisk package/advisory surface (workbook tab `Basilisk` is the offline fallback; do not scrape the HTML SPA).
5. Google AOSS Free Python packages.
6. Google AOSS Premium Python packages (archive snapshot).
7. Maintained + co-maintained feedstocks from `https://raw.githubusercontent.com/rxm7706/about/main/README.md`.
8. Curated groups from local config.

Parsing requirements:
1. Parse all workbook tabs dynamically, except output snapshot tabs `verified-all-packages`, `inventory-2026-08-12`, and `identity-2026-08-12` in `docs/Analysis_Dataset-2026-08-12.xlsx` (durable copies of prior-run output — never ingest as sources). `OUTPUT_TABS` is a dated hardcode: a differently-dated output tab (e.g. `identity-2026-08-20`) is NOT in this set and IS parsed as a source sheet — it contributes nothing only because its `Package` column isn't one of the known package columns (bullet 2). The workbook-free path (execution mode 5, Story 23.8) removes this whole class of bug by construction (no sheet parsing at all).
2. Extract package names from known package columns (`name`, `Package_Name`, `raw_names`, `Item`, etc.).
3. Must-include: every parseable name from `CDO-ENT-JFROG` (JFrog/Artifactory consumption inventory; formerly `Analysis_Dataset-2026-07-19`) and from `CDO-ENT-CONDA` is in the final inventory. `10kOpen` is a clone of the JFrog tab — do not double-count.
4. OpenTeams 1:1: every parseable name in `CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA` should have exactly one issue titled `[Conda-Forge Packaging] {name}` (OSS Enhancements project view; workbook `OpenTeams` tab is the snapshot). CVE `|` titles do not count. Report have / missing / surplus; 100% is the goal.
5. Parse OpenTeams-style title patterns:
   - Rule (a): if `Title` contains `|`, package list is trailing text after `|`, split by comma/semicolon/slash.
   - Rule (b): if `Title` matches `[Conda-Forge Packaging] ...`, parse trailing list.
   - Rule (c): ignore non-package rows.
6. Deduplicate package names case-insensitively after normalization (identity only — do not drop a `CDO-ENT-JFROG` or `CDO-ENT-CONDA` library).

Verification and classification:
1. Verify PyPI (`PyPI_Verified`) and conda-forge (`CondaForge_Verified`). These may
   source from live HTTP fetches, local snapshot files (`--cf-channeldata` /
   `--pypi-simple` / `--parselmouth`), or (Story 21.3) directly from the
   pyforge-atlas Kedro data plane's Parquet outputs via `--live-catalog` —
   see execution mode 4 below. When `--analysis-xlsx` is also omitted (Story
   23.8, execution mode 5), the package universe itself is ALSO read from that
   same Kedro data plane (`inventory_universe.parquet`) instead of the
   workbook's sheets.
2. Assign `Packaging_Candidate_Status`:
   - Already Packaged: PyPI = Yes and conda-forge = Yes
   - High Priority Candidate: PyPI = Yes and conda-forge = No and Priority P1–P8
   - Low Priority Candidate: PyPI = Yes and conda-forge = No and Priority P9–P10 or unknown
   - Conda-Forge Only: PyPI = No and conda-forge = Yes
   - Not on PyPI: PyPI = No and conda-forge = No
3. Emit URLs/PURLs:
   - `PyPI_PURL`: `pkg:pypi/{package}` or `N/A`
   - `PyPI_Package_URL`: `https://pypi.org/project/{package}/` or `N/A`
   - `Conda-forge_PURL`: `pkg:conda/{package}?channel=conda-forge` or `N/A`
   - `Conda-Forge_Package_URL`: `https://anaconda.org/conda-forge/{package}/` or `N/A`
   - `Conda-Forge_FeedStock_URL`: `https://github.com/conda-forge/{package}-feedstock` or `N/A`

Deliverables (local files):
1. Full inventory (14 columns) — `derived/inventory_verified_packages/inventory_verified_packages.parquet`; optional CSV `cdao_consolidated_inventory_verified_all_packages.csv`
2. Dated OpenTeams 1:1 universe (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`) — `derived/identity_complete_export/identity_complete_export.parquet` (ranking + identity handoff columns). Historical workbook tab `inventory-2026-08-12` is retired.
3. Identity snapshot — `identity_complete_export.parquet`, then **edit in place** the pinned secret gist files `mgmt-wf-python-modernization-identity.md` (row catalog) and `mgmt-wf-python-modernization-dashboards.md` (canvas summaries) (`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`; gist id from `OPENTEAMS_IDENTITY_GIST_ID` / gitignored `conf/conda-forge-packaging-inventory-operations.local.env` / `--gist-id`; `--skip-gist` when no id). Do not create a new gist. Do not commit the id. `--create-issues` is a separate, **live and irreversible** flag: it opens one GitHub issue (+ adds it to OpenTeams project 1) per record still missing `OpenTeams_Issue_URL`. Absent (the default), the run is dry-run only — it prints/returns what would be created and makes no `gh` mutation call.

   **Story 21.7 (quartet thin-out):** `main()` no longer fetches
   `ASSOCIATOR_URL`, the OpenTeams board, `feedstock-outputs.json`, or
   staged-recipes PRs itself — it reads the pyforge-atlas Kedro catalog's
   `identity_export_parquet` (Story 21.6's `upstream_discovery` Phase D
   join) via `PYFORGE_ATLAS_DATA_ROOT` (default `src/shared/packages/
   pyforge-atlas/data`; run `pixi run -e pyforge-atlas
   pyforge-atlas-bootstrap` first — a missing Parquet is a hard, named
   error, never a live-fetch fallback). The `--tab-in` / `--associator` /
   `--refresh-associator` / `--project-items` / `--feedstock-outputs` /
   `--staged-prs` / `--staged-open-prs` / `--recipes-dir` /
   `--refresh-staged-prs` flags are retired along with that fetch. Once
   generated, the identity tab is ranked by `priority.py` as before.
   `Local_Recipes_URL`/`Local_Build_Status` are the two columns the Parquet
   does NOT supply: both are always freshly re-derived from a live
   `recipes/` filesystem scan on every `main()`/`--gist-only` run, never
   read from the Parquet. `--gist-only` republishes without regenerating
   rows: it reads the same Parquet for identity columns and merges ranking
   columns (`P`/`Rank`/`Score`/`Work` + JFROG/priority fields) from the
   ranked identity tab by `Core_Python_Package_Name` — a name present in
   the Parquet with no match in the ranked tab is dropped from the
   published gist with a stderr warning (never silently, never a hard
   failure); the existing "identity tab missing ranking columns" error is
   unchanged.
4. `cdao_consolidated_inventory_verified_all_packages.md`
5. [`docs/reference/conda-forge-packaging-inventory-operations_prompt.md`](conda-forge-packaging-inventory-operations_prompt.md)
6. AOSS-Free extra Mason queue — dated CSV `aoss-free-queue-YYYY-MM-DD.csv` (same directory as `--output-csv`), columns `Package_Name` / `Reason` / `Verification_Timestamp_UTC`: `GAOSS-Free` names that are on PyPI, absent from conda-forge, and absent from the OpenTeams universe (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`). Never merges into or expands that universe (`write_aoss_free_queue`).
7. Ops + Artifactory/workbook dashboard canvases — `identity-ops.canvas.tsx` and `jfrog-workbook.canvas.tsx` (the second and third of the three Dream-specified dashboard views; catalog is `identity-2026-08-20.canvas.tsx` via `conda-forge-packaging-inventory-operations_priority.py`), written by `write_dashboard_markdown` alongside the gist dashboards markdown. Default paths are under the live Cursor project `canvases/` dir; override with `--ops-canvas PATH` / `--workbook-canvas PATH` (e.g. for offline tests). A canvas-write failure logs a warning and never blocks the gist publish.

Exact CSV columns (14):
1. Repository_Source
2. Role
3. Package_Input_Name
4. Core_Python_Package_Name
5. PyPI_Verified
6. CondaForge_Verified
7. Priority_Bucket
8. Packaging_Candidate_Status
9. PyPI_PURL
10. PyPI_Package_URL
11. Conda-forge_PURL
12. Conda-Forge_Package_URL
13. Conda-Forge_FeedStock_URL
14. Verification_Timestamp_UTC

Markdown report sections (Story 23.9 formatter — derived from export columns only):
1. Total final unique package count.
2. Count not on conda-forge.
3. AOSS-Free Mason queue row count.
4. Packaging Candidate Status Breakdown.
5. Primary Repository Source Attribution in Final Inventory.
6. Net-New Packages breakdown.

Historical workbook-era sections (per-tab matrix, OpenTeams parsing summary) live in Kedro Story 23.8/23.4 nodes — not recomputed in `metrics.py`.

Execution commands (Story 23.9 — workbook-free; `--analysis-xlsx` exits 2):

1. Default Atlas flow (formats Story 23.4 exports only):

```bash
python3 scripts/conda-forge-packaging-inventory-operations_metrics.py \
  --live-catalog "src/shared/packages/pyforge-atlas/data" \
  --output-csv "cdao_consolidated_inventory_verified_all_packages.csv" \
  --output-md "cdao_consolidated_inventory_verified_all_packages.md" \
  --skip-revised-prompt
```

2. Identity gist publish (reads `identity_complete_export.parquet`; ranking already on export):

```bash
python3 scripts/conda-forge-packaging-inventory-operations_openteams_identity.py \
  --gist-only --skip-gist
```

3. Priority ranked export shim (reads `inventory_priority_assignments.parquet`):

```bash
python3 scripts/conda-forge-packaging-inventory-operations_priority.py \
  --ranked-csv "identity-ranked.csv"
```

**Retired flags (Story 23.9, exit 2 with pointer):** `--analysis-xlsx`, `--xlsx`, `--tab-out`, `--tab`.

4. `--live-catalog` detail (Story 23.8/23.9): Kedro materializes
   `inventory_universe.parquet`, `inventory_verified_packages.parquet`, and
   `inventory_aoss_free_queue.parquet`. `metrics.py` reads the latter two and
   formats CSV/MD only. Identity/priority/dashboard scripts read
   `identity_complete_export.parquet` and `inventory_priority_assignments.parquet`.
   No `.xlsx` is opened anywhere in the quartet.

Terminal summary format must still include:

```text
=== MASTER PROMPT V3.0 EXECUTION SUMMARY METRICS ===

Total final unique packages processed: <number>
Count not on conda-forge: <number>
Count from analysis-dataset portion not on conda-forge: <number>
Count parsed from OpenTeams-style portion:
  - rows used by rule (a): <number>
  - rows used by rule (b): <number>
  - rows ignored by rule (c): <number>
  - unique packages extracted from that portion: <number>
```

---

For future reruns, replace only input paths (and optionally output paths).
