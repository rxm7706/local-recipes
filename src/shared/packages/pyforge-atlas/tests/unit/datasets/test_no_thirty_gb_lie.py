"""``test_no_thirty_gb_lie`` — carried over to the dataset level (Story B2, AC-4 / THE CRUX).

The guard that the Phase P cost gate is NOT a lie: any "scans N GB / N TB" claim MUST be
derived from a DRY-RUN's ``total_bytes_processed``, NEVER a hardcoded literal. The
2026-06-12 BigQuery invoice surprise traced to a 2016 napkin number ("~30 GB scanned per
query, within free tier") copied through spec + code + docs without re-verification; the
real cost was ~9.5 TB (~$59), off by ~3,000×. This test pins the discipline: the cost
estimate is a pure function of the dry-run bytes, and no byte/GB magic constant lives in
the cost path.
"""

from __future__ import annotations

import inspect

import pandas as pd

from pyforge.atlas.datasets import BigQueryDownloadsDataset
from pyforge.atlas.datasets import request_datasets


class _StubJob:
    def __init__(self, total_bytes=None, df=None):
        self.total_bytes_processed = total_bytes
        self._df = df

    def result(self):
        return self

    def to_dataframe(self):
        return self._df


class _StubBQClient:
    def __init__(self, dry_bytes):
        self.dry_bytes = dry_bytes

    def query(self, sql, job_config=None):
        if job_config.get("dry_run"):
            return _StubJob(total_bytes=self.dry_bytes)
        return _StubJob(df=pd.DataFrame())


def _ds(client=None):
    return BigQueryDownloadsDataset(
        query_template="SELECT 1 WHERE timestamp >= TIMESTAMP('{start_ts}') AND timestamp < TIMESTAMP('{end_ts}')",
        client=client,
        make_job_config=lambda **kw: dict(kw),
        usd_per_tb=6.25,
    )


def test_cost_estimate_is_derived_from_dry_run_bytes_not_a_literal():
    ds = _ds()
    # doubling the (dry-run) scanned bytes doubles the estimated cost -> it is a pure
    # function of the measured bytes, not a fixed "30 GB" literal.
    assert ds.estimate_cost_usd(2_000_000_000_000) == 2 * ds.estimate_cost_usd(1_000_000_000_000)
    # exact formula: bytes / 1e12 (conservative decimal TB unit) * usd_per_tb
    assert ds.estimate_cost_usd(1_000_000_000_000) == 6.25


def test_preflight_reads_bytes_from_the_clients_dry_run():
    # the estimate must come from THIS run's dry-run, so different table states yield
    # different estimates (the exact failure mode the 2016 literal hid).
    small = _ds(_StubBQClient(dry_bytes=30_000_000_000))    # 30 GB
    big = _ds(_StubBQClient(dry_bytes=9_500_000_000_000))   # 9.5 TB (the real 2026 cost)
    q = "SELECT 1 WHERE timestamp >= TIMESTAMP('a') AND timestamp < TIMESTAMP('b')"
    small_bytes, small_usd = small.preflight(q)
    big_bytes, big_usd = big.preflight(q)
    assert small_bytes == 30_000_000_000 and big_bytes == 9_500_000_000_000
    # the ~3,000× real-vs-napkin gap is visible ONLY because the estimate tracks the
    # live dry-run — a literal would have reported the same (wrong) number for both.
    assert big_usd / small_usd > 100


def test_no_hardcoded_gb_byte_constant_in_the_cost_path():
    # structural guard: the cost path must not carry a hardcoded scan-size literal
    # masquerading as a cost (e.g. a `30_000_000_000` / "30 GB" napkin number). The only
    # byte constant allowed is the bytes-per-TiB unit conversion.
    src = inspect.getsource(request_datasets.BigQueryDownloadsDataset)
    for banned in ("30_000_000_000", "30 GB", "30GB", "within free tier"):
        assert banned not in src, f"cost path carries a napkin literal: {banned!r}"
    # the bytes/TiB unit constant is a documented conversion, not a cost literal
    assert "_BYTES_PER_TB" in inspect.getsource(request_datasets)
