"""Shared fixtures for pyforge-atlas tests."""

import ipaddress
import os
import socket

import pytest
from pyforge.testing_kit import make_flag_provider_fixture

from pyforge.atlas.datasets import basilisk, identity_sources, public_sources
from pyforge.atlas.datasets import credentials as credential_switch

flag_provider = make_flag_provider_fixture()

_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex
_REAL_GETADDRINFO = socket.getaddrinfo


def _loopback(address: object) -> bool:
    """A Unix socket path, ``localhost`` or a loopback IP: the only places a test may connect to."""
    if not isinstance(address, tuple):
        return True  # AF_UNIX: a path on this host
    host = str(address[0])
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _local_name(host: object) -> bool:
    """``localhost``, a loopback IP, or no host at all (a wildcard bind): the only names a test may look up."""
    if host is None or host in ("", "localhost", b"localhost"):
        return True
    try:
        return ipaddress.ip_address(
            str(host.decode() if isinstance(host, bytes) else host).split("%", 1)[0]
        ).is_loopback
    except ValueError:
        return False


def _guarded_getaddrinfo(host, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202 -- socket.getaddrinfo's own signature
    if not _local_name(host):
        raise OSError(f"pyforge-atlas tests never reach the network (lookup of {host!r} refused)")
    return _REAL_GETADDRINFO(host, *args, **kwargs)


def _guarded_connect(self: socket.socket, address: object) -> None:
    if not _loopback(address):
        raise OSError(f"pyforge-atlas tests never reach the network (connect to {address!r} refused)")
    return _REAL_CONNECT(self, address)


def _guarded_connect_ex(self: socket.socket, address: object) -> int:
    if not _loopback(address):
        raise OSError(f"pyforge-atlas tests never reach the network (connect to {address!r} refused)")
    return _REAL_CONNECT_EX(self, address)


def pytest_configure(config: pytest.Config) -> None:
    """Story 36.2 review rounds 7 and 8: no test reaches the network, whatever it patches or undoes.

    Installed for the whole session, outside any ``monkeypatch``, so a test's ``monkeypatch.undo()``
    cannot lift it with its fake transport: a Python-level ``connect``/``connect_ex`` to anything but
    loopback or a Unix socket is refused, so is a name lookup of anything but ``localhost`` or a
    loopback address, and Kedro's telemetry is off (a copied project without its ``.telemetry`` would
    otherwise ask for consent's default and post an event). Loopback stays open for the servers the
    integration suites start. Not covered: a subprocess (Chromium, git, pixi), a C library's own
    sockets, UDP ``sendto`` without a connect, and a test that sets the real functions back on purpose."""
    os.environ.setdefault("KEDRO_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("DO_NOT_TRACK", "1")
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[method-assign]
    socket.getaddrinfo = _guarded_getaddrinfo


def pytest_unconfigure(config: pytest.Config) -> None:
    socket.socket.connect = _REAL_CONNECT  # type: ignore[method-assign]
    socket.socket.connect_ex = _REAL_CONNECT_EX  # type: ignore[method-assign]
    socket.getaddrinfo = _REAL_GETADDRINFO


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


@pytest.fixture(autouse=True)
def _vcs_universe_off_and_no_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 35.1: every test starts with ``pyforge.atlas.live_vcs_universe`` OFF and
    ``PYFORGE_ATLAS_CREDENTIALED`` unset. A test of the credentialed path patches both."""
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: False)
    monkeypatch.setattr(identity_sources, "identity_live", lambda: False)  # Story 36.2
    monkeypatch.delenv(credential_switch.SWITCH, raising=False)
    # Story 36.1: an operator's exported Basilisk token never reaches a test
    monkeypatch.delenv(credential_switch.BASILISK_TOKEN_ENV, raising=False)


@pytest.fixture(autouse=True)
def _basilisk_population_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 36.1: every test starts with ``pyforge.atlas.basilisk_population`` OFF (dev reads it
    ON). A test of the advisory drivers patches ``basilisk.population_live`` ON."""
    monkeypatch.setattr(basilisk, "population_live", lambda: False)


@pytest.fixture(autouse=True)
def _no_credential_without_the_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 35.1 (AD-11): a request any test sends that carries ``Authorization`` while the switch
    is off fails that test, whatever transport it would have reached."""
    import requests.adapters

    real_send = requests.adapters.HTTPAdapter.send

    def guarded(self, request, *args, **kwargs):  # noqa: ANN001, ANN202 -- requests' own signature
        refuse_credential_without_switch(request)
        return real_send(self, request, *args, **kwargs)

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", guarded)


_CREDENTIAL_HEADERS = ("Authorization", "Proxy-Authorization", "PRIVATE-TOKEN", "X-NuGet-ApiKey")


def refuse_credential_without_switch(request) -> None:  # noqa: ANN001 -- a requests PreparedRequest
    if not credential_switch.credentialed() and any(request.headers.get(h) for h in _CREDENTIAL_HEADERS):
        pytest.fail(f"a request to {request.url} carried a credential without {credential_switch.SWITCH}=1")


@pytest.fixture()
def fake_transport(monkeypatch: pytest.MonkeyPatch):
    """Story 35.1: answers each request from ``answers[url] = (status, json)`` (else 404) with no
    network and records every prepared request in ``sent``. The credential guard still applies."""
    import json
    from types import SimpleNamespace

    import requests
    import requests.adapters

    state = SimpleNamespace(sent=[], answers={}, timeouts=[])

    def send(self, request, *args, **kwargs):  # noqa: ANN001, ANN202 -- requests' own signature
        refuse_credential_without_switch(request)
        state.sent.append(request)
        state.timeouts.append(kwargs.get("timeout"))
        status, body = state.answers.get(request.url, (404, {"message": "Not Found"}))
        response = requests.models.Response()
        response.status_code = status
        response._content = json.dumps(body).encode()
        response.headers["Content-Type"] = "application/json"
        response.url = request.url
        response.request = request
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    return state
