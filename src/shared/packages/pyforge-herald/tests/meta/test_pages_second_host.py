"""Story 31.1: Pages artifact builds for the deploying host (CAP-56)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from pyforge.testing_kit.flags import flagd_tree

PAGES_SECOND_HOST_FLAG = "pyforge.herald.pages_second_host"
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


def _pages_second_host():
    root = _repo_root()
    tools = root / "docsite" / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    return _load_module("pages_second_host_under_test", tools / "pages_second_host.py")


def _assemble_pages():
    root = _repo_root()
    return _load_module(
        "assemble_pages_under_test",
        root / "docsite" / "tools" / "assemble_pages.py",
    )


def test_public_site_url_default() -> None:
    psh = _pages_second_host()
    assert psh.public_site_url(github_repository="rxm7706/local-recipes") == ("https://rxm7706.github.io/local-recipes")


def test_combine_pages_host() -> None:
    psh = _pages_second_host()
    url = psh.combine_pages_host(ENTERPRISE_SITE, ENTERPRISE_BASE_PATH)
    assert url == "https://pages.ghe.example/org/local-recipes"


def test_resolve_build_site_url_flag_on() -> None:
    psh = _pages_second_host()
    url = psh.resolve_build_site_url(
        configured_base_url=ENTERPRISE_SITE,
        configured_base_path=ENTERPRISE_BASE_PATH,
        apply_second_host=True,
    )
    assert url == "https://pages.ghe.example/org/local-recipes"


def test_resolve_build_site_url_flag_off_ignores_enterprise() -> None:
    psh = _pages_second_host()
    url = psh.resolve_build_site_url(
        configured_base_url=ENTERPRISE_SITE,
        configured_base_path=ENTERPRISE_BASE_PATH,
        apply_second_host=False,
    )
    assert url == "https://rxm7706.github.io/local-recipes"


def test_export_host_env_flag_on_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    psh = _pages_second_host()
    monkeypatch.setenv("PAGES_HOST_BASE_URL", ENTERPRISE_SITE)
    monkeypatch.setenv("PAGES_HOST_BASE_PATH", ENTERPRISE_BASE_PATH)

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {PAGES_SECOND_HOST_FLAG: "on"})))
    on_env = psh.export_host_env_for_ci()
    assert on_env[psh.ENV_APPLY_HOST] == "1"
    assert on_env[psh.ENV_SITE_URL] == "https://pages.ghe.example/org/local-recipes"

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {PAGES_SECOND_HOST_FLAG: "off"})))
    off_env = psh.export_host_env_for_ci()
    assert off_env[psh.ENV_APPLY_HOST] == "0"
    assert off_env[psh.ENV_SITE_URL] == "https://rxm7706.github.io/local-recipes"


def _minimal_artifact(artifact: Path, site_url: str, *, herald_index_body: str) -> None:
    assemble_pages = _assemble_pages()
    (artifact / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "404.html").write_text("<html></html>", encoding="utf-8")
    herald = artifact / "herald"
    (herald / "dossier").mkdir(parents=True)
    (herald / "dossier" / "index.html").write_text("<html></html>", encoding="utf-8")
    (herald / "index.html").write_text(herald_index_body, encoding="utf-8")
    (artifact / "dossier").mkdir(parents=True, exist_ok=True)
    (artifact / "dossier" / "index.html").write_text(
        assemble_pages.redirect_html("herald/dossier/index.html"),
        encoding="utf-8",
    )
    dashboard = artifact / "dashboard" / "kedro-viz"
    dashboard.mkdir(parents=True)
    (dashboard / "index.html").write_text("<html></html>", encoding="utf-8")
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
    psh = _pages_second_host()
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
    psh = _pages_second_host()
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
    psh = _pages_second_host()
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
    psh = _pages_second_host()
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
    psh = _pages_second_host()
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
    psh = _pages_second_host()
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
    psh = _pages_second_host()
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
    psh = _pages_second_host()
    artifact = tmp_path / "site"
    artifact.mkdir()
    enterprise = psh.combine_pages_host(ENTERPRISE_SITE, ENTERPRISE_BASE_PATH)
    body = '<html><a href="https://rxm7706.github.io/local-recipes/herald/">home</a></html>'
    _minimal_artifact(artifact, enterprise, herald_index_body=body)
    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=enterprise)
    assert exc.value.code == 1


def test_flags_json_carries_pages_second_host() -> None:
    root = _repo_root()
    tree = json.loads((root / "src/platform/config/flags.json").read_text(encoding="utf-8"))
    flag = tree["flags"][PAGES_SECOND_HOST_FLAG]
    assert flag["defaultVariant"] == "off"
