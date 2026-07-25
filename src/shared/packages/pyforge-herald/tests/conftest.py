"""Shared fixtures + the egress-deny harness (Story 1.2).

Herald's suite is offline by construction: an autouse fixture patches the
three socket primitives an outbound call has to go through
(``socket.socket.connect``, ``socket.create_connection``,
``socket.getaddrinfo``) so any accidental network reach is a loud failure
rather than a slow, flaky, credential-dependent test.

Two deliberate differences from warden's harness
(``pyforge-warden/tests/conftest.py``), which patches at import time and
never unpatches:

* This one is a **fixture**, so the ``live`` marker carves a test out.
  ``test_live_design_spike.py`` is the FR-21 proof and must reach the real
  endpoint; every other test never may. Being a fixture also means
  ``monkeypatch`` restores the real primitives at teardown, so collecting
  this suite alongside another one cannot poison it.
* The denial error subclasses ``RuntimeError``, **not** ``OSError``. The
  transport maps connection failures to ``TransportUnreachableError`` by
  catching broadly, so an ``OSError``-shaped denial would be swallowed and
  reported as a tidy "endpoint unreachable" -- the escape hatch would look
  exactly like a passing test.
"""

from __future__ import annotations

import json
import socket
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from pyforge.herald.transport import ToolResult

FAKE_ACCESS_TOKEN = "herald-tests-fake-not-a-real-token"
"""Obviously-fake token for every fixture. Never a real credential."""

_FAR_FUTURE_MS = 4102444800000  # 2100-01-01, epoch milliseconds


class NetworkDeniedError(RuntimeError):
    """Raised when a non-``live`` test attempts outbound network egress."""

    def __init__(self, primitive: str, destination: object) -> None:
        super().__init__(
            f"outbound network egress denied by the herald test harness: "
            f"{primitive} -> {destination!r} (mark the test 'live' if it "
            f"is genuinely meant to reach claude-design)"
        )
        self.primitive = primitive
        self.destination = destination


def _denied_connect(self: socket.socket, address: object, *args: object) -> None:
    raise NetworkDeniedError("socket.socket.connect", address)


def _denied_create_connection(address: object, *args: object, **kwargs: object) -> None:
    raise NetworkDeniedError("socket.create_connection", address)


def _denied_getaddrinfo(
    host: object, port: object, *args: object, **kwargs: object
) -> None:
    raise NetworkDeniedError("socket.getaddrinfo", (host, port))


@pytest.fixture(autouse=True)
def deny_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Deny egress for every test not marked ``live``."""
    if request.node.get_closest_marker("live") is not None:
        return
    monkeypatch.setattr(socket.socket, "connect", _denied_connect)
    monkeypatch.setattr(socket, "create_connection", _denied_create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", _denied_getaddrinfo)


@pytest.fixture
def network_denied_error() -> type[NetworkDeniedError]:
    """The harness's denial class as a fixture -- test modules take the
    fixture rather than importing across test files (warden's convention)."""
    return NetworkDeniedError


class FakeCaller:
    """A recording ``ToolCaller``: no network, no SDK, no async.

    ``responses`` maps a tool name to the canned ``ToolResult`` it answers
    with (or to a list, consumed one per call, for a tool invoked more than
    once). An unmapped tool answers ``{}`` so a marshalling assertion does
    not have to stub a payload it does not care about."""

    def __init__(self, responses: Mapping[str, Any] | None = None) -> None:
        self.responses = dict(responses or {})
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call_tool(self, tool: str, arguments: Mapping[str, Any]) -> ToolResult:
        self.calls.append((tool, dict(arguments)))
        canned = self.responses.get(tool)
        if isinstance(canned, list):
            canned = canned.pop(0) if canned else None
        if canned is None:
            return ToolResult(text="{}")
        if isinstance(canned, str):
            return ToolResult(text=canned)
        return canned

    @property
    def tools(self) -> list[str]:
        return [tool for tool, _ in self.calls]

    def arguments_for(self, tool: str) -> dict[str, Any]:
        """The arguments of the single recorded call to ``tool``."""
        matches = [args for name, args in self.calls if name == tool]
        assert len(matches) == 1, f"expected exactly one {tool} call, got {matches}"
        return matches[0]


@pytest.fixture
def fake_caller():
    """Factory for a ``FakeCaller`` (a factory, not an instance, so one test
    can build several with different canned answers)."""

    def _make(responses: Mapping[str, Any] | None = None) -> FakeCaller:
        return FakeCaller(responses)

    return _make


@pytest.fixture
def credentials_file(tmp_path: Path):
    """Factory writing a fake ``~/.claude/.credentials.json``-shaped blob
    under ``tmp_path`` and returning its path.

    ``payload`` overrides the whole document (for the malformed cases);
    otherwise a well-formed ``designOauth`` block is written with an
    obviously-fake token and a far-future expiry."""

    def _write(
        *,
        access_token: str | None = FAKE_ACCESS_TOKEN,
        expires_at: object = _FAR_FUTURE_MS,
        payload: object = None,
        name: str = ".credentials.json",
        text: str | None = None,
    ) -> Path:
        path = tmp_path / name
        if text is not None:
            path.write_text(text, encoding="utf-8")
            return path
        if payload is None:
            block: dict[str, Any] = {}
            if access_token is not None:
                block["accessToken"] = access_token
            if expires_at is not None:
                block["expiresAt"] = expires_at
            payload = {"designOauth": block}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    return _write
