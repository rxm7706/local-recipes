"""Phase P two-layer BigQuery cost-gate tests (Story B2, THE CRUX / AC-4 / AD-10).

The cost gate is proven against a STUBBED BigQuery client (the lean env carries no
google-cloud-bigquery; credentialed runs are attended-only per NFR-2 / AD-11). Covers:
the free dry-run preflight + cap abort, the server-side ``maximum_bytes_billed`` hard cap
+ ``job_timeout_ms``, the D1 literal-TIMESTAMP-bounds discipline, and the AD-6
admin-opt-in no-op.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.datasets import BigQueryDownloadsDataset, PhasePCostAbort

# A query template with literal TIMESTAMP bounds on the `timestamp` column (D1 — NOT
# _PARTITIONDATE, which the code rejects).
_QUERY = (
    "SELECT file.project AS pypi_name, COUNT(*) AS downloads "
    "FROM `bigquery-public-data.pypi.file_downloads` "
    "WHERE timestamp >= TIMESTAMP('{start_ts}') AND timestamp < TIMESTAMP('{end_ts}') "
    "GROUP BY pypi_name"
)


class _StubJob:
    def __init__(self, total_bytes=None, df=None):
        self.total_bytes_processed = total_bytes
        self._df = df

    def result(self):
        return self

    def to_dataframe(self):
        return self._df


class _StubBQClient:
    """Records every query + job_config; returns dry-run bytes or a result frame."""

    def __init__(self, dry_bytes: int, result_df: pd.DataFrame):
        self.dry_bytes = dry_bytes
        self.result_df = result_df
        self.calls: list[tuple] = []

    def query(self, sql, job_config=None):
        self.calls.append((sql, dict(job_config)))
        if job_config.get("dry_run"):
            return _StubJob(total_bytes=self.dry_bytes)
        return _StubJob(df=self.result_df)


def _make_job_config(**kw):
    # In real runs this builds a vendor QueryJobConfig; the stub keeps it a plain dict so
    # no google.cloud.bigquery symbol is imported anywhere in the package (no-inline-IO).
    return dict(kw)


def _dataset(client, **over):
    return BigQueryDownloadsDataset(
        query_template=_QUERY,
        client=client,
        make_job_config=_make_job_config,
        usd_per_tb=6.25,
        max_cost_usd=10.0,
        max_cost_first_pull_usd=100.0,
        job_timeout_ms=600_000,
        **over,
    )


# -- D1: literal TIMESTAMP bounds, NOT _PARTITIONDATE ------------------------

def test_build_query_uses_literal_timestamp_bounds():
    ds = _dataset(None)
    sql = ds.build_query("2026-01-01 00:00:00 UTC", "2026-04-01 00:00:00 UTC")
    assert "TIMESTAMP('2026-01-01 00:00:00 UTC')" in sql
    assert "_PARTITIONDATE" not in sql


def test_build_query_rejects_partitiondate_template():
    ds = BigQueryDownloadsDataset(
        query_template="SELECT 1 WHERE _PARTITIONDATE >= '{start_ts}'",
        make_job_config=_make_job_config,
    )
    with pytest.raises(ValueError, match="_PARTITIONDATE"):
        ds.build_query("a", "b")


# -- Layer 1: free dry-run preflight + cap abort -----------------------------

def test_preflight_estimate_comes_from_dry_run_bytes():
    # 1 TiB scanned -> $6.25 at 6.25 $/TiB
    client = _StubBQClient(dry_bytes=1_000_000_000_000, result_df=pd.DataFrame())
    ds = _dataset(client)
    bytes_processed, est_usd = ds.preflight(ds.build_query("a", "b"))
    assert bytes_processed == 1_000_000_000_000
    assert est_usd == pytest.approx(6.25)
    assert client.calls[0][1]["dry_run"] is True  # the preflight IS a dry run


def test_run_gated_aborts_above_cap(monkeypatch):
    monkeypatch.setenv("PHASE_P_ENABLED", "1")
    # ~9.5 TiB -> ~$59, far above the $10 incremental cap (the 2026-06-12 real cost)
    client = _StubBQClient(dry_bytes=9_500_000_000_000, result_df=pd.DataFrame())
    ds = _dataset(client)
    with pytest.raises(PhasePCostAbort) as exc:
        ds.run_gated("2026-01-01 00:00:00 UTC", "2026-04-01 00:00:00 UTC")
    assert exc.value.bytes_processed == 9_500_000_000_000  # cites the dry-run, not a literal
    # aborted at the dry-run -> the real (non-dry) query was NEVER issued
    assert all(c[1]["dry_run"] for c in client.calls)


# -- Layer 2: server-side maximum_bytes_billed + job_timeout_ms --------------

def test_run_gated_within_cap_sets_hard_cap_and_timeout():
    monkeypatch_env("PHASE_P_ENABLED", "1")
    result = pd.DataFrame({"pypi_name": ["numpy"], "downloads": [123]})
    client = _StubBQClient(dry_bytes=100_000_000_000, result_df=result)  # ~$0.625, under cap
    ds = _dataset(client)
    try:
        out = ds.run_gated("2026-01-01 00:00:00 UTC", "2026-04-01 00:00:00 UTC")
    finally:
        monkeypatch_env("PHASE_P_ENABLED", None)
    assert out.equals(result)
    real_call = [c for c in client.calls if not c[1]["dry_run"]][0]
    cfg = real_call[1]
    # maximum_bytes_billed = int((cap/usd_per_tb)*1e12) for the $10 incremental cap
    assert cfg["maximum_bytes_billed"] == int((10.0 / 6.25) * 1_000_000_000_000)
    assert cfg["job_timeout_ms"] == 600_000


def test_first_pull_uses_the_higher_cap():
    monkeypatch_env("PHASE_P_ENABLED", "1")
    result = pd.DataFrame({"pypi_name": ["numpy"], "downloads": [1]})
    # ~$59 — above the $10 incremental cap but under the $100 first-pull cap
    client = _StubBQClient(dry_bytes=9_500_000_000_000, result_df=result)
    ds = _dataset(client)
    try:
        out = ds.run_gated("a", "b", first_pull=True)  # first pull -> $100 cap -> allowed
    finally:
        monkeypatch_env("PHASE_P_ENABLED", None)
    assert not out.empty
    real_cfg = [c for c in client.calls if not c[1]["dry_run"]][0][1]
    assert real_cfg["maximum_bytes_billed"] == int((100.0 / 6.25) * 1_000_000_000_000)


# -- AD-6: admin-opt-in, never a default schedule ----------------------------

def test_disabled_load_no_ops():
    monkeypatch_env("PHASE_P_ENABLED", None)
    ds = _dataset(_StubBQClient(1, pd.DataFrame()))
    assert ds.load() is None  # PHASE_P off -> no BigQuery job (mode-machine _phase_p_skip)


def test_run_gated_raises_when_disabled():
    monkeypatch_env("PHASE_P_ENABLED", None)
    ds = _dataset(_StubBQClient(1, pd.DataFrame()))
    with pytest.raises(RuntimeError, match="disabled"):
        ds.run_gated("a", "b")


def test_is_enabled_only_literal_one():
    import os

    for val, expected in (("1", True), ("true", False), ("0", False), ("", False)):
        os.environ["PHASE_P_ENABLED"] = val
        assert BigQueryDownloadsDataset.is_enabled() is expected
    os.environ.pop("PHASE_P_ENABLED", None)
    assert BigQueryDownloadsDataset.is_enabled() is False


# -- review-hardening: construction + preflight guards -----------------------

def test_malformed_env_does_not_crash_construction(monkeypatch):
    # a typo'd PHASE_P_* env must fall back to the default, not raise at construction.
    monkeypatch.setenv("PHASE_P_MAX_COST_USD", "not-a-number")
    monkeypatch.setenv("PHASE_P_JOB_TIMEOUT_MS", "garbage")
    ds = BigQueryDownloadsDataset(query_template=_QUERY, make_job_config=_make_job_config)
    assert ds._max_cost_usd == 10.0  # default
    assert ds._job_timeout_ms == 600_000  # default


def test_zero_price_rejected_at_construction():
    with pytest.raises(ValueError, match="usd_per_tb must be > 0"):
        BigQueryDownloadsDataset(query_template=_QUERY, make_job_config=_make_job_config, usd_per_tb=0)


def test_dry_run_none_bytes_fails_closed():
    class _NoBytesJob:
        total_bytes_processed = None

        def result(self):
            return self

        def to_dataframe(self):
            return pd.DataFrame()

    class _NoBytesClient:
        def query(self, sql, job_config=None):
            return _NoBytesJob()

    ds = _dataset(_NoBytesClient())
    with pytest.raises(RuntimeError, match="cannot estimate cost"):
        ds.preflight(ds.build_query("a", "b"))


# small env helper (avoids a module-level monkeypatch fixture dependency)
def monkeypatch_env(key, value):
    import os

    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
