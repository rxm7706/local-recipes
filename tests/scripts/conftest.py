"""Shared pytest fixtures for repo-root ``scripts/`` tests."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
for _pkg in ("pyforge-core", "pyforge-testing-kit"):
    _src = _REPO / "src" / "shared" / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from pyforge.testing_kit import make_flag_provider_fixture  # noqa: E402

flag_provider = make_flag_provider_fixture()
