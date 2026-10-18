"""Shared fixtures for pyforge-atlas tests."""

import pytest
from pyforge.testing_kit import make_flag_provider_fixture

from pyforge.atlas.datasets import public_sources

flag_provider = make_flag_provider_fixture()

_REAL_LIVE = public_sources.live  # captured before any pin


@pytest.fixture()
def real_live():
    """The unpinned ``public_sources.live``, for the tests that resolve the real flag key."""
    return _REAL_LIVE


@pytest.fixture(autouse=True)
def _public_sources_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 34.4: ``pyforge.atlas.live_public_sources`` reads ON in dev, the default environment,
    so every test starts with it OFF: no test reaches the network (Epic 34's hard boundary, AD-11).
    A test of the live path patches ``public_sources.live`` ON and supplies its own responses."""
    monkeypatch.setattr(public_sources, "live", lambda: False)
