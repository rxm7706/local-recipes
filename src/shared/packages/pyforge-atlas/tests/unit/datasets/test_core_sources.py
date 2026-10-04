"""Core raw-source parser tests (Story B1 ingest gap closure).

Pure parser coverage only — no network. Dataset classes compose APIDataset and are
smoke-tested via catalog loadability + the core pipeline integration run.
"""

from __future__ import annotations

import io
import json
import tarfile
import zipfile

import pandas as pd
import pytest

from pyforge.atlas.datasets import (
    ParselmouthMappingDataset,
    channeldata_json_to_rows,
    parse_cf_graph_tarball,
    parse_feedstock_outputs_zip,
    repodata_json_to_rows,
)
from pyforge.atlas.datasets.core_sources import CondaChanneldataDataset


def _zip_with_outputs(entries: dict[str, dict]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for pkg, payload in entries.items():
            zf.writestr(f"feedstock-outputs-main/outputs/{pkg}.json", json.dumps(payload))
    return buf.getvalue()


def test_parse_feedstock_outputs_zip_maps_feedstocks():
    raw = _zip_with_outputs(
        {
            "numpy": {"feedstocks": ["numpy-feedstock"]},
            "pandas": {"feedstocks": ["pandas-feedstock", "pandas-feedstock2"]},
        }
    )
    df = parse_feedstock_outputs_zip(raw)
    assert list(df.columns) == ["conda_name", "feedstocks"]
    assert len(df) == 2
    numpy_row = df.loc[df["conda_name"] == "numpy"].iloc[0]
    assert numpy_row["feedstocks"] == ["numpy-feedstock"]


def test_parse_feedstock_outputs_zip_empty():
    df = parse_feedstock_outputs_zip(_zip_with_outputs({}))
    assert df.empty
    assert list(df.columns) == ["conda_name", "feedstocks"]


def test_repodata_json_to_rows_flattens_packages():
    repodata = {
        "packages.conda": {
            "numpy-1.26.0-py312_0.conda": {
                "name": "numpy",
                "version": "1.26.0",
                "timestamp": 1700000000,
            }
        },
        "packages": {},
    }
    rows = repodata_json_to_rows(repodata, "linux-64")
    assert len(rows) == 1
    assert rows[0]["conda_name"] == "numpy"
    assert rows[0]["subdir"] == "linux-64"


def test_channeldata_json_to_rows():
    payload = {
        "packages": {
            "numpy": {"subdirs": ["linux-64", "noarch"]},
            "broken": "not-a-dict",
        }
    }
    df = channeldata_json_to_rows(payload)
    assert len(df) == 1
    assert df.iloc[0]["conda_name"] == "numpy"
    assert df.iloc[0]["subdirs"] == ["linux-64", "noarch"]


def _multi_file_tar(*members: tuple[str, dict]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for path, payload in members:
            data = json.dumps(payload).encode()
            info = tarfile.TarInfo(name=path)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_parse_cf_graph_tarball_emits_dependency_edges():
    node_attrs = {
        "meta_yaml": {
            "requirements": {
                "run": ["python >=3.11", "libcurl"],
            }
        }
    }
    pr_info = {"prs": [{"state": "open"}], "issues": [{}]}
    tar_bytes = _multi_file_tar(
        ("cf-graph/pr_info/numpy-feedstock.json", pr_info),
        ("cf-graph/node_attrs/numpy-feedstock.json", node_attrs),
    )
    df = parse_cf_graph_tarball(tar_bytes)
    assert not df.empty
    edge = df.loc[df["depends_on"] == "libcurl"].iloc[0]
    assert edge["feedstock_name"] == "numpy-feedstock"
    assert edge["dep_type"] == "run"
    assert edge["open_prs"] == 1


def test_parse_cf_graph_tarball_empty():
    df = parse_cf_graph_tarball(_multi_file_tar(("other/readme.json", {})))
    assert df.empty
    assert "feedstock_name" in df.columns


# -- ParselmouthMappingDataset (Story 21.2: reads pypi_conda_map_store) ------


def test_parselmouth_reads_pypi_conda_map_store(tmp_path):
    cache_path = tmp_path / "pypi_conda_map.json"
    cache_path.write_text(json.dumps({"numpy": "numpy", "beautifulsoup4": "beautifulsoup4"}))
    ds = ParselmouthMappingDataset(filepath=str(cache_path))
    out = ds.load()
    assert set(out["pypi_name"]) == {"numpy", "beautifulsoup4"}
    assert (out["match_source"] == "pypi_conda_map_store").all()


def test_parselmouth_absent_store_returns_empty_frame_not_stale_crash(tmp_path):
    ds = ParselmouthMappingDataset(filepath=str(tmp_path / "never-written.json"))
    out = ds.load()
    assert out.empty
    assert list(out.columns) == ["pypi_name", "conda_name", "match_source"]


def test_parselmouth_corrupt_store_degrades_to_empty_never_raises(tmp_path):
    cache_path = tmp_path / "pypi_conda_map.json"
    cache_path.write_text("{not valid json")
    ds = ParselmouthMappingDataset(filepath=str(cache_path))
    out = ds.load()  # never raises (AD-13)
    assert out.empty


def test_parselmouth_rejects_unexpected_kwargs():
    """Catches stale catalog misconfiguration loudly rather than silently
    discarding an unrecognized key (review finding)."""
    with pytest.raises(TypeError):
        ParselmouthMappingDataset(filepath="whatever", url="https://example.invalid")


def test_parselmouth_save_is_read_only(tmp_path):
    from kedro.io.core import DatasetError

    ds = ParselmouthMappingDataset(filepath=str(tmp_path / "map.json"))
    with pytest.raises(DatasetError, match="read-only"):
        ds.save({"a": "b"})


# -- CrossChannelRepodataDataset (Story 21.4: selfexplainml + subdir-fallback hardening)


from pyforge.atlas.datasets import core_sources as CS  # noqa: E402


def _repodata(*names: str) -> dict:
    return {
        "packages.conda": {f"{n}-1.0-0.conda": {"name": n, "version": "1.0", "timestamp": 1700000000} for n in names},
        "packages": {},
    }


def test_cross_channel_specs_include_selfexplainml_with_noarch_then_linux64():
    specs = {short: (channel, subdirs) for short, channel, subdirs in CS._CROSS_CHANNEL_SPECS}
    assert specs["selfexplainml"] == ("selfexplainml", ("noarch", "linux-64"))
    # the hardening pass: every channel now carries a 2-subdir fallback list
    assert all(len(subdirs) >= 2 for _, subdirs in specs.values()), specs
    assert set(specs) == {"bioconda", "pytorch", "nvidia", "robostack", "selfexplainml"}


def test_cross_channel_falls_back_to_second_subdir_when_first_fails(monkeypatch):
    """The hardening's actual regression test: a channel whose first subdir yields no
    repodata (every filename/mirror combo 404s) but whose second subdir succeeds returns
    data — instead of being WARN-skipped as "unavailable"."""
    attempted: list[str] = []

    def fake_fetch(url, *, load_args, credentials, metadata):
        attempted.append(url)
        if "/selfexplainml/linux-64/repodata.json" in url:
            return _repodata("piml", "gaminet"), False
        return None, False  # noarch (both filenames, both mirrors) unavailable

    monkeypatch.setattr(CS, "_fetch_repodata_at_url", fake_fetch)
    monkeypatch.setattr(CS, "_CROSS_CHANNEL_SPECS", (("selfexplainml", "selfexplainml", ("noarch", "linux-64")),))
    ds = CS.CrossChannelRepodataDataset(url="ignored")
    out = ds.load()
    assert set(out["conda_name"]) == {"piml", "gaminet"}
    assert set(out["channel"]) == {"selfexplainml"}
    # noarch was tried (and exhausted) BEFORE linux-64 succeeded
    assert any("/noarch/" in u for u in attempted)
    first_success = next(i for i, u in enumerate(attempted) if "/linux-64/" in u)
    assert all("/noarch/" in u for u in attempted[:first_success])


def test_cross_channel_every_subdir_failing_is_skipped_never_raises(monkeypatch):
    monkeypatch.setattr(CS, "_fetch_repodata_at_url", lambda url, **kw: (None, False))
    monkeypatch.setattr(CS, "_CROSS_CHANNEL_SPECS", (("selfexplainml", "selfexplainml", ("noarch", "linux-64")),))
    out = CS.CrossChannelRepodataDataset(url="ignored").load()  # never raises
    assert out.empty
    assert list(out.columns) == ["conda_name", "channel"]


def test_cross_channel_first_subdir_success_short_circuits(monkeypatch):
    attempted: list[str] = []

    def fake_fetch(url, **kw):
        attempted.append(url)
        return (_repodata("torch"), False) if "/noarch/current_repodata.json" in url else (None, False)

    monkeypatch.setattr(CS, "_fetch_repodata_at_url", fake_fetch)
    monkeypatch.setattr(CS, "_CROSS_CHANNEL_SPECS", (("pytorch", "pytorch", ("noarch", "linux-64")),))
    out = CS.CrossChannelRepodataDataset(url="ignored").load()
    assert out["conda_name"].tolist() == ["torch"]
    assert not any("/linux-64/" in u for u in attempted)  # second subdir never tried


class _StubInner:
    """Stand-in for the composed APIDataset: returns a canned payload, no network."""

    def __init__(self, payload):
        self._payload = payload

    def load(self):
        return self._payload


def test_conda_channeldata_dataset_transport_error_returns_empty_columned_frame():
    ds = CondaChanneldataDataset(url="https://example.invalid/anaconda/channeldata.json")

    class _Boom:
        def load(self):
            raise ConnectionError("offline")

    ds._inner = _Boom()
    df = ds.load()
    assert list(df.columns) == ["conda_name", "subdirs"]
    assert df.empty


def test_fetch_repodata_at_url_connection_failure_sets_flag(monkeypatch):
    class _ConnFail:
        def __init__(self, **kwargs):
            pass

        def load(self):
            raise ConnectionError("down")

    monkeypatch.setattr(CS, "APIDataset", _ConnFail)
    repodata, connection_failed = CS._fetch_repodata_at_url(
        "https://conda.anaconda.org/pytorch/noarch/repodata.json",
        load_args=None,
        credentials=None,
        metadata=None,
    )
    assert repodata is None
    assert connection_failed is True


def test_cross_channel_skips_remaining_urls_on_same_mirror_after_connection_failure(monkeypatch):
    attempted: list[str] = []

    def fake_fetch(url, **kw):
        attempted.append(url)
        if "prefix.dev" in url:
            return None, True
        return _repodata("torch"), False

    monkeypatch.setattr(CS, "_fetch_repodata_at_url", fake_fetch)
    monkeypatch.setattr(CS, "_CROSS_CHANNEL_SPECS", (("pytorch", "pytorch", ("noarch",)),))
    out = CS.CrossChannelRepodataDataset(url="ignored").load()
    assert out["conda_name"].tolist() == ["torch"]
    prefix_attempts = [u for u in attempted if "prefix.dev" in u]
    anaconda_attempts = [u for u in attempted if "conda.anaconda.org" in u]
    assert len(prefix_attempts) == 1
    assert len(anaconda_attempts) >= 1


@pytest.mark.parametrize(
    "payload",
    [b"<html>not json</html>", b"[1, 2, 3]", "{not-json", b""],
    ids=["non-json-bytes", "json-list-not-dict", "non-json-str", "empty-bytes"],
)
def test_conda_channeldata_dataset_malformed_payload_returns_empty_columned_frame(payload):
    """Story 21.4 I/O matrix: ``core_anaconda_main_channeldata_raw`` reuses
    ``CondaChanneldataDataset`` UNCHANGED, so a non-JSON / non-dict payload degrades to
    the existing empty ``conda_name``/``subdirs`` frame (``core_channeldata_raw``'s own
    degrade path) and never raises."""
    ds = CondaChanneldataDataset(url="https://example.invalid/anaconda/channeldata.json")
    ds._inner = _StubInner(payload)
    df = ds.load()
    assert list(df.columns) == ["conda_name", "subdirs"]
    assert df.empty


def test_cross_channel_empty_index_on_first_subdir_falls_through_to_second(monkeypatch):
    """Review-pass 1: a VALID but EMPTY index ({"packages": {}, "packages.conda": {}} — an
    unpopulated noarch) must NOT count as success; the second subdir is still tried."""
    attempted: list[str] = []

    def fake_fetch(url, **kw):
        attempted.append(url)
        if "/noarch/" in url:
            return {"packages": {}, "packages.conda": {}}, False  # valid, empty
        if "/linux-64/" in url:
            return _repodata("piml"), False
        return None, False

    monkeypatch.setattr(CS, "_fetch_repodata_at_url", fake_fetch)
    monkeypatch.setattr(CS, "_CROSS_CHANNEL_SPECS", (("selfexplainml", "selfexplainml", ("noarch", "linux-64")),))
    out = CS.CrossChannelRepodataDataset(url="ignored").load()
    assert out["conda_name"].tolist() == ["piml"]
    assert any("/noarch/" in u for u in attempted)
    assert any("/linux-64/" in u for u in attempted)  # the second subdir WAS attempted


def test_repodata_has_packages_helper():
    assert CS._repodata_has_packages(_repodata("x")) is True
    assert CS._repodata_has_packages({"packages": {"a": {}}}) is True
    assert CS._repodata_has_packages({"packages": {}, "packages.conda": {}}) is False
    assert CS._repodata_has_packages({}) is False
    assert CS._repodata_has_packages({"packages": "nope"}) is False


def test_cross_channel_repodata_filename_fallback_current_then_repodata(monkeypatch):
    """The repodata-FILENAME fallback (the spec's named coverage gap): for ONE subdir,
    current_repodata.json fails on both mirrors and repodata.json succeeds -> data is
    returned, and current_repodata.json was tried BEFORE repodata.json."""
    attempted: list[str] = []

    def fake_fetch(url, **kw):
        attempted.append(url)
        return (_repodata("piml"), False) if url.endswith("/noarch/repodata.json") else (None, False)

    monkeypatch.setattr(CS, "_fetch_repodata_at_url", fake_fetch)
    monkeypatch.setattr(CS, "_CROSS_CHANNEL_SPECS", (("selfexplainml", "selfexplainml", ("noarch",)),))
    out = CS.CrossChannelRepodataDataset(url="ignored").load()
    assert out["conda_name"].tolist() == ["piml"]
    first_repodata = next(i for i, u in enumerate(attempted) if u.endswith("/repodata.json"))
    assert first_repodata > 0
    assert all(u.endswith("/current_repodata.json") for u in attempted[:first_repodata])
    # both mirrors of current_repodata.json were exhausted before the filename fallback
    assert len(attempted[:first_repodata]) == 2


def test_cross_channels_node_tuple_matches_dataset_specs():
    """The hand-maintained `_CROSS_CHANNELS` (pypi_intelligence/nodes.py — drives the
    in_<channel> output columns) and `_CROSS_CHANNEL_SPECS` (datasets/core_sources.py —
    drives the fetch) must never drift: the in_selfexplainml column only "falls out
    automatically" because BOTH were edited (review-pass 1 pin)."""
    from pyforge.atlas.pipelines.pypi_intelligence.nodes import _CROSS_CHANNELS

    assert _CROSS_CHANNELS == tuple(short for short, _, _ in CS._CROSS_CHANNEL_SPECS)


def test_api_json_normalizes_response_json():
    class _Resp:
        def json(self):
            return {"packages": {}}

    class _BadResp:
        def json(self):
            raise ValueError("not json")

    assert CS._api_json(_Resp()) == {"packages": {}}
    assert CS._api_json(_BadResp()) is None
    assert CS._api_json(b'{"a": 1}') == {"a": 1}
    assert CS._api_json(b"[1]") is None


def test_as_bytes_rejects_non_bytes_like_payload():
    with pytest.raises(TypeError, match="bytes-like"):
        CS._as_bytes(42)


def test_parse_pypi_simple_index_skips_invalid_project_rows():
    df = CS.parse_pypi_simple_index(
        {"projects": [{"name": "ok", "_last-serial": 1}, "skip", {"no_name": True}]}
    )
    assert df.iloc[0]["pypi_name"] == "ok"
    assert len(df) == 1


def test_conda_repodata_merges_rows_from_multiple_subdirs(monkeypatch):
    class _Inner:
        def __init__(self, **kwargs):
            self._url = str(kwargs.get("url", ""))

        def load(self):
            if "/noarch/" in self._url:
                return json.dumps(_repodata("noarch-pkg")).encode()
            if "/linux-64/" in self._url:
                return json.dumps(_repodata("linux-pkg")).encode()
            return b"{}"

    monkeypatch.setattr(CS, "APIDataset", _Inner)
    ds = CS.CondaRepodataDataset(url="https://example/base", subdirs=("noarch", "linux-64"))
    df = ds.load()
    assert set(df["conda_name"]) == {"noarch-pkg", "linux-pkg"}


def test_fetch_repodata_at_url_non_connection_error_returns_no_connection_flag(monkeypatch):
    class _ValueFail:
        def __init__(self, **kwargs):
            pass

        def load(self):
            raise ValueError("bad payload")

    monkeypatch.setattr(CS, "APIDataset", _ValueFail)
    repodata, connection_failed = CS._fetch_repodata_at_url(
        "https://conda.anaconda.org/bioconda/noarch/repodata.json",
        load_args=None,
        credentials=None,
        metadata=None,
    )
    assert repodata is None
    assert connection_failed is False


def test_conda_repodata_dataset_skips_non_dict_payload(monkeypatch):
    class _Inner:
        def __init__(self, **kwargs):
            pass

        def load(self):
            return b"not-json"

    monkeypatch.setattr(CS, "APIDataset", _Inner)
    ds = CS.CondaRepodataDataset(url="https://example/base", subdirs=("linux-64",))
    df = ds.load()
    assert df.empty


def test_conda_repodata_dataset_aggregates_subdir_rows(monkeypatch):
    class _Inner:
        def __init__(self, **kwargs):
            self._url = kwargs.get("url", "")

        def load(self):
            if "linux-64" in self._url:
                return json.dumps(_repodata("numpy")).encode()
            return b"{}"

    monkeypatch.setattr(CS, "APIDataset", _Inner)
    ds = CS.CondaRepodataDataset(url="https://example/base", subdirs=("linux-64",))
    df = ds.load()
    assert df.iloc[0]["conda_name"] == "numpy"
    assert df.iloc[0]["subdir"] == "linux-64"


def test_pypi_simple_index_dataset_parses_projects(monkeypatch):
    payload = {"projects": [{"name": "requests", "_last-serial": 99}]}

    class _Inner:
        def load(self):
            return payload

    ds = CS.PyPISimpleIndexDataset(url="https://pypi.org/simple")
    ds._inner = _Inner()
    df = ds.load()
    assert df.iloc[0]["pypi_name"] == "requests"
    assert df.iloc[0]["last_serial"] == 99


def test_feedstock_outputs_archive_dataset_parses_zip(monkeypatch):
    raw = _zip_with_outputs({"numpy": {"feedstocks": ["numpy-feedstock"]}})

    class _BytesInner:
        def load(self):
            return raw

    ds = CS.FeedstockOutputsArchiveDataset(url="https://example/outputs.zip")
    ds._inner = _BytesInner()
    df = ds.load()
    assert df.iloc[0]["conda_name"] == "numpy"


def test_cf_graph_tarball_dataset_parses_tar(monkeypatch):
    tar_bytes = _multi_file_tar(("cf-graph/node_attrs/n-feedstock.json", {"meta_yaml": {"requirements": {"run": []}}}))

    class _BytesInner:
        def load(self):
            return tar_bytes

    ds = CS.CfGraphTarballDataset(url="https://example/graph.tgz")
    ds._inner = _BytesInner()
    assert isinstance(ds.load(), pd.DataFrame)


def test_s3_download_stats_returns_empty_columned_frame():
    df = CS.S3DownloadStatsDataset(url="s3://bucket/prefix").load()
    assert list(df.columns) == ["conda_name", "month", "platform", "pyver", "channel", "downloads"]
    assert df.empty


def test_resolve_anaconda_channel_urls_honors_channel_env_override(monkeypatch):
    monkeypatch.setenv("PYTORCH_BASE_URL", "https://custom.example/pytorch")
    urls = CS._resolve_anaconda_channel_urls("pytorch", "noarch", "repodata.json")
    assert urls[0] == "https://custom.example/pytorch/noarch/repodata.json"


def test_parselmouth_mapping_cache_exception_degrades_empty(monkeypatch, tmp_path):
    ds = ParselmouthMappingDataset(filepath=str(tmp_path / "map.json"))

    def _boom() -> None:
        raise OSError("cache unreadable")

    monkeypatch.setattr(ds._cache, "load", _boom)
    out = ds.load()
    assert out.empty
    assert list(out.columns) == ["pypi_name", "conda_name", "match_source"]


def test_parselmouth_non_dict_cache_degrades_empty(monkeypatch, tmp_path):
    ds = ParselmouthMappingDataset(filepath=str(tmp_path / "map.json"))
    monkeypatch.setattr(ds._cache, "load", lambda: ["not-a-dict"])
    assert ds.load().empty


def test_conda_repodata_dataset_iterates_default_subdirs(monkeypatch):
    seen: list[str] = []

    class _Inner:
        def __init__(self, **kwargs):
            seen.append(str(kwargs.get("url", "")))

        def load(self):
            return b"{}"

    monkeypatch.setattr(CS, "APIDataset", _Inner)
    CS.CondaRepodataDataset(url="https://conda.anaconda.org/conda-forge").load()
    assert len(seen) == len(CS.CONDA_FORGE_SUBDIRS)


def test_cross_channel_repodata_describe_lists_channels():
    desc = CS.CrossChannelRepodataDataset(url="ignored")._describe()
    assert "channels" in desc
    assert len(desc["channels"]) == len(CS._CROSS_CHANNEL_SPECS)
