"""Story 31.1: Pages artifact builds for the deploying host (CAP-56).

Story 42.3 (CAP-60): ``actions/configure-pages`` is authoritative on every host, so the build takes
``PAGES_HOST_BASE_URL`` and ``PAGES_HOST_BASE_PATH`` whenever both are set and the public github.io URL
otherwise, with no flag. The resolver is ``docsite/tools/pages_site_url.py``; the flag, its reader
(``pyforge/herald/pages_host.py``) and the workflow exporter (``docsite/tools/export_pages_host_env.py``)
are gone, and the retired key is spelled here only in pieces so a tracked-file grep for it stays empty.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

#: The retired key, assembled so this file does not itself carry the string AC5 greps for.
RETIRED_FLAG = "pyforge.herald." + "pages" + "_second_host"
ENTERPRISE_SITE = "https://pages.ghe.example/org/local-recipes"
ENTERPRISE_BASE_PATH = "/org/local-recipes/"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _site_url():
    root = _repo_root()
    tools = root / "docsite" / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    return _load_module("pages_site_url_under_test", tools / "pages_site_url.py")


def _assemble_pages():
    root = _repo_root()
    return _load_module(
        "assemble_pages_under_test",
        root / "docsite" / "tools" / "assemble_pages.py",
    )


def test_public_site_url_default() -> None:
    psh = _site_url()
    assert psh.public_site_url(github_repository="rxm7706/local-recipes") == ("https://rxm7706.github.io/local-recipes")


def test_combine_pages_host() -> None:
    psh = _site_url()
    url = psh.combine_pages_host(ENTERPRISE_SITE, ENTERPRISE_BASE_PATH)
    assert url == "https://pages.ghe.example/org/local-recipes"


def test_both_host_values_set_are_the_site_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC1: both configure-pages values, no flag anywhere."""
    psh = _site_url()
    monkeypatch.setenv("PAGES_HOST_BASE_URL", "https://pages.ghe.example")
    monkeypatch.setenv("PAGES_HOST_BASE_PATH", "/org/local-recipes")
    assert psh.resolve_from_process_environment() == "https://pages.ghe.example/org/local-recipes"


@pytest.mark.parametrize(
    ("base_url", "base_path"),
    [
        (None, None),
        ("https://pages.ghe.example", None),
        (None, "/org/local-recipes"),
        ("https://pages.ghe.example", ""),
    ],
    ids=["neither", "url-only", "path-only", "empty-path"],
)
def test_one_value_or_none_falls_back_to_the_public_url(
    monkeypatch: pytest.MonkeyPatch, base_url: str | None, base_path: str | None
) -> None:
    """AC2: neither variable, or only one, builds for the public github.io URL."""
    psh = _site_url()
    monkeypatch.setenv("GITHUB_REPOSITORY", "rxm7706/local-recipes")
    for name, value in (("PAGES_HOST_BASE_URL", base_url), ("PAGES_HOST_BASE_PATH", base_path)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    assert psh.resolve_from_process_environment() == "https://rxm7706.github.io/local-recipes"


@pytest.mark.parametrize(
    ("base_url", "base_path", "expected"),
    [
        ("https://pages.ghe.example", "/", "https://pages.ghe.example"),
        (ENTERPRISE_SITE, "/org/local-recipes", ENTERPRISE_SITE),
        ("https://rxm7706.github.io/local-recipes", "/local-recipes", "https://rxm7706.github.io/local-recipes"),
    ],
    ids=["root-base-path", "url-already-carries-path", "github-io"],
)
def test_resolve_build_site_url_combines_without_a_flag(base_url: str, base_path: str, expected: str) -> None:
    psh = _site_url()
    assert psh.resolve_build_site_url(configured_base_url=base_url, configured_base_path=base_path) == expected


def test_no_flag_read_in_docsite_and_the_reader_is_gone() -> None:
    """AC3."""
    root = _repo_root()
    pattern = re.compile("|".join(["pages_" + "second_host", "PYFORGE_PAGES_" + "APPLY_HOST", "read_" + "boolean"]))
    hits = [
        f"{path.relative_to(root)}:{number}"
        for path in sorted((root / "docsite").rglob("*"))
        if path.is_file() and path.suffix in {".py", ".md", ".yml", ".yaml", ".j2", ".html", ".toml", ".json"}
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1)
        if pattern.search(line)
    ]
    assert hits == []
    assert not (root / "src/shared/packages/pyforge-herald/src/pyforge/herald/pages_host.py").exists()
    assert not (root / "docsite/tools/export_pages_host_env.py").exists()


def test_the_retired_key_is_gone_from_the_tree_and_every_overlay() -> None:
    """AC4."""
    root = _repo_root()
    tree = json.loads((root / "src/platform/config/flags.json").read_text(encoding="utf-8"))
    assert RETIRED_FLAG not in tree["flags"]
    overlays = json.loads((root / "src/platform/config/flag-overlays.json").read_text(encoding="utf-8"))
    for environment, values in overlays.items():
        assert RETIRED_FLAG not in values, environment
    inventory = (root / "docs/governance/flag-inventory/pyforge-herald.md").read_text(encoding="utf-8")
    assert "pages_" + "second_host" not in inventory


# Story 40.1 (FR-8.6): pages-check requires herald's shared menu, exactly as docsite/content/site.yml
# lists it, on every docs page and every herald shell page; the docs root also links every herald
# target from its sidebar. (label, docs path from the site root, herald href from the /herald/ mount)
_SHARED_MENU = [
    ("Docs", "", "../"),
    ("Overview", "herald/", "index.html"),
    ("Dossier", "herald/dossier/", "dossier/index.html"),
    ("Infographics", "herald/infographics/", "infographics/index.html"),
    ("Decks", "herald/decks/", "decks/index.html"),
    ("Kedro-Viz", "dashboard/kedro-viz/", "../dashboard/kedro-viz/"),
]


def _write_shared_menu(artifact: Path, base: str, *, herald_index_extra: str = "") -> None:
    """The docs root and 404 with the top menu and Herald sidebar links, and herald's four shell
    pages with the same menu as relative links."""
    top = "".join(f'<a data-pf-menu-link href="{base}{path}">{label}</a>' for label, path, _ in _SHARED_MENU)
    sidebar = "".join(f'<a href="{base}{path}">{label}</a>' for label, path, _ in _SHARED_MENU[1:])
    for rel in ("index.html", "404.html"):
        (artifact / rel).write_text(
            f"<html>{top}{sidebar}<main><div class='sl-markdown-content'><p>Shelf page body.</p></div></main></html>",
            encoding="utf-8",
        )
    for sub in ("", "dossier/", "infographics/", "decks/"):
        rel = "../" if sub else ""
        menu = "".join(f'<a data-pf-menu-link href="{rel}{href}">{label}</a>' for label, _, href in _SHARED_MENU)
        page = artifact / "herald" / sub / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        extra = herald_index_extra if not sub else ""
        page.write_text(f"<html>{menu}{extra}</html>", encoding="utf-8")


def _minimal_artifact(artifact: Path, site_url: str, *, herald_index_body: str) -> None:
    assemble_pages = _assemble_pages()
    _write_shared_menu(artifact, assemble_pages._base_path(site_url), herald_index_extra=herald_index_body)
    # The former-root redirect stub for every herald page (CAP-52), as pages-build writes them.
    assemble_pages._write_dossier_redirects(artifact)
    # A mounted Kedro-Viz export (Story 42.2): the bundle, its manifest, and herald's pipelines page.
    dashboard = artifact / "dashboard" / "kedro-viz"
    dashboard.mkdir(parents=True)
    (dashboard / "index.html").write_text("<html></html>", encoding="utf-8")
    (dashboard / "manifest.json").write_text(
        json.dumps({"export_commit": "0" * 40, "export_date": "2026-10-15T09:23:50Z"}), encoding="utf-8"
    )
    pipelines_menu = "".join(
        f'<a data-pf-menu-link href="{"kedro-viz/" if label == "Kedro-Viz" else "../herald/" + href}">{label}</a>'
        for label, _, href in _SHARED_MENU
    )
    (artifact / "dashboard" / "index.html").write_text(f"<html>{pipelines_menu}</html>", encoding="utf-8")
    (artifact / "kedro-viz").mkdir(parents=True, exist_ok=True)
    (artifact / "kedro-viz" / "index.html").write_text(
        assemble_pages.redirect_html("../dashboard/kedro-viz/index.html"),
        encoding="utf-8",
    )
    assemble_pages._write_site_url_marker(artifact, site_url)


@pytest.mark.parametrize(
    ("snippet", "kind", "origin"),
    [
        ('<script src="https://cdn.example/x.js"></script>', "script", "https://cdn.example"),
        ('<script src="//cdn.example/x.js"></script>', "script", "//cdn.example"),
        ('<link rel="stylesheet" href="https://cdn.example/x.css">', "stylesheet", "https://cdn.example"),
        (
            "<style>@font-face { src: url(https://fonts.gstatic.com/font.woff2); }</style>",
            "font",
            "https://fonts.gstatic.com",
        ),
        (
            "<style>@import url(https://fonts.googleapis.com/css2?family=Inter);</style>",
            "stylesheet",
            "https://fonts.googleapis.com",
        ),
        ('<link rel="preconnect" href="https://fonts.gstatic.com">', "preconnect", "https://fonts.gstatic.com"),
        ('<link rel="preload" as="font" href="https://cdn.example/f.woff2">', "font", "https://cdn.example"),
        ('<img src="https://cdn.example/x.png">', "image", "https://cdn.example"),
        ('<img srcset="/a.png 1x, https://cdn.example/x.png 2x">', "image", "https://cdn.example"),
        ('<iframe src="https://cdn.example/embed"></iframe>', "frame", "https://cdn.example"),
        ('<script>fetch("https://platform.example/api")</script>', "fetch", "https://platform.example"),
        ('<script>xhr.open("GET", "https://platform.example/api")</script>', "xhr", "https://platform.example"),
        (
            '<script>var s = document.createElement("script"); s.src = "https://cdn.example/t.js";</script>',
            "dynamic src",
            "https://cdn.example",
        ),
    ],
)
def test_pages_check_cross_origin_kinds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], snippet: str, kind: str, origin: str
) -> None:
    assemble_pages = _assemble_pages()
    psh = _site_url()
    artifact = tmp_path / "site"
    artifact.mkdir()
    site_url = psh.public_site_url()
    body = f"<html><body>{snippet}</body></html>"
    _minimal_artifact(artifact, site_url, herald_index_body=body)

    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=site_url)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert f"cross-origin {kind}: herald/index.html -> '{origin}" in err
    assert "1 cross-origin finding(s)" in err


@pytest.mark.parametrize(
    "snippet",
    [
        '<a href="https://docs.python.org/3/">Python docs</a>',
        '<a href="https://github.com/rxm7706/local-recipes">repo</a>',
        '<area href="https://docs.python.org/3/" alt="docs">',
        '<link rel="canonical" href="https://docs.python.org/3/">',
        '<link rel="alternate" type="application/rss+xml" href="https://docs.python.org/3/feed.xml">',
        '<meta property="og:image" content="https://docs.python.org/3/og.png">',
        "<pre><code>fetch(&quot;https://platform.example/api&quot;)</code></pre>",
    ],
)
def test_pages_check_passes_navigation_and_non_loading_links(tmp_path: Path, snippet: str) -> None:
    assemble_pages = _assemble_pages()
    psh = _site_url()
    artifact = tmp_path / "site"
    artifact.mkdir()
    site_url = psh.public_site_url()
    _minimal_artifact(artifact, site_url, herald_index_body=f"<html><body>{snippet}</body></html>")
    assemble_pages.check(artifact, site_url=site_url)


def test_pages_check_judges_the_element_not_the_outside_host(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One outside origin: the <a href> passes; the stylesheet, script and image it loads fail."""
    assemble_pages = _assemble_pages()
    psh = _site_url()
    site_url = psh.public_site_url()
    link = '<a href="https://docs.python.org/3/">Python docs</a>'

    passing = tmp_path / "passing"
    passing.mkdir()
    _minimal_artifact(passing, site_url, herald_index_body=f"<html><body>{link}</body></html>")
    assemble_pages.check(passing, site_url=site_url)

    failing = tmp_path / "failing"
    failing.mkdir()
    loads = (
        '<link rel="stylesheet" href="https://docs.python.org/3/_static/pydoctheme.css">'
        '<script src="https://docs.python.org/3/_static/doctools.js"></script>'
        '<img src="https://docs.python.org/3/_static/py.svg">'
    )
    _minimal_artifact(failing, site_url, herald_index_body=f"<html><head>{loads}</head><body>{link}</body></html>")
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(failing, site_url=site_url)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "cross-origin stylesheet: herald/index.html -> 'https://docs.python.org/3/_static/pydoctheme.css'" in err
    assert "cross-origin script: herald/index.html -> 'https://docs.python.org/3/_static/doctools.js'" in err
    assert "cross-origin image: herald/index.html -> 'https://docs.python.org/3/_static/py.svg'" in err
    assert "'https://docs.python.org/3/'" not in err
    assert "3 cross-origin finding(s)" in err


@pytest.mark.parametrize(
    ("rel_path", "content", "kind"),
    [
        ("herald/site.css", "@import url(https://fonts.googleapis.com/css2?family=Inter);", "stylesheet"),
        ("herald/app.js", 'fetch("https://platform.example/api");', "fetch"),
        ("herald/app.js", 'el.innerHTML = "<img src=\\"https://cdn.example/x.png\\">";', "image"),
    ],
)
def test_pages_check_reads_css_and_js_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], rel_path: str, content: str, kind: str
) -> None:
    assemble_pages = _assemble_pages()
    psh = _site_url()
    artifact = tmp_path / "site"
    artifact.mkdir()
    site_url = psh.public_site_url()
    _minimal_artifact(artifact, site_url, herald_index_body="<html></html>")
    (artifact / rel_path).write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=site_url)
    assert exc.value.code == 1
    assert f"cross-origin {kind}: {rel_path} -> " in capsys.readouterr().err


def test_pages_check_js_navigation_link_passes(tmp_path: Path) -> None:
    """A map-attribution style <a href> built in a JS string is navigation, not a load."""
    assemble_pages = _assemble_pages()
    psh = _site_url()
    artifact = tmp_path / "site"
    artifact.mkdir()
    site_url = psh.public_site_url()
    _minimal_artifact(artifact, site_url, herald_index_body="<html></html>")
    (artifact / "herald" / "map.js").write_text(
        'var a = \'© <a target="_blank" href="https://www.openstreetmap.org/copyright">OSM</a>\';',
        encoding="utf-8",
    )
    assemble_pages.check(artifact, site_url=site_url)


_VENDORED_KEDRO_VIZ = {
    "index.html": (
        '<html><head><link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Inter" rel="stylesheet"></head></html>'
    ),
    "telemetry.html": (
        '<script type="text/javascript">var r=document.createElement("script");'
        'r.src="https://cdn.heapanalytics.com/js/heap-"+e+".js";</script>'
    ),
    "assets/index.js": 'Y.crossOrigin="Anonymous",Y.src="https://unpkg.com/maki@2.1.0/icons/"+n+".svg";',
}


def test_vendored_roots_are_a_named_allowlist() -> None:
    assemble_pages = _assemble_pages()
    assert list(assemble_pages.VENDORED_ROOTS) == ["dashboard/kedro-viz/"]
    assert all(reason.strip() for reason in assemble_pages.VENDORED_ROOTS.values())


def test_pages_check_exempts_vendored_kedro_viz_and_reports_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assemble_pages = _assemble_pages()
    psh = _site_url()
    artifact = tmp_path / "site"
    artifact.mkdir()
    site_url = psh.public_site_url()
    _minimal_artifact(artifact, site_url, herald_index_body="<html></html>")
    root = artifact / "dashboard" / "kedro-viz"
    for rel, content in _VENDORED_KEDRO_VIZ.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content, encoding="utf-8")

    assemble_pages.check(artifact, site_url=site_url)
    out = capsys.readouterr().out
    assert "exempt vendored root dashboard/kedro-viz/ (AD-21 rule 5:" in out
    assert "4 cross-origin reference(s) to" in out
    for origin in ("https://cdn.heapanalytics.com", "https://fonts.googleapis.com", "https://unpkg.com"):
        assert origin in out


@pytest.mark.parametrize("rel_root", ["dashboard/other-board", "kedro-viz"])
def test_pages_check_exemption_is_not_a_blanket_skip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], rel_root: str
) -> None:
    """The same vendored bytes outside the named root fail, even beside it under dashboard/."""
    assemble_pages = _assemble_pages()
    psh = _site_url()
    artifact = tmp_path / "site"
    artifact.mkdir()
    site_url = psh.public_site_url()
    _minimal_artifact(artifact, site_url, herald_index_body="<html></html>")
    target = artifact / rel_root / "telemetry.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_VENDORED_KEDRO_VIZ["telemetry.html"], encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=site_url)
    assert exc.value.code == 1
    assert f"cross-origin dynamic src: {rel_root}/telemetry.html -> 'https://cdn.heapanalytics.com" in (
        capsys.readouterr().err
    )


def test_pages_check_absolute_internal_other_host(tmp_path: Path) -> None:
    assemble_pages = _assemble_pages()
    psh = _site_url()
    artifact = tmp_path / "site"
    artifact.mkdir()
    enterprise = psh.combine_pages_host(ENTERPRISE_SITE, ENTERPRISE_BASE_PATH)
    body = '<html><a href="https://rxm7706.github.io/local-recipes/herald/">home</a></html>'
    _minimal_artifact(artifact, enterprise, herald_index_body=body)
    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=enterprise)
    assert exc.value.code == 1


def test_flags_json_carries_ci_surfaces_tile() -> None:
    root = _repo_root()
    tree = json.loads((root / "src/platform/config/flags.json").read_text(encoding="utf-8"))
    flag = tree["flags"]["pyforge.herald.ci_surfaces_tile"]
    assert flag["defaultVariant"] == "off"
    assert flag["metadata"]["story"].startswith("39-1-")
