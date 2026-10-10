"""Shared pytest fixtures for repo-root ``scripts/`` tests."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _pkg in ("pyforge-core", "pyforge-testing-kit"):
    _src = _REPO / "src" / "shared" / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))


@pytest.fixture(name="flag_provider")
def flag_provider(request: pytest.FixtureRequest) -> Iterator[dict[str, bool]]:
    """OpenFeature ON/OFF values for ``@flag_states`` tests (skipped when openfeature is absent)."""
    pytest.importorskip("openfeature")
    from pyforge.testing_kit.flags import installed_flags

    values = dict(getattr(request, "param", None) or {})
    with installed_flags(values):
        yield values
