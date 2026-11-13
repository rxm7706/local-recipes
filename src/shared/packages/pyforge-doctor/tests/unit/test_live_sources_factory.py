"""Story 58.2 (spec-pyforge-doctor:CAP-97) -- the live-tree half of ``test_sources_factory.py``.

``factory._env_count`` reads the repository's own ``pixi.toml`` here; every test that builds its own tree (the real
tmp git repositories ``_bootstrap`` seeds) stays in the package half (``test_sources_factory.py``).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from pyforge.doctor.sources import factory

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def test_env_count_reads_the_live_manifest_like_tomllib() -> None:
    repo = Path(__file__).resolve().parents[6]
    with (repo / "pixi.toml").open("rb") as fh:
        declared = len(tomllib.load(fh)["environments"])
    assert factory._env_count(repo) == declared
