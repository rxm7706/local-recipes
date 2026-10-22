"""Story 35.4 (spec-pyforge-atlas CAP-65): GitLab, Codeberg and the eight registries fill.

With ``pyforge.atlas.live_vcs_universe`` on, the hosts read legacy Phase K's release-then-tag REST
path and the registries legacy Phase L's version choices. No network: an injected fetcher, or the
suite's ``fake_transport`` where a request's headers matter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pyforge.testing_kit import flag_states

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


@flag_states("pyforge.atlas.live_vcs_universe")  # spelled out: the flag gate reads this file for the key
def test_nuget_takes_the_last_stable_version_with_the_flag_on(monkeypatch, flag_provider):
    flag = flag_provider[credential_switch.FLAG_KEY]
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: flag)

    assert V._nuget_extract({"versions": ["1.0.0", "2.0.0", "3.0.0-beta"]}) == ("2.0.0" if flag else "3.0.0-beta")


@flag_states("pyforge.atlas.live_vcs_universe")  # spelled out: the flag gate reads this file for the key
def test_crates_prefers_the_stable_version_with_the_flag_on(monkeypatch, flag_provider):
    flag = flag_provider[credential_switch.FLAG_KEY]
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: flag)
    payload = {"crate": {"max_stable_version": "1.2.0", "max_version": "1.3.0-rc1", "newest_version": "1.3.0-rc1"}}

    assert V._crates_extract(payload) == ("1.2.0" if flag else "1.3.0-rc1")


def test_a_registry_request_names_atlas_as_its_agent_with_the_flag_on(tmp_path, flag_on, fake_transport):
    url = "https://crates.io/api/v1/crates/serde"
    fake_transport.answers[url] = (200, {"crate": {"max_stable_version": "1.0.0"}})
    ds = RegistryUpstreamDataset(url="https://crates.io", registry="crates", filepath=str(tmp_path / "c"), rps=1000.0)

    ds.load_many([("rust-serde", "serde")])

    (sent,) = fake_transport.sent
    assert sent.headers["User-Agent"] == V.USER_AGENT and "Authorization" not in sent.headers


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


# -- review round 1 ------------------------------------------------------------------------------


def _redirecting(monkeypatch, location: str, status: int = 302, only: str | None = None) -> list:  # noqa: ANN001
    """Answer every request (or only those whose URL contains ``only``; the rest 404) with a ``status``
    redirect to ``location``; record what is sent."""
    import requests
    import requests.adapters

    sent: list = []

    def send(self, request, *args, **kwargs):  # noqa: ANN001, ANN202
        sent.append(request)
        response = requests.models.Response()
        code = status if only is None or only in request.url else 404
        response.status_code, response._content, response.url, response.request = code, b"", request.url, request
        response.headers["Location"] = location
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    return sent


@pytest.mark.parametrize("location", ["https://evil.example/x", "http://gitlab.com.evil.example/x"])
def test_a_request_carrying_gitlabs_token_never_follows_a_redirect(tmp_path, flag_on, monkeypatch, location):
    monkeypatch.setenv(credential_switch.SWITCH, "1")
    sent = _redirecting(monkeypatch, location)

    frame = _host(tmp_path, "gitlab", credentials="glpat-real").load_many([("pkg", "g/p")])

    assert all(r.url.startswith(GITLAB) for r in sent)  # the release, then the tags; never the Location
    assert frame["last_error"].tolist() == ["HTTP 302"]


def test_a_malformed_codeberg_identifier_is_its_rows_error(tmp_path, flag_on, fake_transport):
    frame = _host(tmp_path, "codeberg").load_many([("pkg", "owner/repo/extra")])

    assert fake_transport.sent == [] and "codeberg" in frame["last_error"].iloc[0]


def test_a_hosts_request_never_reads_netrc(tmp_path, flag_on, fake_transport, monkeypatch):
    netrc = tmp_path / "netrc"
    netrc.write_text("machine codeberg.org login someone password secret\n", encoding="utf-8")
    netrc.chmod(0o600)
    monkeypatch.setenv("NETRC", str(netrc))
    release_url, _ = V._live_host_paths("codeberg", CODEBERG, "o/r")
    fake_transport.answers[release_url] = (200, {"tag_name": "v1"})

    _host(tmp_path, "codeberg").load_many([("pkg", "o/r")])

    assert all("Authorization" not in r.headers for r in fake_transport.sent)


def test_the_first_tag_is_the_latest(tmp_path, flag_on):
    release_url, tags_url = V._live_host_paths("gitlab", GITLAB, "g/p")
    fetch, _asked = _answers({release_url: [], tags_url: [{"name": "v3"}, {"name": "v2"}]})

    assert _host(tmp_path, "gitlab")._release_or_tag("g/p", fetcher=fetch) == ("3", None)


def test_a_release_that_answers_404_goes_to_the_tags_at_once(tmp_path, flag_on, fake_transport):
    release_url, tags_url = V._live_host_paths("gitlab", GITLAB, "g/p")
    fake_transport.answers[tags_url] = (200, [{"name": "v7"}])  # the release URL answers 404 (default)
    ds = VcsHostSeedDataset(
        url=GITLAB, host="gitlab", filepath=str(tmp_path / "g"), max_retries=3, sleep=lambda _s: None
    )

    frame = ds.load_many([("pkg", "g/p")])

    assert [r.url for r in fake_transport.sent] == [release_url, tags_url] and frame["upstream_version"].tolist() == [
        "7"
    ]


def test_a_tags_failure_is_recorded_as_its_status(tmp_path, flag_on, fake_transport):
    frame = _host(tmp_path, "gitlab").load_many([("pkg", "g/p")])  # both URLs answer 404

    assert frame["last_error"].tolist() == ["HTTP 404"]


def test_a_gitlab_release_without_a_tag_name_reads_its_name_and_maven_its_v(flag_on):
    assert V._release_tag([{"name": "v1.4"}]) == "v1.4" and V._release_tag({"name": "x"}) is None
    assert V._maven_extract({"response": {"docs": [{"v": "2.0"}]}}) == "2.0"


def test_with_the_flag_off_maven_never_falls_back_to_v():
    assert V._maven_extract({"response": {"docs": [{"v": "2.0"}]}}) is None  # as before Story 35.4
    assert V._maven_extract({"response": {"docs": [{"latestVersion": "3.1", "v": "2.0"}]}}) == "3.1"


def test_a_hosts_request_names_atlas_as_its_agent(tmp_path, flag_on, fake_transport):
    _host(tmp_path, "codeberg").load_many([("pkg", "o/r")])

    assert {r.headers["User-Agent"] for r in fake_transport.sent} == {V.USER_AGENT}


# -- review round 2 ------------------------------------------------------------------------------


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_no_redirect_status_carries_gitlabs_token_away(tmp_path, flag_on, monkeypatch, status):
    monkeypatch.setenv(credential_switch.SWITCH, "1")
    sent = _redirecting(monkeypatch, "https://evil.example/x", status)

    frame = _host(tmp_path, "gitlab", credentials="glpat-real").load_many([("pkg", "g/p")])

    assert all(r.url.startswith(GITLAB) for r in sent) and frame["last_error"].tolist() == [f"HTTP {status}"]


def test_a_redirect_on_the_tags_alone_is_never_followed(tmp_path, flag_on, monkeypatch):
    monkeypatch.setenv(credential_switch.SWITCH, "1")
    sent = _redirecting(monkeypatch, "https://evil.example/x", 307, only="/repository/tags")

    frame = _host(tmp_path, "gitlab", credentials="glpat-real").load_many([("pkg", "g/p")])

    assert [r.url.split("/projects/", 1)[1].split("?", 1)[0] for r in sent] == [
        "g%2Fp/releases",
        "g%2Fp/repository/tags",
    ]
    assert frame["last_error"].tolist() == ["HTTP 307"]


def _http_error(status: int, retry_after: str | None = None) -> Exception:
    from types import SimpleNamespace

    from kedro.io import DatasetError

    headers = {"Retry-After": retry_after} if retry_after else {}
    return DatasetError(
        "Failed to fetch data", SimpleNamespace(response=SimpleNamespace(status_code=status, headers=headers))
    )


def _flaky(first: Exception, answer: Any):  # noqa: ANN202
    calls = {"n": 0}

    def fetch(_url: str) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise first
        return answer

    return fetch


def _retrying(tmp_path: Path, waits: list[float]) -> VcsHostSeedDataset:
    return VcsHostSeedDataset(
        url=CODEBERG, host="codeberg", filepath=str(tmp_path / "c"), max_retries=2, sleep=waits.append
    )


def test_a_429_waits_its_retry_after_and_retries(tmp_path, flag_on):
    waits: list[float] = []

    release = _retrying(tmp_path, waits)._get("u", _flaky(_http_error(429, "7"), {"tag_name": "v1"}))

    assert release == {"tag_name": "v1"} and waits == [7.0]


def test_a_5xx_is_retried_after_a_backoff(tmp_path, flag_on):
    waits: list[float] = []

    assert _retrying(tmp_path, waits)._get("u", _flaky(_http_error(503), {"ok": 1})) == {"ok": 1}
    assert len(waits) == 1 and waits[0] < 7.0


def test_a_failure_with_no_status_is_retried_and_named_by_its_cause(tmp_path, flag_on):
    from kedro.io import DatasetError

    def dropped() -> Exception:
        try:
            raise ConnectionError("connection reset by peer")
        except ConnectionError as exc:
            try:
                raise DatasetError("Failed to fetch data") from exc
            except DatasetError as wrapped:
                return wrapped

    waits: list[float] = []
    ds = _retrying(tmp_path, waits)
    assert ds._get("u", _flaky(dropped(), {"ok": 1})) == {"ok": 1} and len(waits) == 1

    def always(_url: str) -> Any:
        raise dropped()

    assert ds._release_or_tag("o/r", fetcher=always) == (None, "ConnectionError")  # its cause, never its text


def test_a_404_is_never_retried(tmp_path, flag_on):
    waits: list[float] = []

    with pytest.raises(Exception, match="Failed to fetch"):
        _retrying(tmp_path, waits)._get("u", _flaky(_http_error(404), {"ok": 1}))
    assert waits == []


def test_a_tag_without_a_name_reads_its_tag_name(tmp_path, flag_on):
    release_url, tags_url = V._live_host_paths("codeberg", CODEBERG, "o/r")
    fetch, _asked = _answers({release_url: {}, tags_url: [{"tag_name": "v4"}]})

    assert _host(tmp_path, "codeberg")._release_or_tag("o/r", fetcher=fetch) == ("4", None)


# -- review round 3 ------------------------------------------------------------------------------


def test_a_programming_error_is_never_retried(tmp_path, flag_on):
    waits: list[float] = []

    with pytest.raises(TypeError):
        _retrying(tmp_path, waits)._get("u", _flaky(TypeError("bad call"), {"ok": 1}))
    assert waits == []


def test_each_attempt_takes_its_own_rate_token(tmp_path, flag_on, monkeypatch):
    ds = _retrying(tmp_path, [])
    tokens: list[int] = []
    monkeypatch.setattr(ds.scheduler, "acquire", lambda *a, **k: tokens.append(1))

    ds._get("u", _flaky(_http_error(503), {"ok": 1}))

    assert len(tokens) == 2  # the failed try and the retry


def test_a_cause_chain_that_loops_is_named_without_hanging():
    first, second = OSError("a"), ValueError("b")
    first.__cause__, second.__cause__ = second, first  # each names the other

    assert V._why(first) == "ValueError"
    looped = RuntimeError("c")
    looped.__cause__ = looped
    assert V._why(looped) == "RuntimeError"


def test_the_host_stores_ask_with_legacys_timeout():
    import yaml

    catalog = yaml.safe_load((Path(__file__).resolve().parents[3] / "conf" / "base" / "catalog.yml").read_text())

    assert catalog["vcs_gitlab_api_raw"]["timeout_seconds"] == catalog["vcs_codeberg_api_raw"]["timeout_seconds"] == 20
