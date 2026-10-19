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


# -- review round 2 ------------------------------------------------------------------------------


def _pr(number: int, state: str = "open") -> dict:
    return {"number": number, "state": state, "html_url": f"https://g/{number}", "title": f"Add p{number}"}


def _list_page(page: int) -> str:
    return f"{API}/repos/conda-forge/staged-recipes/pulls?state=all&per_page=100&page={page}"


def _files(number: int) -> str:
    return f"{API}/repos/conda-forge/staged-recipes/pulls/{number}/files?per_page=100&page=1"


_FULL_CLOSED = [_pr(n, "closed") for n in range(1000, 1100)]  # a full page, so page 2 is asked


def test_a_pr_list_stopped_part_way_keeps_a_fuller_last_good(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[_list_page(1)] = (200, _FULL_CLOSED + [])
    in_turn.answers[_list_page(2)] = (200, [_pr(n, "closed") for n in range(1, 51)])
    ds = _prs(tmp_path)
    _save(ds)
    assert len(ds.load()) == 150
    in_turn.answers[_list_page(2)] = (502, {})

    _save(ds)

    assert len(ds.load()) == 150 and "PR list stopped at page 2: HTTP 502" in _marker(ds)


def test_a_pr_list_stopped_part_way_with_no_store_writes_the_pages_read(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[_list_page(1)] = (200, _FULL_CLOSED)
    in_turn.answers[_list_page(2)] = (502, {})
    ds = _prs(tmp_path)

    _save(ds)

    assert len(ds.load()) == 100 and "PR list stopped at page 2: HTTP 502" in _marker(ds)


def test_a_store_that_stopped_short_is_refreshed_again_inside_its_cadence(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[_list_page(1)] = (200, _FULL_CLOSED)
    in_turn.answers[_list_page(2)] = (502, {})
    ds = _prs(tmp_path)
    _save(ds)
    in_turn.answers[_list_page(2)] = (200, [_pr(1, "closed")])
    sent_before = len(in_turn.sent)

    ds.save(RefreshRequest(store="x"))  # not forced; the store is minutes old

    assert len(in_turn.sent) > sent_before and len(ds.load()) == 101 and ds.staleness() is None


@pytest.mark.parametrize("status", [401, 403, 429])
def test_a_refusal_on_the_list_sends_no_files_request(tmp_path, in_turn, identity_on, switch_on, status):
    in_turn.answers[_list_page(1)] = (200, [_pr(n) for n in range(1, 101)])
    in_turn.answers[_list_page(2)] = (status, {})
    ds = _prs(tmp_path)

    _save(ds)

    assert [r.url for r in in_turn.sent] == [_list_page(1), _list_page(2)]
    assert f"PR list stopped at page 2: HTTP {status}" in _marker(ds)


@pytest.mark.parametrize("status", [401, 403, 429])
def test_a_files_refusal_keeps_each_prs_last_good_paths(tmp_path, in_turn, identity_on, switch_on, status):
    in_turn.answers[_list_page(1)] = (200, [_pr(1), _pr(2)])
    in_turn.answers[_files(1)] = (200, [{"filename": "recipes/a/meta.yaml"}])
    in_turn.answers[_files(2)] = (200, [{"filename": "recipes/b/meta.yaml"}])
    ds = _prs(tmp_path)
    _save(ds)
    in_turn.answers[_files(1)] = (status, {})

    _save(ds)

    assert ds.load().set_index("number")["file_paths"].to_dict() == {1: "recipes/a/meta.yaml", 2: "recipes/b/meta.yaml"}
    assert f"PR files stopped at PR #1: HTTP {status}" in _marker(ds)
    assert _files(2) not in [r.url for r in in_turn.sent[-2:]]  # nothing after the refusal


def test_the_files_requests_stop_after_ten_failures_in_a_row(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[_list_page(1)] = (200, [_pr(n) for n in range(1, 21)])
    ds = _prs(tmp_path)  # every files URL answers 404 (fake_transport's default)

    _save(ds)

    assert sum("/files" in r.url for r in in_turn.sent) == 10
    assert "PR files stopped at PR #11: 10 failures in a row" in _marker(ds)


def test_a_failure_is_logged_by_its_status_never_its_text(tmp_path, in_turn, identity_on, switch_on, caplog):
    in_turn.answers[_list_page(1)] = (200, [_pr(1)])
    in_turn.answers[_files(1)] = (500, {})
    ds = _prs(tmp_path)

    _save(ds)

    assert "PR #1 files fetch failed: HTTP 500" in caplog.text and "/files" not in caplog.text


def test_a_clean_save_after_a_stopped_one_reads_fresh(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[GRAPHQL] = [(200, _page([1], "C1")), (502, {})]
    ds = _board(tmp_path)
    _save(ds)
    in_turn.answers[GRAPHQL] = (200, _page([1, 2], None))

    _save(ds)

    assert ds.staleness() is None and sorted(ds.load()["number"]) == [1, 2]


# -- review round 3 ------------------------------------------------------------------------------


def test_the_reasons_add_up_in_the_marker(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[_list_page(1)] = (200, [_pr(n) for n in range(1, 101)])
    in_turn.answers[_list_page(2)] = (502, {})
    in_turn.answers[_files(1)] = (403, {})
    ds = _prs(tmp_path)

    _save(ds)

    assert (
        json.loads(_marker(ds))["reason"] == "PR list stopped at page 2: HTTP 502; PR files stopped at PR #1: HTTP 403"
    )


def test_a_clean_store_inside_its_cadence_sends_nothing(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[GRAPHQL] = (200, _page([1], None))
    ds = _board(tmp_path)
    _save(ds)
    sent = len(in_turn.sent)

    ds.save(RefreshRequest(store="x"))  # not forced; the store is minutes old and clean

    assert len(in_turn.sent) == sent and ds.staleness() is None


def test_an_offline_marker_does_not_make_the_store_due(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[GRAPHQL] = (200, _page([1], None))
    ds = _board(tmp_path)
    _save(ds)
    ds._mark_stale("refresh due but no refresher wired (offline / unattended run)")
    sent = len(in_turn.sent)

    ds.save(RefreshRequest(store="x"))

    assert len(in_turn.sent) == sent  # only this mixin's own stop markers bring a refresh forward


def test_scattered_files_failures_do_not_trip_the_breaker(tmp_path, in_turn, identity_on, switch_on):
    in_turn.answers[_list_page(1)] = (200, [_pr(n) for n in range(1, 25)])
    for n in range(1, 25):
        if n % 3:  # two of every three PRs fail (404); every third answers
            continue
        in_turn.answers[_files(n)] = (200, [{"filename": f"recipes/p{n}/meta.yaml"}])
    ds = _prs(tmp_path)

    _save(ds)

    assert sum("/files" in r.url for r in in_turn.sent) == 24  # never ten in a row
    assert json.loads(_marker(ds))["reason"] == "PR files failed for 16 PRs (they keep last-good paths)"
