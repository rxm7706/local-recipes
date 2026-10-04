"""Playwright-based browser-level E2E tests for the Vizro dashboard (FR-9)."""

from __future__ import annotations

import multiprocessing
import os
import re
import shutil
import socket
import time
from pathlib import Path

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


FIXTURE_DATA_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "data"


@pytest.fixture()
def dashboard_server(bmad_fixture, tmp_path_factory):
    """Spawn the Vizro server over a data root materialized from the STATIC fixture
    Parquet tree (``tests/fixtures/data/``, Story 27.3 closing DW-FU-20-5-4).

    That tree already mirrors the catalog's own ``data/`` layout, so materializing
    the root is one copy and every page resolves its backing file exactly as it
    would against a real ``data/``. Before this, the e2e suite hand-placed three
    tmp files and every other page was checked against an absent file only.
    """
    tmp_path = tmp_path_factory.mktemp("dashboard_e2e")

    # 1. Materialize the data root from the static fixture Parquet.
    data_root = tmp_path / "data"
    shutil.copytree(FIXTURE_DATA_ROOT, data_root, ignore=shutil.ignore_patterns("*.py", "*.md", "__pycache__"))

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


# The row each grounded page must actually show, keyed by page id. "Grounded"
# is PageDef.kind == "grounded-data" -- the pages whose backing dataset is
# migrated today, so against the static fixture data root every one of them
# has rows (Story 27.3, DW-FU-20-5-4: the data-present visual pass).
GROUNDED_PAGE_EVIDENCE = {
    "feedstock-health": ("alpha", "beta", "gamma"),
    "my-feedstocks": ("alice", "bob", "carol"),
    "estate-cache": ("sku-alpha", "sku-beta", "sku-gamma"),
}


def test_every_grounded_page_renders_rows_on_the_fixture_data_root(dashboard_server):
    """DW-FU-20-5-4: the data-present pass. Against a data root materialized from
    the static fixture Parquet, every ``grounded-data`` page renders its rows in
    the browser -- not an empty grid, and not a page the suite never visited."""
    grounded = [p for p in app.PAGE_INVENTORY if p.kind == "grounded-data"]
    assert {p.id for p in grounded} == set(GROUNDED_PAGE_EVIDENCE), (
        "a grounded page was added or removed without extending this gate: "
        f"{sorted(p.id for p in grounded)}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            for page_def in grounded:
                page.goto(f"{dashboard_server}/{page_def.id}")
                grid = page.locator(f"#{page_def.id}--grid")
                expect(grid).to_be_visible()
                for cell in GROUNDED_PAGE_EVIDENCE[page_def.id]:
                    expect(grid).to_contain_text(cell)
        finally:
            browser.close()


def test_declared_controls_render_against_real_rows(dashboard_server):
    """DW-FU-20-5: a page whose ``PageDef`` declares a filter and a chart really
    builds both once its backing Parquet has rows. ``distribution-breakdown``
    declares both (DESIGN.md § 3.8) and the fixture tree carries its dataset."""
    page_def = next(p for p in app.PAGE_INVENTORY if p.id == "distribution-breakdown")
    assert page_def.filters == ("facet",)
    assert page_def.chart is not None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{dashboard_server}/{page_def.id}")
            expect(page.locator("#distribution-breakdown--filter-facet")).to_be_visible()
            expect(page.locator("#distribution-breakdown--chart")).to_be_visible()
            grid = page.locator("#distribution-breakdown--grid")
            expect(grid).to_contain_text("linux-64")
        finally:
            browser.close()


def test_the_scan_pages_offer_a_path_input_and_a_submit_control(dashboard_server):
    """DW-FU-20-5-2: the two ``live-scan-artifact`` pages carry the path field and
    the Run button whose action runs the scan through ``pyforge.core.process``.
    The scan itself is not driven here (it shells to another pixi env); the unit
    gate in ``tests/unit/test_scan_submit.py`` drives the submit path end to end."""
    scan_pages = [p for p in app.PAGE_INVENTORY if p.kind == "live-scan-artifact"]
    assert {p.id for p in scan_pages} == {"scan-project", "env-inspect"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            for page_def in scan_pages:
                page.goto(f"{dashboard_server}/{page_def.id}")
                expect(page.locator(f"#{page_def.id}--path")).to_be_visible()
                expect(page.locator(f"#{page_def.id}--submit")).to_be_visible()
                expect(page.locator(f"#{page_def.id}--status")).to_contain_text("No scan submitted yet")
        finally:
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
        page's title, and the page's own legibility Card/stamp Card is present;
      * the page select sits in a ``navigation`` landmark and the page content in a
        ``main`` landmark, on every page — Vizro 0.1.60 ships neither, so
        ``app.LandmarkDashboard`` re-tags its two containers and this is the gate
        on that (Story 27.3, DW-FU-20-5-3).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(dashboard_server)

        # -- the nav accordion carries real ARIA state on its one interactive control --
        toggle = page.locator("#nav-panel button.accordion-button")
        expect(toggle).to_have_attribute("aria-expanded", "true")

        # -- the two landmarks a browser agent jumps between --
        navigation = page.locator("[role='navigation']")
        expect(navigation).to_have_count(1)
        expect(navigation).to_have_attribute("aria-label", "Dashboard pages")
        # The page select really is INSIDE the navigation landmark.
        expect(navigation.locator("#nav-panel")).to_have_count(1)
        main = page.locator("[role='main']")
        expect(main).to_have_count(1)
        expect(main.locator("h2#page-title")).to_have_count(1)

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
            # The landmarks are per-page, not just on the home page.
            expect(page.locator("[role='navigation']")).to_have_count(1)
            expect(page.locator("[role='main']")).to_have_count(1)
            # no Dash client-side error overlay leaked onto the rendered page.
            assert (
                page.locator("._dash-error-menu, #_dash-global-error-container .dash-fe-error__title").count() == 0
            ), f"page {page_def.id} raised a client-side error"

        browser.close()
