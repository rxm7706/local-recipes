"""Live-tree half of the ``scripts/promote_sprint_status`` pins (Story 116.2, spec-pyforge-marshal:CAP-305).

Every test here loads the repository's own ``scripts/promote_sprint_status.py`` (and ``scripts/fleet_scan.py``).
``test_promote_sprint_status_regressions.py`` keeps the regression guards and the bare-sync repair, marked whole
into the same half; these are the epic roll-ups, doctor Story 25.3's ``--rekey`` and Story 107.1's stale-slug
and ``--feed-only`` cases, moved here so neither module holds more than 20 tests. The helpers come from that
module; the scripts are loaded when a test runs, never at import, so the module imports off the tree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_promote_sprint_status_regressions import (
    _load_promote,
    _make_generate_stub,
    _parse,
    _parse_status_file,
    _write_status_file,
)

pytestmark = pytest.mark.live_tree


@pytest.fixture(scope="module")
def promote():
    return _load_promote()


def test_apply_epic_rollups_all_stories_done(promote):
    statuses = {
        "45-1-eval-quality-joins-the-suite": "done",
        "45-2-the-reviewer-is-measured-against-a-planted-defect": "done",
        "epic-45": "backlog",
    }
    rolled = promote.apply_epic_rollups(statuses)
    assert rolled["epic-45"] == "done"


def test_apply_epic_rollups_partial_progress(promote):
    statuses = {
        "46-1-the-adoption-register-governs-wiring": "done",
        "46-10-the-release-cadence-is-one-runbook-and-the-next-rehearsal-has-run-once": "backlog",
        "epic-46": "backlog",
    }
    rolled = promote.apply_epic_rollups(statuses)
    assert rolled["epic-46"] == "in-progress"


# --- doctor Story 25.3: --rekey (spec-one-chain-per-station CAP-3(g)) --------


def _feed(tmp_path: Path, statuses: dict[str, str]) -> Path:
    p = tmp_path / "sprint-status.yaml"
    body = "".join(f"  {k}: {v}\n" for k, v in statuses.items())
    p.write_text("# header kept\ndevelopment_status:\n" + body, encoding="utf-8")
    return p


def test_apply_rekey_moves_keys_carries_statuses_and_rewrites_feed(tmp_path: Path) -> None:
    mod = _load_promote()
    feed = _feed(tmp_path, {"46-1-old": "done", "46-2-b": "backlog", "epic-46": "done"})
    translated, reasons = mod.apply_rekey(
        feed,
        _parse_status_file(feed),
        {"46-1-old": "1-1-new", "46-2-b": "1-2-b", "epic-46": "epic-1"},
    )
    assert reasons == []
    assert translated == {"1-1-new": "done", "1-2-b": "backlog", "epic-1": "done"}
    on_disk = feed.read_text(encoding="utf-8")
    assert on_disk.startswith("# header kept\n")
    assert _parse_status_file(feed) == translated
    # byte-stable on a second run over the already-translated feed
    again, reasons2 = mod.apply_rekey(feed, translated, {})
    assert reasons2 == [] and again == translated


def test_apply_rekey_refuses_dangling_and_collision(tmp_path: Path) -> None:
    mod = _load_promote()
    feed = _feed(tmp_path, {"46-1-a": "done", "46-2-b": "done"})
    before = feed.read_text(encoding="utf-8")
    translated, reasons = mod.apply_rekey(
        feed,
        _parse_status_file(feed),
        {"46-1-a": "1-1-x", "46-2-b": "1-1-x", "99-9-ghost": "1-9-z"},
    )
    assert translated is None
    assert any(r.startswith("dangling: 99-9-ghost") for r in reasons)
    assert any(r.startswith("collision:") for r in reasons)
    assert feed.read_text(encoding="utf-8") == before  # refused == untouched


# --- Story 107.1: a stale-slug key never reaches the twin; --feed-only ---------------

# The 2026-10-25 shape: the twin's keys come from chain.slugify_title, and the feed's
# copies from sprint_plan.py's _slug (cut at 60 characters, `_` and non-ASCII letters
# kept), at `backlog` beside the twin's `done`.
_TWIN_LONG = "1-2-transport-port-primary-mcp-client-adapter-the-transport-spike"
_FEED_LONG = "1-2-transport-port-primary-mcp-client-adapter-the-transport-spik"
_TWIN_UNDERSCORE = "9-1-the-repo-s-ci-is-consumable-via-workflow-call"
_FEED_UNDERSCORE = "9-1-the-repo-s-ci-is-consumable-via-workflow_call"
_TWIN_NON_ASCII = "22-4-a-diataxis-adapted-information-architecture"
_FEED_NON_ASCII = "22-4-a-diátaxis-adapted-information-architecture"
_STALE = sorted([_FEED_LONG, _FEED_UNDERSCORE, _FEED_NON_ASCII])


def _replay_twin() -> dict[str, str]:
    return {
        _TWIN_LONG: "done",
        _TWIN_UNDERSCORE: "done",
        _TWIN_NON_ASCII: "done",
        "epic-1": "done",
        "epic-9": "done",
        "epic-22": "done",
    }


def _replay_feed() -> dict[str, str]:
    feed = _replay_twin()
    feed.update({_FEED_LONG: "backlog", _FEED_UNDERSCORE: "backlog", _FEED_NON_ASCII: "backlog"})
    return feed


def _sandbox(tmp_path, promote, monkeypatch, feed_map, twin_map, *, feed_rel="feed.yaml"):
    slug = "pyforge-acme"
    feed = tmp_path / feed_rel
    twin_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts"
    twin_dir.mkdir(parents=True)
    twin = twin_dir / "sprint-status-ledger.yaml"
    if feed_map is not None:
        _write_status_file(feed, feed_map)
    if twin_map is not None:
        _write_status_file(twin, twin_map)
    else:
        twin_dir.rmdir()
    stub = _make_generate_stub(feed_rel, slug)
    monkeypatch.setattr(promote, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(promote, "_load_generate", lambda: stub)
    return feed, twin


def test_stale_slug_keys_pairs_each_copy_with_the_twin_key_for_its_number(promote):
    feed = _replay_feed()
    feed["5-1-a-story-the-twin-lacks"] = "ready-for-dev"
    feed["22-4a-a-suffixed-story"] = "backlog"
    assert promote.stale_slug_keys(feed, _replay_twin()) == [
        (_FEED_LONG, _TWIN_LONG),
        (_FEED_NON_ASCII, _TWIN_NON_ASCII),
        (_FEED_UNDERSCORE, _TWIN_UNDERSCORE),
    ]


def test_main_drops_stale_slug_keys_before_it_promotes(tmp_path, promote, monkeypatch, capsys):
    feed, twin = _sandbox(tmp_path, promote, monkeypatch, _replay_feed(), _replay_twin())

    rc = promote.main(["--project", "acme"])

    assert rc == 0
    assert _parse_status_file(twin) == _replay_twin()
    assert not set(_STALE) & set(_parse_status_file(feed))
    out = capsys.readouterr().out
    assert "DROPPED   acme: 3 stale-slug key(s)" in out
    assert f"{_FEED_LONG}: feed backlog (the twin carries it as {_TWIN_LONG}: done)" in out
    assert f"{_FEED_NON_ASCII}: feed backlog (the twin carries it as {_TWIN_NON_ASCII}: done)" in out
    assert f"{_FEED_UNDERSCORE}: feed backlog (the twin carries it as {_TWIN_UNDERSCORE}: done)" in out


def test_main_drops_stale_slug_keys_under_allow_regression(tmp_path, promote, monkeypatch):
    feed, twin = _sandbox(tmp_path, promote, monkeypatch, _replay_feed(), _replay_twin())

    assert promote.main(["--project", "acme", "--allow-regression"]) == 0
    assert _parse_status_file(twin) == _replay_twin()


def test_main_promotes_a_key_whose_number_the_twin_lacks(tmp_path, promote, monkeypatch):
    feed_map = _replay_feed()
    feed_map["5-1-a-story-the-twin-lacks"] = "ready-for-dev"
    feed, twin = _sandbox(tmp_path, promote, monkeypatch, feed_map, _replay_twin())

    assert promote.main(["--project", "acme"]) == 0
    assert _parse_status_file(twin)["5-1-a-story-the-twin-lacks"] == "ready-for-dev"
    assert _parse_status_file(feed)["5-1-a-story-the-twin-lacks"] == "ready-for-dev"


def test_feed_only_brings_the_feed_into_step_and_never_writes_the_twin(tmp_path, promote, monkeypatch, capsys):
    twin_map = _replay_twin()
    twin_map.update({"3-1-in-flight": "backlog", "4-1-twin-only": "backlog"})
    feed_map = _replay_feed()
    feed_map.update({"3-1-in-flight": "in-progress", _TWIN_LONG: "backlog"})
    feed, twin = _sandbox(tmp_path, promote, monkeypatch, None, twin_map)
    body = "".join(f"  {k}: {v}\n" for k, v in sorted(feed_map.items()))
    tail = "generated: '2026-07-25'\nproject: pyforge-acme\n"
    feed.write_text("# header kept\ndevelopment_status:\n" + body + tail, encoding="utf-8")
    twin_before = twin.read_bytes()

    rc = promote.main(["--project", "acme", "--feed-only"])

    assert rc == 0
    assert twin.read_bytes() == twin_before
    text = feed.read_text(encoding="utf-8")
    expected = {**twin_map, "3-1-in-flight": "in-progress"}
    expected_body = "".join(f"  {k}: {v}\n" for k, v in sorted(expected.items()))
    assert text == "# header kept\ndevelopment_status:\n" + expected_body + tail
    report = json.loads(capsys.readouterr().out)
    assert report == {
        "ok": True,
        "project": "acme",
        "feed": "feed.yaml",
        "dropped": _STALE,
        "kept": [],
        "repaired": sorted([_TWIN_LONG, "4-1-twin-only"]),
    }


def test_feed_only_writes_an_absent_feed_from_the_twin(tmp_path, promote, monkeypatch, capsys):
    feed, twin = _sandbox(tmp_path, promote, monkeypatch, None, _replay_twin(), feed_rel="impl/sprint-status.yaml")

    assert promote.main(["--project", "acme", "--feed-only"]) == 0
    text = feed.read_text(encoding="utf-8")
    for line in (
        "project: pyforge-acme",
        "project_key: acme",
        "tracking_system: file-system",
        "story_location: _bmad-output/projects/pyforge-acme/implementation-artifacts",
    ):
        assert line in text
    assert promote._split_development_status(text)[1] != ""
    assert {k: v for k, v in _parse_status_file(feed).items() if k in _replay_twin()} == _replay_twin()
    assert json.loads(capsys.readouterr().out)["repaired"] == sorted(_replay_twin())


def test_feed_only_skips_without_a_tracked_twin(tmp_path, promote, monkeypatch, capsys):
    feed, _twin = _sandbox(tmp_path, promote, monkeypatch, _replay_feed(), None)
    before = feed.read_bytes()

    assert promote.main(["--project", "acme", "--feed-only"]) == 0
    assert feed.read_bytes() == before
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True and "no tracked twin" in report["skipped"]


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--project", "acme", "--project", "acme"],
        ["--project", "acme", "--rekey", "map.md"],
        ["--project", "acme", "--allow-regression"],
    ],
)
def test_feed_only_needs_exactly_one_project_and_no_other_mode(promote, capsys, extra):
    assert promote.main(["--feed-only", *extra]) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_feed_only_keeps_a_key_whose_number_the_twin_lacks(tmp_path, promote, monkeypatch, capsys):
    feed_map = _replay_feed()
    feed_map["5-1-a-story-the-twin-lacks"] = "ready-for-dev"
    feed, _twin = _sandbox(tmp_path, promote, monkeypatch, feed_map, _replay_twin())

    assert promote.main(["--project", "acme", "--feed-only"]) == 0
    assert _parse(feed)["5-1-a-story-the-twin-lacks"] == "ready-for-dev"
    assert "5-1-a-story-the-twin-lacks" not in json.loads(capsys.readouterr().out)["dropped"]


@pytest.mark.parametrize("content", ["", "# truncated before its map\nproject: pyforge-acme\n"])
def test_feed_only_rebuilds_a_feed_with_no_map_and_stays_idempotent(tmp_path, promote, monkeypatch, content):
    feed, _twin = _sandbox(tmp_path, promote, monkeypatch, None, _replay_twin())
    feed.write_text(content, encoding="utf-8")

    assert promote.main(["--project", "acme", "--feed-only"]) == 0
    first = feed.read_text(encoding="utf-8")
    assert promote.main(["--project", "acme", "--feed-only"]) == 0
    assert feed.read_text(encoding="utf-8") == first
    assert first.count("development_status:") == 1
    assert _parse(feed) == _replay_twin()


def test_a_stale_key_ahead_of_its_twin_key_is_kept_and_named(tmp_path, promote, monkeypatch, capsys):
    """Review S2: a run working story 3.1 under its old title, while the ledger moved to the
    new one, must not lose that progress; the key is kept and named for a --rekey."""
    twin_map = {"3-1-the-new-title": "backlog", "epic-3": "backlog"}
    feed_map = {**twin_map, "3-1-the-old-title": "in-progress"}
    feed, twin = _sandbox(tmp_path, promote, monkeypatch, feed_map, twin_map)

    assert promote.main(["--project", "acme", "--feed-only"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["kept"] == ["3-1-the-old-title"] and report["dropped"] == []
    assert _parse(feed)["3-1-the-old-title"] == "in-progress"

    assert promote.main(["--project", "acme"]) == 0
    out = capsys.readouterr().out
    assert "KEPT      acme: 1 stale-slug key(s)" in out
    assert "3-1-the-old-title: feed in-progress (the twin carries it as 3-1-the-new-title: backlog)" in out
    assert _parse(twin)["3-1-the-old-title"] == "in-progress"


def test_split_stale_keys_keeps_only_a_key_ahead_of_its_story(promote):
    """Review round 2: only a stale key further along than the best value its story has is
    kept; behind, level, `blocked` and a `done` or `blocked` twin key all go."""
    twin = {
        "1-1-a": "done",
        "2-1-b": "in-progress",
        "3-1-c": "review",
        "4-1-d": "backlog",
        "5-1-e": "review",
        "6-1-f": "in-progress",
        "7-1-g": "backlog",
        "8-1-h": "blocked",
        "9-1-i": "backlog",
        "10-1-j": "ready-for-dev",
    }
    feed = {
        **twin,
        "9-1-i": "in-progress",  # the feed already advanced the twin's own key
        "1-1-a-old": "in-progress",  # twin done
        "2-1-b-old": "backlog",  # behind
        "3-1-c-old": "review",  # level
        "4-1-d-old": "done",  # ahead: kept
        "5-1-e-old": "in-progress",  # behind
        "6-1-f-old": "ready-for-dev",  # behind
        "7-1-g-old": "blocked",  # blocked ranks lowest
        "8-1-h-old": "in-progress",  # twin blocked
        "9-1-i-old": "in-progress",  # level with the feed's own value for 9-1-i
        "10-1-j-old": "review",  # ahead: kept
    }
    drop, keep = promote.split_stale_keys(feed, twin)
    assert keep == [("10-1-j-old", "10-1-j"), ("4-1-d-old", "4-1-d")]
    assert sorted(k for k, _ in drop) == sorted(
        ["1-1-a-old", "2-1-b-old", "3-1-c-old", "5-1-e-old", "6-1-f-old", "7-1-g-old", "8-1-h-old", "9-1-i-old"]
    )


def test_a_repaired_key_is_named_once(tmp_path, promote, monkeypatch, capsys):
    feed, _twin = _sandbox(
        tmp_path, promote, monkeypatch, {"1-1-demo": "backlog"}, {"1-1-demo": "backlog", "1-2-gone": "done"}
    )

    assert promote.main(["--project", "acme"]) == 0
    out = capsys.readouterr().out
    assert out.count("1-2-gone: feed <absent> -> twin done") == 1
    assert "restored 1 regressed + 0 missing key(s)" in out
