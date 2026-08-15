"""``herald deck qa <slug>`` CLI wiring (Story 14.1): argument parsing and
composing ``deck_qa.run`` through ``dispatch`` (AD-6) -- entirely local, no
``McpTransport``/``bridge.run`` involved (mirrors ``test_cli_status.py``'s
own shape).
"""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.herald import cli, deck_qa


def test_deck_qa_help_exits_zero():
    assert cli.main(["deck", "qa", "--help"]) == 0


def test_deck_qa_returns_0_and_prints_a_parseable_report(tmp_path: Path, capsys):
    exit_code = cli.main(["deck", "qa", "pyforge-warden", "--repo-root", str(tmp_path)])

    assert exit_code == 0
    out = capsys.readouterr().out
    parsed = deck_qa.parse_report(json.loads(out))
    assert parsed.slug == "pyforge-warden"
    assert parsed.gates == {}


def test_deck_qa_defaults_repo_root_to_cwd(monkeypatch, tmp_path: Path, capsys):
    seen = {}
    real_run = deck_qa.run

    def _fake(slug, repo_root, gates=deck_qa.DEFAULT_GATES):
        seen["repo_root"] = repo_root
        return real_run(slug, repo_root, gates=gates)

    monkeypatch.setattr(deck_qa, "run", _fake)
    monkeypatch.chdir(tmp_path)

    exit_code = cli.main(["deck", "qa", "pyforge-warden"])

    assert exit_code == 0
    assert seen["repo_root"] == tmp_path


def test_deck_qa_never_constructs_an_mcp_transport(monkeypatch, tmp_path: Path):
    """Regression against the spec's boundary: ``deck qa`` must never talk
    to Claude Design. Patches ``McpTransport`` to explode on construction --
    a passing test proves ``_run_deck_qa`` never instantiates it."""

    class _ExplodingTransport:
        def __init__(self, *args, **kwargs):
            raise AssertionError("herald deck qa must never construct McpTransport")

    monkeypatch.setattr(cli, "McpTransport", _ExplodingTransport)

    exit_code = cli.main(["deck", "qa", "pyforge-warden", "--repo-root", str(tmp_path)])

    assert exit_code == 0
