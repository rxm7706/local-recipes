"""Story 25.4: the live Artifactory transport factory in ``tools/`` (outside
``src/pyforge/atlas/`` -- see the module's own docstring for why).

Loaded via ``importlib.util.spec_from_file_location`` since ``tools/`` is a
plain scripts directory, not a package (mirrors how ``scripts/
promote_sprint_status.py``'s own test suite loads its target)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from pyforge.atlas.artifactory.aql_adapter import AqlRequest, ArtifactoryAqlError

_TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"


def _load_transport_module():
    path = _TOOLS_DIR / "live_artifactory_transport.py"
    spec = importlib.util.spec_from_file_location("_live_artifactory_transport_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def transport_mod():
    return _load_transport_module()


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None) -> None:
        self.status_code = status_code
        self._json_body = json_body

    def json(self):
        if self._json_body is None:
            raise ValueError("no json body")
        return self._json_body

    @property
    def text(self):
        return "" if self._json_body is None else str(self._json_body)


def test_api_key_sets_jfrog_header(transport_mod, monkeypatch):
    captured = {}

    def _fake_request(method, url, *, json, headers, timeout):
        captured.update(method=method, url=url, json=json, headers=headers, timeout=timeout)
        return _FakeResponse(200, {"results": []})

    monkeypatch.setattr(transport_mod.requests, "request", _fake_request)
    transport = transport_mod.live_transport("https://artifactory.example.com", api_key="tok123")
    response = transport(AqlRequest(method="POST", url="/api/search/aql", body={"q": 1}))

    assert captured["headers"] == {"X-JFrog-Art-Api": "tok123"}
    assert captured["url"] == "https://artifactory.example.com/api/search/aql"
    assert response.status_code == 200
    assert response.body == {"results": []}


def test_username_password_sets_basic_auth(transport_mod, monkeypatch):
    captured = {}

    def _fake_request(method, url, *, json, headers, timeout):
        captured.update(headers=headers)
        return _FakeResponse(200, {})

    monkeypatch.setattr(transport_mod.requests, "request", _fake_request)
    transport = transport_mod.live_transport("https://artifactory.example.com", username="alice", password="s3cret")
    transport(AqlRequest(method="GET", url="/api/repositories"))

    assert "Authorization" in captured["headers"]
    assert captured["headers"]["Authorization"].startswith("Basic ")


def test_neither_credential_raises_named_error(transport_mod):
    with pytest.raises(ArtifactoryAqlError, match="no Artifactory credentials"):
        transport_mod.live_transport("https://artifactory.example.com")


def test_base_url_trailing_slash_is_normalized(transport_mod, monkeypatch):
    captured = {}

    def _fake_request(method, url, *, json, headers, timeout):
        captured["url"] = url
        return _FakeResponse(200, {})

    monkeypatch.setattr(transport_mod.requests, "request", _fake_request)
    transport = transport_mod.live_transport("https://artifactory.example.com/", api_key="tok123")
    transport(AqlRequest(method="GET", url="/api/repositories"))

    assert captured["url"] == "https://artifactory.example.com/api/repositories"
