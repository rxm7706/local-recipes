"""Core raw-source parser tests (Story B1 ingest gap closure).

Pure parser coverage only — no network. Dataset classes compose APIDataset and are
smoke-tested via catalog loadability + the core pipeline integration run.
"""

from __future__ import annotations

import io
import json
import tarfile
import zipfile

import pytest
from pyforge.atlas.datasets import (
    ParselmouthMappingDataset,
    channeldata_json_to_rows,
    parse_cf_graph_tarball,
    parse_feedstock_outputs_zip,
    repodata_json_to_rows,
)


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
