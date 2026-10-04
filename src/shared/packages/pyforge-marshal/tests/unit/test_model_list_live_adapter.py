"""Live adapter coverage for model-list refresh (Story 84.1)."""

from __future__ import annotations

import http.client
import json
from unittest.mock import MagicMock

import pytest
from pyforge.core.process import ProcessError

from pyforge.marshal.adapters.model_list_http import http_get_for_model_list
from pyforge.marshal.adapters.model_list_live import LiveModelListFetch, fetch_live_ids_for_profile
from pyforge.marshal.core.harness_profile import HarnessProfile, ModelListSource
from pyforge.marshal.ports.model_list_fetch import HttpGetResult


def test_live_fetch_run_command_empty_argv():
    result = LiveModelListFetch().run_command([])
    assert result.exit_code == 127
    assert result.stderr == "empty argv"


def test_live_fetch_run_command_binary_missing():
    result = LiveModelListFetch(repo_root="/nonexistent-root").run_command(["missing-binary-xyz"])
    assert result.exit_code == 127
    assert "binary not found" in result.stderr


def test_live_fetch_run_command_success(monkeypatch):
    fetch = LiveModelListFetch(repo_root="/tmp")

    monkeypatch.setattr(
        "pyforge.marshal.adapters.model_list_live._resolve_binary",
        lambda binary, dirs, root: "/usr/bin/echo",
    )

    class _RunResult:
        returncode = 0
        stdout = "out"
        stderr = ""

    monkeypatch.setattr(fetch._process, "run", lambda *a, **k: _RunResult())
    result = fetch.run_command(["echo"], timeout_s=30.0)
    assert result.exit_code == 0
    assert result.stdout == "out"


def test_live_fetch_run_command_process_error_timeout(monkeypatch):
    fetch = LiveModelListFetch(repo_root="/tmp")
    monkeypatch.setattr(
        "pyforge.marshal.adapters.model_list_live._resolve_binary",
        lambda *a, **k: "/bin/true",
    )

    def _raise(*a, **k):
        raise ProcessError("process timeout exceeded")

    monkeypatch.setattr(fetch._process, "run", _raise)
    result = fetch.run_command(["true"], timeout_s=1.0)
    assert result.exit_code == 124


def test_live_fetch_run_command_process_error_other(monkeypatch):
    fetch = LiveModelListFetch(repo_root="/tmp")
    monkeypatch.setattr(
        "pyforge.marshal.adapters.model_list_live._resolve_binary",
        lambda *a, **k: "/bin/true",
    )

    def _boom(*a, **k):
        raise ProcessError("boom")

    monkeypatch.setattr(fetch._process, "run", _boom)
    result = fetch.run_command(["true"])
    assert result.exit_code == 1


def test_live_fetch_run_command_timeout_error(monkeypatch):
    fetch = LiveModelListFetch(repo_root="/tmp")
    monkeypatch.setattr(
        "pyforge.marshal.adapters.model_list_live._resolve_binary",
        lambda *a, **k: "/bin/true",
    )

    def _timeout(*a, **k):
        raise TimeoutError()

    monkeypatch.setattr(fetch._process, "run", _timeout)
    result = fetch.run_command(["true"])
    assert result.exit_code == 124


def test_live_fetch_http_get_catches_oserror(monkeypatch):
    fetch = LiveModelListFetch()

    def _boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(
        "pyforge.marshal.adapters.model_list_live.http_get_for_model_list",
        _boom,
    )
    result = fetch.http_get("https://example.com/v1/models", {})
    assert result.status_code == 0
    assert result.body == b"network error"


def test_fetch_http_timeout_reason():
    profile = HarnessProfile(
        name="claude",
        binary="claude",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url="https://api.anthropic.com/v1/models",
            credential_env="ANTHROPIC_API_KEY",
            credential_header="x-api-key",
            pagination="anthropic",
        ),
    )

    class _TimeoutFetch:
        def run_command(self, *a, **k):
            raise AssertionError("not used")

        def http_get(self, *a, **k):
            return HttpGetResult(status_code=0, body=b"timeout")

    result = fetch_live_ids_for_profile(profile, _TimeoutFetch(), env={"ANTHROPIC_API_KEY": "x"})
    assert result.status == "unavailable"
    assert result.reason == "HTTP request timed out"


def test_fetch_invalid_credential_env_name():
    profile = HarnessProfile(
        name="claude",
        binary="claude",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url="https://api.anthropic.com/v1/models",
            credential_env="not-a-valid-env",
            credential_header="x-api-key",
            pagination="anthropic",
        ),
    )

    class _Fetch:
        def run_command(self, *a, **k):
            raise AssertionError("not used")

        def http_get(self, *a, **k):
            raise AssertionError("not used")

    result = fetch_live_ids_for_profile(profile, _Fetch(), env={"x": "y"})
    assert result.status == "unavailable"
    assert "invalid credential_env" in (result.reason or "")


def test_fetch_anthropic_pagination_stuck():
    base = "https://api.anthropic.com/v1/models"
    body = json.dumps({"data": [{"id": "m1"}], "has_more": True, "last_id": "m1"}).encode()

    class _StuckFetch:
        def run_command(self, *a, **k):
            raise AssertionError("not used")

        def http_get(self, url, headers, *, timeout_s=60.0):
            del headers, timeout_s
            return HttpGetResult(status_code=200, body=body)

    profile = HarnessProfile(
        name="claude",
        binary="claude",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url=base,
            credential_env="ANTHROPIC_API_KEY",
            credential_header="x-api-key",
            pagination="anthropic",
        ),
    )
    result = fetch_live_ids_for_profile(profile, _StuckFetch(), env={"ANTHROPIC_API_KEY": "k"})
    assert result.status == "unavailable"
    assert "pagination cursor did not advance" in (result.reason or "")


def test_fetch_command_nonzero_exit():
    profile = HarnessProfile(
        name="cursor",
        binary="cursor-agent",
        argv=("{prompt}",),
        model_list=ModelListSource(catalog_provider="cursor", command=("cursor-agent", "models")),
    )

    class _FailCmd:
        def run_command(self, *a, **k):
            from pyforge.marshal.ports.model_list_fetch import CommandRunResult

            return CommandRunResult(exit_code=1, stdout="", stderr="err")

        def http_get(self, *a, **k):
            raise AssertionError("not used")

    result = fetch_live_ids_for_profile(profile, _FailCmd())
    assert result.status == "unavailable"
    assert "command failed" in (result.reason or "")


def test_fetch_http_missing_pagination_kind():
    profile = HarnessProfile(
        name="claude",
        binary="claude",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url="https://api.anthropic.com/v1/models",
            credential_env="ANTHROPIC_API_KEY",
            credential_header="x-api-key",
            pagination="",
        ),
    )

    class _Fetch:
        def run_command(self, *a, **k):
            raise AssertionError("not used")

        def http_get(self, *a, **k):
            return HttpGetResult(status_code=200, body=b"{}")

    result = fetch_live_ids_for_profile(profile, _Fetch(), env={"ANTHROPIC_API_KEY": "k"})
    assert result.status == "unavailable"
    assert "pagination" in (result.reason or "")


def test_http_parse_invalid_port_and_host():
    assert http_get_for_model_list("https://:443/x", {}, timeout_s=1.0).status_code == 0
    assert http_get_for_model_list("https://host:badport/x", {}, timeout_s=1.0).status_code == 0


def test_http_network_error_on_connect(monkeypatch):
    mock_conn = MagicMock()
    mock_conn.request.side_effect = OSError("refused")
    monkeypatch.setattr(
        "pyforge.marshal.adapters.model_list_http.http.client.HTTPSConnection",
        lambda *a, **k: mock_conn,
    )
    result = http_get_for_model_list("https://example.com/v1/models", {}, timeout_s=1.0)
    assert result.body == b"network error"


def test_http_http_exception(monkeypatch):
    mock_conn = MagicMock()
    mock_conn.request.side_effect = http.client.HTTPException("bad line")

    monkeypatch.setattr(
        "pyforge.marshal.adapters.model_list_http.http.client.HTTPSConnection",
        lambda *a, **k: mock_conn,
    )
    result = http_get_for_model_list("https://example.com/v1/models", {}, timeout_s=1.0)
    assert result.body == b"network error"


class _PagedFetch:
    """Serves scripted 200 pages in order and records each URL."""

    def __init__(self, pages: list[object]) -> None:
        self.pages = list(pages)
        self.urls: list[str] = []

    def run_command(self, *a, **k):
        raise AssertionError("not used")

    def http_get(self, url, headers, *, timeout_s=60.0):
        del headers, timeout_s
        self.urls.append(url)
        page = self.pages.pop(0)
        body = page if isinstance(page, bytes) else json.dumps(page).encode()
        return HttpGetResult(status_code=200, body=body)


def _paged_profile(pagination: str) -> HarnessProfile:
    return HarnessProfile(
        name="paged",
        binary="paged",
        argv=("{prompt}",),
        model_list=ModelListSource(
            catalog_provider="anthropic",
            url="https://models.invalid/v1/models",
            credential_env="PAGED_KEY",
            credential_header="x-api-key",
            pagination=pagination,
        ),
    )


_ANTHROPIC_PAGE_1 = {"data": [{"id": "m1"}], "has_more": True, "last_id": "m1"}
_GEMINI_PAGE_1 = {
    "models": [{"name": "models/g1", "supportedGenerationMethods": ["generateContent"]}],
    "nextPageToken": "t1",
}


@pytest.mark.parametrize(
    "later_page",
    [
        {"has_more": False},
        {"data": None, "has_more": False},
        {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}},
    ],
    ids=["data-missing", "data-null", "error-body"],
)
def test_anthropic_later_page_without_list_is_unavailable_never_page_one(later_page):
    """Story 84.2: page 2 without a ``data`` list never ends an ok listing of page 1's ids."""
    fetch = _PagedFetch([_ANTHROPIC_PAGE_1, later_page])
    result = fetch_live_ids_for_profile(_paged_profile("anthropic"), fetch, env={"PAGED_KEY": "k"})
    assert len(fetch.urls) == 2
    assert result.status == "unavailable"
    assert result.reason == "unexpected page shape"
    assert result.live_ids == frozenset()


@pytest.mark.parametrize(
    "later_page",
    [
        {},
        {"models": None},
        {"error": {"code": 500, "message": "Internal error encountered.", "status": "INTERNAL"}},
    ],
    ids=["models-missing", "models-null", "error-body"],
)
def test_gemini_later_page_without_list_is_unavailable_never_page_one(later_page):
    """Story 84.2: page 2 without a ``models`` list never ends an ok listing of page 1's ids."""
    fetch = _PagedFetch([_GEMINI_PAGE_1, later_page])
    result = fetch_live_ids_for_profile(_paged_profile("gemini"), fetch, env={"PAGED_KEY": "k"})
    assert len(fetch.urls) == 2
    assert result.status == "unavailable"
    assert result.reason == "unexpected page shape"
    assert result.live_ids == frozenset()


@pytest.mark.parametrize(
    ("pagination", "page"),
    [
        ("anthropic", {"type": "error", "error": {"type": "authentication_error", "message": "x"}}),
        ("gemini", {"error": {"code": 403, "message": "x", "status": "PERMISSION_DENIED"}}),
    ],
)
def test_first_page_error_body_is_unexpected_shape(pagination, page):
    result = fetch_live_ids_for_profile(_paged_profile(pagination), _PagedFetch([page]), env={"PAGED_KEY": "k"})
    assert result.status == "unavailable"
    assert result.reason == "unexpected page shape"


@pytest.mark.parametrize(
    ("body", "reason"),
    [(b"\xff\xfe", "invalid JSON response"), (b"not json", "invalid JSON response"), (b"[1, 2]", "invalid JSON shape")],
)
def test_undecodable_page_is_unavailable(body, reason):
    result = fetch_live_ids_for_profile(_paged_profile("anthropic"), _PagedFetch([body]), env={"PAGED_KEY": "k"})
    assert result.status == "unavailable"
    assert result.reason == reason


def test_well_formed_pages_still_list_every_id():
    anthropic = fetch_live_ids_for_profile(
        _paged_profile("anthropic"),
        _PagedFetch([_ANTHROPIC_PAGE_1, {"data": [{"id": "m2"}], "has_more": False}]),
        env={"PAGED_KEY": "k"},
    )
    gemini = fetch_live_ids_for_profile(
        _paged_profile("gemini"),
        _PagedFetch(
            [_GEMINI_PAGE_1, {"models": [{"name": "models/g2", "supportedGenerationMethods": ["generateContent"]}]}]
        ),
        env={"PAGED_KEY": "k"},
    )
    assert (anthropic.status, anthropic.live_ids) == ("ok", frozenset({"m1", "m2"}))
    assert (gemini.status, gemini.live_ids) == ("ok", frozenset({"g1", "g2"}))
