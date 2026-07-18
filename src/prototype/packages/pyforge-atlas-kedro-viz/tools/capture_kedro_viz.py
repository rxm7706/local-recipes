#!/usr/bin/env python3
"""Capture the ACTUAL kedro-viz UI of the prototype DAG as a PNG.

Pixel-faithful to `kedro viz` (unlike the Graphviz SVGs from
``regenerate_from_atlas.py``, which are a cleaner but non-native layout). Runs
``kedro viz build``, serves the static SPA, and drives headless Chrome
(playwright + the system ``google-chrome``) to screenshot the real kedro-viz
flowchart into ``docs/kedro-viz-dag.png`` (onboarding popup dismissed).

    pixi run -e local-recipes capture-kedro-viz-proto

Soft deps (script skips, not fatal, if playwright is absent): playwright + a
chrome/chromium binary, kedro-viz. NOTE: the static build doesn't route
``?pipeline_id=``, so this captures the full ``__default__`` DAG only; for a
single pipeline, run ``kedro viz`` and pick it in the pipeline dropdown, or use
the per-pipeline Graphviz SVGs from ``regenerate-kedro-viz-proto``.
"""
from __future__ import annotations

import functools
import http.server
import socketserver
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # pyforge-atlas-kedro-viz
BUILD = ROOT / "build"
DOCS = ROOT / "docs"
PORT = 8237
_GRAPH = "svg.pipeline-flowchart__graph"

# Suppress the first-run feature-tour popup + force light theme by pre-seeding
# kedro-viz's OWN localStorage before its bundle runs (add_init_script) — robust,
# unlike clicking/removing the popup after render (which blanked the app once).
_INIT = """
try {
    const k = 'KedroViz';
    const cur = JSON.parse(window.localStorage.getItem(k) || '{}');
    cur.showFeatureHints = false;
    cur.theme = 'light';
    window.localStorage.setItem(k, JSON.stringify(cur));
} catch (e) {}
"""


def _serve(directory: Path, port: int):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        print(f"playwright unavailable ({exc}); skipped kedro-viz capture")
        return 0

    print("kedro viz build ...")
    subprocess.run(["kedro", "viz", "build"], cwd=ROOT, check=True,
                   capture_output=True, text=True)
    DOCS.mkdir(exist_ok=True)

    httpd = _serve(BUILD, PORT)
    out = DOCS / "kedro-viz-dag.png"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            pg = browser.new_page(viewport={"width": 2600, "height": 1700},
                                  device_scale_factor=2)
            pg.add_init_script(_INIT)                 # kill feature-tour + set light theme
            pg.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle")
            pg.wait_for_selector(_GRAPH, timeout=45000)
            pg.wait_for_timeout(2800)                 # graph layout + auto-fit settle
            pg.screenshot(path=str(out), full_page=False)
            browser.close()
    finally:
        httpd.shutdown()
    print(f"captured {out.relative_to(ROOT.parents[3])}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
