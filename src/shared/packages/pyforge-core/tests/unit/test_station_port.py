"""Unit tests for ``pyforge.core.station_port`` (Story 43.3)."""

from __future__ import annotations

import pytest

from pyforge.core.errors import PyforgeError
from pyforge.core.station_port import (
    StationPortError,
    invoke_in_process,
    is_station_remote,
    register_in_process_invoker,
    reset_in_process_invoker,
)


@pytest.fixture(autouse=True)
def _clear_invoker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STATION_REMOTE", raising=False)
    reset_in_process_invoker()


def test_is_station_remote_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert is_station_remote() is False
    monkeypatch.setenv("STATION_REMOTE", "1")
    assert is_station_remote() is True
    monkeypatch.setenv("STATION_REMOTE", "true")
    assert is_station_remote() is True


def test_invoke_without_registration_raises() -> None:
    with pytest.raises(StationPortError, match="no in-process"):
        invoke_in_process("GET", "http://host/stations/warden/api/v1/health", {}, None)


def test_invoke_while_remote_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    register_in_process_invoker(
        lambda method, url, headers, body: b"{}",
    )
    monkeypatch.setenv("STATION_REMOTE", "1")
    with pytest.raises(StationPortError, match="STATION_REMOTE"):
        invoke_in_process("GET", "http://host/stations/warden/api/v1/health", {}, None)


def test_registered_invoker_is_called() -> None:
    seen: dict[str, object] = {}

    def invoker(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
        seen["method"] = method
        seen["url"] = url
        seen["headers"] = headers
        seen["body"] = body
        return b'{"ok": true}'

    register_in_process_invoker(invoker)
    payload = invoke_in_process(
        "POST",
        "http://host/stations/warden/api/v1/compliance/check",
        {"Authorization": "Bearer tok"},
        b'{"recipe_name":"numpy"}',
    )
    assert payload == b'{"ok": true}'
    assert seen["method"] == "POST"
    assert seen["url"].endswith("/compliance/check")
    assert seen["headers"]["Authorization"] == "Bearer tok"


def test_station_port_error_is_pyforge_error() -> None:
    assert issubclass(StationPortError, PyforgeError)
