"""Story 16.2 `kedro-test` gate -- the real httpx opener rehearsed over REAL HTTP (CAP-2/CAP-3).

`test_lasuite.py` proves the create/update/idempotent-skip/resume contract against an in-memory
`MockWagtail` -- no network. This module proves the SAME contract against a real
`tools/lasuite_bringup.py::build_httpx_opener()`, driven over a tiny stdlib `http.server` loopback
stub implementing `MockWagtail`'s same four routes + Bearer-token check. The stub runs on
`127.0.0.1` only (ephemeral port), started and torn down inside the fixture itself -- no external
network, no real credentials -- so this stays fully offline and belongs in the DEFAULT `kedro-test`
gate (no new pytest marker; see `spec-wagtail-corporate-brain/SPEC.md`'s resolved open question 3).

`tools/` is not a packaged/importable path, so `build_httpx_opener` is loaded via
`importlib.util.spec_from_file_location` rather than a normal `import` (mirrors how the bring-up
script is actually invoked -- `python tools/lasuite_bringup.py` -- never as a package)."""

from __future__ import annotations

import importlib.util
import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from pyforge.atlas.factory.lasuite import (
    LaSuiteClient,
    LaSuiteConfig,
    LaSuiteError,
    WikiSyncer,
)
from pyforge.atlas.factory.wiki import scaffold_wiki

_TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
_BRINGUP_PATH = _TOOLS_DIR / "lasuite_bringup.py"


def _load_bringup_module():
    """Load `tools/lasuite_bringup.py` the way it is really run -- NOT a package import."""
    spec = importlib.util.spec_from_file_location("lasuite_bringup", _BRINGUP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wiki_with_outputs(tmp_path: Path, pages: dict[str, str]):
    layout = scaffold_wiki(tmp_path / "wiki")
    for name, text in pages.items():
        layout.stage_path("outputs", name).write_text(text, encoding="utf-8")
    return layout


# --- loopback Wagtail stub --------------------------------------------------------------------


@dataclass
class _WagtailState:
    """Per-test server state -- a fresh instance every test, mirroring `MockWagtail`'s own
    per-test `docs`/`creates`/`updates` counters, plus `requests` (every attempted call,
    auth-rejected included -- what the wrong-token scenario asserts against)."""

    token: str
    docs: dict[str, dict] = field(default_factory=dict)
    next_id: int = 0
    creates: int = 0
    updates: int = 0
    requests: int = 0


def _make_handler(state: _WagtailState) -> type[BaseHTTPRequestHandler]:
    class _WagtailHandler(BaseHTTPRequestHandler):
        _state = state

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass  # silence stdlib's default per-request stderr logging in test output

        def _authorized(self) -> bool:
            return self.headers.get("Authorization") == f"Bearer {self._state.token}"

        def _read_json(self) -> dict | None:
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return None
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def _respond(self, status: int, body: Any) -> None:
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _route(self, method: str) -> None:
            self._state.requests += 1
            if not self._authorized():
                self._respond(401, {"detail": "unauthorized"})
                return
            path = self.path
            if method == "POST" and path == "/api/v1/documents/":
                payload = self._read_json()
                self._state.next_id += 1
                doc_id = str(self._state.next_id)
                self._state.docs[doc_id] = {"id": doc_id, **(payload or {})}
                self._state.creates += 1
                self._respond(201, self._state.docs[doc_id])
                return
            if method == "GET" and path == "/api/v1/documents/all/":
                self._respond(200, list(self._state.docs.values()))
                return
            if method == "PATCH" and path.startswith("/api/v1/documents/"):
                doc_id = path[len("/api/v1/documents/") :].rstrip("/")
                if doc_id not in self._state.docs:
                    self._respond(404, {"detail": "not found"})
                    return
                payload = self._read_json()
                self._state.docs[doc_id].update(payload or {})
                self._state.updates += 1
                self._respond(200, self._state.docs[doc_id])
                return
            if method == "GET" and path.startswith("/api/v1/documents/"):
                doc_id = path[len("/api/v1/documents/") :].rstrip("/")
                if doc_id in self._state.docs:
                    self._respond(200, self._state.docs[doc_id])
                else:
                    self._respond(404, {"detail": "not found"})
                return
            self._respond(400, {"detail": f"unrouted {method} {path}"})

        def do_POST(self) -> None:  # noqa: N802 - stdlib-mandated name
            self._route("POST")

        def do_GET(self) -> None:  # noqa: N802 - stdlib-mandated name
            self._route("GET")

        def do_PATCH(self) -> None:  # noqa: N802 - stdlib-mandated name
            self._route("PATCH")

    return _WagtailHandler


@dataclass
class _StubHandle:
    base_url: str
    state: _WagtailState


@pytest.fixture()
def wagtail_stub():
    """Start a fresh loopback stub (127.0.0.1, ephemeral port) for one test; always torn down."""
    state = _WagtailState(token="tok-1234")
    server = HTTPServer(("127.0.0.1", 0), _make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield _StubHandle(base_url=f"http://127.0.0.1:{server.server_port}", state=state)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


# --- the rehearsal -----------------------------------------------------------------------------


def test_live_round_trip_push_update_idempotent_resume(tmp_path: Path, wagtail_stub: _StubHandle):
    """Reproduces `test_round_trip_push_update_idempotent` +
    `test_mapping_persists_so_a_fresh_syncer_resumes`'s exact proven counts, but over REAL HTTP
    through the real `build_httpx_opener` -- proving the real opener, not a hand-rolled one,
    satisfies the mock-proven contract (CAP-2/CAP-3)."""
    bringup = _load_bringup_module()
    config = LaSuiteConfig(base_url=wagtail_stub.base_url, api_token=wagtail_stub.state.token)
    layout = _wiki_with_outputs(
        tmp_path,
        {
            "a.md": "---\ntitle: A\n---\nalpha\n",
            "b.md": "---\ntitle: B\n---\nbeta\n",
        },
    )

    syncer = WikiSyncer(LaSuiteClient(config, opener=bringup.build_httpx_opener()), layout)

    # 1) first push -> both CREATE.
    r1 = syncer.sync_all()
    assert sorted(r1.created) == ["a.md", "b.md"]
    assert r1.updated == [] and r1.skipped == []
    assert wagtail_stub.state.creates == 2 and wagtail_stub.state.updates == 0

    # 2) idempotent re-push (nothing changed) -> NO remote call at all.
    requests_before = wagtail_stub.state.requests
    r2 = syncer.sync_all()
    assert sorted(r2.skipped) == ["a.md", "b.md"]
    assert r2.created == [] and r2.updated == []
    assert wagtail_stub.state.requests == requests_before

    # 3) change one page -> exactly one UPDATE, no duplicate create.
    layout.stage_path("outputs", "a.md").write_text(
        "---\ntitle: A\n---\nalpha revised\n", encoding="utf-8"
    )
    r3 = syncer.sync_all()
    assert r3.updated == ["a.md"] and r3.skipped == ["b.md"] and r3.created == []
    assert wagtail_stub.state.creates == 2 and wagtail_stub.state.updates == 1

    # 4) a fresh syncer (mapping reloaded from the persisted sidecar) resumes -- 0 creates.
    fresh = WikiSyncer(LaSuiteClient(config, opener=bringup.build_httpx_opener()), layout)
    r4 = fresh.sync_all()
    assert sorted(r4.skipped) == ["a.md", "b.md"] and r4.created == []
    assert wagtail_stub.state.creates == 2  # no duplicate create


def test_wrong_bearer_token_returns_401_as_lasuite_error(
    tmp_path: Path, wagtail_stub: _StubHandle
):
    """The I/O matrix's second scenario: a token the stub doesn't recognize -> 401 -> a clear
    `LaSuiteError`, and exactly one attempted call (this suite's remote-call-counting discipline,
    mirroring `test_client_raises_clear_error_on_non_2xx`'s error-clarity assertion style)."""
    bringup = _load_bringup_module()
    bad_config = LaSuiteConfig(base_url=wagtail_stub.base_url, api_token="not-the-real-token")
    client = LaSuiteClient(bad_config, opener=bringup.build_httpx_opener())

    with pytest.raises(LaSuiteError) as exc:
        client.create_document("T", "body")
    assert "401" in str(exc.value)
    assert wagtail_stub.state.requests == 1
