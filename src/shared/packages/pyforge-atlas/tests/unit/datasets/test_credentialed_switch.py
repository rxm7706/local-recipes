"""Story 35.1 (spec-pyforge-atlas CAP-65): one opt-in switch, and GitHub authenticates.

No network: ``fake_transport`` (root ``conftest.py``) answers every request and records it; the
autouse guard fails any test whose request carries a credential while the switch is off.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import credentials as credential_switch
from pyforge.atlas.datasets.rate_limit import RateLimitedScheduler
from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.datasets.request_datasets import GitHubRequestDataset

GRAPHQL = "https://api.github.com/graphql"
TOKEN = "ghp_test_not_a_real_token"


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
    return RefreshRequest(store="vcs_github_api_raw", cadence_seconds=0, force=True, github_repos=tuple(repos))


def _health(name: str = "r") -> dict:
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
    fake_transport.answers[GRAPHQL] = (200, {"data": {"r0": _health()}})
    ds = _dataset(tmp_path)

    ds.save(_request(("o", "r")))

    (sent,) = fake_transport.sent
    assert sent.method == "POST" and sent.headers["Authorization"] == f"Bearer {TOKEN}"
    assert 'repository(owner: "o", name: "r")' in json.loads(sent.body)["query"]
    row = ds.load().iloc[0]
    assert (row["feedstock_name"], row["stars"], row["open_issues"]) == ("r", 7, 2)
    assert ds.staleness() is None


def test_a_url_off_api_github_com_never_receives_the_token(fake_transport, flag_on, switch_on, tmp_path):
    ds = _dataset(tmp_path, url="https://github.example.com/api/graphql")

    ds.save(_request(("o", "r")))

    assert fake_transport.sent == [] and "github.example.com" in _marker_text(ds)


@pytest.mark.parametrize("credentials", [{"token": ""}, {}, ["user", "password"], "  "])
def test_no_usable_token_sends_nothing(fake_transport, flag_on, switch_on, tmp_path, credentials):
    ds = _dataset(tmp_path, credentials=credentials)

    ds.save(_request(("o", "r")))

    assert fake_transport.sent == [] and "no github_token" in _marker_text(ds)


def test_a_rejected_token_degrades_and_never_reaches_a_marker_or_a_row(fake_transport, flag_on, switch_on, tmp_path):
    fake_transport.answers[GRAPHQL] = (401, {"message": "Bad credentials"})
    ds = _dataset(tmp_path)
    _write_last_good(ds)

    ds.save(_request(("o", "r")))

    assert len(fake_transport.sent) == 2  # one attempt and one retry
    assert "401" in _marker_text(ds) and TOKEN not in _marker_text(ds)
    assert list(ds.load()["feedstock_name"]) == ["old"]  # last-good kept


def test_flag_off_keeps_the_path_this_story_found(fake_transport, switch_on, tmp_path):
    # OFF is today's behaviour: the GET-only load() route, which sends nothing for a POST
    ds = _dataset(tmp_path)

    frame = ds.fetch_repo_health([("o", "r")])

    assert fake_transport.sent == [] and frame["last_error"].str.contains("Only GET").all()


def test_bearer_auth_sets_the_header_only_for_its_host_and_hides_the_token():
    auth = credential_switch.BearerAuth(TOKEN, "api.github.com")
    own = auth(SimpleNamespace(url="https://api.github.com/graphql", headers={}))
    other = auth(SimpleNamespace(url="https://evil.example/graphql", headers={}))

    assert own.headers == {"Authorization": f"Bearer {TOKEN}"} and other.headers == {}
    assert TOKEN not in repr(auth)


@pytest.mark.parametrize(
    ("credentials", "token"),
    [({"token": " t "}, "t"), ("t", "t"), ({"token": ""}, None), (["u", "p"], None), (None, None), ({}, None)],
)
def test_token_of_reads_the_two_catalog_shapes(credentials, token):
    assert credential_switch.token_of(credentials) == token


def test_the_guard_fails_a_credentialed_request_without_the_switch(fake_transport):
    import requests

    with pytest.raises(pytest.fail.Exception, match=credential_switch.SWITCH):
        requests.get("https://api.github.com/x", headers={"Authorization": "Bearer t"}, timeout=1)


@flag_states("pyforge.atlas.live_vcs_universe")  # spelled out: the flag gate reads this file for the key
def test_the_flag_is_read_at_each_save(fake_transport, switch_on, tmp_path, flag_provider, monkeypatch):
    """On: the switch decides and the bearer POST runs. Off: the path before this story (no request)."""
    flag_on = flag_provider[credential_switch.FLAG_KEY]
    ds = _dataset(tmp_path)  # built before the flag is read
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: flag_on)
    fake_transport.answers[GRAPHQL] = (200, {"data": {"r0": _health()}})

    ds.save(_request(("o", "r")))

    assert bool(fake_transport.sent) is flag_on
