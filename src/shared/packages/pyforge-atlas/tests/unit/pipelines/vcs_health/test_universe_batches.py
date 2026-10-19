"""Story 35.2 (spec-pyforge-atlas CAP-65): the VCS and registry batches come from the whole universe.

Pure frames in the shapes measured on 2026-10-18; the stores' selection is exercised with injected
fetchers, so nothing reaches the network.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import credentials as credential_switch
from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.datasets.vcs_sources import RegistryUpstreamDataset, VcsHostSeedDataset
from pyforge.atlas.pipelines.vcs_health.nodes import (
    refresh_vcs_github_store,
    refresh_vcs_host_stores,
    refresh_vcs_registry_stores,
)
from pyforge.atlas.pipelines.vcs_health.vcs_refresh_identifiers import (
    batches_from_universe,
    registry_names,
    vcs_repo,
)

ENUM = pd.DataFrame({"conda_name": ["airflow", "airflow-with-amazon", "glab", "cb", "jsx", "javaish", "solo"]})
GRAPH = pd.DataFrame(
    {
        "feedstock_name": ["airflow", "glab", "cb", "jsx", "javaish", "solo-fs", "gone"],
        "conda_name": ["airflow", "glab", "cb", "jsx", "javaish", "solo", "gone"],
        "depends_on": [None] * 7,
        "source_url": [
            "https://pypi.io/packages/source/a/apache-airflow/a.tgz",
            None,
            None,
            "https://registry.npmjs.org/@scope/jsx/-/jsx-1.0.tgz",
            "https://repo.maven.apache.org/maven2/org/acme/thing/1.0/thing-1.0.jar",
            None,
            None,
        ],
        "repo_url": ["https://github.com/apache/airflow/", None, None, None, None, None, "https://github.com/x/gone"],
        "dev_url": [None, "https://gitlab.com/group/sub/glab.git", None, None, None, None, None],
        "home_url": [
            None,
            None,
            "https://codeberg.org/someone/cb",
            None,
            "https://crates.io/crates/javaish-rs",
            "https://github.com/solo/solo-py.git",
            None,
        ],
    }
)
ATTRIBUTION = pd.DataFrame(
    {
        "conda_name": ["airflow", "airflow-with-amazon", "glab", "cb", "jsx", "javaish"],
        "feedstock_name": ["airflow", "airflow", "glab", "cb", "jsx", "javaish"],
    }
)
IDENTITY = pd.DataFrame(
    {
        "Core_Python_Package_Name": ["requests"],
        "primary_purl": ["pkg:github/psf/requests"],
        "alternative_purls": [""],
        "source_repository_url": [""],
    }
)


@pytest.mark.parametrize(
    ("urls", "repo"),
    [
        (("https://github.com/apache/airflow/",), ("github", "apache", "airflow")),
        (("https://github.com/solo/solo-py.git",), ("github", "solo", "solo-py")),  # legacy stops at the dot
        (("https://gitlab.com/group/sub/proj/-/tree/main",), ("gitlab", "group/sub/proj", "proj")),
        (("https://gitlab.com/group/proj.git",), ("gitlab", "group/proj", "proj")),
        (("https://codeberg.org/someone/cb",), ("codeberg", "someone", "cb")),
        ((None, "", "https://example.org"), None),
        (
            (None, "https://gitlab.com/a/b", "https://github.com/c/d"),
            ("gitlab", "a/b", "b"),
        ),  # the first URL that names one
        (("https://sqlite.org/src", "https://github.com/c/d"), ("github", "c", "d")),  # a non-VCS URL falls through
    ],
)
def test_vcs_repo_is_legacy_phase_ks_extraction(urls: tuple[Any, ...], repo: tuple[str, str, str] | None):
    assert vcs_repo(*urls) == repo


def test_registry_names_read_the_source_url_then_the_about_urls():
    assert registry_names(
        "https://repo1.maven.org/maven2/org/acme/thing/1.0/thing-1.0.pom",
        "https://rubygems.org/gems/thing",
        "https://search.maven.org/artifact/org.acme/thing",
        "https://www.nuget.org/packages/Thing.Net",
    ) == [("maven", "org.acme:thing"), ("rubygems", "thing"), ("nuget", "Thing.Net")]
    assert registry_names("https://registry.npmjs.org/left-pad/-/left-pad-1.tgz") == [("npm", "left-pad")]
    assert registry_names(None, None) == []


def test_the_universe_batches_follow_each_packages_feedstock():
    batches = batches_from_universe(ENUM, GRAPH, ATTRIBUTION)

    assert batches["upstream_repos"] == (
        ("airflow", "apache", "airflow"),
        ("airflow-with-amazon", "apache", "airflow"),  # attributed to the airflow feedstock, not an anchor
        ("solo", "solo", "solo-py"),  # no attribution row: its anchor
    )
    assert batches["gitlab"] == (("glab", "group/sub/glab"),)
    assert batches["codeberg"] == (("cb", "someone/cb"),)
    assert batches["registries"]["npm"] == (("jsx", "@scope/jsx"),)
    assert batches["registries"]["maven"] == (("javaish", "org.acme:thing"),)
    assert batches["registries"]["crates"] == (("javaish", "javaish-rs"),)
    assert batches["registries"]["cran"] == ()  # legacy never writes cran, cpan or luarocks names
    assert batches["feedstocks"] == ("airflow", "cb", "glab", "javaish", "jsx")  # gone: not enumerated


@pytest.mark.parametrize("args", [(None, None, None), (pd.DataFrame(), GRAPH, ATTRIBUTION), (ENUM, None, None)])
def test_missing_inputs_give_empty_batches(args):
    batches = batches_from_universe(*args)

    assert batches["upstream_repos"] == () and batches["gitlab"] == () and not any(batches["registries"].values())


def test_the_triggers_carry_both_batches():
    github = refresh_vcs_github_store({}, IDENTITY, ENUM, GRAPH, ATTRIBUTION)
    gitlab, codeberg = refresh_vcs_host_stores({}, IDENTITY, ENUM, GRAPH, ATTRIBUTION)
    registries = {r.store: r for r in refresh_vcs_registry_stores({}, IDENTITY, ENUM, GRAPH, ATTRIBUTION)}

    assert github.github_repos == (("psf", "requests"),)  # the identity batch, unchanged
    assert ("airflow", "apache", "airflow") in github.upstream_repos and "airflow" in github.feedstocks
    assert gitlab.universe_pairs == (("glab", "group/sub/glab"),) and codeberg.universe_pairs == (("cb", "someone/cb"),)
    assert registries["vcs_registry_npm_raw"].universe_pairs == (("jsx", "@scope/jsx"),)


class _Recorder(VcsHostSeedDataset):
    def __init__(self, tmp_path) -> None:  # noqa: ANN001
        super().__init__(url="https://gitlab.com/api/v4", host="gitlab", filepath=str(tmp_path / "store"))
        self.asked: list[Any] = []

    def load_many(self, pairs, **kwargs):  # noqa: ANN001, ANN003, ANN201
        self.asked = list(pairs)


@flag_states("pyforge.atlas.live_vcs_universe")  # spelled out: the flag gate reads this file for the key
def test_a_host_store_reads_the_universe_only_with_the_flag_on(tmp_path, flag_provider, monkeypatch):
    flag_on = flag_provider[credential_switch.FLAG_KEY]
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: flag_on)
    ds = _Recorder(tmp_path)
    request = RefreshRequest(
        store="vcs_gitlab_api_raw",
        cadence_seconds=0,
        force=True,
        vcs_pairs=(("ident", "a/b"),),
        universe_pairs=(("uni", "c/d"),),
    )

    ds.save(request)

    assert ds.asked == ([("uni", "c/d")] if flag_on else [("ident", "a/b")])


@flag_states("pyforge.atlas.live_vcs_universe")  # spelled out: the flag gate reads this file for the key
def test_a_registry_store_reads_the_universe_only_with_the_flag_on(tmp_path, flag_provider, monkeypatch):
    flag_on = flag_provider[credential_switch.FLAG_KEY]
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: flag_on)
    asked: list[Any] = []
    ds = RegistryUpstreamDataset(url="https://registry.npmjs.org", registry="npm", filepath=str(tmp_path / "s"))
    monkeypatch.setattr(ds, "load_many", lambda pairs, **_k: asked.extend(pairs))

    ds.save(
        RefreshRequest(
            store="vcs_registry_npm_raw",
            cadence_seconds=0,
            force=True,
            vcs_pairs=(("left-pad", "left-pad"),),
            universe_pairs=(("jsx", "@scope/jsx"),),
        )
    )

    assert asked == ([("jsx", "@scope/jsx")] if flag_on else [("left-pad", "left-pad")])


def test_an_archived_feedstock_and_its_packages_are_left_out():
    graph = GRAPH.assign(feedstock_archived=[False, False, False, True, False, False, False])  # jsx archived

    batches = batches_from_universe(ENUM, graph, ATTRIBUTION)

    assert "jsx" not in batches["feedstocks"] and batches["registries"]["npm"] == ()
    assert "airflow" in batches["feedstocks"]


def test_a_feedstock_is_asked_only_for_an_enumerated_package():
    attribution = pd.concat([ATTRIBUTION, pd.DataFrame({"conda_name": ["gone"], "feedstock_name": ["gone"]})])

    assert "gone" not in batches_from_universe(ENUM, GRAPH, attribution)["feedstocks"]


def test_registry_names_skip_a_missing_url_and_read_a_maven_about_url():
    assert registry_names(float("nan"), None, "") == []
    assert registry_names(None, "https://search.maven.org/artifact/org.x/y") == [("maven", "org.x:y")]


def test_the_new_request_fields_serialize():
    request = RefreshRequest(
        store="s", upstream_repos=(("c", "o", "r"),), universe_pairs=(("c", "p"),), feedstocks=("f",)
    )

    out = request.to_dict()
    assert out["upstream_repos"] == [("c", "o", "r")] and out["universe_pairs"] == [("c", "p")]
    assert out["feedstocks"] == ["f"]


def test_with_the_flag_on_the_identity_subset_no_longer_drives_the_github_batch(tmp_path, monkeypatch):
    # the population test: identity names one repo the universe does not; the store asks for the universe's
    from pyforge.atlas.datasets.request_datasets import GitHubRequestDataset

    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: True)
    monkeypatch.setenv(credential_switch.SWITCH, "1")
    asked: list[Any] = []
    ds = GitHubRequestDataset(
        url="https://api.github.com/graphql", filepath=str(tmp_path / "gh"), credentials={"token": "t"}
    )
    monkeypatch.setattr(
        ds, "fetch_github", lambda upstream, feedstocks, **_k: asked.extend((o, r) for _c, o, r in upstream)
    )

    ds.save(refresh_vcs_github_store({}, IDENTITY, ENUM, GRAPH, ATTRIBUTION))

    assert ("psf", "requests") not in asked and ("apache", "airflow") in asked and ("solo", "solo-py") in asked
