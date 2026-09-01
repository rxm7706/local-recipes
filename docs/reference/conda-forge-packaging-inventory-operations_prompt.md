# Revised Master Prompt — Consolidated Verified Package Inventory (Standalone)

You are an **Expert Python Ecosystem Analyst and Open Source Packaging Specialist**.

Your job is to build a **single consolidated, deduplicated, verified package inventory** from the Atlas Kedro data plane (Story 23.8/23.9 workbook-free path), then output:
1. Full inventory (14 columns) — durable copy: `derived/inventory_verified_packages/inventory_verified_packages.parquet`; optional CSV `cdao_consolidated_inventory_verified_all_packages.csv`
2. Dated OpenTeams universe (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`) — durable copy: `derived/identity_complete_export/identity_complete_export.parquet` (ranking + identity handoff columns). Historical workbook tab names (`inventory-2026-08-12`, `identity-2026-08-12`) are retired.
3. `cdao_consolidated_inventory_verified_all_packages.md`
4. A brief terminal summary in the exact metrics format below.

Do **not** depend on any pre-existing repo script. Execute the full workflow yourself.

---

## 1) Inputs (replace paths as needed)

- Atlas data root (`PYFORGE_ATLAS_DATA_ROOT`) — **required (Story 23.9)**: pass
  `--live-catalog PATH` to `conda-forge-packaging-inventory-operations_metrics.py`.
  The package universe is read from `inventory_universe.parquet`; verified
  deliverable A rows from `inventory_verified_packages.parquet`; the AOSS-Free
  Mason queue from `inventory_aoss_free_queue.parquet`. See
  [`conda-forge-packaging-inventory-operations_replay.md`](conda-forge-packaging-inventory-operations_replay.md)
  execution mode 5 for the exact CLI shape.  
  `{{PYFORGE_ATLAS_DATA_ROOT}}`
- OpenTeams export (`.tsv`):  
  `{{OPENTEAMS_TSV_PATH}}`
- Optional curated groups file (`.json`):  
  `{{CURATED_GROUPS_JSON_PATH}}`  
  If missing, continue with empty curated groups and record that in report notes.

Catalog sources (Story 23.8 `inventory_universe.parquet` — replaces workbook sheet parsing):  
`tab:CDO-ENT-JFROG`, `tab:GAOSS-Free`, `tab:GAOSS-Premium`, `tab:Anaconda-Main`, `tab:Anaaconda-Dist`, `tab:Conda-Forge`, `tab:Basilisk`, `tab:OpenTeams`, `tab:CDO-ENT-CONDA`.

Historical output snapshot tabs (retired 2026-08-30, Story 23.9 — do **not** ingest):  
`verified-all-packages`, `inventory-2026-08-12`, `identity-2026-08-12` in `docs/Analysis_Dataset-2026-08-12.xlsx`.

Must-include (every parseable library from these two is in the final inventory; 100% inclusion):
- `CDO-ENT-JFROG` is the CDO JFrog/Artifactory consumption inventory (`name` plus Artifactory/internal-use/packaging-tier columns). Formerly `Analysis_Dataset-2026-07-19`. `10kOpen` is a clone of this tab — do not double-count.
- `CDO-ENT-CONDA` is the CDO enterprise conda-forge feedstock inventory (`Package_Name`, `Role`, `Feedstock`).

OpenTeams 1:1 packaging tracker (live board
https://github.com/orgs/OpenTeams-WFT-CDO/projects/1/views/6?sliceBy%5Bvalue%5D=OSS+Enhancements+%28Conda+Forge%2C+Pixi%2C+ect%29 ;
`openteams_project_1_board_raw.parquet` is the snapshot source): every parseable library in `CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA` must have exactly one issue titled `[Conda-Forge Packaging] {name}` (example `[Conda-Forge Packaging] grpcio`). One name per issue. CVE `|` titles do not count.

---

## 2) External sources to integrate

Use these sources and attribute packages to each source:

1. Anaconda Distribution 2026.x page:  
   `https://www.anaconda.com/docs/getting-started/anaconda/release/2026.x`
2. Anaconda main channel package index.
3. conda-forge channel package index.
4. Basilisk package/advisory surface:  
   `https://basilisk.prefix.dev/?view=all`  
   API docs context: `https://prefix-dev.github.io/basilisk/docs/api/`
5. Google AOSS free tier python packages:  
   `https://docs.cloud.google.com/assured-open-source-software/docs/supported-packages#python`
6. Google AOSS premium tier snapshot:  
   `https://web.archive.org/web/20260419090548/https://docs.cloud.google.com/security-command-center/docs/aoss-supported-packages-premium#python`
7. Maintainer/co-maintainer feedstocks from:  
   `https://raw.githubusercontent.com/rxm7706/about/main/README.md`  
   Parse both sections:
   - `List Of FeedStocks - As Maintainer`
   - `List Of FeedStocks - As Co-Maintainer`
8. Curated groups from provided JSON (if available): Apache, Django, Linux AI & Data, NumFOCUS, Jazzband, FINOS, PSF, PyPA, Trendshift, Google AOSS, Microsoft, Kedro, BMAD.

If any live source is unavailable, fallback to the nearest materialized Atlas Parquet when possible and document the fallback.

---

## 3) Deep parsing requirements

Parse **all catalog sources** from `inventory_universe.parquet` and extract package candidates from:

1. Direct package columns (case-insensitive names), including:
   - `name`, `Package_Name`, `raw_names`, `Item`, `pypi_name`, `conda_forge_name`, `import_name`
2. Single-column package lists.
3. OpenTeams-style title parsing:
   - Rule (a): if `Title` contains `|`, parse trailing text after `|`, split by comma/semicolon/slash.
   - Rule (b): if title matches `[Conda-Forge Packaging] ...`, parse trailing text and split.
   - Rule (c): otherwise ignore as non-package/meta row.

Normalization rules:
- lowercase
- trim whitespace
- replace `_` with `-`
- dedupe case-insensitively

Validity filters:
- keep only package-like tokens (`[a-z0-9][a-z0-9._-]*`)
- drop obvious non-package tokens (`new`, `ready`, `done`, `blocked`, `yes`, `no`, etc.)

Track per package:
- raw input names observed
- tab attribution(s)
- source attribution(s)
- any priority hints (`P1..P10`)
- availability hints from workbook (PyPI/conda-forge fields if present)

---

## 4) Verification logic

For each canonical package:

1. **PyPI verification (`PyPI_Verified`)**
   - Primary: check PyPI existence via canonical endpoint (e.g., `/pypi/{pkg}/json` or `/project/{pkg}/`).
   - If rate/perf constraints prevent full live verification, use a capped live check + clearly documented fallback heuristic:
     - workbook hints
     - conda-forge presence as supportive signal
   - Mark Yes/No deterministically.

2. **conda-forge verification (`CondaForge_Verified`)**
   - Verify from conda-forge channel index/repodata and/or reliable feedstock mapping.
   - Mark Yes/No deterministically.

3. **Priority bucket**
   - Extract from available fields (e.g., `Priority`, `Priority_Bucket`), normalize to `P1..P10` where possible.
   - If missing, use `N/A`.

4. **Packaging candidate status**
   - `Already Packaged`: PyPI=Yes and conda-forge=Yes
   - `High Priority`: PyPI=Yes and conda-forge=No and priority in P1–P8
   - `Low Priority`: PyPI=Yes and conda-forge=No and priority in P9–P10 or unknown
   - `Not on PyPI`: PyPI=No

5. **Derived URL/PURL fields**
   - `PyPI_PURL`: `pkg:pypi/{package}` or `N/A`
   - `PyPI_Package_URL`: `https://pypi.org/project/{package}/` or `N/A`
   - `Conda-forge_PURL`: `pkg:conda/{package}` or `N/A`
   - `Conda-Forge_Package_URL`: `https://anaconda.org/conda-forge/{package}/` or `N/A`
   - `Conda-Forge_FeedStock_URL`: `https://github.com/conda-forge/{package}-feedstock` or `N/A`

Use a single UTC timestamp value for all rows: `Verification_Timestamp_UTC`.

---

## 5) Required CSV output schema (exact 14 columns)

Output files:
- Full inventory (exact 14 columns below) — workbook tab `verified-all-packages`; optional CSV `cdao_consolidated_inventory_verified_all_packages.csv`
- Dated OpenTeams universe (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA` only) — workbook tab `inventory-2026-08-12` in `docs/Analysis_Dataset-2026-08-12.xlsx`. Same 14 columns first, then appended handoff columns:
  `OpenTeams_Title`, `OpenTeams_Cohort` (`JFROG_NEW` / `JFROG_ON_CF` / `CONDA_ONLY`),
  `OpenTeams_Batch` (`Fix vulnerability` / `Create recipe` /
  `File OpenTeams tracking issue [Conda-Forge Packaging]` /
  `Already tracked`; was A / B / C / TRACKED), `OpenTeams_Labels`,
  `OpenTeams_Milestone`, `OpenTeams_Coverage` (`Have_Issue` / `Missing_Issue`),
  `OpenTeams_Issue_URL`, `Source_Repository_URL`.
  `Conda-Forge_FeedStock_URL` is the feedstock GitHub link (`N/A` if not on conda-forge).

Columns, exact order:
1. `Repository_Source`
2. `Role`
3. `Package_Input_Name`
4. `Core_Python_Package_Name`
5. `PyPI_Verified`
6. `CondaForge_Verified`
7. `Priority_Bucket`
8. `Packaging_Candidate_Status`
9. `PyPI_PURL`
10. `PyPI_Package_URL`
11. `Conda-forge_PURL`
12. `Conda-Forge_Package_URL`
13. `Conda-Forge_FeedStock_URL`
14. `Verification_Timestamp_UTC`

Notes:
- `Repository_Source` = primary attribution (deterministic precedence if multiple).
- `Role` = `Maintainer` / `Co-Maintainer` / `N/A` from rxm7706 about README feedstock lists.
- `Package_Input_Name` = representative original value (first stable raw token from inputs).
- `Core_Python_Package_Name` = normalized canonical package name.

---

## 6) Required markdown report

Output file: `cdao_consolidated_inventory_verified_all_packages.md`

Include sections:
1. Total final unique package count.
2. Packaging Candidate Status Breakdown.
3. Per-Worksheet Tab Package Inclusion & Verification Matrix:
   - tab name
   - raw supplied package count
   - included package count
   - inclusion %
4. Per-Source Package Inclusion & Verification Matrix:
   - source name
   - raw supplied package count
   - included package count
   - inclusion %
5. Primary Repository Source Attribution in Final Inventory.
6. OpenTeams-Style Portion Parsing Summary:
   - rows used by rule (a)
   - rows used by rule (b)
   - rows ignored by rule (c)
   - unique packages extracted from OpenTeams-style portion
7. Net-New Packages breakdown (define net-new as not on conda-forge).
8. Fallbacks/warnings section for unavailable live sources.

---

## 7) Terminal summary output (exact shape)

Print:

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

## 8) Quality gates (must pass before completion)

1. CSV has exactly 14 columns in exact order.
2. `Core_Python_Package_Name` is unique per row.
3. Markdown report includes all required sections.
4. Inclusion matrices are internally consistent with computed totals.
5. Terminal summary numbers match computed outputs.

If any gate fails, correct and rerun before finalizing.
