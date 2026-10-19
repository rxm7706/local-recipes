"""Shared fixtures for pyforge-atlas tests."""

import pytest
from pyforge.testing_kit import make_flag_provider_fixture

from pyforge.atlas.datasets import basilisk, public_sources
from pyforge.atlas.datasets import credentials as credential_switch

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


@pytest.fixture(autouse=True)
def _vcs_universe_off_and_no_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 35.1: every test starts with ``pyforge.atlas.live_vcs_universe`` OFF and
    ``PYFORGE_ATLAS_CREDENTIALED`` unset. A test of the credentialed path patches both."""
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: False)
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
