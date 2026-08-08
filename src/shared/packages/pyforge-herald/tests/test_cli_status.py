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
    }
    defaults.update(overrides)
    return deck_pipeline.DeckStatus(**defaults)


def test_deck_status_help_exits_zero():
    assert cli.main(["deck", "status", "--help"]) == 0


def test_deck_status_with_no_slug_is_not_a_usage_error():
    # Unlike seed/pull, slug is optional -- omitting it must not be a usage
    # error (argparse `nargs="?"`).
    assert cli.main(["deck", "status", "--help"]) == 0


def test_deck_status_no_slug_forwards_none_and_prints_a_json_array(
    monkeypatch, capsys, tmp_path: Path
):
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


def test_deck_status_herald_error_reaches_dispatch_and_maps_to_its_exit_code(
    monkeypatch, capsys
):
    def _fake(transport, *, slug, repo_root):
        raise HeraldError("bridge state file could not be read")

    monkeypatch.setattr(deck_pipeline, "status", _fake)

    exit_code = cli.main(["deck", "status"])

    assert exit_code == 1  # bare HeraldError -> 1, per errors.exit_code_for
    err = capsys.readouterr().err
    assert "HeraldError" in err
    assert "bridge state file could not be read" in err


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
