# Verification matrix — `--live-catalog`

Companion to `SPEC.md`. Maps inventory fields to Kedro Parquet paths under
`PYFORGE_ATLAS_DATA_ROOT`. Metrics runner reads these directly; no duplicate
HTTP clients when `--live-catalog` is set.

| Inventory field / rule | Kedro source |
|------------------------|--------------|
| `PyPI_Verified` | `pypi_simple_index_raw`, `pypi_json_raw` |
| `CondaForge_Verified` | `core_channeldata_raw`, `pypi_conda_mapping` |
| `Source_Repository_URL` | channeldata URLs + `pypi_json_raw` / VCS pipeline |
| Basilisk membership | `discovery_basilisk_packages_raw` |
| AOSS free / premium | `discovery_aoss_free_python_raw`, `discovery_aoss_premium_python_raw` |
| Anaconda main / Dist | `core_anaconda_main_channeldata_raw`, `discovery_anaconda_dist_2026x_raw` |
| Cross-channel BOOLs | `pypi_cross_channel_flags` (+ SelfExplainML) |
| `identity_source`, `primary_purl`, `conda_purl` | `identity_packages_primary` |
| `OpenTeams_Issue_URL` | `openteams_project_1_board_raw` join |
| Feedstock / staged / local URLs | Phase D overlays |
| `Packaging_Candidate_Status` | `inventory_verified_packages` (Epic 23.4) |
| `P1`–`P10`, Score, Work | `inventory_priority_assignments` → `identity_complete_export` (Epic 23.3/23.5) |
| JFROG telemetry columns | `enterprise_jfrog_consumption.parquet` (Epic 23.2) |

## CLI contract (metrics)

New flags (proposed):

```
--live-catalog PATH   # PYFORGE_ATLAS_DATA_ROOT or explicit Parquet root
--live-catalog-only   # fail if any required dataset missing/stale
```

Documented Parquet paths per dataset in companion `catalog-sources.md` and
operator env block shipped with `pyforge-atlas-bootstrap`.

## Stays outside matrix until Epic 23 (CAP-8)

- Enterprise JFROG telemetry columns → **23.2** `enterprise_jfrog_consumption.parquet`
- Ranking / candidate status → **23.3–23.5** Kedro derived exports
- OpenTeams issue creation (optional; not data-closure required)
- Dashboard canvas generation → Epic 22 Vizro; DATA from **23.5** complete export
- Excel workbook tabs
