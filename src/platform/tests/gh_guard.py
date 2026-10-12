"""Story 16.1: no platform test may run the operator's ``gh`` (a live token source).

The fleet-inventory task runs ``gh auth token`` through one seam,
``django_warden_fabric.fleet_inventory._run_gh``. ``refuse_real_gh`` makes that seam
refuse for the length of one test, and fails the test at teardown even when the
refusal was swallowed (an eager Celery task, a broad ``except``). The root conftest's
autouse ``real_gh_attempts`` fixture is this generator; it lives here, importable,
so ``test_warden_fleet_inventory.py`` can drive its teardown directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

GH_SEAM = "django_warden_fabric.fleet_inventory._run_gh"


class RealGhInvokedError(AssertionError):
    """A test reached the operator's ``gh`` token provider (Story 16.1, M7)."""


def refuse_real_gh(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[list[str]]]:
    """Refuse the ``gh`` seam, yield the attempts, fail at teardown if any."""
    attempts: list[list[str]] = []

    def _refuse(argv: list[str], *, timeout: float) -> None:
        attempts.append(list(argv[1:]))
        msg = (
            "a test reached the real gh token provider; inject a fake "
            "provider or GhAuthTokenProvider(runner=...)"
        )
        raise RealGhInvokedError(msg)

    monkeypatch.setattr(GH_SEAM, _refuse)
    yield attempts
    if attempts:
        pytest.fail(
            f"{len(attempts)} call(s) reached the real gh token provider",
            pytrace=False,
        )
