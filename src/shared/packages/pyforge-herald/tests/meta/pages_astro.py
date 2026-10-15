"""Shared by the Epic 43 page tests (Stories 43.2, 43.3): build docs-site's Astro over a tree, write a fixture
tree, and read what a herald page links and offers. Not a test module; the meta tests import it by name.

Building Astro needs docs-site's ``node_modules`` and generated menu (``pixi run -e site docs-site-install
docs-site-sidebar``); without them ``needs_astro`` skips, naming that command. Each build rewrites
``docs-site/public/`` from scratch, as every build does (Story 43.3)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]
DOCS_SITE = REPO_ROOT / "docs-site"
ASTRO_BIN = DOCS_SITE / "node_modules" / "astro" / "bin" / "astro.mjs"
NODE = shutil.which("node")
_GENERATED = ("src/sidebar.generated.json", "src/topnav.generated.json")
RENDER_READY = NODE is not None and ASTRO_BIN.is_file() and all((DOCS_SITE / g).is_file() for g in _GENERATED)
needs_node = pytest.mark.skipif(NODE is None, reason="node is not on PATH")
#: No CI lane that runs the herald suite installs docs-site (the suite is offline by construction), so these
#: skip there; CI enforces the same comparisons on the real artifact through ``pages-check`` with the flag on
#: (``assemble_pages._check_herald_parity``, Story 43.2's review), in the Pages lane and ``pr-preflight``.
needs_astro = pytest.mark.skipif(
    not RENDER_READY,
    reason="docs-site is not installed (pixi run -e site docs-site-install docs-site-sidebar); "
    "pages-check runs the same parity on the built artifact",
)


def load_build(name: str = "docsite_build_pages") -> object:
    """``docsite/build.py``, the Jinja path, as a fresh module."""
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "docsite" / "build.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def write(path: Path, text: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def site_yml(root: Path) -> dict:
    return yaml.safe_load((root / "docsite" / "content" / "site.yml").read_text(encoding="utf-8"))


#: Shaped as the tracked Design exports are: ``<head>`` on its own line, the Google Fonts links one per line.
POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"><title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400&amp;display=swap" rel="stylesheet">
</head><body><main><h1>{title}</h1><p>{body}</p></main></body></html>
"""


def fixture_tree(root: Path, *, second_pptx: bool = False, exports: bool = False) -> Path:
    """Two families and a third deck with no poster: Alpha with every view, a stamped Infographic Deck and
    a stamped PPTX; Beta with no Executive Summary, no PPTX and no sidecar; Gamma with only a facts.yaml.
    ``exports`` adds a Kedro-Viz and a Vizro export to the build input, ``docs/dashboard/``."""
    site = site_yml(REPO_ROOT)
    site["infographics"] = {
        "include": [
            "presentations/fx-alpha/project/*Infographic standalone.html",
            "presentations/fx-beta/project/*Infographic standalone.html",
            "presentations/fx-gamma/project/*Infographic standalone.html",
        ],
        "exclude": [],
        "inject_backbar": True,
        "overrides": {
            "presentations/fx-alpha/project/Alpha Infographic standalone.html": {
                "title": "Alpha",
                "description": "The first fixture family.",
                "order": 20,
            },
            "Beta Infographic standalone.html": {"order": 10},
        },
    }
    content = root / "docsite" / "content"
    write(content / "site.yml", yaml.safe_dump(site, sort_keys=False, allow_unicode=True))
    shutil.copy2(REPO_ROOT / "docsite" / "content" / "dossier.yml", content / "dossier.yml")

    alpha = root / "presentations" / "fx-alpha"
    write(alpha / "project" / "Alpha Infographic standalone.html", POSTER.format(title="Alpha poster", body="a" * 400))
    deck = write(
        alpha / "project" / "Alpha - Infographic Deck.dc.html", POSTER.format(title="Alpha deck", body="d" * 300)
    )
    write(Path(f"{deck}.stamp.json"), json.dumps({"tree": "0123456789abcdef", "etag": "etag-alpha-deck-1"}))
    write(alpha / "project" / "Alpha - Executive Summary.dc.html", POSTER.format(title="Alpha summary", body="e" * 200))
    pptx = write(alpha / "src" / "pptx" / "fx-alpha-deck-2026-01-01.pptx", b"PK\x03\x04alpha")
    write(Path(f"{pptx}.stamp.json"), json.dumps({"tree": "fedcba9876543210", "etag": "etag-alpha-pptx"}))
    if second_pptx:
        write(alpha / "src" / "pptx" / "fx-alpha-deck-2026-02-01.pptx", b"PK\x03\x04alpha-2")
    write(alpha / "src" / "marp" / "fx-alpha-deck-2026-01-01.md", "# Alpha\n")
    write(alpha / "src" / "marp" / "fx-alpha-narration-2026-01-02.md", "# Alpha narration\n")
    write(
        alpha / "facts.yaml",
        "deck: fx-alpha\nderived_at: '2026-01-02T00:00:00Z'\nfacts:\n  - id: one\n    value: '1'\n",
    )

    beta = root / "presentations" / "fx-beta"
    write(beta / "project" / "Beta Infographic standalone.html", POSTER.format(title="Beta &amp; Co", body="b" * 400))
    write(beta / "project" / "Beta - Infographic Deck.dc.html", POSTER.format(title="Beta deck", body="d" * 300))
    write(beta / "src" / "marp" / "fx-beta-2026-02-02.md", "# Beta\n")
    write(beta / "facts.yaml", "deck: fx-beta\nfacts: []\n")

    write(root / "presentations" / "fx-gamma" / "facts.yaml", "deck: fx-gamma\nfacts: []\n")

    if exports:
        dashboard = root / "docs" / "dashboard"
        write(dashboard / "README.md", "# docs/dashboard\n")
        write(dashboard / "kedro-viz" / "index.html", "<!doctype html><title>Kedro-Viz</title><p>graph</p>\n")
        write(dashboard / "kedro-viz" / "api" / "main", '{"nodes": []}\n')
        manifest = {"export_commit": "0123456789abcdef0123456789abcdef01234567", "export_date": "2026-10-15T09:23:50Z"}
        write(dashboard / "kedro-viz" / "manifest.json", json.dumps(manifest))
        write(dashboard / "vizro" / "index.html", "<!doctype html><title>Boards</title><p>boards</p>\n")
        write(dashboard / "vizro" / "estate" / "index.html", '<script src="../assets/plotly.min.js"></script>\n')
        write(
            dashboard / "vizro" / "assets" / "plotly.min.js",
            "/* plotly */ fetch('https://cdn.plot.ly/un/world_110m.json');\n",
        )
        write(dashboard / "vizro" / "manifest.json", json.dumps({**manifest, "boards": []}))
    return root


def astro_build(out: Path, *, flag: bool, root: Path | None = None) -> subprocess.CompletedProcess[str]:
    """``astro build`` into ``out`` with pyforge.herald.pages_one_generator ``flag``, over ``root`` when given."""
    env = {k: v for k, v in os.environ.items() if k not in ("HERALD_PAGES_REPO_ROOT", "PYTEST_ADDOPTS")}
    env.update({"PYFORGE_PAGES_ONE_GENERATOR": "1" if flag else "0", "PYFORGE_CI_SURFACES_TILE": "0"})
    env["PYFORGE_STATUS_PAGES"] = "0"
    if root is not None:
        env["HERALD_PAGES_REPO_ROOT"] = str(root)
    return subprocess.run(
        [NODE or "node", str(ASTRO_BIN), "build", "--outDir", str(out)],
        cwd=DOCS_SITE,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class Page(HTMLParser):
    """What a herald page links and offers: its body's anchors (not the shared menu), its cards, its
    downloads and its preview frames."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.shots: list[tuple[str, str]] = []
        self.downloads: list[str] = []
        self.dl_meta: list[str] = []
        self.frames: list[dict[str, str]] = []
        self._shot: str | None = None
        self._capture: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "a" and "href" in a and "data-pf-menu-link" not in a and "site-brand" not in a.get("class", ""):
            self.hrefs.append(a["href"])
            if "shot" in a.get("class", "").split():
                self._shot = a["href"]
            if "download" in a:
                self._capture, self._text = "download", []
        elif tag == "h3" and self._shot is not None:
            self._capture, self._text = "shot", []
        elif tag == "span" and "dl-meta" in a.get("class", ""):
            self._capture, self._text = "meta", []
        elif tag == "iframe":
            self.frames.append(a)

    def handle_endtag(self, tag: str) -> None:
        text = " ".join("".join(self._text).split())
        if tag == "a" and self._capture == "download":
            self.downloads.append(text)
            self._capture = None
        elif tag == "h3" and self._capture == "shot":
            self.shots.append((self._shot or "", text))
            self._shot, self._capture = None, None
        elif tag == "span" and self._capture == "meta":
            self.dl_meta.append(text)
            self._capture = None
        if tag == "a":
            self._shot = None

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)


def page(path: Path) -> Page:
    parsed = Page()
    parsed.feed(path.read_text(encoding="utf-8"))
    parsed.close()
    return parsed
