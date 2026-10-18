# Live sources — what fills each dataset, and how it is judged (CAP-64..CAP-68)

Companion to `SPEC.md` (minted 2026-10-18). One row per external source a plain or opted-in run reaches. **Parity
measure** is the legacy `cf_atlas.db` figure each story compares against on the same day; the legacy admin refresh of
2026-10-18 00:27 is the first reference (its Phases E, J and M read nothing, the same R1 break, so their rows name a
substitute oracle). **Credential:** `—` public, unauthenticated; `opt-in` runs only with
`PYFORGE_ATLAS_CREDENTIALED=1`.

| Source | Atlas datasets it fills | Legacy phase | Parity measure | Credential | Story |
|---|---|---|---|---|---|
| endoflife.date `api/all.json` | `pypi_endoflife_raw` → `seed_gaps_lts_registry_report` | `lts_registry_gap.py` | product list parses; report rows > 0 | — | 34.1 |
| SPDX `license-list-data` `licenses.json` | `seed_spdx_upstream_list_raw` → `seed_gaps_spdx_report` | `spdx_schema_gap.py` | license ids parse; report rows > 0 | — | 34.1 |
| conda-forge-bot-data `mappings/pypi/name_mapping.yaml` | `pypi_parselmouth_mapping_raw` → `pypi_conda_mapping` → H, R, S, release velocity | C | legacy C matched 11,005 conda rows | — | 34.2 |
| pypi.org `/pypi/<name>/json` (per mapped project) | `pypi_json_raw` → `pypi_current_versions`, `pypi_intelligence_enriched`, `pypi_intelligence_scored` | H | legacy H's eligible set (never fetched, serial moved, 30-day re-check) | — | 34.2 (candidates), 34.10 (coverage) |
| conda-forge-bot-data-node_attrs, -pr_info, -version_pr_info (sharded) | `core_cf_graph_raw` → `core_dependencies`, `core_feedstock_health`, `vcs_maintainers`, `vcs_package_maintainers`, Phase E fields | E, J, M | feedstock count vs `all_feedstocks.json`; edges vs node_attrs requirements (legacy reads 0 since the split) | — | 34.3 |
| `anaconda-package-data` monthly S3 parquet | `core_downloads` + 3 breakdowns, `core_version_download_history` | F (s3) | legacy F fetched 31,041 packages | — | 34.4 |
| Homebrew, Nixpkgs, Spack, Debian, Fedora indexes | 5 Tier-3 stores → `pypi_tier3_channel_flags` | — (new signal) | each store non-empty; flags rows > 0 | — | 34.5 |
| GitHub trending, about-maintainers, purl associator, Anaconda distribution 2026.x, AOSS premium | discovery stores → `trending_candidates_classified`, `enterprise_conda_maintainers`, identity enrichment | — | each store non-empty | — | 34.6 |
| appthreat vdb (vuln-db env), OSV bucket | `vulnerability_vdb_store`, `vulnerability_osv_offline_store` → `vulnerability_package_rollup`, `vulnerability_package_version_vulns` | G, G′ | legacy G scanned 33,841 | — | 34.7 |
| conda-forge-bot-data `status/migration_json` | migration category + detail → `vcs_migration_readiness` | — | 37 migration partitions (2026-10-17) | — | 34.8 |
| ClickHouse public PyPI mirror | `pypi_downloads_monthly` | P (default source) | legacy P upserted 1,000 rows | — | 34.9 |
| GitHub GraphQL (releases, tags; feedstock health) | `vcs_upstream_versions`, `vcs_live_health`, `vcs_archived_feedstocks` | K, E.5, N | legacy K fetched 23,896; N 28,682 feedstocks; E.5 marked 864 archived | opt-in | 35.1–35.3 |
| GitLab, Codeberg, npm, CRAN, CPAN, LuaRocks, crates, RubyGems, NuGet, Maven | `vcs_registry_versions`, GitLab/Codeberg upstream versions | K, L | legacy L fetched 375; K GitLab 400, Codeberg 26 | — (registries); opt-in where a host needs a token | 35.4 |
| api.basilisk.prefix.dev | `vulnerability_basilisk_advisories`, `…_details`, `…_rollup` | — | population ≈ `core_packages_enumerated` | — (open question: unattended or opt-in) | 36.1 |
| OpenTeams project board (GraphQL), staged-recipes PRs (REST) | identity sources → `identity_packages_primary`, identity exports, inventory priorities | — | rows per `identity_source` > 0 | opt-in | 36.2 |
| platform OLTP extract (canopy FR-47 Mode B) | `query_plane_estate_source` → `query_plane_estate` | — | open question: which tables | open question | 36.3 |

Out of scope: BigQuery Phase P (operator ruling 2026-10-17); the Artifactory AQL path (Story 24.2, ledger `blocked`
until the operator flips it).
