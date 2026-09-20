"""pyforge-atlas custom Kedro datasets.

Story A3 — ``IncrementalParquetDataset`` TTL/checkpoint primitive (AD-5) that the
15 flipped catalog entries resolve to.

Story B1 — the two request-parameterized API datasets (the B1 catalog FLIPs): per-
package anaconda downloads + per-query GitHub requests, each owning the request
parameterization + rate-limit discipline (AD-2, THE CRUX), plus the pure rate-limit
scheduler / fetcher-client primitives they share.

Story B2 — ``PyPIJsonRequestDataset`` (the pypi_json_raw FLIP: per-project
``/pypi/<name>/json`` fan-out with the DW-B1-2 ``acquire()`` wiring) + the Phase P
``BigQueryDownloadsDataset`` (the two-layer cost gate, authored + fixture-tested;
credentialed materialization attended-only) + ``coerce_cvss_score`` (AC-3(b) vdb
ScoreType unwrap, boundary layer).
"""

from .basilisk import (
    BASILISK_QUERYBATCH_MAX,
    BasiliskBatchDataset,
    BasiliskDetailDataset,
    BasiliskPackagesDataset,
    build_conda_purl,
    chunk_queries,
    parse_basilisk_packages_response,
)
from .core_sources import (
    CfGraphTarballDataset,
    CondaChanneldataDataset,
    CondaRepodataDataset,
    CrossChannelRepodataDataset,
    FeedstockOutputsArchiveDataset,
    ParselmouthMappingDataset,
    PyPISimpleIndexDataset,
    S3DownloadStatsDataset,
    channeldata_json_to_rows,
    parse_cf_graph_tarball,
    parse_feedstock_outputs_zip,
    parse_pypi_simple_index,
    repodata_json_to_rows,
)
from .identity_sources import (
    LocalRecipesOverlayDataset,
    OpenTeamsBoardDataset,
    PurlAssociatorMappingsDataset,
    StagedRecipesPRDataset,
    parse_openteams_board_nodes,
    parse_pr_files_response,
    parse_purl_associator_index,
    parse_recipe_dir,
    parse_staged_pr_page,
)
from .incremental_parquet import IncrementalParquetDataset
from .migration_status import (
    ACTIVE_CATEGORIES,
    BLOCKER_BUCKETS,
    CATEGORY_FILES,
    EXCLUDED_STATUS_FILES,
    MIGRATION_BUCKETS,
    MigrationCategoryDataset,
    MigrationDetailDataset,
    migration_names,
)
from .rate_limit import (
    FetcherClient,
    FetchError,
    RateLimitedScheduler,
    StubFetcherClient,
    parse_retry_after,
    resolve_worker_count,
)
from .refresh import (
    LEGACY_REFRESH_TTLS,
    VULN_DB_ENV_RESOURCE,
    WEEKLY_SECONDS,
    ExternalRefreshDataset,
    MappingCacheDataset,
    OSVOfflineStoreDataset,
    RefreshRequest,
    RequiredResource,
    StalenessMarker,
    VDBStoreDataset,
)
from .request_datasets import (
    AnacondaDownloadsDataset,
    BigQueryDownloadsDataset,
    GitHubRequestDataset,
    PhasePCostAbort,
    PyPIBigQueryDownloadsDataset,
    PyPIJsonFanOutDataset,
    PyPIJsonRequestDataset,
)
from .sbom_intake import (
    SbomIntakeDataset,
    TransitiveResolverDataset,
    normalize_ws,
    parse_conda_list_text,
    parse_cyclonedx,
    parse_intake,
    parse_pip_list_text,
    parse_requirements_txt,
)
from .tier3_sources import (
    DebianPackagesDataset,
    FedoraPackagesDataset,
    HomebrewPackagesDataset,
    NixpkgsPackagesDataset,
    SpackPackagesDataset,
    parse_debian_packages_control,
    parse_fedora_packages,
    parse_homebrew_formulae_json,
    parse_nixpkgs_packages_json,
    parse_spack_packages,
)
from .upstream_discovery import (
    AboutMaintainersDataset,
    AnacondaDist2026Dataset,
    AossPremiumPythonDataset,
    TrackedSeedDataset,
    TrendingSnapshotDataset,
    parse_about_readme,
    parse_anaconda_dist_html,
    parse_aoss_premium_doc,
    parse_aoss_python_package_names,
    parse_search_api_response,
    parse_trending_html,
    read_tracked_seed,
)
from .vcs_sources import (
    RegistryUpstreamDataset,
    VcsHostSeedDataset,
)
from .vdb_boundary import coerce_cvss_score
from .vulnerability_feeds import (
    CisaKevDataset,
    CweCatalogDataset,
    EpssFeedDataset,
    parse_cisa_kev_catalog,
    parse_cwe_catalog_zip,
    parse_epss_csv_gz,
)

__all__ = [
    "IncrementalParquetDataset",
    "AnacondaDownloadsDataset",
    "GitHubRequestDataset",
    "PyPIJsonRequestDataset",
    "PyPIJsonFanOutDataset",
    "PyPIBigQueryDownloadsDataset",
    "BigQueryDownloadsDataset",
    "PhasePCostAbort",
    "coerce_cvss_score",
    "RateLimitedScheduler",
    "FetcherClient",
    "StubFetcherClient",
    "FetchError",
    "parse_retry_after",
    "resolve_worker_count",
    # Story B5 — external-refresh assets (§ 3.4)
    "ExternalRefreshDataset",
    "VDBStoreDataset",
    "OSVOfflineStoreDataset",
    "MappingCacheDataset",
    "RequiredResource",
    "RefreshRequest",
    "StalenessMarker",
    "VULN_DB_ENV_RESOURCE",
    "LEGACY_REFRESH_TTLS",
    "WEEKLY_SECONDS",
    # Story B7 — Universal SBOM intake (§ 4.10) + transitive resolver (FR-17)
    "SbomIntakeDataset",
    "TransitiveResolverDataset",
    "normalize_ws",
    "parse_intake",
    "parse_requirements_txt",
    "parse_pip_list_text",
    "parse_conda_list_text",
    "parse_cyclonedx",
    # Story B8 — Basilisk conda-native vulnerability source (FR-19)
    "BasiliskBatchDataset",
    "BasiliskDetailDataset",
    "chunk_queries",
    "build_conda_purl",
    "BASILISK_QUERYBATCH_MAX",
    # Story B10 — conda-forge-bot-data migration-status source (FR-21)
    "MigrationCategoryDataset",
    "MigrationDetailDataset",
    "migration_names",
    "CATEGORY_FILES",
    "ACTIVE_CATEGORIES",
    "MIGRATION_BUCKETS",
    "BLOCKER_BUCKETS",
    "EXCLUDED_STATUS_FILES",
    # Story 13.1 — GitHub-trending discovery ingest (CAP-1, FR-64)
    "TrendingSnapshotDataset",
    "parse_trending_html",
    "parse_search_api_response",
    # Story 21.4 — Tier 1 catalog sources (CAP-2): Basilisk packages, Anaconda Dist,
    # AOSS premium (external-refresh) + the generic tracked-seed reader (AOSS free)
    "BasiliskPackagesDataset",
    "parse_basilisk_packages_response",
    "AnacondaDist2026Dataset",
    "parse_anaconda_dist_html",
    "AossPremiumPythonDataset",
    "parse_aoss_premium_doc",
    "parse_aoss_python_package_names",
    "TrackedSeedDataset",
    "read_tracked_seed",
    # Story 21.5 — Tier 2 catalog sources (CDO-ENT-CONDA): rxm7706/about maintainer
    # + co-maintainer feedstock lists (external-refresh)
    "AboutMaintainersDataset",
    "parse_about_readme",
    # Story 21.6 — identity join sources (CAP-3, Phase D): PURL Associator index,
    # OpenTeams board, staged-recipes PRs, local recipes filesystem overlay
    "PurlAssociatorMappingsDataset",
    "parse_purl_associator_index",
    "OpenTeamsBoardDataset",
    "parse_openteams_board_nodes",
    "StagedRecipesPRDataset",
    "parse_staged_pr_page",
    "parse_pr_files_response",
    "LocalRecipesOverlayDataset",
    "parse_recipe_dir",
    # Story 23.1 — Tier 3 OS-distro bulk indexes (homebrew/nixpkgs/spack/debian/fedora)
    "HomebrewPackagesDataset",
    "NixpkgsPackagesDataset",
    "SpackPackagesDataset",
    "DebianPackagesDataset",
    "FedoraPackagesDataset",
    "parse_homebrew_formulae_json",
    "parse_nixpkgs_packages_json",
    "parse_spack_packages",
    "parse_debian_packages_control",
    "parse_fedora_packages",
    # Core raw-source parsers + datasets (B1 ingest gap)
    "FeedstockOutputsArchiveDataset",
    "CondaRepodataDataset",
    "CondaChanneldataDataset",
    "CfGraphTarballDataset",
    "S3DownloadStatsDataset",
    "parse_feedstock_outputs_zip",
    "repodata_json_to_rows",
    "channeldata_json_to_rows",
    "parse_cf_graph_tarball",
    # Vulnerability side-catalog feeds (KEV / EPSS / CWE)
    "CisaKevDataset",
    "EpssFeedDataset",
    "CweCatalogDataset",
    "parse_cisa_kev_catalog",
    "parse_epss_csv_gz",
    "parse_cwe_catalog_zip",
    # VCS / registry live sources (vcs_health)
    "VcsHostSeedDataset",
    "RegistryUpstreamDataset",
]
