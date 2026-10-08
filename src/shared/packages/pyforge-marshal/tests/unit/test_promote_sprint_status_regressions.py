"""Regression pin for ``scripts/promote_sprint_status`` guards (FR-139 / Story 48.1).

Downgrade refusal for ``done`` shipped 2026-08-08 (DW-SYNC-2026-08-08-1). Story 48.1
extends the same posture to story ``blocked`` and twin-only missing keys.
"""

from __future__ import annotations

import importlib.util
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


def test_main_repairs_missing_twin_key_on_bare_sync(
    tmp_path, promote, monkeypatch, capsys
):
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
    tail = (
        "generated: '2026-09-01'\n"
        "last_updated: '2026-09-02'\n"
        "project: pyforge-marshal\n"
    )
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
