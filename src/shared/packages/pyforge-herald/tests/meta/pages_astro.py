"""Shared by the Pages tests (Epic 43; Story 43.7 made ``docs-site/`` the one generator): build docs-site's Astro over
a tree, write a fixture tree, run ``pages-check`` over an artifact, and read what a herald page links and offers. Not a
test module; the meta tests import it by name.

Building Astro needs docs-site's ``node_modules`` (``pixi run -e site docs-site-install``); without them ``needs_astro``
skips, naming that command. Each build rewrites ``docs-site/public/`` from scratch, as every build does (Story 43.3).
``pages-check`` (``docs-site/scripts/pages.mts``) needs only node: its herald tests run wherever node does."""

from __future__ import annotations

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
PAGES_MTS = DOCS_SITE / "scripts" / "pages.mts"
SITE_YML_REL = "docs-site/src/content/site.yml"
DOSSIER_REL = "docs-site/src/content/dossier/dossier.yml"
SITE_URL = "https://rxm7706.github.io/local-recipes"
NODE = shutil.which("node")
RENDER_READY = NODE is not None and ASTRO_BIN.is_file()
needs_node = pytest.mark.skipif(NODE is None, reason="node is not on PATH")
#: No CI lane that runs the herald suite installs docs-site (the suite is offline by construction), so these skip
#: there; CI judges the real artifact through ``pages-check`` in the Pages lane and ``pr-preflight``.
needs_astro = pytest.mark.skipif(
    not RENDER_READY,
    reason="docs-site is not installed (pixi run -e site docs-site-install); pages-check judges the built artifact",
)


def write(path: Path, text: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def site_yml(root: Path) -> dict:
    return yaml.safe_load((root / SITE_YML_REL).read_text(encoding="utf-8"))


def node_env() -> dict[str, str]:
    """This process's environment for a node child: no pytest options, no fixture-root or input overrides."""
    drop = ("PYTEST_ADDOPTS", "HERALD_PAGES_REPO_ROOT", "PAGES_BUILD_INPUTS_DIR")
    return {k: v for k, v in os.environ.items() if k not in drop}


def ts(module: Path, expression: str, **inputs: object) -> object:
    """Evaluate ``expression`` with ``module`` imported as ``m`` and ``inputs`` bound as ``inp``, through node's type
    stripping; a thrown error comes back as ``{"error": name, "message": ...}``."""
    script = (
        f"import * as m from {json.dumps(module.as_uri())};\n"
        f"const inp = {json.dumps(inputs)};\n"
        "try {\n"
        f"  const value = await (async () => {{ {expression} }})();\n"
        "  process.stdout.write(JSON.stringify({ value }));\n"
        "} catch (exc) {\n"
        "  process.stdout.write(JSON.stringify({ error: exc.name, message: exc.message }));\n"
        "}\n"
    )
    done = subprocess.run(
        [NODE or "node", "--experimental-strip-types", "--no-warnings", "--input-type=module", "-e", script],
        cwd=DOCS_SITE,
        env=node_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    return result if "error" in result else result["value"]


def pages_check(
    root: Path,
    *,
    env: dict[str, str] | None = None,
    repo_root: Path | None = None,
    origins: bool = True,
) -> list[str]:
    """``pages-check``'s findings over the artifact at ``root`` (``docs-site/scripts/pages.mts``'s ``check``), with
    ``env`` as the build environment (the flags, the host) and ``repo_root`` the tree whose ``docs/dashboard/`` the
    build mounted (default: an empty one beside ``root``)."""
    base_env = {"HERALD_PYTHON": sys.executable, **(env or {})}
    repo = repo_root if repo_root is not None else root.parent / f"{root.name}-repo"
    repo.mkdir(parents=True, exist_ok=True)
    options = {"env": base_env, "repoRoot": str(repo), "origins": origins}
    result = ts(PAGES_MTS, f"return m.check({json.dumps(str(root))}, inp.options);", options=options)
    assert isinstance(result, list), result
    return result


#: Shaped as the tracked Design exports are: ``<head>`` on its own line, the Google Fonts links one per line.
POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"><title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400&amp;display=swap" rel="stylesheet">
</head><body><main><h1>{title}</h1><p>{body}</p></main></body></html>
"""


#: Story 43.5: the stations the dossier's ``check:`` stats measure, each fixture package with a known line count.
STATIONS = ("atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden")


def station_packages(root: Path) -> dict[str, dict[str, int]]:
    """A package per station under ``root/src/shared/packages/`` with known counts, for ``verify_claims.py``'s
    measurer (Story 43.5): station ``i`` has ``1000 + 7 * i`` source lines in ``2 + i`` files and ``500 + i`` test
    lines. Returns ``{station: {"src_lines", "src_files", "test_lines"}}``."""
    counts = {}
    for i, station in enumerate(STATIONS):
        pkg = root / "src" / "shared" / "packages" / f"pyforge-{station}"
        src_lines, files = 1000 + 7 * i, 2 + i
        for n in range(files):
            lines = src_lines - (files - 1) if n == 0 else 1
            write(pkg / "src" / "pyforge" / station / f"mod{n}.py", "x = 1\n" * lines)
        write(pkg / "tests" / "test_mod.py", "y = 2\n" * (500 + i))
        write(pkg / "pyproject.toml", '[project]\nrequires-python = ">=3.14"\n')
        counts[station] = {"src_lines": src_lines, "src_files": files, "test_lines": 500 + i}
    return counts


def fixture_tree(root: Path, *, second_pptx: bool = False, exports: bool = False) -> Path:
    """Two families and a third deck with no poster: Alpha with every view, a stamped Infographic Deck and
    a stamped PPTX; Beta with no Executive Summary, no PPTX and no sidecar; Gamma with only a facts.yaml.
    ``exports`` adds a Kedro-Viz and a Vizro export to the build input, ``docs/dashboard/``, and one board as steward's
    ``deploy static`` publishes it there (Story 43.3's review: the tree AD-21 gives ``/dashboard/`` mounts whole)."""
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
    write(root / SITE_YML_REL, yaml.safe_dump(site, sort_keys=False, allow_unicode=True))
    write(root / DOSSIER_REL, (REPO_ROOT / DOSSIER_REL).read_text(encoding="utf-8"))
    station_packages(root)  # Story 43.5: the dossier's measured stats count these

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
        write(dashboard / "fleet-board" / "index.html", "<!doctype html><title>Fleet board</title><p>board</p>\n")
        write(dashboard / ".vizro-staging" / "index.html", "<p>a gitignored staging leftover: never mounted</p>\n")
    return root


#: The environment a build reads its built-from line from (Story 43.5): a test sets it only through ``extra_env``,
#: so a build under CI's ``GITHUB_SHA`` renders what a local one does.
BUILT_FROM_ENV = ("GITHUB_SHA", "GITHUB_RUN_ID", "PAGES_BUILT_AT")


def astro_build(
    out: Path,
    *,
    root: Path | None = None,
    status: bool = False,
    tile: bool = False,
    inputs: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """``astro build`` into ``out`` for the public site URL (``SITE_URL``, recorded in ``out`` as ``pages-build``
    records it, so ``pages_check`` reads the same base path), over ``root`` when given, with
    ``pyforge.herald.status_pages`` (``status``) and ``pyforge.herald.ci_surfaces_tile`` (``tile``) as the Guild step
    would export them, and the build inputs from ``inputs`` when given."""
    env = {k: v for k, v in node_env().items() if k not in BUILT_FROM_ENV}
    env.update({"PYFORGE_STATUS_PAGES": "1" if status else "0", "PYFORGE_CI_SURFACES_TILE": "1" if tile else "0"})
    env["SITE_URL"] = SITE_URL
    env.update(extra_env or {})
    if root is not None:
        env["HERALD_PAGES_REPO_ROOT"] = str(root)
    if inputs is not None:
        env["PAGES_BUILD_INPUTS_DIR"] = str(inputs)
    done = subprocess.run(
        [NODE or "node", str(ASTRO_BIN), "build", "--outDir", str(out)],
        cwd=DOCS_SITE,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode == 0:
        write(out / ".pages-build-site-url", f"{env['SITE_URL']}\n")
    return done


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
