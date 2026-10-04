"""``marshal adapters models`` end to end through the real HTTP adapter (Story 84.2).

Story 84.1's CLI sentinel test stubbed ``fetch_live_ids_for_profile`` and
ran JSON only, so a mutant that put the transport exception text back into
``reason`` passed it. These drive ``run_adapters_models`` with no fetch port
injected -- the handler builds the live adapter -- and patch only
``http.client.HTTPSConnection``, which never opens a socket here.
"""

from __future__ import annotations

import argparse
import http.client
import json
from datetime import date
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.cli import adapters as adapters_cli
from pyforge.marshal.core.harness_profile import HarnessProfile, ModelListSource

#: An obvious sentinel, never shaped like a real provider key.
SENTINEL = "SENTINEL-NOT-A-REAL-KEY-84-2"

LEAK = ("leak.invalid", 8443)
REDIRECT = ("redirect.invalid", 9443)
REDIRECT_TARGET = ("redirect.invalid", 9444)
HEALTHY = ("healthy.invalid", 7443)
CRLF_HOST = ("crlf.invalid", 6443)

_ENV = {
    "leaky": "MODEL_LIST_84_2_LEAKY_KEY",
    "redirected": "MODEL_LIST_84_2_REDIRECTED_KEY",
    "healthy": "MODEL_LIST_84_2_HEALTHY_KEY",
    "crlf": "MODEL_LIST_84_2_CRLF_KEY",
}


class _FakeResponse:
    def __init__(self, status: int, body: bytes = b"", location: str | None = None) -> None:
        self.status = status
        self._body = body
        self._location = location

    def read(self) -> bytes:
        return self._body

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._location if name.lower() == "location" else default


class _Wire:
    """Every connection and request the patched ``HTTPSConnection`` saw."""

    def __init__(self, script: dict[tuple[str, int], object]) -> None:
        self.script = script
        self.connections: list[tuple[str, int]] = []
        self.requests: list[tuple[tuple[str, int], str, dict[str, str]]] = []

    def requests_to(self, endpoint: tuple[str, int]) -> list[dict[str, str]]:
        return [headers for where, _path, headers in self.requests if where == endpoint]


def _patch_wire(monkeypatch: pytest.MonkeyPatch, script: dict[tuple[str, int], object]) -> _Wire:
    wire = _Wire(script)

    class FakeHTTPSConnection:
        def __init__(self, host: str, port: int | None = None, **_kwargs: object) -> None:
            self._endpoint = (host, port if port is not None else 443)
            self._response: object = None
            wire.connections.append(self._endpoint)

        def request(self, method: str, url: str, body: object = None, headers: dict[str, str] | None = None) -> None:
            del method, body
            wire.requests.append((self._endpoint, url, dict(headers or {})))
            behaviour = wire.script[self._endpoint]
            if isinstance(behaviour, BaseException):
                raise behaviour
            self._response = behaviour

        def getresponse(self) -> object:
            return self._response

        def close(self) -> None:
            return None

    monkeypatch.setattr(http.client, "HTTPSConnection", FakeHTTPSConnection)
    return wire


def _profile(name: str, endpoint: tuple[str, int]) -> HarnessProfile:
    host, port = endpoint
    return HarnessProfile(
        name=name,
        binary=name,
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url=f"https://{host}:{port}/v1/models",
            credential_env=_ENV[name],
            credential_header="x-api-key",
            pagination="anthropic",
        ),
    )


def _transport_failures() -> list[BaseException]:
    # Each carries the key in its message, the way ``putheader`` does for a
    # header value it refuses.
    return [
        ValueError(f"Invalid header value b'{SENTINEL}'"),
        OSError(f"connection reset while sending x-api-key {SENTINEL}"),
        http.client.BadStatusLine(SENTINEL),
    ]


@pytest.mark.parametrize("fmt", ["text", "json"])
@pytest.mark.parametrize("failure", _transport_failures(), ids=lambda exc: type(exc).__name__)
def test_sentinel_key_never_reaches_output_and_redirect_target_gets_nothing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    fmt: str,
    failure: BaseException,
) -> None:
    for name in ("leaky", "redirected", "healthy"):
        monkeypatch.setenv(_ENV[name], SENTINEL)
    monkeypatch.setenv(_ENV["crlf"], SENTINEL + "\r")
    wire = _patch_wire(
        monkeypatch,
        {
            LEAK: failure,
            REDIRECT: _FakeResponse(302, location=f"https://{REDIRECT_TARGET[0]}:{REDIRECT_TARGET[1]}/v1/models"),
            # Scripted so a redirect-following mutant succeeds quietly and
            # only the no-request assertion below can catch it.
            REDIRECT_TARGET: _FakeResponse(200, json.dumps({"data": [{"id": "target-model"}]}).encode()),
            HEALTHY: _FakeResponse(200, json.dumps({"data": [{"id": "healthy-model"}], "has_more": False}).encode()),
            CRLF_HOST: _FakeResponse(200, json.dumps({"data": [{"id": "crlf-model"}]}).encode()),
        },
    )
    profiles = {
        "crlf": _profile("crlf", CRLF_HOST),
        "healthy": _profile("healthy", HEALTHY),
        "leaky": _profile("leaky", LEAK),
        "redirected": _profile("redirected", REDIRECT),
    }
    monkeypatch.setattr(adapters_cli, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(adapters_cli, "load_profiles", lambda _root: (profiles, ()))
    args = argparse.Namespace(slug="pyforge-marshal", format=fmt, write=True)

    code = adapters_cli.run_adapters_models(args, fs=LocalFs())

    out = capsys.readouterr().out
    snapshot = (
        tmp_path
        / "_bmad-output/projects/pyforge-marshal/planning-artifacts/model-lists"
        / f"model-list-{date.today().isoformat()}.json"
    ).read_text(encoding="utf-8")
    assert code == 0
    for text in (out, snapshot):
        assert "NOT-A-REAL-KEY" not in text

    # The key went only where its profile points: once to the leaking host
    # (whose failure carried it), once to the redirecting host, never to the
    # redirect target, never anywhere for the refused CR key.
    assert [h["x-api-key"] for h in wire.requests_to(LEAK)] == [SENTINEL]
    assert [h["x-api-key"] for h in wire.requests_to(REDIRECT)] == [SENTINEL]
    assert REDIRECT_TARGET not in wire.connections
    assert wire.requests_to(REDIRECT_TARGET) == []
    assert CRLF_HOST not in wire.connections

    expected = {
        "crlf": {
            "status": "unavailable",
            "count": 0,
            "reason": f"credential env {_ENV['crlf']!r} contains invalid characters",
        },
        "healthy": {"status": "ok", "count": 1, "reason": None},
        "leaky": {"status": "unavailable", "count": 0, "reason": "HTTP network error"},
        "redirected": {"status": "unavailable", "count": 0, "reason": "HTTP redirect not followed"},
    }
    if fmt == "json":
        assert json.loads(out)["data"]["harness_results"] == expected
    else:
        assert "[healthy] listed 1 model id(s)" in out
        assert "[leaky] unavailable: HTTP network error" in out
        assert "[redirected] unavailable: HTTP redirect not followed" in out
        assert f"[crlf] unavailable: credential env {_ENV['crlf']!r} contains invalid characters" in out
    assert json.loads(snapshot)["harnesses"]["healthy"] == {"status": "ok", "ids": ["healthy-model"]}
