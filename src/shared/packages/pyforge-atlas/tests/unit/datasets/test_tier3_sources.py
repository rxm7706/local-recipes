"""Story 23.1 — Tier 3 OS-distro bulk-index dataset + parser tests."""

from __future__ import annotations

import gzip
import json

import pandas as pd
import pytest

from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.datasets.tier3_sources import (
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

_HOMEBREW_FIXTURE = json.dumps([{"name": "python"}, {"name": "numpy"}])
_NIXPKGS_FIXTURE = json.dumps({"python3Packages.requests": {}, "python3Packages.numpy": {}})
_SPACK_FIXTURE = json.dumps(["py-numpy", "py-pandas"])
_DEBIAN_FIXTURE = "Package: python3-numpy\n\nPackage: python3-requests\n"
_FEDORA_JSON_FIXTURE = json.dumps({"projects": [{"name": "python-requests"}, {"name": "python-numpy"}]})


def test_parse_homebrew_formulae_json_happy_path():
    assert parse_homebrew_formulae_json(_HOMEBREW_FIXTURE) == ["python", "numpy"]


def test_parse_homebrew_formulae_json_malformed_returns_empty():
    assert parse_homebrew_formulae_json("not json") == []
    assert parse_homebrew_formulae_json({}) == []


def test_parse_nixpkgs_packages_json_happy_path():
    names = parse_nixpkgs_packages_json(_NIXPKGS_FIXTURE)
    assert "python3Packages.requests" in names
    assert len(names) == 2


def test_parse_nixpkgs_packages_json_malformed_returns_empty():
    assert parse_nixpkgs_packages_json(None) == []


def test_parse_spack_packages_happy_path():
    assert parse_spack_packages(_SPACK_FIXTURE) == ["py-numpy", "py-pandas"]


def test_parse_spack_packages_dict_keys():
    assert parse_spack_packages('{"py-numpy": {}, "py-pandas": {}}') == ["py-numpy", "py-pandas"]


def test_parse_debian_packages_control_happy_path():
    assert parse_debian_packages_control(_DEBIAN_FIXTURE) == [
        "python3-numpy",
        "python3-requests",
    ]


def test_parse_debian_packages_control_gzip():
    gz = gzip.compress(_DEBIAN_FIXTURE.encode())
    assert parse_debian_packages_control(gz) == ["python3-numpy", "python3-requests"]


def test_parse_fedora_packages_json_happy_path():
    assert parse_fedora_packages(_FEDORA_JSON_FIXTURE) == [
        "python-requests",
        "python-numpy",
    ]


def test_parse_fedora_packages_xml():
    xml = "<projects><name>python-flask</name><name>python-django</name></projects>"
    assert parse_fedora_packages(xml) == ["python-flask", "python-django"]


def _homebrew_ds(tmp_path, fetcher=None) -> HomebrewPackagesDataset:
    return HomebrewPackagesDataset(
        url="https://formulae.brew.sh/api/formula.json",
        filepath=str(tmp_path / "homebrew"),
        fetcher=fetcher,
    )


def test_homebrew_happy_path_persists_and_loads(tmp_path):
    ds = _homebrew_ds(tmp_path, fetcher=lambda: _HOMEBREW_FIXTURE)
    ds.save(RefreshRequest(store="discovery_homebrew_packages_raw", force=True))
    frame = ds.load()
    assert list(frame.columns) == ["name"]
    assert set(frame["name"]) == {"python", "numpy"}
    assert ds.is_stale() is False


def test_homebrew_fetch_failure_keeps_last_good(tmp_path):
    ds = _homebrew_ds(tmp_path, fetcher=lambda: _HOMEBREW_FIXTURE)
    ds.save(RefreshRequest(store="discovery_homebrew_packages_raw", force=True))
    ds._refresher = lambda: (_ for _ in ()).throw(RuntimeError("network down"))  # type: ignore[method-assign]
    ds.save(RefreshRequest(store="discovery_homebrew_packages_raw", force=True))
    frame = ds.load()
    assert len(frame) == 2
    assert ds.is_stale() is True


def test_homebrew_first_run_fetch_failure_empty_and_stale(tmp_path):
    ds = _homebrew_ds(tmp_path, fetcher=lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    ds.save(RefreshRequest(store="discovery_homebrew_packages_raw", force=True))
    frame = ds.load()
    assert frame.empty and list(frame.columns) == ["name"]
    assert ds.is_stale() is True


def test_homebrew_offline_no_fetcher_marks_stale(tmp_path):
    ds = _homebrew_ds(tmp_path)
    ds.save(RefreshRequest(store="discovery_homebrew_packages_raw", force=True))
    frame = ds.load()
    assert frame.empty
    assert ds.is_stale() is True


def test_homebrew_malformed_refresh_rejects_write(tmp_path):
    ds = _homebrew_ds(tmp_path, fetcher=lambda: _HOMEBREW_FIXTURE)
    with pytest.raises(ValueError, match="missing required column"):
        ds._write(pd.DataFrame({"nope": [1]}))


def test_nixpkgs_load_degrades_on_missing_store(tmp_path):
    ds = NixpkgsPackagesDataset(
        url="https://example/nixpkgs",
        filepath=str(tmp_path / "nix"),
    )
    frame = ds.load()
    assert frame.empty and list(frame.columns) == ["name"]


def test_all_empty_inputs_flag_node_degrades():
    from pyforge.atlas.pipelines.pypi_intelligence.nodes import flag_tier3_channels

    empty = pd.DataFrame(columns=["name"])
    out = flag_tier3_channels(empty, empty, empty, empty, empty)
    assert out.empty
    assert list(out.columns) == [
        "pypi_name",
        "in_homebrew",
        "in_nixpkgs",
        "in_spack",
        "in_debian",
        "in_fedora",
    ]


def test_malformed_column_skipped_in_flag_node():
    from pyforge.atlas.pipelines.pypi_intelligence.nodes import flag_tier3_channels

    bad = pd.DataFrame({"nope": ["x"]})
    good = pd.DataFrame({"name": ["Foo.Bar"]})
    out = flag_tier3_channels(bad, good, bad, bad, bad)
    assert len(out) == 1
    assert out.iloc[0]["pypi_name"] == "foo-bar"
    assert bool(out.iloc[0]["in_nixpkgs"]) is True


@pytest.mark.parametrize(
    ("cls", "fixture", "store"),
    [
        (HomebrewPackagesDataset, _HOMEBREW_FIXTURE, "discovery_homebrew_packages_raw"),
        (NixpkgsPackagesDataset, _NIXPKGS_FIXTURE, "discovery_nixpkgs_packages_raw"),
        (SpackPackagesDataset, _SPACK_FIXTURE, "discovery_spack_packages_raw"),
        (DebianPackagesDataset, _DEBIAN_FIXTURE, "discovery_debian_packages_raw"),
        (FedoraPackagesDataset, _FEDORA_JSON_FIXTURE, "discovery_fedora_packages_raw"),
    ],
)
def test_each_tier3_dataset_persists_fixture(tmp_path, cls, fixture, store):
    ds = cls(
        url="https://example.test/index",
        filepath=str(tmp_path / store),
        fetcher=lambda f=fixture: f,
    )
    ds.save(RefreshRequest(store=store, force=True))
    frame = ds.load()
    assert not frame.empty
    assert "name" in frame.columns
