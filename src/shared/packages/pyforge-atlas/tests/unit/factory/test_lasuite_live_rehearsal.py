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
script is actually invoked -- `pixi run -e pyforge-atlas python tools/lasuite_bringup.py` -- never
as a package).

`main()` is the half the attended DW-H3 session actually runs, and the half that has shipped a
false "success having contacted nothing" TWICE, so EVERY documented exit code (0/1/2/3/4) is
covered below, plus a dedicated regression test for the reachability probe."""

from __future__ import annotations

import importlib.util
import json
import threading
from collections.abc import Callable
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

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
_BRINGUP_PATH = _TOOLS_DIR / "lasuite_bringup.py"

#: Nothing ever listens here (port 9 = discard, unbound on this host): a base URL that is
#: syntactically fine and transport-dead, which is exactly the shape of the false success the
#: reachability probe exists to catch.
DEAD_BASE_URL = "http://127.0.0.1:9"


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
    auth-rejected and stray-verb included -- what the wrong-token scenario asserts against)."""

    token: str
    docs: dict[str, dict] = field(default_factory=dict)
    next_id: int = 0
    creates: int = 0
    updates: int = 0
    lists: int = 0
    requests: int = 0


def _make_handler(state: _WagtailState) -> type[BaseHTTPRequestHandler]:
    class _WagtailHandler(BaseHTTPRequestHandler):
        _state = state

        def log_message(self, format: str, *args: Any) -> None:
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
                self._state.lists += 1
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

        def do_POST(self) -> None:
            self._route("POST")

        def do_GET(self) -> None:
            self._route("GET")

        def do_PATCH(self) -> None:
            self._route("PATCH")

        # Every remaining verb routes too, so a stray-verb call is COUNTED by `state.requests`
        # and answered by the stub's own oracle (400 unrouted) rather than short-circuited by
        # stdlib's 501 before the stub ever sees it.
        def do_PUT(self) -> None:
            self._route("PUT")

        def do_DELETE(self) -> None:
            self._route("DELETE")

        def do_HEAD(self) -> None:
            self._route("HEAD")

        def do_OPTIONS(self) -> None:
            self._route("OPTIONS")

    return _WagtailHandler


@dataclass
class _StubHandle:
    base_url: str
    state: _WagtailState
    shutdown: Callable[[], None]  # idempotent; a test may stop the stub early (transport-error)


@pytest.fixture()
def wagtail_stub(monkeypatch):
    """Start a fresh loopback stub (127.0.0.1, ephemeral port) for one test; always torn down.

    Ambient proxy env is neutralized HERE, not in `build_httpx_opener`: `httpx.Client` defaults
    `trust_env=True` and applies NO localhost bypass, so with `HTTP_PROXY` exported every request
    below is handed to a proxy that cannot reach this ephemeral loopback port and the tests red in
    the default `kedro-test` gate (verified: `passed` clean vs `failed` proxied, stub recording 0
    hits). The gate's offline independence is the fixture's job; the opener keeps `trust_env=True`
    because the attended ENTERPRISE bring-up genuinely needs the proxy / `SSL_CERT_FILE` env chain.
    """
    for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")

    state = _WagtailState(token="tok-1234")
    server = HTTPServer(("127.0.0.1", 0), _make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    stopped = False

    def _shutdown() -> None:
        nonlocal stopped
        if stopped:
            return
        stopped = True
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        # A surviving thread means the stub is still bound to that port; a later test binding a
        # fresh ephemeral port would then race it. Fail loudly rather than continue silently.
        if thread.is_alive():
            raise RuntimeError("wagtail stub thread did not stop within 5s")

    try:
        yield _StubHandle(base_url=f"http://127.0.0.1:{server.server_port}", state=state, shutdown=_shutdown)
    finally:
        _shutdown()


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
    layout.stage_path("outputs", "a.md").write_text("---\ntitle: A\n---\nalpha revised\n", encoding="utf-8")
    r3 = syncer.sync_all()
    assert r3.updated == ["a.md"] and r3.skipped == ["b.md"] and r3.created == []
    assert wagtail_stub.state.creates == 2 and wagtail_stub.state.updates == 1

    # 4) a fresh syncer (mapping reloaded from the persisted sidecar) resumes -- 0 creates.
    fresh = WikiSyncer(LaSuiteClient(config, opener=bringup.build_httpx_opener()), layout)
    r4 = fresh.sync_all()
    assert sorted(r4.skipped) == ["a.md", "b.md"] and r4.created == []
    assert wagtail_stub.state.creates == 2  # no duplicate create


def test_wrong_bearer_token_returns_401_as_lasuite_error(wagtail_stub: _StubHandle):
    """The I/O matrix's second scenario: a token the stub doesn't recognize -> 401 -> a clear
    `LaSuiteError`, and exactly one attempted call (this suite's remote-call-counting discipline,
    mirroring `test_client_raises_clear_error_on_non_2xx`'s error-clarity assertion style)."""
    bringup = _load_bringup_module()
    bad_config = LaSuiteConfig(base_url=wagtail_stub.base_url, api_token="not-the-real-token")
    client = LaSuiteClient(bad_config, opener=bringup.build_httpx_opener())

    with pytest.raises(LaSuiteError) as exc:
        client.create_document("T", "body")
    msg = str(exc.value)
    # "HTTP 401", never a bare "401": the ephemeral port in the URL (34010-34019, 40100-40199,
    # 44010-44019, ...) can satisfy a bare substring test spuriously.
    assert "HTTP 401" in msg and "unauthorized" in msg
    assert wagtail_stub.state.requests == 1


# --- main(): the half the attended session actually runs ---------------------------------------


def test_main_exit_0_on_a_real_push_against_the_live_stub(
    tmp_path: Path, wagtail_stub: _StubHandle, monkeypatch, capsys
):
    """The attended checklist's step 4, executed: a populated `outputs/` tree + a live CMS ->
    exit 0, the counts printed, and the stub actually hit (a create AND the reachability probe)."""
    bringup = _load_bringup_module()
    _wiki_with_outputs(tmp_path, {"a.md": "---\ntitle: A\n---\nalpha\n"})
    monkeypatch.setenv("LASUITE_BASE_URL", wagtail_stub.base_url)
    monkeypatch.setenv("LASUITE_API_TOKEN", wagtail_stub.state.token)
    monkeypatch.setenv("ATLAS_WIKI_ROOT", str(tmp_path / "wiki"))

    assert bringup.main() == 0
    out = capsys.readouterr().out
    assert "created=1 updated=0 skipped=0" in out
    assert wagtail_stub.base_url in out  # the operator can see what it talked to
    assert wagtail_stub.state.creates == 1
    assert wagtail_stub.state.lists == 1  # the reachability probe genuinely reached the CMS
    assert wagtail_stub.state.requests == 2


def test_main_exit_2_when_an_all_skipped_run_never_reaches_the_cms(
    tmp_path: Path, wagtail_stub: _StubHandle, monkeypatch
):
    """Regression test for the reachability probe (spec review pass 3).

    `SyncReport.skipped` means "unchanged -- NO remote call made", so an all-skipped re-run
    contacts the CMS ZERO times while still satisfying both the outputs/ pre-check and the
    non-zero-total post-check. Before the probe, re-running against a DEAD base URL with a
    populated `.lasuite_sync.json` printed `created=0 updated=0 skipped=1` and exited **0** with a
    success banner. It must now exit 2. Without this test the guard rots silently -- every
    all-skipped run's report line looks identical to a pass."""
    bringup = _load_bringup_module()
    _wiki_with_outputs(tmp_path, {"a.md": "---\ntitle: A\n---\nalpha\n"})
    monkeypatch.setenv("LASUITE_API_TOKEN", wagtail_stub.state.token)
    monkeypatch.setenv("ATLAS_WIKI_ROOT", str(tmp_path / "wiki"))

    # 1) a real push against the live stub -- writes the sidecar, exit 0.
    monkeypatch.setenv("LASUITE_BASE_URL", wagtail_stub.base_url)
    assert bringup.main() == 0

    # 2) the SAME sidecar, re-run against a dead endpoint -- every page skips, so the sync itself
    # makes no call and reports a non-zero total. Only the probe can tell this apart from a pass.
    monkeypatch.setenv("LASUITE_BASE_URL", DEAD_BASE_URL)
    assert bringup.main() == 2


def test_main_refuses_to_report_success_when_nothing_was_synced(tmp_path: Path, wagtail_stub: _StubHandle, monkeypatch):
    """A bring-up that pushed ZERO pages must never exit 0 -- the attended checklist's step 8
    closes DW-H3 on this script's word. Both guards: a wiki root with no `outputs/` (must exit 3
    WITHOUT creating anything -- a typo'd `ATLAS_WIKI_ROOT` fails loudly rather than silently
    scaffolding a fresh empty tree at the wrong path), and a scaffolded-but-empty `outputs/`
    (must exit 3 having made no request at all)."""
    bringup = _load_bringup_module()
    monkeypatch.setenv("LASUITE_BASE_URL", wagtail_stub.base_url)
    monkeypatch.setenv("LASUITE_API_TOKEN", wagtail_stub.state.token)

    # (a) pre-check: a typo'd root -- exit 3, and NOTHING is created on disk.
    typo_root = tmp_path / "typo-wiki"
    monkeypatch.setenv("ATLAS_WIKI_ROOT", str(typo_root))
    assert bringup.main() == 3
    assert not typo_root.exists()

    # (b) post-check: the root exists and is scaffolded, but outputs/ holds no pages -- the sync
    # reports created=0 updated=0 skipped=0, having made zero HTTP calls. Still exit 3.
    empty_root = tmp_path / "empty-wiki"
    scaffold_wiki(empty_root)
    monkeypatch.setenv("ATLAS_WIKI_ROOT", str(empty_root))
    assert bringup.main() == 3
    assert wagtail_stub.state.requests == 0


def test_main_exits_2_on_a_transport_failure(tmp_path: Path, wagtail_stub: _StubHandle, monkeypatch):
    """With pages to push but the server gone, the httpx transport error must surface as a clean
    `LaSuiteError` -> exit 2, never a raw `httpx` traceback (which would exit 1 and collide with
    the documented "unconfigured" code)."""
    bringup = _load_bringup_module()
    _wiki_with_outputs(tmp_path, {"a.md": "---\ntitle: A\n---\nalpha\n"})
    monkeypatch.setenv("LASUITE_BASE_URL", wagtail_stub.base_url)
    monkeypatch.setenv("LASUITE_API_TOKEN", wagtail_stub.state.token)
    monkeypatch.setenv("ATLAS_WIKI_ROOT", str(tmp_path / "wiki"))

    wagtail_stub.shutdown()  # nothing listening on that port any more
    assert bringup.main() == 2


def test_main_exits_2_on_a_malformed_base_url(tmp_path: Path, wagtail_stub: _StubHandle, monkeypatch):
    """A typo'd `LASUITE_BASE_URL` is the likeliest attended-session operator error. It must be a
    clean exit 2, never the raw `httpx.InvalidURL` traceback that exits 1 and collides with the
    documented "unconfigured" code (`InvalidURL` is NOT an `httpx.HTTPError` subclass)."""
    bringup = _load_bringup_module()
    _wiki_with_outputs(tmp_path, {"a.md": "---\ntitle: A\n---\nalpha\n"})
    monkeypatch.setenv("LASUITE_BASE_URL", "http://[::bad")
    monkeypatch.setenv("LASUITE_API_TOKEN", wagtail_stub.state.token)
    monkeypatch.setenv("ATLAS_WIKI_ROOT", str(tmp_path / "wiki"))

    assert bringup.main() == 2


def test_main_exits_1_when_unconfigured(tmp_path: Path, monkeypatch):
    """Neither env var set -> exit 1, and (unlike exit 3) it never even resolves a wiki root."""
    bringup = _load_bringup_module()
    monkeypatch.delenv("LASUITE_BASE_URL", raising=False)
    monkeypatch.delenv("LASUITE_API_TOKEN", raising=False)
    assert bringup.main() == 1

    # a PARTIAL config is still unconfigured (resolve_lasuite_config's both-or-nothing contract).
    monkeypatch.setenv("LASUITE_BASE_URL", "http://127.0.0.1:1")
    assert bringup.main() == 1


def test_main_exits_4_on_an_unreadable_wiki_page(tmp_path: Path, wagtail_stub: _StubHandle, monkeypatch):
    """A non-UTF-8 `.md` raises `UnicodeDecodeError` out of `sync_all()` -- neither a
    `LaSuiteError` nor anything the exit-2 path should claim. It must exit 4, and (since
    `UnicodeDecodeError` IS a `ValueError` subclass) must not be captured by the exit-2
    `ValueError` handler that covers the httpx client constructor."""
    bringup = _load_bringup_module()
    layout = scaffold_wiki(tmp_path / "wiki")
    layout.stage_path("outputs", "broken.md").write_bytes(b"\xff\xfe not utf-8\n")
    monkeypatch.setenv("LASUITE_BASE_URL", wagtail_stub.base_url)
    monkeypatch.setenv("LASUITE_API_TOKEN", wagtail_stub.state.token)
    monkeypatch.setenv("ATLAS_WIKI_ROOT", str(tmp_path / "wiki"))

    assert bringup.main() == 4
