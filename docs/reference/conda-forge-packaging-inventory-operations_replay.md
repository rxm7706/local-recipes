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
Build a single, consolidated, verified package inventory across all workbook tabs and integrated sources, with PyPI + conda-forge verification, packaging status buckets, and source/tab attribution.

Local Inputs:
1. Analysis workbook (`.xlsx`) export path.
2. OpenTeams export (`.tsv`) path.
3. Curated groups config (`conf/conda-forge-packaging-inventory-operations_curated_groups.json`).

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
1. Parse all workbook tabs dynamically, except output snapshot tabs `verified-all-packages`, `inventory-2026-08-12`, and `identity-2026-08-12` in `docs/Analysis_Dataset-2026-08-12.xlsx` (durable copies of prior-run output — never ingest as sources).
2. Extract package names from known package columns (`name`, `Package_Name`, `raw_names`, `Item`, etc.).
3. Must-include: every parseable name from `CDO-ENT-JFROG` (JFrog/Artifactory consumption inventory; formerly `Analysis_Dataset-2026-07-19`) and from `CDO-ENT-CONDA` is in the final inventory. `10kOpen` is a clone of the JFrog tab — do not double-count.
4. OpenTeams 1:1: every parseable name in `CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA` should have exactly one issue titled `[Conda-Forge Packaging] {name}` (OSS Enhancements project view; workbook `OpenTeams` tab is the snapshot). CVE `|` titles do not count. Report have / missing / surplus; 100% is the goal.
5. Parse OpenTeams-style title patterns:
   - Rule (a): if `Title` contains `|`, package list is trailing text after `|`, split by comma/semicolon/slash.
   - Rule (b): if `Title` matches `[Conda-Forge Packaging] ...`, parse trailing list.
   - Rule (c): ignore non-package rows.
6. Deduplicate package names case-insensitively after normalization (identity only — do not drop a `CDO-ENT-JFROG` or `CDO-ENT-CONDA` library).

Verification and classification:
1. Verify PyPI (`PyPI_Verified`) and conda-forge (`CondaForge_Verified`).
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
1. Full inventory (14 columns) — workbook tab `verified-all-packages`; optional CSV `cdao_consolidated_inventory_verified_all_packages.csv`
2. Dated OpenTeams 1:1 universe (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`) — workbook tab `inventory-2026-08-12` in `docs/Analysis_Dataset-2026-08-12.xlsx` (14 inventory columns + 8 handoff columns). Repo-root `cdao_consolidated_inventory-2026-08-12.csv` is not the stored copy.
3. Identity snapshot — workbook tab `identity-2026-08-12`, then **edit in place** the pinned secret gist file `mgmt-wf-python-modernization-identity.md` (`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`; gist id from `OPENTEAMS_IDENTITY_GIST_ID` / gitignored `conf/conda-forge-packaging-inventory-operations.local.env` / `--gist-id`; `--skip-gist` when no id). Do not create a new gist. Do not commit the id.
4. `cdao_consolidated_inventory_verified_all_packages.md`
5. [`docs/reference/conda-forge-packaging-inventory-operations_prompt.md`](conda-forge-packaging-inventory-operations_prompt.md)

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

Markdown report sections:
1. Total final unique package count.
2. Packaging Candidate Status Breakdown.
3. Per-Worksheet Tab Package Inclusion & Verification Matrix.
4. Per-Source Package Inclusion & Verification Matrix.
5. Primary Repository Source Attribution in Final Inventory.
6. OpenTeams-Style Portion Parsing Summary.
7. Net-New Packages breakdown.

Execution commands:
1. Fast mode (default):

```bash
python3 scripts/conda-forge-packaging-inventory-operations_metrics.py \
  --analysis-xlsx "docs/Analysis_Dataset-2026-08-12.xlsx" \
  --curated-config "conf/conda-forge-packaging-inventory-operations_curated_groups.json" \
  --output-csv "cdao_consolidated_inventory_verified_all_packages.csv" \
  --output-md "cdao_consolidated_inventory_verified_all_packages.md" \
  --skip-revised-prompt \
  --verify-mode fast
```

2. Strict mode:

```bash
python3 scripts/conda-forge-packaging-inventory-operations_metrics.py \
  --analysis-xlsx "docs/Analysis_Dataset-2026-08-12.xlsx" \
  --curated-config "conf/conda-forge-packaging-inventory-operations_curated_groups.json" \
  --output-csv "cdao_consolidated_inventory_verified_all_packages.csv" \
  --output-md "cdao_consolidated_inventory_verified_all_packages.md" \
  --skip-revised-prompt \
  --verify-mode strict \
  --strict-max-live-checks 5000 \
  --strict-fetch
```

3. Optional: include live HTML scraping for AOSS/Basilisk/Anaconda-release pages (off by default to avoid noisy token extraction):

```bash
python3 scripts/conda-forge-packaging-inventory-operations_metrics.py \
  --analysis-xlsx "docs/Analysis_Dataset-2026-08-12.xlsx" \
  --curated-config "conf/conda-forge-packaging-inventory-operations_curated_groups.json" \
  --verify-mode fast \
  --skip-revised-prompt \
  --use-live-html-sources
```

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
