"""pyforge-atlas custom Kedro datasets (Story A3).

Exports the ``IncrementalParquetDataset`` TTL/checkpoint primitive (AD-5) that the
15 flipped catalog entries resolve to.
"""

from .incremental_parquet import IncrementalParquetDataset

__all__ = ["IncrementalParquetDataset"]
