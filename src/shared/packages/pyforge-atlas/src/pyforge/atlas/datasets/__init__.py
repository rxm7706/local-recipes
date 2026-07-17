"""pyforge-atlas custom Kedro datasets.

Story A3 — ``IncrementalParquetDataset`` TTL/checkpoint primitive (AD-5) that the
15 flipped catalog entries resolve to.

Story B1 — the two request-parameterized API datasets (the B1 catalog FLIPs): per-
package anaconda downloads + per-query GitHub requests, each owning the request
parameterization + rate-limit discipline (AD-2, THE CRUX), plus the pure rate-limit
scheduler / fetcher-client primitives they share.
"""

from .incremental_parquet import IncrementalParquetDataset
from .rate_limit import (
    FetcherClient,
    FetchError,
    RateLimitedScheduler,
    StubFetcherClient,
    parse_retry_after,
    resolve_worker_count,
)
from .request_datasets import AnacondaDownloadsDataset, GitHubRequestDataset

__all__ = [
    "IncrementalParquetDataset",
    "AnacondaDownloadsDataset",
    "GitHubRequestDataset",
    "RateLimitedScheduler",
    "FetcherClient",
    "StubFetcherClient",
    "FetchError",
    "parse_retry_after",
    "resolve_worker_count",
]
