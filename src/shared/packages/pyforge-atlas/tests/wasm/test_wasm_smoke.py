"""``wasm-smoke`` gate (Story G1, FR-14) — headless client-side load-and-query.

This is the Wave-G FIRST deliverable (AD-11): a Playwright HEADLESS Chromium load
against the built, backend-free DuckDB-WASM artifact. It proves the load-bearing G1
acceptance criterion — **the dashboard's read surface loads and its query runs
CLIENT-SIDE in the browser with NO backend** — by actually driving a browser, not by
static analysis.

What it does (genuinely, not hollowly):

  * serves ``wasm/build/`` (produced by ``wasm-build``) over a loopback static host —
    a dumb file server, NOT an application backend; it answers only static-asset GETs;
  * launches the pre-provisioned headless Chromium (``PLAYWRIGHT_BROWSERS_PATH``);
  * **blocks every non-loopback request** and asserts none was attempted — so a page
    that secretly reached a CDN / API / ``extensions.duckdb.org`` would FAIL the gate
    (this is the offline + no-backend proof, AD-21);
  * waits for the page's ``#status`` to reach ``ready`` OR ``error`` and asserts it is
    ``ready`` — an in-browser exception (blank page, failed wasm, empty result) flips
    the status to ``error`` and FAILS the gate rather than passing trivially;
  * asserts the CLIENT-SIDE query's result — the exact ``ci_red`` count and the
    per-feedstock rows — matches the D1 ``feedstock-health`` semantics
    (``ci_red = ci_status IN ('failure','error')``) over the seed dataset.

Skip-guards are narrow and DISTINCT so a skip can never masquerade as a pass:
  * Playwright not importable → skip (env lacks the binding);
  * no Chromium executable under the browsers path → skip (browser unavailable);
  * ``wasm/build/`` not present → skip with "run wasm-build first".
None of these is the browser-ran-but-query-failed case, which always FAILS.

The full Vizro-AI dashboard RENDERED inside Pyodide is the heavier half and is
DEFERRED — see ``implementation-artifacts/deferred-work.md`` (DW-G1). G1 delivers the
zero-backend client-side QUERY surface (the load-bearing "no backend" claim) with a
genuine DuckDB-WASM engine.
"""

from __future__ import annotations

import glob
import http.server
import os
import socketserver
import threading
from pathlib import Path
from urllib.parse import urlparse

import pytest

WASM_DIR = Path(__file__).resolve().parents[2] / "wasm"
BUILD_DIR = WASM_DIR / "build"

# Seed dataset (wasm/data/feedstock_health.csv): ci_red = ci_status IN ('failure','error').
# alpha=failure, beta=success, gamma=error, delta=success, epsilon=failure  -> 3 red.
EXPECTED_RED_COUNT = 3
EXPECTED_ROWS = {
    "alpha": True,
    "beta": False,
    "gamma": True,
    "delta": False,
    "epsilon": True,
}


def _chromium_executable() -> str | None:
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    for pat in (
        f"{base}/chromium-*/chrome-linux/chrome",
        f"{base}/chromium_headless_shell-*/chrome-linux/headless_shell",
    ):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


@pytest.fixture(scope="module")
def playwright_sync():
    pytest.importorskip("playwright", reason="playwright not installed in this env")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


def _wasm_required() -> bool:
    """When set (CI, or an explicit WASM_SMOKE_REQUIRED=1), a missing browser / unbuilt
    artifact is a FAILURE, not a skip — so a misconfigured CI cannot pass this gate having
    verified nothing (Reviewer-A skip-to-green). Locally it stays a skip for convenience."""
    return bool(os.environ.get("WASM_SMOKE_REQUIRED") or os.environ.get("CI"))


def _skip_or_fail(reason: str) -> None:
    if _wasm_required():
        pytest.fail(f"WASM_SMOKE_REQUIRED but the gate could not run: {reason}")
    pytest.skip(reason)


@pytest.fixture(scope="module")
def static_server():
    """Serve wasm/build/ on a loopback port — a static file host, not a backend."""
    if not (BUILD_DIR / "index.html").exists():
        _skip_or_fail(
            "wasm artifact not built — run `pixi run -e local-recipes wasm-build` first "
            f"(expected {BUILD_DIR / 'index.html'})"
        )

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(BUILD_DIR), **kw)

        def log_message(self, *a):  # keep the test output quiet
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


def test_wasm_smoke_client_side_query(playwright_sync, static_server):
    exe = _chromium_executable()
    if exe is None:
        _skip_or_fail("no Chromium executable under PLAYWRIGHT_BROWSERS_PATH")

    external_requests: list[str] = []
    console_errors: list[str] = []

    browser = playwright_sync.chromium.launch(headless=True, executable_path=exe)
    try:
        page = browser.new_page()
        page.on(
            "console",
            lambda m: console_errors.append(m.text) if m.type == "error" else None,
        )

        # Block + record every non-loopback request. If the artifact secretly needed
        # a CDN / API / extensions.duckdb.org, it would show up here and be aborted,
        # flipping #status to error -> the gate FAILS. This is the offline/no-backend proof.
        def _route(route):
            url = route.request.url
            # Parse the HOST (not a substring): "http://127.0.0.1.evil.example" contains the
            # substring "127.0.0.1" but is NOT loopback (Reviewer-A NIT).
            host_ok = urlparse(url).hostname in ("127.0.0.1", "localhost", "::1")
            if host_ok or url.startswith("data:") or url.startswith("blob:"):
                route.continue_()
            else:
                external_requests.append(url)
                route.abort()

        page.route("**/*", _route)

        page.goto(f"{static_server}/index.html", wait_until="load")

        # Wait for the query to resolve to EITHER ready or error, then require ready.
        # (Waiting for "ready" only would let an error state hang until timeout; this
        # fails fast and surfaces the real error text.)
        page.wait_for_selector('#status[data-state="ready"], #status[data-state="error"]',
                               timeout=60_000)
        state = page.get_attribute("#status", "data-state")
        status_text = page.inner_text("#status")
        assert state == "ready", (
            f"in-browser query did not reach ready state: status={status_text!r}; "
            f"console_errors={console_errors}; external_requests={external_requests}"
        )

        # No external network was attempted at runtime (offline / no backend, AD-21).
        assert external_requests == [], f"unexpected external requests: {external_requests}"

        # The engine actually ran (guards against a hollow page that sets ready blindly).
        engine = page.inner_text("#engine")
        assert "DuckDB-WASM" in engine, f"engine marker missing: {engine!r}"

        # Assert the CLIENT-SIDE query RESULT.
        red_count = page.inner_text("#red-count").strip()
        assert red_count == str(EXPECTED_RED_COUNT), (
            f"ci_red count from the in-browser query = {red_count!r}, "
            f"expected {EXPECTED_RED_COUNT}"
        )

        rows = page.query_selector_all("#result-body tr")
        assert len(rows) == len(EXPECTED_ROWS), (
            f"expected {len(EXPECTED_ROWS)} result rows, got {len(rows)} "
            "(empty/partial result => FAIL, never a silent pass)"
        )
        got = {
            r.get_attribute("data-feedstock"): r.get_attribute("data-ci-red") == "1"
            for r in rows
        }
        assert got == EXPECTED_ROWS, f"per-feedstock ci_red mismatch: {got}"
    finally:
        browser.close()
