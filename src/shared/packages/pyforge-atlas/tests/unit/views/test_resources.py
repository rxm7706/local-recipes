"""Story 14.4 (CAP-4) -- render-profile introspection regression tests.

Covers the intent-contract's AIRGAPPED_MODE_INTROSPECTION / CDN_MODE_INTROSPECTION rows (unit
tests over every one of Bokeh's resource modes, via ``resources.current_mode()``/
``is_airgapped()``, plus the unset/default case) and its DEFAULT_PROFILE_LIVE /
CDN_PROFILE_NEGATIVE_CONTROL rows (two real-live-server HTTP-level regression tests -- the CDN
negative control proves the default-profile test isn't a tautology, i.e. it's capable of
failing).

Empirically verified against this env's Bokeh 3.9.2 (see ``resources.py``'s module docstring):
``bokeh.settings.settings.resources`` re-resolves ``BOKEH_RESOURCES`` fresh on every call --
neither ``PrioritizedSetting`` itself nor a live ``bokeh.server.server.Server`` (which calls
``settings.resources(default="server")`` per-request, not once at construction time) caches a
resolved value, so a plain ``monkeypatch.setenv``/``delenv`` is picked up immediately with no
``unset_value()`` needed. Confirmed directly: a real ``build_live_server`` fetched under
unset/``BOKEH_RESOURCES=server``/``BOKEH_RESOURCES=cdn`` produced the expected same-origin vs.
``cdn.bokeh.org`` script sources in every case.
"""

from __future__ import annotations

import threading
import time
import urllib.request

import pytest
from pyforge.atlas.views import cli_bridge, resources
from pyforge.atlas.views.live import build_live_server
from pyforge.atlas.views.registry import get_view
from pyforge.atlas.views.render import render_rows

# Every non-"cdn" Bokeh resource mode -- all air-gap-safe (no network fetch to an external
# host). Combined with "cdn" (tested separately, below) and the unset/default case, this
# covers the full ResourcesMode set the story's I/O matrix calls for.
AIRGAPPED_RESOURCE_MODES = (
    "server",
    "server-dev",
    "inline",
    "relative",
    "relative-dev",
    "absolute",
    "absolute-dev",
)


def _loaded_module(view, db_path, monkeypatch):
    """Established technique (test_live.py) -- load the real CLI module and monkeypatch its
    DB_PATH so a live server's modify_doc callback queries the hermetic fixture db."""
    module = cli_bridge.load_cli_module(
        view.script, scripts_dir=cli_bridge.default_scripts_dir()
    )
    monkeypatch.setattr(module, "DB_PATH", db_path)
    return module


def _fetch_live_page(view) -> str:
    """Start a real ``build_live_server`` on an OS-assigned ephemeral port, fetch its served
    page via a plain HTTP GET (polling until the server accepts connections), and tear the
    server down -- mirrors test_live.py's
    ``test_live_session_round_trip_via_a_real_websocket_connection`` server lifecycle and its
    "skip if the sandbox forbids a socket bind" escape hatch, but only needs an HTTP fetch (no
    WebSocket session)."""
    try:
        server = build_live_server(views=(view,), port=0)
    except (OSError, PermissionError) as exc:
        pytest.skip(f"sandbox forbids binding a localhost TCP socket: {exc}")

    server.start()
    thread = threading.Thread(target=server.io_loop.start, daemon=True)
    thread.start()
    try:
        url = f"http://localhost:{server.port}/{view.name}"
        last_exc: Exception | None = None
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=1.0) as response:
                    return response.read().decode("utf-8")
            except Exception as exc:  # server not accepting connections yet
                last_exc = exc
                time.sleep(0.1)
        raise AssertionError(f"could not fetch the live server's page: {last_exc}")
    finally:
        server.io_loop.add_callback(server.io_loop.stop)
        thread.join(timeout=5)
        server.stop()


@pytest.mark.parametrize("mode", AIRGAPPED_RESOURCE_MODES)
def test_current_mode_and_is_airgapped_for_every_airgapped_resource_mode(mode, monkeypatch):
    """AIRGAPPED_MODE_INTROSPECTION: is_airgapped() is True for every one of Bokeh's non-cdn
    resource modes."""
    monkeypatch.setenv("BOKEH_RESOURCES", mode)

    assert resources.current_mode() == mode
    assert resources.is_airgapped() is True


def test_current_mode_and_is_airgapped_for_cdn(monkeypatch):
    """CDN_MODE_INTROSPECTION: is_airgapped() is False when BOKEH_RESOURCES=cdn."""
    monkeypatch.setenv("BOKEH_RESOURCES", "cdn")

    assert resources.current_mode() == "cdn"
    assert resources.is_airgapped() is False


def test_current_mode_defaults_to_server_when_bokeh_resources_is_unset(monkeypatch):
    """The unset case: with no BOKEH_RESOURCES set at all, current_mode() falls back to its
    own "server" default (bokeh/server/tornado.py's exact call/default) -- never the
    library-wide "cdn" default the PrioritizedSetting itself declares."""
    monkeypatch.delenv("BOKEH_RESOURCES", raising=False)

    assert resources.current_mode() == "server"
    assert resources.is_airgapped() is True


def test_default_profile_live_server_page_has_no_cdn_reference(atlas_db_path, monkeypatch):
    """DEFAULT_PROFILE_LIVE: no BOKEH_RESOURCES set; a real live server's served page HTML
    contains zero cdn.bokeh.org references -- every Bokeh JS/CSS asset URL is same-origin."""
    monkeypatch.delenv("BOKEH_RESOURCES", raising=False)
    view = get_view("staleness-report")
    _loaded_module(view, atlas_db_path, monkeypatch)

    body = _fetch_live_page(view)

    assert "cdn.bokeh.org" not in body
    assert "/static/js/" in body


def test_cdn_profile_negative_control_live_server_page_has_a_cdn_reference(
    atlas_db_path, monkeypatch
):
    """CDN_PROFILE_NEGATIVE_CONTROL: BOKEH_RESOURCES=cdn set before the server starts -- the
    served page's HTML DOES contain cdn.bokeh.org, proving the DEFAULT_PROFILE_LIVE test above
    isn't a tautology (the assertion is actually capable of failing)."""
    monkeypatch.setenv("BOKEH_RESOURCES", "cdn")
    view = get_view("staleness-report")
    _loaded_module(view, atlas_db_path, monkeypatch)

    body = _fetch_live_page(view)

    assert "cdn.bokeh.org" in body


def test_static_fragment_stays_cdn_free_even_under_an_explicit_cdn_profile(
    atlas_db_path, monkeypatch
):
    """STATIC_FRAGMENT_NO_CDN, exercised dynamically rather than as a structural pin alone
    (review-pass patch): test_render.py's FORBIDDEN_MARKERS check never varies BOKEH_RESOURCES,
    so it only ever proves the claim under whatever value happens to be ambient in the test
    environment. This test sets BOKEH_RESOURCES=cdn explicitly -- the one setting that DOES
    make the live path reference cdn.bokeh.org (see the negative control above) -- and confirms
    the static path stays unaffected, because bokeh.embed.components() never reads
    BOKEH_RESOURCES or emits any asset URL at all; only a full-page wrapper (none exists in
    this package) would ever consult the render profile for the static path."""
    monkeypatch.setenv("BOKEH_RESOURCES", "cdn")
    view = get_view("staleness-report")
    module = _loaded_module(view, atlas_db_path, monkeypatch)
    rows = cli_bridge.call_query(module, **view.query_kwargs)

    script, div = render_rows(view, rows)

    assert "cdn.bokeh.org" not in script
    assert "cdn.bokeh.org" not in div
