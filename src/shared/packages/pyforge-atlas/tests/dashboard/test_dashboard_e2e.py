"""Playwright-based browser-level E2E tests for the Vizro dashboard (FR-9)."""

from __future__ import annotations

import multiprocessing
import os
import shutil
import socket
import time
from pathlib import Path
import re
from playwright.sync_api import sync_playwright, expect
import pytest

from pyforge.atlas.dashboard.app import build_dashboard
from vizro import Vizro


def get_free_port() -> int:
    """Find a free port on localhost."""
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run_vizro_server(port: int, data_root: str, stamp: str, now: int, sprint_path: str, epics_path: str, specs_dir: str) -> None:
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
def dashboard_server(feedstock_health_parquet, package_maintainers_parquet, packages_parquet, bmad_fixture, tmp_path_factory):
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
    
    # Give the server a couple of seconds to spin up and bind to the port
    time.sleep(3.0)
    
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
