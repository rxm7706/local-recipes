"""Suite-wide pytest fixtures for pyforge-mason (Story 1.9, AD-16).

`fake_cfe_root` exposes the on-disk fixture CFE root the whole suite can
resolve/invoke against instead of a real conda-forge-expert install."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fake_cfe_root() -> Path:
    """Return the path to the fixture CFE root tree
    (`tests/fixtures/fake_cfe_root/`), containing a real
    `.claude/scripts/conda-forge-expert/` marker directory with stub
    scripts."""
    return Path(__file__).parent / "fixtures" / "fake_cfe_root"
