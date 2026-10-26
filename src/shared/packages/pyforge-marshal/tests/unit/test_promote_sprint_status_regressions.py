"""Regression pin for ``scripts/promote_sprint_status`` guards (FR-139 / Story 48.1).

Downgrade refusal for ``done`` shipped 2026-08-08 (DW-SYNC-2026-08-08-1). Story 48.1
extends the same posture to story ``blocked`` and twin-only missing keys.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[6]


def _load_promote():
    path = _REPO_ROOT / "scripts" / "promote_sprint_status.py"
    spec = importlib.util.spec_from_file_location("_promote_sprint_status_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_status_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    in_block = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        line = raw.strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def _make_generate_stub(feed_rel: str, slug: str):
    class _StubGenerate:
        PROJECT_SOURCES = {"acme": feed_rel}
        _KEY_SLUG_OVERRIDE = {"acme": slug}

        @staticmethod
        def parse_sprint_status(path: Path) -> dict[str, str]:
            return _parse_status_file(Path(path))

    return _StubGenerate


@pytest.fixture(scope="module")
def promote():
    return _load_promote()


def test_regressions_detects_done_to_backlog(promote):
    lost = promote.regressions(
        {"1-1-demo": "done", "1-2-other": "in-progress"},
        {"1-1-demo": "backlog", "1-2-other": "in-progress"},
    )
    assert lost == [("1-1-demo", "done", "backlog")]


def test_regressions_detects_dropped_done_key(promote):
    lost = promote.regressions(
        {"1-1-demo": "done"},
        {"1-2-other": "backlog"},
    )
    assert lost == [("1-1-demo", "done", "<absent>")]


def test_regressions_detects_blocked_to_backlog(promote):
    lost = promote.regressions(
        {"44-3-open-the-foundry": "blocked"},
        {"44-3-open-the-foundry": "backlog"},
    )
    assert lost == [("44-3-open-the-foundry", "blocked", "backlog")]


def test_regressions_detects_dropped_blocked_key(promote):
    lost = promote.regressions(
        {"44-3-open-the-foundry": "blocked", "44-4-fold-the-packages": "backlog"},
        {"44-4-fold-the-packages": "backlog"},
    )
    assert lost == [("44-3-open-the-foundry", "blocked", "<absent>")]


def test_regressions_empty_when_monotonic(promote):
    lost = promote.regressions(
        {"1-1-demo": "backlog"},
        {"1-1-demo": "done"},
    )
    assert lost == []


def test_regressions_preserves_blocked_without_regression(promote):
    lost = promote.regressions(
        {"44-3-open-the-foundry": "blocked"},
        {"44-3-open-the-foundry": "blocked"},
    )
    assert lost == []


def test_regressions_detects_done_to_blocked(promote):
    """Live incident 2026-09-10: a genuinely `done` story (pyforge-doctor 20.4)
    had a stale Tier-3 `blocked` value the original guard did not catch, because
    `done` and story `blocked` were both treated as an undifferentiated
    "protected" class -- a lateral move between them was never flagged. `done`
    is strictly senior to `blocked`: this transition must be refused too."""
    lost = promote.regressions(
        {"20-4-bmad-os-root-cause-analysis-is-doctor-wielded": "done"},
        {"20-4-bmad-os-root-cause-analysis-is-doctor-wielded": "blocked"},
    )
    assert lost == [("20-4-bmad-os-root-cause-analysis-is-doctor-wielded", "done", "blocked")]


def test_regressions_detects_done_to_any_other_status(promote):
    """The fix widens detection from "feed says backlog" to "feed says anything
    other than done" -- pin the other non-done statuses too, not just blocked."""
    for other in ("ready-for-dev", "in-progress", "review"):
        lost = promote.regressions(
            {"1-1-demo": "done"},
            {"1-1-demo": other},
        )
        assert lost == [("1-1-demo", "done", other)], other


def test_regressions_blocked_to_done_is_not_a_regression(promote):
    """A story reaching done from blocked is a real completion, not a loss --
    only a move AWAY from done is ever flagged."""
    lost = promote.regressions(
        {"44-3-open-the-foundry": "blocked"},
        {"44-3-open-the-foundry": "done"},
    )
    assert lost == []


def test_terminal_is_only_done(promote):
    assert promote.TERMINAL == frozenset({"done"})


def test_sticky_statuses_mirrors_sprint_plan(promote):
    assert promote.STICKY_STATUSES == {"story": frozenset({"blocked"})}


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


def _write_status_file(path: Path, statuses: dict[str, str]) -> None:
    body = "".join(f"  {k}: {v}\n" for k, v in sorted(statuses.items()))
    path.write_text("development_status:\n" + body, encoding="utf-8")


def test_main_repairs_missing_twin_key_on_bare_sync(tmp_path, promote, monkeypatch, capsys):
    slug = "pyforge-acme"
    feed = tmp_path / "feed.yaml"
    twin_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts"
    twin_dir.mkdir(parents=True)
    twin = twin_dir / "sprint-status-ledger.yaml"
    _write_status_file(feed, {"1-1-demo": "backlog"})
    _write_status_file(twin, {"1-1-demo": "backlog", "1-2-missing": "optional"})

    stub = _make_generate_stub(feed.relative_to(tmp_path).as_posix(), slug)

    monkeypatch.setattr(promote, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(promote, "_load_generate", lambda: stub)

    rc = promote.main(["--project", "acme"])
    assert rc == 0
    assert "1-2-missing" in feed.read_text(encoding="utf-8")
    out = capsys.readouterr().out
    assert "REPAIRED" in out
    assert "1-2-missing: feed <absent> -> twin optional" in out


def test_repair_feed_restores_done_lost_to_blocked(tmp_path, promote):
    """--repair-feed's write-back half must catch the same done->blocked case
    regressions() now does -- it calls regressions() internally, so this pins
    that the fix reaches the repair path too, not just the refusal path."""
    feed_path = tmp_path / "feed.yaml"
    _write_status_file(feed_path, {"20-4-bmad-os-root-cause-analysis-is-doctor-wielded": "blocked"})
    incoming = {"20-4-bmad-os-root-cause-analysis-is-doctor-wielded": "blocked"}
    twin_values = {"20-4-bmad-os-root-cause-analysis-is-doctor-wielded": "done"}

    merged, lost, missing = promote.repair_feed(feed_path, incoming, twin_values)

    assert merged == {"20-4-bmad-os-root-cause-analysis-is-doctor-wielded": "done"}
    assert lost == [("20-4-bmad-os-root-cause-analysis-is-doctor-wielded", "done", "blocked")]
    assert missing == []
    assert "20-4-bmad-os-root-cause-analysis-is-doctor-wielded: done" in feed_path.read_text(encoding="utf-8")


def test_main_repair_feed_matches_bare_sync(tmp_path, promote, monkeypatch):
    slug = "pyforge-acme"
    feed = tmp_path / "feed.yaml"
    twin_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts"
    twin_dir.mkdir(parents=True)
    twin = twin_dir / "sprint-status-ledger.yaml"
    _write_status_file(feed, {"1-1-demo": "backlog"})
    _write_status_file(twin, {"1-1-demo": "backlog", "1-2-missing": "optional"})

    stub = _make_generate_stub(feed.relative_to(tmp_path).as_posix(), slug)

    monkeypatch.setattr(promote, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(promote, "_load_generate", lambda: stub)

    rc_bare = promote.main(["--project", "acme"])
    feed_after_bare = feed.read_text(encoding="utf-8")
    twin_after_bare = twin.read_text(encoding="utf-8")

    _write_status_file(feed, {"1-1-demo": "backlog"})
    _write_status_file(twin, {"1-1-demo": "backlog", "1-2-missing": "optional"})
    rc_flag = promote.main(["--project", "acme", "--repair-feed"])

    assert rc_bare == 0 and rc_flag == 0
    assert feed.read_text(encoding="utf-8") == feed_after_bare
    assert twin.read_text(encoding="utf-8") == twin_after_bare


def _doctor_24_2_fixture() -> tuple[dict[str, str], dict[str, str]]:
    """Twin holds 13 unrelated `done` rows; feed is behind on all of them plus one promotion."""
    drift_keys = [f"24-{i}-story-{i}" for i in range(1, 14)]
    twin = {k: "done" for k in drift_keys}
    twin["54-1-promoted"] = "backlog"
    feed = {k: "backlog" for k in drift_keys[:7]}
    for k in drift_keys[7:]:
        pass  # absent from feed
    feed["54-1-promoted"] = "done"
    return feed, twin


def test_main_bare_sync_doctor_24_2_fixture(tmp_path, promote, monkeypatch, capsys):
    slug = "pyforge-acme"
    feed = tmp_path / "feed.yaml"
    twin_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts"
    twin_dir.mkdir(parents=True)
    twin = twin_dir / "sprint-status-ledger.yaml"
    feed_map, twin_map = _doctor_24_2_fixture()
    _write_status_file(feed, feed_map)
    _write_status_file(twin, twin_map)

    stub = _make_generate_stub(feed.relative_to(tmp_path).as_posix(), slug)
    monkeypatch.setattr(promote, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(promote, "_load_generate", lambda: stub)

    rc = promote.main(["--project", "acme"])
    assert rc == 0
    twin_after = _parse_status_file(twin)
    feed_after = _parse_status_file(feed)
    assert twin_after["54-1-promoted"] == "done"
    for k, v in twin_map.items():
        if k == "54-1-promoted":
            continue
        assert feed_after[k] == v
    out = capsys.readouterr().out
    for k in twin_map:
        if k == "54-1-promoted":
            continue
        assert k in out


def test_repair_feed_preserves_trailing_metadata(tmp_path, promote):
    feed_path = tmp_path / "feed.yaml"
    tail = "generated: '2026-09-01'\nlast_updated: '2026-09-02'\nproject: pyforge-marshal\n"
    feed_path.write_text(
        "# header\ndevelopment_status:\n  1-1-a: backlog\n" + tail,
        encoding="utf-8",
    )
    incoming = {"1-1-a": "backlog"}
    twin_values = {"1-1-a": "done"}
    promote.repair_feed(feed_path, incoming, twin_values)
    assert feed_path.read_text(encoding="utf-8").endswith(tail)


def test_main_allow_regression_writes_done_to_backlog(tmp_path, promote, monkeypatch, capsys):
    slug = "pyforge-acme"
    feed = tmp_path / "feed.yaml"
    twin_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts"
    twin_dir.mkdir(parents=True)
    twin = twin_dir / "sprint-status-ledger.yaml"
    _write_status_file(feed, {"1-1-demo": "backlog"})
    _write_status_file(twin, {"1-1-demo": "done"})

    stub = _make_generate_stub(feed.relative_to(tmp_path).as_posix(), slug)
    monkeypatch.setattr(promote, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(promote, "_load_generate", lambda: stub)

    rc = promote.main(["--project", "acme", "--allow-regression"])
    assert rc == 0
    assert _parse_status_file(twin)["1-1-demo"] == "backlog"
    out = capsys.readouterr().out
    assert "WARNING" in out
    assert "1-1-demo" in out


def test_main_promotion_not_rewritten_by_repair(tmp_path, promote, monkeypatch):
    slug = "pyforge-acme"
    feed = tmp_path / "feed.yaml"
    twin_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts"
    twin_dir.mkdir(parents=True)
    twin = twin_dir / "sprint-status-ledger.yaml"
    _write_status_file(feed, {"54-1-x": "done", "24-1-other": "backlog"})
    _write_status_file(twin, {"54-1-x": "backlog", "24-1-other": "done"})

    stub = _make_generate_stub(feed.relative_to(tmp_path).as_posix(), slug)
    monkeypatch.setattr(promote, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(promote, "_load_generate", lambda: stub)

    rc = promote.main(["--project", "acme"])
    assert rc == 0
    assert _parse_status_file(twin)["54-1-x"] == "done"
    assert _parse_status_file(feed)["24-1-other"] == "done"


def test_main_restores_twin_blocked_from_feed_backlog(tmp_path, promote, monkeypatch, capsys):
    slug = "pyforge-acme"
    feed = tmp_path / "feed.yaml"
    twin_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts"
    twin_dir.mkdir(parents=True)
    twin = twin_dir / "sprint-status-ledger.yaml"
    key = "44-3-open-the-foundry"
    _write_status_file(feed, {key: "backlog"})
    _write_status_file(twin, {key: "blocked"})

    stub = _make_generate_stub(feed.relative_to(tmp_path).as_posix(), slug)
    monkeypatch.setattr(promote, "REPO_ROOT", tmp_path, raising=False)
    monkeypatch.setattr(promote, "_load_generate", lambda: stub)

    rc = promote.main(["--project", "acme"])
    assert rc == 0
    assert _parse_status_file(feed)[key] == "blocked"
    out = capsys.readouterr().out
    assert f"{key}: feed backlog -> twin blocked" in out


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
    assert f"{_FEED_LONG}: feed backlog (the twin carries it as {_TWIN_LONG})" in out
    assert f"{_FEED_NON_ASCII}: feed backlog (the twin carries it as {_TWIN_NON_ASCII})" in out
    assert f"{_FEED_UNDERSCORE}: feed backlog (the twin carries it as {_TWIN_UNDERSCORE})" in out


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
    assert text.startswith("# header kept\ndevelopment_status:\n")
    assert text.endswith(tail)
    after = _parse_status_file(feed)
    assert not set(_STALE) & set(after)
    assert after[_TWIN_LONG] == "done"
    assert after["4-1-twin-only"] == "backlog"
    assert after["3-1-in-flight"] == "in-progress"
    report = json.loads(capsys.readouterr().out)
    assert report == {
        "ok": True,
        "project": "acme",
        "feed": "feed.yaml",
        "dropped": _STALE,
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


def test_feed_only_needs_exactly_one_project(promote, capsys):
    assert promote.main(["--feed-only"]) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_a_repaired_key_is_named_once(tmp_path, promote, monkeypatch, capsys):
    feed, _twin = _sandbox(
        tmp_path, promote, monkeypatch, {"1-1-demo": "backlog"}, {"1-1-demo": "backlog", "1-2-gone": "done"}
    )

    assert promote.main(["--project", "acme"]) == 0
    out = capsys.readouterr().out
    assert out.count("1-2-gone: feed <absent> -> twin done") == 1
    assert "restored 1 regressed + 0 missing key(s)" in out
