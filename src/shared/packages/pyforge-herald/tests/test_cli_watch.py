"""``herald deck watch <slug> [<slug> ...]`` CLI wiring (Epic 4): argument
parsing, composing ``bridge.run`` + ``watch.watch`` over the V1-default
``McpTransport``, and routing the result through ``dispatch`` (AD-6).

``watch.watch`` itself is monkeypatched here -- its own poll/debounce/
backoff/halt behavior is ``test_watch.py``'s job. What's under test is the
CLI's own composition: which transport it builds, which arguments (slugs,
repo-root, interval) it forwards, and that a raised ``HeraldError``
(including Story 4.3's ``AuthError``) reaches ``dispatch`` unchanged and
maps to its usual exit code -- mirrors ``test_cli_pull.py``'s own shape.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.herald import cli, watch as watch_module
from pyforge.herald.errors import HeraldError


def test_deck_watch_help_exits_zero():
    assert cli.main(["deck", "watch", "--help"]) == 0


def test_deck_watch_missing_slug_is_a_usage_error():
    assert cli.main(["deck", "watch"]) == 2


def test_deck_watch_forwards_one_slug_repo_root_and_default_interval(
    monkeypatch, tmp_path: Path
):
    seen = {}

    def _fake_watch(transport, *, slugs, repo_root, interval):
        seen["transport"] = transport
        seen["slugs"] = slugs
        seen["repo_root"] = repo_root
        seen["interval"] = interval

    monkeypatch.setattr(watch_module, "watch", _fake_watch)

    exit_code = cli.main(
        ["deck", "watch", "pyforge-warden", "--repo-root", str(tmp_path)]
    )

    assert exit_code == 0
    assert seen["slugs"] == ["pyforge-warden"]
    assert seen["repo_root"] == tmp_path
    assert seen["interval"] == watch_module.DEFAULT_POLL_INTERVAL


def test_deck_watch_forwards_multiple_slugs(monkeypatch):
    seen = {}

    def _fake_watch(transport, *, slugs, repo_root, interval):
        seen["slugs"] = slugs

    monkeypatch.setattr(watch_module, "watch", _fake_watch)

    cli.main(["deck", "watch", "pyforge-warden", "pyforge-marshal"])

    assert seen["slugs"] == ["pyforge-warden", "pyforge-marshal"]


def test_deck_watch_forwards_a_custom_interval(monkeypatch):
    seen = {}

    def _fake_watch(transport, *, slugs, repo_root, interval):
        seen["interval"] = interval

    monkeypatch.setattr(watch_module, "watch", _fake_watch)

    cli.main(["deck", "watch", "pyforge-warden", "--interval", "90"])

    assert seen["interval"] == 90.0


def test_deck_watch_defaults_repo_root_to_cwd(monkeypatch, tmp_path: Path):
    seen = {}

    def _fake_watch(transport, *, slugs, repo_root, interval):
        seen["repo_root"] = repo_root

    monkeypatch.setattr(watch_module, "watch", _fake_watch)
    monkeypatch.chdir(tmp_path)

    cli.main(["deck", "watch", "pyforge-warden"])

    assert seen["repo_root"] == tmp_path


def test_deck_watch_success_returns_0_and_prints_nothing_to_stderr(
    monkeypatch, capsys
):
    def _fake_watch(transport, *, slugs, repo_root, interval):
        return None

    monkeypatch.setattr(watch_module, "watch", _fake_watch)

    exit_code = cli.main(["deck", "watch", "pyforge-warden"])

    assert exit_code == 0
    assert capsys.readouterr().err == ""


def test_deck_watch_herald_error_reaches_dispatch_and_maps_to_its_exit_code(
    monkeypatch, capsys
):
    def _fake_watch(transport, *, slugs, repo_root, interval):
        raise HeraldError("no bridge state recorded")

    monkeypatch.setattr(watch_module, "watch", _fake_watch)

    exit_code = cli.main(["deck", "watch", "pyforge-warden"])

    assert exit_code == 1  # bare HeraldError -> 1, per errors.exit_code_for
    err = capsys.readouterr().err
    assert "HeraldError" in err
    assert "no bridge state recorded" in err
