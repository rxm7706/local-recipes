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


# -- review round 1: pages, refusals and the marker ----------------------------------------------


class _InTurn(dict):
    """``fake_transport.answers`` where a URL may hold a list: each request takes the next answer,
    and the last one repeats."""

    def get(self, url, default=None):  # noqa: ANN001, ANN201
        answer = super().get(url, default)
        if isinstance(answer, list):
            return answer.pop(0) if len(answer) > 1 else answer[0]
        return answer


@pytest.fixture()
def in_turn(fake_transport, monkeypatch):
    fake_transport.answers = _InTurn()
    monkeypatch.setattr(I.time, "sleep", lambda _s: None)
    return fake_transport


def _page(numbers: list[int], cursor: str | None) -> dict:
    info = {"hasNextPage": cursor is not None, "endCursor": cursor}
    return {
        "data": {"organization": {"projectV2": {"items": {"pageInfo": info, "nodes": [_issue(n) for n in numbers]}}}}
    }


def _bodies(transport) -> list[dict]:  # noqa: ANN001
    return [json.loads(r.body) for r in transport.sent]


def test_the_board_follows_its_cursor_and_stops_waiting_after_a_minute(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[GRAPHQL] = [(200, _page([1], "C1")), (200, _page([2], None))]
    ds = _board(tmp_path)

    _save(ds)

    assert [b["variables"] for b in _bodies(in_turn)] == [{}, {"cursor": "C1"}]
    assert in_turn.timeouts == [60, 60] and sorted(ds.load()["number"]) == [1, 2]


def test_an_open_prs_files_are_read_with_the_bearer(tmp_path, in_turn, identity_on, switch_on):
    pr = {"number": 5, "state": "open", "html_url": "https://g/5", "title": "Add foo"}
    files = f"{API}/repos/conda-forge/staged-recipes/pulls/5/files?per_page=100&page=1"
    in_turn.answers[_PRS] = (200, [pr])
    in_turn.answers[files] = (200, [{"filename": "recipes/foo/meta.yaml"}])
    ds = _prs(tmp_path)

    _save(ds)

    assert [r.url for r in in_turn.sent] == [_PRS, files]
    assert all(r.headers["Authorization"] == f"Bearer {TOKEN}" for r in in_turn.sent) and in_turn.timeouts == [60, 60]
    assert ds.load()["file_paths"].tolist() == ["recipes/foo/meta.yaml"]


@pytest.mark.parametrize("url", ["https://ghe.example.com/graphql", "http://api.github.com/graphql"])
def test_another_host_or_plain_http_is_sent_nothing(tmp_path, fake_transport, identity_on, switch_on, url):
    ds = I.OpenTeamsBoardDataset(filepath=str(tmp_path / "b"), url=url, credentials={"token": TOKEN})

    _save(ds)

    assert fake_transport.sent == [] and TOKEN not in _marker(ds) and "stale" in _marker(ds)


def test_a_failure_part_way_keeps_a_fuller_last_good(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[GRAPHQL] = (200, _page([1, 2, 3], None))
    ds = _board(tmp_path)
    _save(ds)
    in_turn.answers[GRAPHQL] = [(200, _page([1], "C1")), (502, {})]

    _save(ds)

    assert sorted(ds.load()["number"]) == [1, 2, 3]  # never the one page read before the 502
    assert "board stopped at page 2: HTTP 502" in _marker(ds)


def test_a_failure_part_way_with_no_store_writes_the_pages_read_and_says_so(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[GRAPHQL] = [(200, _page([1], "C1")), (502, {})]
    ds = _board(tmp_path)

    _save(ds)

    assert ds.load()["number"].tolist() == [1] and "board stopped at page 2: HTTP 502" in _marker(ds)
    assert len(in_turn.sent) == 2 + ds._max_retries  # the 502 page asked again before giving up


def test_a_page_github_could_not_answer_in_time_is_asked_again(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[GRAPHQL] = [(502, {}), (200, _page([4], None))]
    ds = _board(tmp_path)

    _save(ds)

    assert ds.load()["number"].tolist() == [4] and ds.staleness() is None


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        ((401, {"message": "Bad credentials"}), "HTTP 401"),
        ((200, {"errors": [{"message": "no org"}]}), "GraphQL error: no org"),
    ],
    ids=["401", "graphql-errors"],
)
def test_the_marker_names_why_the_first_page_failed(tmp_path, in_turn, identity_on, switch_on, answer, reason):
    in_turn.answers[GRAPHQL] = answer
    ds = _board(tmp_path)

    _save(ds)

    assert len(in_turn.sent) == 1 and reason in _marker(ds) and TOKEN not in _marker(ds)


def test_a_refused_files_request_stops_every_later_one(tmp_path, in_turn, identity_on, switch_on, caplog):
    prs = [{"number": n, "state": "open", "html_url": f"https://g/{n}", "title": "Add x"} for n in (1, 2, 3)]
    in_turn.answers[_PRS] = (200, prs)
    files = f"{API}/repos/conda-forge/staged-recipes/pulls/1/files?per_page=100&page=1"
    in_turn.answers[files] = (429, {"message": "rate limited"})
    ds = _prs(tmp_path)

    _save(ds)

    assert [r.url for r in in_turn.sent] == [_PRS, files]  # nothing after the refusal
    assert sorted(ds.load()["number"]) == [1, 2, 3] and "PR files stopped at PR #1: HTTP 429" in _marker(ds)
    assert TOKEN not in caplog.text and "rate limited" not in caplog.text


def test_the_real_reader_defaults_off_when_the_tree_lacks_the_key(tmp_path, monkeypatch):
    from pyforge.testing_kit import flagd_tree

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {"pyforge.atlas.some_other_flag": "on"})))

    assert _REAL_IDENTITY() is False
