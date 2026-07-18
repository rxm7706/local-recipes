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

from .incremental_parquet import IncrementalParquetDataset
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
from .rate_limit import (
    FetcherClient,
    FetchError,
    RateLimitedScheduler,
    StubFetcherClient,
    parse_retry_after,
    resolve_worker_count,
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
from .request_datasets import (
    AnacondaDownloadsDataset,
    BigQueryDownloadsDataset,
    GitHubRequestDataset,
    PhasePCostAbort,
    PyPIJsonRequestDataset,
)
from .vdb_boundary import coerce_cvss_score
from .basilisk import (
    BASILISK_QUERYBATCH_MAX,
    BasiliskBatchDataset,
    BasiliskDetailDataset,
    build_conda_purl,
    chunk_queries,
)
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

__all__ = [
    "IncrementalParquetDataset",
    "AnacondaDownloadsDataset",
    "GitHubRequestDataset",
    "PyPIJsonRequestDataset",
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
]
