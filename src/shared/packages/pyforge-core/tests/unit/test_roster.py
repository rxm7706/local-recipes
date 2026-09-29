"""Unit tests for ``pyforge.core.roster`` (Story 59.6, CAP-137).

Covers: the roster is exactly the eight declared stations, matches
``docs/governance/guild-roster.json``'s ``stations`` key, and
``long_form`` derives the ``pyforge-<station>`` path/package/env form.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.core.roster import STATIONS, long_form


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude)")


def test_stations_is_eight_unique_names():
    assert len(STATIONS) == 8
    assert len(set(STATIONS)) == 8


def test_stations_matches_guild_roster_json():
    payload = json.loads((_repo_root() / "docs" / "governance" / "guild-roster.json").read_text(encoding="utf-8"))
    assert list(STATIONS) == payload["stations"]


def test_long_form_prefixes_pyforge():
    assert long_form("steward") == "pyforge-steward"
    assert long_form("mason") == "pyforge-mason"


def test_long_form_covers_every_station():
    assert {long_form(s) for s in STATIONS} == {f"pyforge-{s}" for s in STATIONS}
