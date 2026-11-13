"""``pyforge.core.roster`` matches the governance roster (Story 59.6, CAP-137).

Moved from ``test_roster.py`` with its root finder, name and body unchanged
(Story 117.1, spec-pyforge-core:CAP-14): it reads
``docs/governance/guild-roster.json``, outside this package, so it runs in
the core suite's live-tree half. It stays under ``tests/unit`` so the
pip-install lane, which runs ``tests/unit`` whole, keeps running it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.core.roster import STATIONS

pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude)")


def test_stations_matches_guild_roster_json():
    payload = json.loads((_repo_root() / "docs" / "governance" / "guild-roster.json").read_text(encoding="utf-8"))
    assert list(STATIONS) == payload["stations"]
