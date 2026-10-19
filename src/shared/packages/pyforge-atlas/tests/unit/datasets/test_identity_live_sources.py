"""Story 36.2 (spec-pyforge-atlas CAP-67): the OpenTeams board and the staged-recipes PRs fill on opt-in.

Both fetch with Story 35.1's bearer auth, only under the switch. No network: ``fake_transport``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import credentials as credential_switch
from pyforge.atlas.datasets import identity_sources as I
from pyforge.atlas.datasets.refresh import RefreshRequest

GRAPHQL = "https://api.github.com/graphql"
API = "https://api.github.com"
TOKEN = "ghp_test_not_a_real_token"
_REAL_IDENTITY = I.identity_live  # captured before the suite's autouse pin
_PRS = f"{API}/repos/conda-forge/staged-recipes/pulls?state=all&per_page=100&page=1"


@pytest.fixture()
def identity_on(monkeypatch):
    monkeypatch.setattr(I, "identity_live", lambda: True)


@pytest.fixture()
def switch_on(monkeypatch):
    monkeypatch.setenv(credential_switch.SWITCH, "1")


def _board(tmp_path: Path) -> I.OpenTeamsBoardDataset:
    return I.OpenTeamsBoardDataset(filepath=str(tmp_path / "board"), url=GRAPHQL, credentials={"token": TOKEN})


def _prs(tmp_path: Path) -> I.StagedRecipesPRDataset:
    return I.StagedRecipesPRDataset(filepath=str(tmp_path / "prs"), url=API, credentials={"token": TOKEN})


def _save(ds) -> None:  # noqa: ANN001
    ds.save(RefreshRequest(store="x", force=True))


def _marker(ds) -> str:  # noqa: ANN001
    return Path(ds._filepath, ".staleness.json").read_text(encoding="utf-8")


def _issue(number: int) -> dict:
    return {
        "content": {
            "__typename": "Issue",
            "number": number,
            "title": f"t{number}",
            "url": f"https://u/{number}",
            "state": "OPEN",
            "milestone": None,
        }
    }


def test_the_board_posts_its_graphql_with_the_bearer(tmp_path, fake_transport, identity_on, switch_on):
    page = {
        "data": {"organization": {"projectV2": {"items": {"pageInfo": {"hasNextPage": False}, "nodes": [_issue(7)]}}}}
    }
    fake_transport.answers[GRAPHQL] = (200, page)
    ds = _board(tmp_path)

    _save(ds)

    (sent,) = fake_transport.sent
    assert sent.method == "POST" and sent.headers["Authorization"] == f"Bearer {TOKEN}"
    assert "OpenTeams-WFT-CDO" in json.loads(sent.body)["query"]
    assert ds.load()["number"].tolist() == [7]


def test_the_staged_prs_page_with_the_bearer(tmp_path, fake_transport, identity_on, switch_on):
    pr = {
        "number": 1,
        "state": "closed",
        "html_url": "https://g/1",
        "title": "Add foo",
        "user": {"login": "a"},
        "labels": [],
    }
    fake_transport.answers[_PRS] = (200, [pr])
    ds = _prs(tmp_path)

    _save(ds)

    assert [r.url for r in fake_transport.sent] == [_PRS]
    assert fake_transport.sent[0].headers["Authorization"] == f"Bearer {TOKEN}"
    assert ds.load()["number"].tolist() == [1]


@pytest.mark.parametrize("make", [_board, _prs], ids=["board", "prs"])
def test_without_the_switch_nothing_is_sent_and_the_marker_says_why(tmp_path, fake_transport, identity_on, make):
    ds = make(tmp_path)

    _save(ds)

    assert fake_transport.sent == [] and credential_switch.SWITCH in _marker(ds) and TOKEN not in _marker(ds)


@pytest.mark.parametrize("make", [_board, _prs], ids=["board", "prs"])
def test_with_the_flag_off_there_is_no_live_refresher(tmp_path, make):
    assert make(tmp_path)._live_refresher() is None


def test_a_stub_credential_pair_is_no_token(tmp_path, fake_transport, identity_on, switch_on):
    ds = I.OpenTeamsBoardDataset(filepath=str(tmp_path / "b"), url=GRAPHQL, credentials=["x-access-token", "stub"])

    _save(ds)

    assert fake_transport.sent == [] and "no github_token" in _marker(ds)


@flag_states("pyforge.atlas.identity_live_sources")  # spelled out: the flag gate reads this file for the key
def test_the_flag_is_read_at_each_refresh(tmp_path, fake_transport, switch_on, flag_provider, monkeypatch):
    flag_on = flag_provider[I.IDENTITY_FLAG_KEY]
    ds = _prs(tmp_path)  # built before the flag is read
    monkeypatch.setattr(I, "identity_live", lambda: flag_on)
    fake_transport.answers[_PRS] = (200, [])

    _save(ds)

    assert bool(fake_transport.sent) is flag_on


@pytest.mark.parametrize("variant", ["on", "off"])
def test_the_real_reader_reads_the_key_from_the_tree(tmp_path, monkeypatch, variant):
    from pyforge.testing_kit import flagd_tree

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {I.IDENTITY_FLAG_KEY: variant})))

    assert _REAL_IDENTITY() is (variant == "on")
