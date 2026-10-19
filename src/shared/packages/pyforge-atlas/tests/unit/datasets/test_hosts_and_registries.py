"""Story 35.4 (spec-pyforge-atlas CAP-65): GitLab, Codeberg and the eight registries fill.

With ``pyforge.atlas.live_vcs_universe`` on, the hosts read legacy Phase K's release-then-tag REST
path and the registries legacy Phase L's version choices. No network: an injected fetcher, or the
suite's ``fake_transport`` where a request's headers matter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pyforge.atlas.datasets import credentials as credential_switch
from pyforge.atlas.datasets import vcs_sources as V
from pyforge.atlas.datasets.vcs_sources import RegistryUpstreamDataset, VcsHostSeedDataset

GITLAB = "https://gitlab.com/api/v4"
CODEBERG = "https://codeberg.org/api/v1"


@pytest.fixture()
def flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: True)


def _host(tmp_path: Path, host: str, **kwargs: Any) -> VcsHostSeedDataset:
    url = GITLAB if host == "gitlab" else CODEBERG
    return VcsHostSeedDataset(
        url=url, host=host, filepath=str(tmp_path / host), max_retries=0, sleep=lambda _s: None, **kwargs
    )


def test_the_host_paths_are_legacy_phase_ks_rest_pair():
    assert V._live_host_paths("gitlab", GITLAB, "group/sub/proj") == (
        f"{GITLAB}/projects/group%2Fsub%2Fproj/releases?per_page=1",
        f"{GITLAB}/projects/group%2Fsub%2Fproj/repository/tags?per_page=1",
    )
    assert V._live_host_paths("codeberg", CODEBERG, "owner/repo") == (
        f"{CODEBERG}/repos/owner/repo/releases/latest",
        f"{CODEBERG}/repos/owner/repo/tags?limit=10",
    )
    with pytest.raises(ValueError):
        V._live_host_paths("codeberg", CODEBERG, "owner/repo/extra")


def _answers(answers: dict[str, Any]):  # noqa: ANN202
    asked: list[str] = []

    def fetch(url: str) -> Any:
        asked.append(url)
        answer = answers.get(url)
        if isinstance(answer, Exception):
            raise answer
        return answer

    return fetch, asked


@pytest.mark.parametrize(
    ("host", "ident", "answers", "expected"),
    [
        ("gitlab", "g/p", {"releases": [{"tag_name": "v2.1"}]}, ("2.1", None)),  # a release wins
        ("codeberg", "o/r", {"releases": {"tag_name": "Release_3"}}, ("3", None)),  # Gitea: the latest release
        ("gitlab", "g/p", {"releases": [], "tags": [{"name": "rel-1.0"}]}, ("1.0", None)),  # no release: the tags
        ("codeberg", "o/r", {"releases": RuntimeError("404"), "tags": [{"name": "v9"}]}, ("9", None)),
        ("gitlab", "g/p", {"releases": [], "tags": []}, (None, "no tags")),
        ("gitlab", "g/p", {"releases": [], "tags": RuntimeError("boom")}, (None, "RuntimeError")),
    ],
    ids=["release", "gitea-release", "tag", "release-404", "neither", "tags-fail"],
)
def test_the_release_comes_before_the_tags(tmp_path, flag_on, host, ident, answers, expected):
    release_url, tags_url = V._live_host_paths(host, GITLAB if host == "gitlab" else CODEBERG, ident)
    fetch, asked = _answers({release_url: answers.get("releases"), tags_url: answers.get("tags")})

    assert _host(tmp_path, host)._release_or_tag(ident, fetcher=fetch) == expected
    assert asked[0] == release_url


def test_with_the_flag_on_load_many_reads_releases_and_persists(tmp_path, flag_on):
    release_url, _ = V._live_host_paths("gitlab", GITLAB, "g/p")
    fetch, _asked = _answers({release_url: [{"tag_name": "v4"}]})
    ds = _host(tmp_path, "gitlab")

    frame = ds.load_many([("pkg", "g/p")], fetcher=fetch)

    assert frame[["conda_name", "upstream_version", "last_error"]].values.tolist() == [["pkg", "4", None]]
    assert ds.load()["upstream_version"].tolist() == ["4"]


def test_with_the_flag_off_load_many_is_the_path_before(tmp_path):
    asked: list[str] = []

    def fetch(identifier: str) -> Any:
        asked.append(identifier)
        return [{"name": "v5"}]

    frame = _host(tmp_path, "gitlab").load_many([("pkg", "g/p")], fetcher=fetch)

    assert asked == ["g/p"] and frame["upstream_version"].tolist() == ["v5"]  # not normalized, one request


@pytest.mark.parametrize(
    ("switch", "credentials", "header"),
    [("1", "glpat-real", "glpat-real"), ("", "glpat-real", None), ("1", ["PRIVATE-TOKEN", "stub"], None)],
    ids=["switch-on", "switch-off", "stub-pair"],
)
def test_gitlab_carries_its_private_token_only_under_the_switch(
    tmp_path, flag_on, fake_transport, monkeypatch, switch, credentials, header
):
    monkeypatch.setenv(credential_switch.SWITCH, switch)
    release_url, _ = V._live_host_paths("gitlab", GITLAB, "g/p")
    fake_transport.answers[release_url] = (200, [{"tag_name": "v1"}])

    _host(tmp_path, "gitlab", credentials=credentials).load_many([("pkg", "g/p")])

    assert fake_transport.sent[0].headers.get("PRIVATE-TOKEN") == header
    assert "Authorization" not in fake_transport.sent[0].headers


def test_codeberg_never_carries_a_credential(tmp_path, flag_on, fake_transport, monkeypatch):
    monkeypatch.setenv(credential_switch.SWITCH, "1")
    release_url, _ = V._live_host_paths("codeberg", CODEBERG, "o/r")
    fake_transport.answers[release_url] = (200, {"tag_name": "v1"})

    _host(tmp_path, "codeberg", credentials="secret").load_many([("pkg", "o/r")])

    assert all("PRIVATE-TOKEN" not in r.headers and "Authorization" not in r.headers for r in fake_transport.sent)


def test_header_auth_sets_its_header_only_over_https_to_its_host():
    from types import SimpleNamespace

    auth = credential_switch.HeaderAuth("PRIVATE-TOKEN", "glpat-x", "gitlab.com")

    assert auth(SimpleNamespace(url="https://gitlab.com/api/v4/x", headers={})).headers == {"PRIVATE-TOKEN": "glpat-x"}
    assert auth(SimpleNamespace(url="http://gitlab.com/api/v4/x", headers={})).headers == {}
    assert auth(SimpleNamespace(url="https://evil.example/x", headers={})).headers == {}
    assert "glpat-x" not in repr(auth)


def test_maven_asks_for_group_and_artifact_with_the_flag_on(flag_on):
    path = V._maven_path("https://search.maven.org", "org.acme:thing")

    assert "q=g%3A%22org.acme%22%20AND%20a%3A%22thing%22" in path
    assert "q=a%3A%22solo%22" in V._maven_path("https://search.maven.org", "solo")


def test_maven_is_unchanged_with_the_flag_off():
    assert "q=a:org.acme%3Athing" in V._maven_path("https://search.maven.org", "org.acme:thing")


@pytest.mark.parametrize(("flag", "version"), [(True, "2.0.0"), (False, "3.0.0-beta")])
def test_nuget_takes_the_last_stable_version_with_the_flag_on(monkeypatch, flag, version):
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: flag)

    assert V._nuget_extract({"versions": ["1.0.0", "2.0.0", "3.0.0-beta"]}) == version


@pytest.mark.parametrize(("flag", "version"), [(True, "1.2.0"), (False, "1.3.0-rc1")])
def test_crates_prefers_the_stable_version_with_the_flag_on(monkeypatch, flag, version):
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: flag)
    payload = {"crate": {"max_stable_version": "1.2.0", "max_version": "1.3.0-rc1", "newest_version": "1.3.0-rc1"}}

    assert V._crates_extract(payload) == version


def test_the_slow_registries_run_at_one_request_a_second():
    import yaml

    catalog = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "conf" / "base" / "catalog.yml").read_text(encoding="utf-8")
    )

    assert catalog["vcs_registry_crates_raw"]["rps"] == 1.0 and catalog["vcs_registry_rubygems_raw"]["rps"] == 1.0
    assert (
        RegistryUpstreamDataset(url="https://crates.io", registry="crates", filepath="/tmp/x", rps=1.0).scheduler.rps
        == 1.0
    )
