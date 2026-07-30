"""Unit tests for the provenance post-tool-call hook — AUD-CFE-009.

Three defects: `http_request` declared `-> bytes` but returned None,
`--wait_for_response` was declared without `action="store_true"` so it consumed
the following argv entry, and a transport failure surfaced only as a traceback.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[4] / "hooks" / "post-tool-call.py"


@pytest.fixture(scope="module")
def hook():
    spec = importlib.util.spec_from_file_location("post_tool_call_under_test", HOOK)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["post_tool_call_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class _FakeConn:
    """Minimal HTTPConnection stand-in."""

    def __init__(self, payload=b'{"ok":true}'):
        self.payload = payload
        self.requested = None
        self.closed = False

    def request(self, method, location, body=None, headers=None):
        self.requested = (method, location, body, headers)

    def getresponse(self):
        conn = self

        class _Resp:
            def read(self):
                return conn.payload

        return _Resp()

    def close(self):
        self.closed = True


class TestHttpRequestReturnsBody:
    def test_returns_the_response_body_when_waiting(self, hook, monkeypatch):
        fake = _FakeConn(b'{"stored":1}')
        monkeypatch.setattr(hook, "HTTPConnection", lambda *a, **k: fake)
        out = hook.http_request(
            "POST", "localhost", 1234, "/x", body=b"{}", wait_for_response=True
        )
        assert out == b'{"stored":1}', "the body was read and thrown away before"

    def test_returns_empty_bytes_when_not_waiting(self, hook, monkeypatch):
        fake = _FakeConn()
        monkeypatch.setattr(hook, "HTTPConnection", lambda *a, **k: fake)
        out = hook.http_request(
            "POST", "localhost", 1234, "/x", body=b"{}", wait_for_response=False
        )
        assert out == b""

    def test_connection_is_closed_either_way(self, hook, monkeypatch):
        fake = _FakeConn()
        monkeypatch.setattr(hook, "HTTPConnection", lambda *a, **k: fake)
        hook.http_request("POST", "localhost", 1234, "/x", wait_for_response=True)
        assert fake.closed


class TestSendDiffErrors:
    def test_missing_port_file_raises_provenance_error(self, hook, monkeypatch):
        def _boom():
            raise FileNotFoundError(2, "no such file", "/tmp/nope-port.txt")

        monkeypatch.setattr(hook, "get_server_port", _boom)
        with pytest.raises(hook.ProvenanceHookError, match="Could not determine API port"):
            hook.send_diff_to_webserver("/tmp/x.py", 0, False)

    def test_network_failure_raises_provenance_error(self, hook, monkeypatch):
        monkeypatch.setattr(hook, "get_server_port", lambda: 65535)

        def _refuse(*a, **k):
            raise ConnectionRefusedError("nope")

        monkeypatch.setattr(hook, "http_request", _refuse)
        with pytest.raises(hook.ProvenanceHookError, match="Network error"):
            hook.send_diff_to_webserver("/tmp/x.py", 0, False)


def _run_hook(payload: dict, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK), *argv],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": "/tmp/definitely-not-a-project"},
    )


class TestCliContract:
    def test_bare_flag_is_accepted_as_a_boolean(self):
        """`--wait_for_response` used to be a value-taking option.

        A settings.json hook line like `post-tool-call.py --wait_for_response`
        either errored on the missing value or swallowed the next argument.
        """
        r = _run_hook({"tool_name": "Read", "tool_input": {}}, "--wait_for_response")
        assert r.returncode == 0, f"stdout={r.stdout} stderr={r.stderr}"
        assert "expected one argument" not in r.stderr

    def test_non_modification_tool_is_a_no_op(self):
        r = _run_hook({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}})
        assert r.returncode == 0

    def test_transport_failure_exits_non_zero_with_a_message(self):
        """No provenance server is listening, so this must fail loudly.

        Previously the only signal was an excepthook traceback.
        """
        r = _run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.py"}}
        )
        assert r.returncode == 1
        assert "Could not determine API port" in r.stderr
        assert "Traceback" not in r.stderr, "should be a message, not a traceback"
