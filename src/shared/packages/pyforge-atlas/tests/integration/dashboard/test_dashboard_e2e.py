"""Playwright-based browser-level E2E tests for the Vizro dashboard (FR-9)."""

from __future__ import annotations

import multiprocessing
import os
import re
import shutil
import socket
import time

import pytest
from playwright.sync_api import expect, sync_playwright
from vizro import Vizro

from pyforge.atlas.dashboard import app
from pyforge.atlas.dashboard.app import build_dashboard


def get_free_port() -> int:
    """Find a free port on localhost."""
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_for_server(port: int, proc: multiprocessing.Process, timeout: float = 60.0) -> None:
    """Block until the server accepts connections on `port`.

    Vizro builds every page before werkzeug binds the socket, so how long that
    takes varies with the machine. Polling instead of sleeping a fixed interval
    keeps the fixture from handing out a URL that is not listening yet.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not proc.is_alive():
            raise RuntimeError(f"dashboard server exited (code {proc.exitcode}) before binding port {port}")
        with socket.socket() as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError(f"dashboard server did not bind port {port} within {timeout:.0f}s")


def run_vizro_server(
    port: int, data_root: str, stamp: str, now: int, sprint_path: str, epics_path: str, specs_dir: str
) -> None:
    """Target function for background server process."""
    os.environ["PORT"] = str(port)
    dashboard = build_dashboard(
        build_stamp=stamp,
        data_root=data_root,
        now=now,
        sprint_status_path=sprint_path,
        epics_path=epics_path,
        specs_dir=specs_dir,
        reset=True,
    )
    Vizro().build(dashboard).run(port=port, debug=False, use_reloader=False)


@pytest.fixture()
def dashboard_server(
    feedstock_health_parquet, package_maintainers_parquet, packages_parquet, bmad_fixture, tmp_path_factory
):
    """Fixture to spawn the Vizro server in a background process for the module duration."""
    tmp_path = tmp_path_factory.mktemp("dashboard_e2e")

    # 1. Structure the BSL parquets directory
    data_root = tmp_path / "data"

    fh_dir = data_root / "primary/core_feedstock_health"
    fh_dir.mkdir(parents=True)
    shutil.copy(feedstock_health_parquet, fh_dir / "core_feedstock_health.parquet")

    pm_dir = data_root / "intermediate/vcs_package_maintainers"
    pm_dir.mkdir(parents=True)
    shutil.copy(package_maintainers_parquet, pm_dir / "vcs_package_maintainers.parquet")

    pkg_dir = data_root / "primary/semantic_packages"
    pkg_dir.mkdir(parents=True)
    shutil.copy(packages_parquet, pkg_dir / "semantic_packages.parquet")

    # 2. Extract paths from the BMAD fixture
    sprint_path = bmad_fixture["sprint"]
    epics_path = bmad_fixture["epics"]
    specs_dir = bmad_fixture["specs"]

    # 3. Find a free port
    port = get_free_port()

    # 4. Start process
    now = 1_700_000_000
    stamp = "2026-07-18T12:00:00Z"

    proc = multiprocessing.Process(
        target=run_vizro_server,
        args=(port, str(data_root), stamp, now, sprint_path, epics_path, specs_dir),
    )
    proc.start()

    # Wait for the server to actually bind, however long the Vizro build takes
    wait_for_server(port, proc)

    yield f"http://localhost:{port}"

    # Clean up background process
    proc.terminate()
    proc.join()


def test_dashboard_e2e_navigation_and_rendering(dashboard_server):
    """Playwright-based visual and interactive validation of pages (FR-9)."""
    with sync_playwright() as p:
        # Launch headless browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Open the home page (feedstock-health is the first page)
        page.goto(dashboard_server)

        # Assert page title or header
        expect(page).to_have_title(re.compile("cf_atlas Factory"))

        # 2. Check feedstock-health page card is visible and has correct content (expect handles wait)
        about_card = page.locator("#feedstock-health--about")
        expect(about_card).to_contain_text("Ports the feedstock-health read CLI")

        # 3. Verify AgGrid is rendered and contains feedstock data
        grid_fh = page.locator("#feedstock-health--grid")
        expect(grid_fh).to_be_visible()
        expect(grid_fh).to_contain_text("alpha")
        expect(grid_fh).to_contain_text("beta")
        expect(grid_fh).to_contain_text("gamma")

        # 4. Navigate to "My Feedstocks" page
        page.goto(f"{dashboard_server}/my-feedstocks")

        # Verify page content and grid are visible (expect handles wait)
        about_my = page.locator("#my-feedstocks--about")
        expect(about_my).to_contain_text("Ports the my-feedstocks read CLI")

        grid_my = page.locator("#my-feedstocks--grid")
        expect(grid_my).to_be_visible()
        expect(grid_my).to_contain_text("alice")
        expect(grid_my).to_contain_text("bob")

        # 5. Navigate to "Factory Status" page
        page.goto(f"{dashboard_server}/factory-status")

        # Verify that factory status page renders its specific card and timestamp (AD-17)
        stamp_card = page.locator("#factory-status--stamp")
        expect(stamp_card).to_contain_text("Build timestamp (AD-17):")
        expect(stamp_card).to_contain_text("2026-07-18T12:00:00Z")

        grid_fs = page.locator("#factory-status--grid")
        expect(grid_fs).to_be_visible()
        expect(grid_fs).to_contain_text("d1-define-the-boring-semantic-layer-bsl-models")
        expect(grid_fs).to_contain_text("done")

        # 6. Navigate to "Staleness Report" page (a BSL-wired shell page)
        page.goto(f"{dashboard_server}/staleness-report")

        # Verify BSL-wired shell description and AgGrid
        about_st = page.locator("#staleness-report--about")
        expect(about_st).to_contain_text("Wired to build_packages_model.staleness_age_days")

        grid_st = page.locator("#staleness-report--grid")
        expect(grid_st).to_be_visible()

        # 7. Close browser
        browser.close()


def test_dashboard_pages_semantic_nav_and_aria(dashboard_server):
    """DW-D2-3 residual (Story 20.5): the §2.1 semantic-HTML/ARIA browser-agent
    navigation check — a browser-agent must be able to enumerate every page in
    ``PAGE_INVENTORY`` via real, accessible-name-bearing anchors and land on a
    deterministic, agent-legible heading + content region for each, with NO
    client-side error.

    What this asserts as REAL (verified against the rendered DOM, never assumed):
      * exactly one real ``<a href>`` navigation link per ``PAGE_INVENTORY`` entry
        ``PAGE_INVENTORY`` entry, in its deterministic order) — genuine semantic
        HTML anchors, not JS-only click handlers a scraper/browser-agent could miss;
      * each link's accessible name (its text content) equals that page's title
        EXACTLY — the accessible name IS the page identity, never generic
        boilerplate ("Page 1", "Link") a browser-agent would have to guess at;
      * the accordion toggle exposes real ARIA state (``aria-expanded``) — the one
        genuinely interactive nav control on this page;
      * navigating to EVERY page (not just the 3 the rest of this file drives) by
        its own href renders a deterministic ``<h2 id="page-title">`` matching that
        page's title, and the page's own legibility Card/stamp Card is present.

    What this deliberately does NOT assert (a real, documented gap, not silently
    papered over per the ARIA_CHECK_FAILS edge case's "surfaced, never swallowed"
    contract): Vizro's shipped page-select control is a ``<div>``-based accordion,
    not a native ``<nav>``/``role="navigation"`` landmark, and page content sits in
    a plain ``<div>``, not a ``<main>``/``role="main"`` landmark. That is a
    pre-existing Vizro/dash-bootstrap-components framework limitation outside a
    single recipe-dashboard-pages story's surgical-change scope (patching Vizro's
    own component templates is a framework-level change, not a page port) —
    recorded as a residual in the deferred-work-ledger, not asserted away here.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dashboard_server)

        # -- the nav accordion carries real ARIA state on its one interactive control --
        toggle = page.locator("#nav-panel button.accordion-button")
        expect(toggle).to_have_attribute("aria-expanded", "true")

        # -- every page has a real, accessible-name-bearing anchor, in deterministic order --
        links = page.locator("#nav-panel a.accordion-item-link")
        expect(links).to_have_count(len(app.PAGE_INVENTORY))
        got = [(links.nth(i).get_attribute("href"), links.nth(i).inner_text()) for i in range(len(app.PAGE_INVENTORY))]
        expected = [
            ("/" if i == 0 else f"/{page_def.id}", page_def.title) for i, page_def in enumerate(app.PAGE_INVENTORY)
        ]
        assert got == expected, f"nav link href/accessible-name mismatch: {got} != {expected}"

        # -- every page is independently reachable + renders a deterministic heading --
        for page_def in app.PAGE_INVENTORY:
            path = "/" if page_def is app.PAGE_INVENTORY[0] else f"/{page_def.id}"
            page.goto(f"{dashboard_server}{path}")
            heading = page.locator("h2#page-title")
            expect(heading).to_contain_text(page_def.title)
            content_id = f"{page_def.id}--stamp" if page_def.kind == "factory" else f"{page_def.id}--about"
            expect(page.locator(f"#{content_id}")).to_be_visible()
            # no Dash client-side error overlay leaked onto the rendered page.
            assert (
                page.locator("._dash-error-menu, #_dash-global-error-container .dash-fe-error__title").count() == 0
            ), f"page {page_def.id} raised a client-side error"

        browser.close()
