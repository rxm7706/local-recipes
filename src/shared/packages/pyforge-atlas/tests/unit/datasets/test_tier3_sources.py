"""Story 23.1 — Tier 3 OS-distro bulk-index dataset + parser tests."""

from __future__ import annotations

import gzip
import json

import pandas as pd
import pytest
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import public_sources
from pyforge.atlas.datasets import tier3_sources as T
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


# -- Story 34.5: the shapes the live indexes serve (measured 2026-10-18) ----------------

_NIXPKGS_V2 = json.dumps(
    {
        "version": 2,
        "packages": {
            "python312Packages.numpy": {"name": "python3.12-numpy-2.3.1", "pname": "numpy", "version": "2.3.1"},
            "python313Packages.numpy": {"name": "python3.13-numpy-2.3.1", "pname": "numpy", "version": "2.3.1"},
            "ripgrep": {"name": "ripgrep-14.1.1", "pname": "ripgrep", "meta": {"description": 'a "quoted" tool'}},
            "weird": {"pname": 'we"ird'},
        },
    }
)


def test_parse_nixpkgs_reports_each_pname_once():
    assert parse_nixpkgs_packages_json(_NIXPKGS_V2.encode()) == ["numpy", "ripgrep", 'we"ird']


def test_parse_nixpkgs_decodes_a_still_compressed_brotli_body():
    brotli = pytest.importorskip("brotli")

    assert parse_nixpkgs_packages_json(brotli.compress(_NIXPKGS_V2.encode())) == ["numpy", "ripgrep", 'we"ird']


def test_parse_nixpkgs_garbage_bytes_return_empty():
    assert parse_nixpkgs_packages_json(b"\x00\x01 not brotli, not json") == []


def test_parse_spack_records_with_a_name():
    payload = json.dumps([{"name": "py-numpy", "description": "x"}, {"description": "no name"}, {"name": "zlib"}])

    assert parse_spack_packages(payload) == ["py-numpy", "zlib"]


def test_parse_fedora_pagure_owner_alias_rpms():
    payload = json.dumps({"container": {"bcg729": []}, "rpms": {"python-numpy": ["a"], "0ad": ["b"]}, "modules": {}})

    assert parse_fedora_packages(payload) == ["python-numpy", "0ad"]


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


def test_tier3_corrupt_parquet_store_degrades_to_empty(tmp_path):
    ds = _homebrew_ds(tmp_path, fetcher=lambda: _HOMEBREW_FIXTURE)
    ds.save(RefreshRequest(store="discovery_homebrew_packages_raw", force=True))
    ds._store_path.write_bytes(b"not-a-parquet")
    frame = ds.load()
    assert frame.empty and list(frame.columns) == ["name"]
    assert ds.is_stale() is True


def test_tier3_store_missing_name_column_degrades(tmp_path):
    ds = _homebrew_ds(tmp_path, fetcher=lambda: _HOMEBREW_FIXTURE)
    ds.save(RefreshRequest(store="discovery_homebrew_packages_raw", force=True))
    pd.DataFrame({"nope": [1]}).to_parquet(ds._store_path, index=False)
    frame = ds.load()
    assert frame.empty


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


# -- Story 34.5: each store refreshes itself from its public index ------------------------

_LIVE_SHAPES = {
    HomebrewPackagesDataset: (_HOMEBREW_FIXTURE.encode(), ["python", "numpy"]),
    NixpkgsPackagesDataset: (_NIXPKGS_V2.encode(), ["numpy", "ripgrep", 'we"ird']),
    SpackPackagesDataset: (json.dumps([{"name": "py-numpy"}, {"name": "zlib"}]).encode(), ["py-numpy", "zlib"]),
    DebianPackagesDataset: (  # a name repeated across stanzas is one row
        gzip.compress((_DEBIAN_FIXTURE + "\nPackage: python3-numpy\n").encode()),
        ["python3-numpy", "python3-requests"],
    ),
    FedoraPackagesDataset: (json.dumps({"rpms": {"python-numpy": []}}).encode(), ["python-numpy"]),
}


class _Response:
    def __init__(self, content):
        self.content = content


@flag_states("pyforge.atlas.live_public_sources")  # spelled out: the flag gate reads this file for the key
@pytest.mark.parametrize("cls", list(_LIVE_SHAPES))
def test_a_store_with_no_fetcher_refreshes_from_its_own_index(tmp_path, flag_provider, monkeypatch, cls):
    """On: the store fetches its URL through a composed APIDataset (with a timeout) and holds its
    names. Off: today's behaviour, nothing requested and a 'no refresher wired' marker."""
    body, names = _LIVE_SHAPES[cls]
    requested = []

    class _API:
        def __init__(self, *, url, load_args=None):
            requested.append((url, load_args))

        def load(self):
            return _Response(body)

    monkeypatch.setattr(T, "APIDataset", _API)
    monkeypatch.setattr(public_sources, "live", lambda: flag_provider[public_sources.FLAG_KEY])
    ds = cls(url="https://example.test/index", filepath=str(tmp_path / "store"))

    ds.save(RefreshRequest(store="x", force=True))
    frame = ds.load()

    if flag_provider[public_sources.FLAG_KEY]:
        assert [(u, a["timeout"]) for u, a in requested] == [("https://example.test/index", 300)]
        assert requested[0][1]["auth"]("req") == "req"  # a no-op auth: requests never reads ~/.netrc
        assert list(frame["name"]) == names and not ds.is_stale()
    else:
        assert requested == [] and frame.empty
        assert ds.staleness().reason.startswith("refresh due but no refresher wired")


def test_a_public_body_that_is_not_bytes_keeps_last_good(tmp_path, monkeypatch):
    class _API:
        def __init__(self, *, url, load_args=None):
            pass

        def load(self):
            return _Response("a text body")

    monkeypatch.setattr(T, "APIDataset", _API)
    monkeypatch.setattr(public_sources, "live", lambda: True)
    ds = HomebrewPackagesDataset(url="https://example.test/index", filepath=str(tmp_path / "store"))

    ds.save(RefreshRequest(store="x", force=True))

    assert ds.load().empty and "refresh failed: DatasetError" in ds.staleness().reason


def test_an_injected_fetcher_wins_over_the_public_fetch(tmp_path, monkeypatch):
    monkeypatch.setattr(public_sources, "live", lambda: True)
    monkeypatch.setattr(T, "APIDataset", lambda **_kw: pytest.fail("the injected fetcher must be used"))
    ds = HomebrewPackagesDataset(
        url="https://example.test/index", filepath=str(tmp_path / "store"), fetcher=lambda: _HOMEBREW_FIXTURE
    )

    ds.save(RefreshRequest(store="x", force=True))

    assert list(ds.load()["name"]) == ["python", "numpy"]


def test_the_flag_is_read_at_the_refresh_not_at_construction(tmp_path, monkeypatch):
    """A Dagster code location constructs its stores at import: turning the flag off afterwards
    must stop the fetch, and turning it on must start one."""
    requested = []

    class _API:
        def __init__(self, *, url, load_args=None):
            requested.append(url)

        def load(self):
            return _Response(_HOMEBREW_FIXTURE.encode())

    monkeypatch.setattr(T, "APIDataset", _API)
    monkeypatch.setattr(public_sources, "live", lambda: True)
    built_on = HomebrewPackagesDataset(url="https://example.test/on", filepath=str(tmp_path / "on"))
    monkeypatch.setattr(public_sources, "live", lambda: False)
    built_off = HomebrewPackagesDataset(url="https://example.test/off", filepath=str(tmp_path / "off"))

    built_on.save(RefreshRequest(store="x", force=True))  # flag now off
    assert requested == [] and built_on.staleness().reason.startswith("refresh due but no refresher wired")

    monkeypatch.setattr(public_sources, "live", lambda: True)
    built_off.save(RefreshRequest(store="x", force=True))  # flag now on
    assert requested == ["https://example.test/off"] and list(built_off.load()["name"]) == ["python", "numpy"]


def test_the_request_timeout_is_the_stores_own(tmp_path, monkeypatch):
    seen = []

    class _API:
        def __init__(self, *, url, load_args=None):
            seen.append(load_args)

        def load(self):
            return _Response(_HOMEBREW_FIXTURE.encode())

    monkeypatch.setattr(T, "APIDataset", _API)
    monkeypatch.setattr(public_sources, "live", lambda: True)
    ds = HomebrewPackagesDataset(url="https://example.test/i", filepath=str(tmp_path / "s"), request_timeout_seconds=7)

    ds.save(RefreshRequest(store="x", force=True))

    assert [a["timeout"] for a in seen] == [7]


def test_parse_nixpkgs_skips_a_bad_escape_and_an_empty_pname():
    body = b'{"packages": {"a": {"pname": "bad\\xescape"}, "b": {"pname": ""}, "c": {"pname": "ok"}}}'

    assert parse_nixpkgs_packages_json(body) == ["ok"]


def test_parse_nixpkgs_reads_pnames_from_a_decoded_object_too():
    doc = json.loads(_NIXPKGS_V2)

    assert parse_nixpkgs_packages_json(doc) == ["numpy", "ripgrep", 'we"ird']  # same as the bytes


def test_a_compressed_body_starting_with_a_bracket_still_decodes(monkeypatch):
    """The JSON sniff used to skip decompression for a brotli stream whose first byte is '['
    (3 of 80 sampled streams, review 2026-10-18): decompression is now tried whatever the byte."""
    opaque = b"[\x8b\x07\x00 not json, a compressed stream"
    monkeypatch.setattr(T, "_brotli_decompress", lambda data: _NIXPKGS_V2.encode() if data == opaque else None)

    assert parse_nixpkgs_packages_json(opaque) == ["numpy", "ripgrep", 'we"ird']


def test_a_nixpkgs_body_with_no_brotli_installed_says_so(tmp_path, monkeypatch):
    brotli = pytest.importorskip("brotli")
    body = brotli.compress(_NIXPKGS_V2.encode())
    real_import = T.importlib.import_module

    def _no_brotli(name, *a, **kw):
        if name == "brotli":
            raise ModuleNotFoundError("No module named 'brotli'")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(T.importlib, "import_module", _no_brotli)
    real_find_spec = T.importlib.util.find_spec
    monkeypatch.setattr(
        T.importlib.util, "find_spec", lambda name, *a: None if name == "brotli" else real_find_spec(name, *a)
    )
    ds = NixpkgsPackagesDataset(url="https://example.test/i", filepath=str(tmp_path / "s"), fetcher=lambda: body)

    ds.save(RefreshRequest(store="x", force=True))

    assert "no brotli module is installed" in ds.staleness().reason


def test_an_empty_parse_with_brotli_installed_is_no_data_not_a_missing_module(tmp_path):
    """The missing-brotli marker needs all three: an empty parse, a non-JSON body, and no brotli."""
    pytest.importorskip("brotli")
    ds = NixpkgsPackagesDataset(
        url="https://example.test/i", filepath=str(tmp_path / "s"), fetcher=lambda: b"<html>x</html>"
    )

    ds.save(RefreshRequest(store="x", force=True))

    assert ds.staleness().reason == "refresh returned no data"


def test_parse_nixpkgs_dict_path_drops_an_empty_pname():
    doc = {"packages": {"a": {"pname": ""}, "b": {"pname": "ok"}, "c": {"pname": None}}}

    assert parse_nixpkgs_packages_json(doc) == ["ok"]


def test_describe_names_the_public_index(tmp_path):
    """A store with no injected fetcher still has its own public index; _describe says so without
    reading the flag (reading it here would bring the import-time read back)."""
    ds = HomebrewPackagesDataset(url="https://example.test/i", filepath=str(tmp_path / "s"))

    assert ds._describe()["public_index"] == "https://example.test/i"
