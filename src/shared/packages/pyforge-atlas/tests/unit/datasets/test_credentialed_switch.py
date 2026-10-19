"""Story 35.1 (spec-pyforge-atlas CAP-65): one opt-in switch, and GitHub authenticates.

No network: ``fake_transport`` (root ``conftest.py``) answers every request and records it; the
autouse guard fails any test whose request carries a credential while the switch is off.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import credentials as credential_switch
from pyforge.atlas.datasets.rate_limit import RateLimitedScheduler
from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.datasets.request_datasets import GITHUB_BATCH_QUERY_MAX, GitHubRequestDataset
from pyforge.atlas.datasets.vcs_sources import RegistryUpstreamDataset, VcsHostSeedDataset

GRAPHQL = "https://api.github.com/graphql"
TOKEN = "ghp_test_not_a_real_token"
_REAL_FLAG_READER = credential_switch.live_vcs_universe  # captured before the suite's autouse pin


def _dataset(tmp_path: Path, url: str = GRAPHQL, credentials=None) -> GitHubRequestDataset:  # noqa: ANN001
    return GitHubRequestDataset(
        url=url,
        filepath=str(tmp_path / "store"),
        credentials={"token": TOKEN} if credentials is None else credentials,
        scheduler=RateLimitedScheduler(rps=1000.0, bucket_capacity=100),
        sleep=lambda _s: None,
        max_retries=1,
    )


def _request(*repos: tuple[str, str]) -> RefreshRequest:
    # Story 35.2: with the flag on the store reads the universe's upstreams (conda_name, owner, repo)
    upstream = tuple((f"conda-{repo}", owner, repo) for owner, repo in repos)
    return RefreshRequest(
        store="vcs_github_api_raw", cadence_seconds=0, force=True, github_repos=tuple(repos), upstream_repos=upstream
    )


def _release(tag: str = "v1.2") -> dict:
    """Story 35.3: a Phase K repository node (latest release, latest tag)."""
    return {"releases": {"nodes": [{"tagName": tag}]}, "refs": {"nodes": []}}


def _health() -> dict:
    return {"isArchived": False, "stargazerCount": 7, "pushedAt": "2026-10-18T00:00:00Z", "issues": {"totalCount": 2}}


@pytest.fixture()
def flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: True)


@pytest.fixture()
def switch_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(credential_switch.SWITCH, "1")


def _write_last_good(ds: GitHubRequestDataset) -> None:
    Path(ds._filepath).mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"feedstock_name": "old", "stars": 1}]).to_parquet(ds._store_path, index=False)


def _marker_text(ds: GitHubRequestDataset) -> str:
    return ds._staleness_path.read_text(encoding="utf-8")


def test_without_the_switch_nothing_is_sent_and_last_good_is_kept_under_stale(fake_transport, flag_on, tmp_path):
    ds = _dataset(tmp_path)
    _write_last_good(ds)

    ds.save(_request(("o", "r")))

    marker = _marker_text(ds)
    assert fake_transport.sent == []
    assert credential_switch.SWITCH in marker and TOKEN not in marker
    assert list(ds.load()["feedstock_name"]) == ["old"]


@pytest.mark.parametrize("value", ["", "0", "true", "yes", " 1"])
def test_only_the_exact_value_1_turns_the_switch_on(monkeypatch, value):
    monkeypatch.setenv(credential_switch.SWITCH, value)
    assert credential_switch.credentialed() is False


def test_with_the_switch_github_gets_a_bearer_header_and_the_rows_land(fake_transport, flag_on, switch_on, tmp_path):
    fake_transport.answers[GRAPHQL] = (200, {"data": {"r0": _release()}})
    ds = _dataset(tmp_path)

    ds.save(_request(("o", "r")))

    sent = fake_transport.sent[0]  # Phase K's batch; Phase E.5's listing follows (Story 35.3)
    assert all(r.method == "POST" and r.headers["Authorization"] == f"Bearer {TOKEN}" for r in fake_transport.sent)
    # Story 35.3: a GraphQL POST waits 60 s at most
    assert set(fake_transport.timeouts) == {min(ds._timeout_seconds, ds.GRAPHQL_TIMEOUT_SECONDS)}
    assert 'repository(owner: "o", name: "r")' in json.loads(sent.body)["query"]
    row = ds.load().set_index("key").loc["conda-r"]
    assert (row["kind"], row["repo"], row["upstream_version"]) == ("upstream", "o/r", "1.2")
    assert ds.staleness() is None


@pytest.mark.parametrize(
    ("url", "named"),
    [("https://github.example.com/api/graphql", "github.example.com"), ("http://api.github.com/graphql", "http://")],
    ids=["another-host", "plain-http"],
)
def test_a_url_off_https_api_github_com_never_receives_the_token(
    fake_transport, flag_on, switch_on, tmp_path, url, named
):
    ds = _dataset(tmp_path, url=url)

    ds.save(_request(("o", "r")))

    assert fake_transport.sent == [] and named in _marker_text(ds)


def test_the_switch_is_read_at_save_not_at_construction(fake_transport, flag_on, tmp_path, monkeypatch):
    ds = _dataset(tmp_path)  # built with the switch unset
    monkeypatch.setenv(credential_switch.SWITCH, "1")
    fake_transport.answers[GRAPHQL] = (200, {"data": {"r0": _release()}})

    ds.save(_request(("o", "r")))

    assert fake_transport.sent


@pytest.mark.parametrize(
    "credentials",
    [{"token": ""}, {}, ["user", "password"], "  ", {"token": "abc\ndef"}, "a b"],
    ids=["empty", "missing", "pair", "blank", "newline-inside", "space-inside"],
)
def test_no_usable_token_sends_nothing(fake_transport, flag_on, switch_on, tmp_path, credentials):
    ds = _dataset(tmp_path, credentials=credentials)

    ds.save(_request(("o", "r")))

    assert fake_transport.sent == [] and "no github_token" in _marker_text(ds)


@pytest.mark.parametrize("status", [401, 403, 429])
def test_a_refusal_is_sent_once_and_never_reaches_a_marker_or_a_row(
    fake_transport, flag_on, switch_on, tmp_path, status
):
    fake_transport.answers[GRAPHQL] = (status, {"message": "refused"})
    ds = _dataset(tmp_path)
    _write_last_good(ds)
    repos = [("o", f"r{i}") for i in range(GITHUB_BATCH_QUERY_MAX + 1)]  # two chunks

    ds.save(_request(*repos))

    assert len(fake_transport.sent) == 1  # no retry, and the second chunk is never sent
    assert f"HTTP {status}" in _marker_text(ds) and TOKEN not in _marker_text(ds)
    assert list(ds.load()["feedstock_name"]) == ["old"]  # last-good kept


def test_a_refusal_after_a_good_chunk_keeps_its_rows_and_marks_the_store_stale(
    fake_transport, flag_on, switch_on, tmp_path, monkeypatch
):
    answers = iter([(200, {"data": {f"r{i}": _release() for i in range(GITHUB_BATCH_QUERY_MAX)}}), (429, {})])
    fake_transport.answers = _Each(answers)
    ds = _dataset(tmp_path)
    repos = [("o", f"r{i}") for i in range(GITHUB_BATCH_QUERY_MAX * 2 + 1)]  # three chunks

    ds.save(_request(*repos))

    assert len(fake_transport.sent) == 2 and len(ds.load()) == GITHUB_BATCH_QUERY_MAX * 2
    assert "stopped after HTTP 429" in _marker_text(ds)


class _Each(dict):
    """``answers.get(url, default)`` that hands out the next scripted answer per request."""

    def __init__(self, answers) -> None:  # noqa: ANN001
        super().__init__()
        self._answers = answers

    def get(self, _url, default=None):  # noqa: ANN001, ANN202
        return next(self._answers, default)


def test_a_failure_without_a_status_names_only_its_type_on_the_credentialed_path(
    fake_transport, flag_on, switch_on, tmp_path, monkeypatch
):
    import requests.adapters

    def refuse(self, request, *args, **kwargs):  # noqa: ANN001, ANN202
        raise ValueError(f"could not send {request.headers}")  # kedro keeps this text; it quotes the header

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", refuse)
    ds = _dataset(tmp_path)

    ds.save(_request(("o", "r")))

    marker = _marker_text(ds)
    assert "DatasetError" in marker and TOKEN not in marker and "could not send" not in marker


def test_a_malformed_graphql_error_path_never_fails_the_run(fake_transport, flag_on, switch_on, tmp_path):
    odd = {"type": "NOT_FOUND", "path": [["r0"]], "message": "x"}
    fake_transport.answers[GRAPHQL] = (200, {"data": {"r0": None}, "errors": [odd]})
    ds = _dataset(tmp_path)

    ds.save(_request(("o", "gone")))  # no raise (AD-13)


def test_a_graphql_error_body_says_why(fake_transport, flag_on, switch_on, tmp_path):
    error = {"type": "RATE_LIMITED", "message": "API rate limit exceeded"}
    fake_transport.answers[GRAPHQL] = (200, {"errors": [error]})
    ds = _dataset(tmp_path)

    ds.save(_request(("o", "r")))

    assert "RATE_LIMITED: API rate limit exceeded" in _marker_text(ds)


def test_a_missing_repository_keeps_its_own_graphql_error(fake_transport, flag_on, switch_on, tmp_path):
    missing = {"type": "NOT_FOUND", "path": ["r0"], "message": "Could not resolve to a Repository"}
    fake_transport.answers[GRAPHQL] = (200, {"data": {"r0": None, "r1": _release()}, "errors": [missing]})
    ds = _dataset(tmp_path)

    ds.save(_request(("o", "gone"), ("o", "here")))

    errors = dict(zip(ds.load()["key"], ds.load()["last_error"], strict=True))
    assert errors["conda-gone"].startswith("NOT_FOUND") and errors["conda-here"] is None


def test_flag_off_keeps_the_path_this_story_found(fake_transport, switch_on, tmp_path):
    # OFF is today's behaviour: the GET-only load() route, which sends nothing for a POST
    ds = _dataset(tmp_path)

    frame = ds.fetch_repo_health([("o", "r")])

    assert fake_transport.sent == [] and frame["last_error"].str.contains("Only GET").all()
    assert "fetch returned no data" in _marker_text(ds)  # the marker this story found


def test_bearer_auth_sets_the_header_only_for_its_host_and_hides_the_token():
    auth = credential_switch.BearerAuth(TOKEN, "api.github.com")
    own = auth(SimpleNamespace(url="https://api.github.com/graphql", headers={}))
    other = auth(SimpleNamespace(url="https://evil.example/graphql", headers={}))
    cleartext = auth(SimpleNamespace(url="http://api.github.com/graphql", headers={}))

    assert own.headers == {"Authorization": f"Bearer {TOKEN}"} and other.headers == {} and cleartext.headers == {}
    assert TOKEN not in repr(auth)


@pytest.mark.parametrize(
    ("credentials", "token"),
    [({"token": " t "}, "t"), ("t", "t"), ({"token": ""}, None), (["u", "p"], None), (None, None), ({}, None)],
)
def test_token_of_reads_the_two_catalog_shapes(credentials, token):
    assert credential_switch.token_of(credentials) == token


@pytest.mark.parametrize("header", ["Authorization", "Proxy-Authorization", "PRIVATE-TOKEN", "X-NuGet-ApiKey"])
def test_the_autouse_guard_fails_a_credentialed_request_without_the_switch(header, monkeypatch):
    import socket

    import requests

    def no_socket(*_a, **_k):  # noqa: ANN002, ANN003, ANN202 -- were the guard ever gone, no network
        raise OSError("sockets are refused in this test")

    monkeypatch.setattr(socket.socket, "connect", no_socket)
    monkeypatch.setattr(socket, "getaddrinfo", no_socket)
    # no fake_transport: the suite's own guard refuses before anything reaches a socket
    with pytest.raises(pytest.fail.Exception, match=credential_switch.SWITCH):
        requests.get("https://api.github.com/x", headers={header: "t"}, timeout=1)


def test_with_the_flag_on_a_host_or_registry_request_carries_a_no_op_auth_and_no_credential(monkeypatch):
    from pyforge.atlas.datasets import public_sources
    from pyforge.atlas.datasets.vcs_sources import USER_AGENT, _request_kwargs

    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: True)
    on = _request_kwargs(30, ["PRIVATE-TOKEN", "stub"])
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: False)
    off = _request_kwargs(30, ["PRIVATE-TOKEN", "stub"])

    # no credential; the no-op auth keeps ~/.netrc out; Story 35.4 names atlas as the agent
    assert on == {"load_args": {**public_sources.request_args(30), "headers": {"User-Agent": USER_AGENT}}}
    assert off == {"load_args": {"timeout": 30}, "credentials": ["PRIVATE-TOKEN", "stub"]}


@pytest.mark.parametrize("flag", [True, False], ids=["flag-on", "flag-off"])
@pytest.mark.parametrize("kind", ["gitlab-host", "npm-registry"])
def test_a_vcs_host_sends_its_credential_only_with_the_flag_off(fake_transport, tmp_path, monkeypatch, flag, kind):
    # Story 35.4 decides which hosts may authenticate; until then the flag-on path is public
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: flag)
    common = {"filepath": str(tmp_path / "store"), "max_retries": 0, "sleep": lambda _s: None}
    if kind == "gitlab-host":
        ds = VcsHostSeedDataset(
            url="https://gitlab.com/api/v4", host="gitlab", credentials=["PRIVATE-TOKEN", "stub"], **common
        )
    else:
        ds = RegistryUpstreamDataset(
            url="https://registry.npmjs.org", registry="npm", credentials=["npm", "stub"], **common
        )

    if flag:
        with contextlib.suppress(Exception):  # the fake transport answers 404; only the request matters
            ds.fetch_one("group/project")
        assert fake_transport.sent
        assert not any("Authorization" in r.headers or "PRIVATE-TOKEN" in r.headers for r in fake_transport.sent)
    else:
        with pytest.raises(pytest.fail.Exception):  # today's path sends the pair as Basic auth: the guard refuses
            ds.fetch_one("group/project")


def test_the_real_reader_reads_off_when_the_tree_lacks_the_key(tmp_path, monkeypatch):
    from pyforge.testing_kit import flagd_tree

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {"pyforge.atlas.live_public_sources": "on"})))

    assert _REAL_FLAG_READER() is False


@pytest.mark.parametrize("variant", ["on", "off"])
def test_the_real_reader_reads_the_key_from_the_tree(tmp_path, monkeypatch, variant):
    from pyforge.testing_kit import flagd_tree

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {credential_switch.FLAG_KEY: variant})))

    assert _REAL_FLAG_READER() is (variant == "on")


@flag_states("pyforge.atlas.live_vcs_universe")  # spelled out: the flag gate reads this file for the key
def test_the_flag_is_read_at_each_save(fake_transport, switch_on, tmp_path, flag_provider, monkeypatch):
    """On: the switch decides and the bearer POST runs. Off: the path before this story (no request)."""
    flag_on = flag_provider[credential_switch.FLAG_KEY]
    ds = _dataset(tmp_path)  # built before the flag is read
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: flag_on)
    fake_transport.answers[GRAPHQL] = (200, {"data": {"r0": _release()}})

    ds.save(_request(("o", "r")))

    assert bool(fake_transport.sent) is flag_on
