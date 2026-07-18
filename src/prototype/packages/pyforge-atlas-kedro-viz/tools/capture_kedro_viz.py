#!/usr/bin/env python3
"""Capture the ACTUAL kedro-viz UI of the prototype DAG — full + per-pipeline.

Pixel-faithful to `kedro viz` (unlike the Graphviz SVGs from
``regenerate_from_atlas.py``, which are a cleaner but non-native layout). Drives
the **live** ``kedro viz run`` server (its API backend can filter per pipeline;
the static ``kedro viz build`` export cannot route ``?pid=``) with headless
Chrome (playwright + the system ``google-chrome``):

  * ``docs/kedro-viz-dag.png``        — the full ``__default__`` DAG
  * ``docs/kedro-viz-<pipeline>.png`` — each pipeline, selected via the in-app
    pipeline dropdown (auto-fit, so smaller pipelines render larger/legible)
  * ``docs/kedro-viz-gallery.html``   — a self-contained dark viewer with zoom
    buttons + drag-pan + pipeline tabs, so the dense pipelines can be zoomed and
    panned to read node names (a single PNG can't; a zoomable gallery can)

Dark theme + the first-run feature-tour popup are pre-seeded into kedro-viz's own
``KedroViz`` localStorage before its bundle runs (robust; clicking/removing the
popup after render once blanked the app).

    pixi run -e local-recipes capture-kedro-viz-proto

Soft dep: script skips (not fatal) if playwright is absent.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]        # pyforge-atlas-kedro-viz
DOCS = ROOT / "docs"
HOST = "127.0.0.1"
PORT = 4243
GRAPH = "svg.pipeline-flowchart__graph"
TOGGLE = ".pipeline-list .dropdown__label"
OPTION = ".pipeline-list .pipeline-list__option, .pipeline-list .menu-option"

# Dark theme + no feature-tour, pre-seeded before the kedro-viz bundle runs.
_INIT = """
try {
    const k = 'KedroViz';
    const cur = JSON.parse(window.localStorage.getItem(k) || '{}');
    cur.showFeatureHints = false;
    cur.theme = 'dark';
    window.localStorage.setItem(k, JSON.stringify(cur));
} catch (e) {}
"""


def _api(port: int, path: str) -> dict:
    with urllib.request.urlopen(f"http://{HOST}:{port}{path}", timeout=10) as r:
        return json.load(r)


def _wait_api(port: int, tries: int = 60) -> bool:
    for _ in range(tries):
        try:
            urllib.request.urlopen(f"http://{HOST}:{port}/api/main", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def _pipelines(port: int) -> list[str]:
    ids = [p["id"] for p in _api(port, "/api/main").get("pipelines", [])]
    return ["__default__", *sorted(i for i in ids if i != "__default__")]


def _counts(port: int, pid: str) -> tuple[int, int, int]:
    path = "/api/main" if pid == "__default__" else f"/api/pipelines/{pid}"
    nodes = _api(port, path).get("nodes", [])
    kinds = [n.get("type") for n in nodes]
    return kinds.count("task"), kinds.count("data"), kinds.count("parameters")


def _select_pipeline(pg, pid: str) -> None:
    pg.click(TOGGLE)
    pg.wait_for_timeout(450)
    pg.eval_on_selector_all(
        OPTION,
        "(els, name) => { const o = els.find(e => e.textContent.trim() === name);"
        " if (o) o.click(); }",
        pid,
    )
    pg.wait_for_timeout(2600)  # auto-fit + relayout settle


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        print(f"playwright unavailable ({exc}); skipped kedro-viz capture")
        return 0

    DOCS.mkdir(exist_ok=True)
    env = {**os.environ, "DO_NOT_TRACK": "1"}  # skip kedro telemetry prompt
    srv = subprocess.Popen(
        ["kedro", "viz", "run", "--no-browser", "--host", HOST, "--port", str(PORT)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
    )
    captured: list[dict] = []
    try:
        print(f"kedro viz run (live server, :{PORT}) ...")
        if not _wait_api(PORT):
            print("kedro viz server did not come up; skipped")
            return 0
        pipes = _pipelines(PORT)

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            pg = browser.new_page(viewport={"width": 2600, "height": 1700},
                                  device_scale_factor=2)
            pg.add_init_script(_INIT)                 # dark theme + kill feature-tour
            pg.goto(f"http://{HOST}:{PORT}/", wait_until="networkidle")
            pg.wait_for_selector(GRAPH, timeout=45000)
            pg.wait_for_timeout(2600)

            for pid in pipes:
                if pid != "__default__":
                    _select_pipeline(pg, pid)
                name = "dag" if pid == "__default__" else pid
                out = DOCS / f"kedro-viz-{name}.png"
                pg.screenshot(path=str(out), full_page=False)
                t, d, prm = _counts(PORT, pid)
                captured.append({
                    "id": pid,
                    "label": "__default__ (full DAG)" if pid == "__default__" else pid,
                    "png": out.name, "tasks": t, "data": d, "params": prm,
                })
                print(f"captured {out.name}  ({t} tasks / {d} datasets"
                      f"{f' / {prm} params' if prm else ''})")
            browser.close()

        _write_gallery(captured)
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except Exception:
            srv.kill()

    print(f"gallery {(DOCS / 'kedro-viz-gallery.html').relative_to(ROOT.parents[3])}")
    return 1


def _write_gallery(captured: list[dict]) -> None:
    """Emit a self-contained dark pan-zoom viewer over the captured PNGs."""
    buttons = []
    for i, c in enumerate(captured):
        meta = f'{c["tasks"]} nodes · {c["data"]} datasets'
        if c["params"]:
            meta += f' · {c["params"]} params'
        active = " active" if i == 0 else ""
        buttons.append(
            f'<button class="tab{active}" data-src="{c["png"]}" data-i="{i}">'
            f'{c["label"]}<span class="meta">{meta}</span></button>'
        )
    first = captured[0]["png"] if captured else ""
    html = (_GALLERY_TEMPLATE
            .replace("__TABS__", "".join(buttons))
            .replace("__FIRST__", first))
    (DOCS / "kedro-viz-gallery.html").write_text(html, encoding="utf-8")


_GALLERY_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pyforge-atlas-kedro-viz — kedro-viz DAG</title>
<style>
  :root { --bg:#111318; --panel:#1a1d24; --edge:#2a2e38; --fg:#e6e9ef;
          --muted:#8b93a3; --accent:#ffd54a; }
  * { box-sizing:border-box; }
  html,body { margin:0; height:100%; background:var(--bg); color:var(--fg);
    font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  body { display:flex; flex-direction:column; }
  header { padding:12px 16px; border-bottom:1px solid var(--edge); }
  header h1 { margin:0; font-size:15px; font-weight:600; letter-spacing:.2px; }
  header p { margin:4px 0 0; color:var(--muted); font-size:12px; }
  .tabs { display:flex; gap:6px; flex-wrap:wrap; padding:10px 16px;
    border-bottom:1px solid var(--edge); }
  .tab { display:flex; flex-direction:column; align-items:flex-start; gap:2px;
    background:var(--panel); color:var(--fg); border:1px solid var(--edge);
    border-radius:8px; padding:7px 11px; cursor:pointer; font-size:13px;
    font-weight:600; transition:border-color .15s, background .15s; }
  .tab:hover { border-color:#3a4150; }
  .tab.active { border-color:var(--accent); background:#20242e; }
  .tab .meta { font-weight:400; color:var(--muted); font-size:11px;
    font-variant-numeric:tabular-nums; }
  .stage { position:relative; flex:1; overflow:hidden; cursor:grab;
    background:
      linear-gradient(var(--edge) 1px, transparent 1px) 0 0 / 28px 28px,
      linear-gradient(90deg, var(--edge) 1px, transparent 1px) 0 0 / 28px 28px,
      var(--bg); }
  .stage.grabbing { cursor:grabbing; }
  .stage img { position:absolute; top:0; left:0; transform-origin:0 0;
    image-rendering:auto; user-select:none; -webkit-user-drag:none;
    box-shadow:0 8px 40px rgba(0,0,0,.5); }
  .controls { position:absolute; right:16px; bottom:16px; display:flex; gap:6px;
    background:var(--panel); border:1px solid var(--edge); border-radius:10px;
    padding:6px; }
  .controls button { width:36px; height:36px; border:none; border-radius:7px;
    background:#232733; color:var(--fg); font-size:18px; cursor:pointer;
    display:flex; align-items:center; justify-content:center; }
  .controls button:hover { background:#2c313d; }
  .controls .zoomval { min-width:52px; display:flex; align-items:center;
    justify-content:center; color:var(--muted); font-size:12px;
    font-variant-numeric:tabular-nums; }
  .hint { position:absolute; left:16px; bottom:16px; color:var(--muted);
    font-size:11px; background:var(--panel); border:1px solid var(--edge);
    border-radius:8px; padding:6px 10px; }
</style>
</head>
<body>
  <header>
    <h1>pyforge-atlas-kedro-viz — actual kedro-viz UI (dark)</h1>
    <p>Captured from the live <code>kedro viz</code> server. Scroll / pinch or the
       buttons to zoom, drag to pan — read node names on the dense pipelines.
       Regenerate with <code>capture-kedro-viz-proto</code>.</p>
  </header>
  <div class="tabs">__TABS__</div>
  <div class="stage" id="stage">
    <img id="img" src="__FIRST__" alt="kedro-viz DAG" draggable="false">
    <div class="hint">scroll = zoom · drag = pan · double-click = reset</div>
    <div class="controls">
      <button id="zout" title="Zoom out">−</button>
      <div class="zoomval" id="zval">100%</div>
      <button id="zin" title="Zoom in">+</button>
      <button id="zfit" title="Fit">⤢</button>
    </div>
  </div>
<script>
(function () {
  const stage = document.getElementById('stage');
  const img = document.getElementById('img');
  const zval = document.getElementById('zval');
  let scale = 1, tx = 0, ty = 0, natW = 0, natH = 0;

  function apply() {
    img.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
    zval.textContent = Math.round(scale * 100) + '%';
  }
  function fit() {
    if (!natW) return;
    const r = stage.getBoundingClientRect();
    scale = Math.min(r.width / natW, r.height / natH) * 0.96;
    tx = (r.width - natW * scale) / 2;
    ty = (r.height - natH * scale) / 2;
    apply();
  }
  function load(src) {
    const probe = new Image();
    probe.onload = () => { natW = probe.naturalWidth; natH = probe.naturalHeight;
      img.style.width = natW + 'px'; img.style.height = natH + 'px';
      img.src = src; fit(); };
    probe.src = src;
  }
  function zoomAt(cx, cy, factor) {
    const ns = Math.min(8, Math.max(0.05, scale * factor));
    tx = cx - (cx - tx) * (ns / scale);
    ty = cy - (cy - ty) * (ns / scale);
    scale = ns; apply();
  }

  stage.addEventListener('wheel', (e) => {
    e.preventDefault();
    const r = stage.getBoundingClientRect();
    zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.12 : 1 / 1.12);
  }, { passive: false });

  let drag = null;
  stage.addEventListener('pointerdown', (e) => {
    drag = { x: e.clientX, y: e.clientY, tx, ty };
    stage.classList.add('grabbing'); stage.setPointerCapture(e.pointerId);
  });
  stage.addEventListener('pointermove', (e) => {
    if (!drag) return;
    tx = drag.tx + (e.clientX - drag.x); ty = drag.ty + (e.clientY - drag.y); apply();
  });
  const endDrag = () => { drag = null; stage.classList.remove('grabbing'); };
  stage.addEventListener('pointerup', endDrag);
  stage.addEventListener('pointercancel', endDrag);
  stage.addEventListener('dblclick', fit);

  const cc = () => { const r = stage.getBoundingClientRect(); return [r.width / 2, r.height / 2]; };
  document.getElementById('zin').onclick = () => zoomAt(...cc(), 1.25);
  document.getElementById('zout').onclick = () => zoomAt(...cc(), 1 / 1.25);
  document.getElementById('zfit').onclick = fit;

  document.querySelectorAll('.tab').forEach((t) => {
    t.onclick = () => {
      document.querySelectorAll('.tab').forEach((x) => x.classList.remove('active'));
      t.classList.add('active'); load(t.dataset.src);
    };
  });
  window.addEventListener('resize', fit);
  load(img.getAttribute('src'));
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
