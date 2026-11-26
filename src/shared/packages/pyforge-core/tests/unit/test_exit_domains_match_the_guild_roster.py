"""``pyforge.core.exit_domains`` matches the governance declaration (steward Story 137.1,
spec-pyforge-steward:CAP-184).

It reads ``docs/governance/guild-roster.json``, outside this package, so it runs in the core
suite's live-tree half, the way ``test_roster_matches_the_guild_roster.py`` does for the roster.
It stays under ``tests/unit`` so the pip-install lane, which runs ``tests/unit`` whole, keeps
running it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.core.exit_domains import EXIT_CODE_DOMAINS, EXIT_CODE_DOMAINS_NARROWING

pytestmark = pytest.mark.live_tree


def _guild_roster() -> dict[str, object]:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude").is_dir():
            payload: dict[str, object] = json.loads(
                (candidate / "docs" / "governance" / "guild-roster.json").read_text(encoding="utf-8")
            )
            return payload
    raise AssertionError("could not locate repo root (pixi.toml + .claude)")


def test_exit_code_domains_match_guild_roster_json() -> None:
    declared = _guild_roster()["exit_code_domains"]
    assert {name: dict(members) for name, members in EXIT_CODE_DOMAINS.items()} == declared


def test_exit_code_domains_narrowing_matches_guild_roster_json() -> None:
    assert dict(EXIT_CODE_DOMAINS_NARROWING) == _guild_roster()["exit_code_domains_narrowing"]
