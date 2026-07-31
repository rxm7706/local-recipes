"""Story 1.3 — pins the exact integer value of every exit code (AD-7)."""

from __future__ import annotations

from pyforge.mason.exit_codes import (
    EXIT_CFE_UNAVAILABLE, EXIT_FAILED, EXIT_INTERRUPTED, EXIT_OK, EXIT_USAGE,
)


def test_exit_code_values():
    assert EXIT_OK == 0
    assert EXIT_FAILED == 1
    assert EXIT_USAGE == 2
    assert EXIT_CFE_UNAVAILABLE == 3
    assert EXIT_INTERRUPTED == 130
