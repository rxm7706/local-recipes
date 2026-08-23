"""CAP-3 locality helpers: fail-closed deployed, explicit local only."""

from __future__ import annotations

from typing import TYPE_CHECKING

from config.locality import LOCAL
from config.locality import RUNTIME_ENV_VAR
from config.locality import is_deployed
from config.locality import is_local
from config.locality import is_serving_process
from config.startup import is_deployed as startup_is_deployed
from config.startup import is_serving_process as startup_is_serving_process

if TYPE_CHECKING:
    import pytest


def test_absent_runtime_is_deployed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(RUNTIME_ENV_VAR, raising=False)
    assert is_deployed() is True
    assert is_local() is False


def test_unrecognized_runtime_is_deployed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(RUNTIME_ENV_VAR, "staging")
    assert is_deployed() is True
    assert is_local() is False


def test_explicit_local_is_not_deployed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    assert is_deployed() is False
    assert is_local() is True


def test_startup_reexports_locality_by_identity() -> None:
    assert startup_is_deployed is is_deployed
    assert startup_is_serving_process is is_serving_process
