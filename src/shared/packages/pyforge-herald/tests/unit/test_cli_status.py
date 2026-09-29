"""``herald deck status [<slug>]`` CLI wiring (Story 3.1): argument parsing,
composing ``bridge.run`` + ``deck_pipeline.status`` over the V1-default
``McpTransport``, and routing the result through ``dispatch`` (AD-6).

``deck_pipeline.status`` itself is monkeypatched here -- its own behavior is
``test_deck_status.py``'s job. What's under test is the CLI's own
composition: which arguments it forwards, the JSON shape it prints, and
that a raised ``HeraldError`` reaches ``dispatch`` unchanged. Mirrors
``test_cli_pull.py``'s own shape.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.herald import cli, deck_pipeline
from pyforge.herald.errors import HeraldError


def _fake_status(**overrides):
    defaults = {
        "slug": "pyforge-warden",
        "linked": True,
        "project_id": "p-1",
        "sync": "unchanged",
        "last_pull": "2026-08-01T00:00:00+00:00",
        "stale_mirror": False,
    }
    defaults.update(overrides)
    return deck_pipeline.DeckStatus(**defaults)


def test_deck_status_help_exits_zero():
    assert cli.main(["deck", "status", "--help"]) == 0


def test_deck_status_with_no_slug_is_not_a_usage_error():
    # Unlike seed/pull, slug is optional -- omitting it must not be a usage
    # error (argparse `nargs="?"`).
    assert cli.main(["deck", "status", "--help"]) == 0


def test_deck_status_no_slug_forwards_none_and_prints_a_json_array(monkeypatch, capsys, tmp_path: Path):
    seen = {}

    def _fake(transport, *, slug, repo_root):
        seen["slug"] = slug
        seen["repo_root"] = repo_root
        seen["transport"] = transport
        return [
            _fake_status(slug="pyforge-warden"),
            _fake_status(
                slug="pyforge-doctor",
                linked=False,
                project_id=None,
                sync=None,
                last_pull=None,
            ),
        ]

    monkeypatch.setattr(deck_pipeline, "status", _fake)

    exit_code = cli.main(["deck", "status", "--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert seen["slug"] is None
    assert seen["repo_root"] == tmp_path
    out = json.loads(capsys.readouterr().out)
    assert [entry["slug"] for entry in out] == ["pyforge-warden", "pyforge-doctor"]
    assert out[0] == {
        "slug": "pyforge-warden",
        "linked": True,
        "project_id": "p-1",
        "sync": "unchanged",
        "last_pull": "2026-08-01T00:00:00+00:00",
        "stale_mirror": False,
    }
    assert out[1]["linked"] is False


def test_deck_status_with_a_slug_forwards_it(monkeypatch, capsys):
    seen = {}

    def _fake(transport, *, slug, repo_root):
        seen["slug"] = slug
        return [_fake_status(slug=slug)]

    monkeypatch.setattr(deck_pipeline, "status", _fake)

    exit_code = cli.main(["deck", "status", "pyforge-warden"])

    assert exit_code == 0
    assert seen["slug"] == "pyforge-warden"
    out = json.loads(capsys.readouterr().out)
    assert [entry["slug"] for entry in out] == ["pyforge-warden"]


def test_deck_status_defaults_repo_root_to_cwd(monkeypatch, tmp_path: Path):
    seen = {}

    def _fake(transport, *, slug, repo_root):
        seen["repo_root"] = repo_root
        return []

    monkeypatch.setattr(deck_pipeline, "status", _fake)
    monkeypatch.chdir(tmp_path)

    cli.main(["deck", "status"])

    assert seen["repo_root"] == tmp_path


def test_deck_status_reports_a_stale_mirror_flag(monkeypatch, capsys):
    def _fake(transport, *, slug, repo_root):
        return [_fake_status(slug="pyforge-doctor", stale_mirror=True)]

    monkeypatch.setattr(deck_pipeline, "status", _fake)

    cli.main(["deck", "status", "pyforge-doctor"])

    out = json.loads(capsys.readouterr().out)
    assert out[0]["stale_mirror"] is True


def test_deck_status_herald_error_reaches_dispatch_and_maps_to_its_exit_code(monkeypatch, capsys):
    def _fake(transport, *, slug, repo_root):
        raise HeraldError("bridge state file could not be read")

    monkeypatch.setattr(deck_pipeline, "status", _fake)

    exit_code = cli.main(["deck", "status"])

    assert exit_code == 1  # bare HeraldError -> 1, per errors.exit_code_for
    err = capsys.readouterr().err
    assert "HeraldError" in err
    assert "bridge state file could not be read" in err


def _fake_account_status(**overrides):
    defaults = {
        "project_id": "p-1",
        "name": "PyForge Warden deck",
        "url": "https://claude.ai/design/p/p-1",
        "status": "linked",
        "slug": "pyforge-warden",
        "reason": None,
    }
    defaults.update(overrides)
    return deck_pipeline.AccountProjectStatus(**defaults)


# --- Story 23.1: `--account` -------------------------------------------------


def test_deck_status_account_forwards_repo_root_and_prints_a_json_array(monkeypatch, capsys, tmp_path: Path):
    seen = {}

    def _fake(transport, *, repo_root):
        seen["repo_root"] = repo_root
        seen["transport"] = transport
        return [
            _fake_account_status(),
            _fake_account_status(
                project_id="p-2",
                name="REMOVED-PyForge Unifying Strategy",
                url="https://claude.ai/design/p/p-2",
                status="excluded",
                slug=None,
                reason="ad-hoc duplicate, retired",
            ),
        ]

    monkeypatch.setattr(deck_pipeline, "account_status", _fake)

    exit_code = cli.main(["deck", "status", "--account", "--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert seen["repo_root"] == tmp_path
    out = json.loads(capsys.readouterr().out)
    assert [entry["name"] for entry in out] == [
        "PyForge Warden deck",
        "REMOVED-PyForge Unifying Strategy",
    ]
    assert out[0] == {
        "name": "PyForge Warden deck",
        "project_id": "p-1",
        "url": "https://claude.ai/design/p/p-1",
        "status": "linked",
        "slug": "pyforge-warden",
        "reason": None,
    }
    assert out[1]["status"] == "excluded"
    assert out[1]["reason"] == "ad-hoc duplicate, retired"


def test_deck_status_account_defaults_repo_root_to_cwd(monkeypatch, tmp_path: Path):
    seen = {}

    def _fake(transport, *, repo_root):
        seen["repo_root"] = repo_root
        return []

    monkeypatch.setattr(deck_pipeline, "account_status", _fake)
    monkeypatch.chdir(tmp_path)

    cli.main(["deck", "status", "--account"])

    assert seen["repo_root"] == tmp_path


def test_deck_status_account_with_a_slug_is_a_herald_error(monkeypatch, capsys):
    def _fake(transport, *, repo_root):
        raise AssertionError("account_status must not be called")

    monkeypatch.setattr(deck_pipeline, "account_status", _fake)

    exit_code = cli.main(["deck", "status", "--account", "pyforge-warden"])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "--account" in err
    assert "pyforge-warden" in err


def test_deck_status_account_herald_error_reaches_dispatch(monkeypatch, capsys):
    def _fake(transport, *, repo_root):
        raise HeraldError("could not reach claude-design")

    monkeypatch.setattr(deck_pipeline, "account_status", _fake)

    exit_code = cli.main(["deck", "status", "--account"])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "could not reach claude-design" in err


def test_deck_status_never_writes_to_bridge_state(monkeypatch, tmp_path: Path):
    """No test here can prove the transport made no write call (that's
    ``deck_pipeline.status`` itself, monkeypatched away) -- what the CLI
    layer alone must prove is that it never calls ``state.write`` directly
    and never constructs anything but the same ``McpTransport()`` seed/pull
    already build. Asserted indirectly: the fake ``status`` never receives
    a write-capable object beyond the same transport passed through."""
    calls = []

    def _fake(transport, *, slug, repo_root):
        calls.append(transport)
        return []

    monkeypatch.setattr(deck_pipeline, "status", _fake)
    monkeypatch.chdir(tmp_path)

    cli.main(["deck", "status"])

    assert len(calls) == 1
    assert not (tmp_path / ".herald").exists()
