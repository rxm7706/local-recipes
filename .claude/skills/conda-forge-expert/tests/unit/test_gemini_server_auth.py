"""Unit tests for gemini_server credential handling — AUD-CFE-010.

The key used to travel as `?key=<secret>` on the URL, which leaks it into proxy
access logs and into any error string that echoes the URL. All four transport
paths must send `x-goog-api-key` and must keep the key out of the URL entirely.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[4] / "tools" / "gemini_server.py"
FAKE_KEY = "AIzaSyFAKE-not-a-real-key-0123456789"


@pytest.fixture
def gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    spec = importlib.util.spec_from_file_location("gemini_under_test", SERVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gemini_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class _Captured:
    """Records the URL / headers of whatever transport call was made."""

    def __init__(self):
        self.url = None
        self.headers = {}
        self.body = None


@pytest.fixture
def captured():
    return _Captured()


@pytest.fixture
def stub_requests(gemini, captured, monkeypatch):
    if gemini.requests is None:
        pytest.skip("requests not importable in this env")

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    def _post(url, json=None, headers=None, timeout=None):
        captured.url, captured.headers, captured.body = url, headers or {}, json
        return _Resp()

    def _get(url, headers=None, timeout=None):
        captured.url, captured.headers = url, headers or {}
        return _Resp()

    monkeypatch.setattr(gemini.requests, "post", _post)
    monkeypatch.setattr(gemini.requests, "get", _get)
    return captured


@pytest.fixture
def stub_urlopen(gemini, captured, monkeypatch):
    class _Resp:
        def read(self):
            return json.dumps({"ok": True}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _urlopen(req, timeout=None):
        captured.url = req.full_url
        # urllib title-cases header keys on the Request object.
        captured.headers = dict(req.headers)
        captured.body = req.data
        return _Resp()

    monkeypatch.setattr(gemini.urllib.request, "urlopen", _urlopen)
    return captured


def _header(headers: dict, name: str) -> str | None:
    for k, v in headers.items():
        if k.lower() == name.lower():
            return v
    return None


class TestRequestsPath:
    def test_post_sends_key_as_header(self, gemini, stub_requests):
        gemini._post_requests("models/x:generateContent", {"a": 1})
        assert _header(stub_requests.headers, "x-goog-api-key") == FAKE_KEY

    def test_post_keeps_key_out_of_url(self, gemini, stub_requests):
        gemini._post_requests("models/x:generateContent", {"a": 1})
        assert "key=" not in stub_requests.url
        assert FAKE_KEY not in stub_requests.url

    def test_post_still_sets_json_content_type(self, gemini, stub_requests):
        gemini._post_requests("models/x:generateContent", {"a": 1})
        assert _header(stub_requests.headers, "content-type") == "application/json"

    def test_get_sends_key_as_header(self, gemini, stub_requests):
        gemini._get_requests("models")
        assert _header(stub_requests.headers, "x-goog-api-key") == FAKE_KEY

    def test_get_keeps_key_out_of_url(self, gemini, stub_requests):
        gemini._get_requests("models")
        assert "key=" not in stub_requests.url
        assert FAKE_KEY not in stub_requests.url

    def test_get_previously_sent_no_headers_at_all(self, gemini, stub_requests):
        """Regression note: _get_requests used to pass no headers kwarg."""
        gemini._get_requests("models")
        assert stub_requests.headers, "GET must now carry auth headers"


class TestUrllibPath:
    def test_post_sends_key_as_header(self, gemini, stub_urlopen):
        gemini._post_urllib("models/x:generateContent", {"a": 1})
        assert _header(stub_urlopen.headers, "x-goog-api-key") == FAKE_KEY
        assert "key=" not in stub_urlopen.url
        assert FAKE_KEY not in stub_urlopen.url

    def test_get_sends_key_as_header(self, gemini, stub_urlopen):
        gemini._get_urllib("models")
        assert _header(stub_urlopen.headers, "x-goog-api-key") == FAKE_KEY
        assert "key=" not in stub_urlopen.url
        assert FAKE_KEY not in stub_urlopen.url

    def test_get_uses_a_request_object_not_a_bare_url(self, gemini, stub_urlopen):
        """A bare URL string cannot carry a header — the old GET passed one."""
        gemini._get_urllib("models")
        assert stub_urlopen.headers


class TestMissingKey:
    @pytest.mark.parametrize(
        "fn,args",
        [
            ("_post_requests", ("models/x:generateContent", {})),
            ("_get_requests", ("models",)),
            ("_post_urllib", ("models/x:generateContent", {})),
            ("_get_urllib", ("models",)),
        ],
    )
    def test_every_path_raises_without_a_key(self, gemini, monkeypatch, fn, args):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        if fn.endswith("_requests") and gemini.requests is None:
            pytest.skip("requests not importable in this env")
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
            getattr(gemini, fn)(*args)


class TestNoQueryStringKeyRemains:
    def test_source_has_no_key_query_parameter(self):
        """Cheap grep gate so the pattern cannot come back in a new helper."""
        src = SERVER.read_text(encoding="utf-8")
        offenders = [
            line
            for line in src.splitlines()
            if "?key=" in line and not line.lstrip().startswith("#")
        ]
        assert not offenders, offenders
