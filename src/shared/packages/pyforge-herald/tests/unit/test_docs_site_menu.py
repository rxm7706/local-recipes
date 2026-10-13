"""Story 40.1 (CAP-58, FR-8.6): the docs site and the herald pages share one menu.

The menu is herald's one navigation list, ``docsite/content/site.yml``. The docs side reads it
through ``docs-site/scripts/sidebar_from_map.py`` (a Herald sidebar group and the top-menu JSON);
the herald side renders it in ``docsite/templates/shell_page.html.j2``; ``pages-check`` fails a
menu link that does not resolve inside the artifact.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[6]
_GENERATOR = REPO_ROOT / "docs-site" / "scripts" / "sidebar_from_map.py"
_ASSEMBLER = REPO_ROOT / "docsite" / "tools" / "assemble_pages.py"
_SITE_YML = REPO_ROOT / "docsite" / "content" / "site.yml"
_SITE_TITLE = REPO_ROOT / "docs-site" / "src" / "components" / "SiteTitle.astro"
_ASTRO_CONFIG = REPO_ROOT / "docs-site" / "astro.config.mjs"


def _herald_env() -> Environment:
    """docsite/build.py's template loader and ``md`` filter; page variables this test does not
    set render empty (the shell's menu reads only ``site``, ``rel`` and ``page_key``)."""
    env = Environment(loader=FileSystemLoader(str(REPO_ROOT / "docsite" / "templates")), autoescape=False)
    env.filters["md"] = lambda text: text
    return env


_LABELS = ["Docs", "Overview", "Dossier", "Infographics", "Decks", "Kedro-Viz"]
_PATHS = ["", "herald/", "herald/dossier/", "herald/infographics/", "herald/decks/", "dashboard/kedro-viz/"]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def gen():
    return _load(_GENERATOR, "sidebar_from_map_menu_under_test")


@pytest.fixture
def assemble():
    return _load(_ASSEMBLER, "assemble_pages_menu_under_test")


# --- the one list -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("href", "path"),
    [
        ("../", ""),
        ("index.html", "herald/"),
        ("dossier/index.html", "herald/dossier/"),
        ("decks/index.html", "herald/decks/"),
        ("../dashboard/kedro-viz/", "dashboard/kedro-viz/"),
    ],
)
def test_site_yml_hrefs_become_site_root_paths(gen, href, path):
    assert gen._site_root_path(href) == path


@pytest.mark.parametrize("href", ["../../elsewhere/", "/herald/", "https://example.com/", ""])
def test_site_root_path_refuses_hrefs_outside_the_mount_rules(gen, href):
    with pytest.raises(ValueError):
        gen._site_root_path(href)


def test_live_site_yml_gives_the_six_link_top_menu(gen):
    menu = gen.top_menu(gen.load_site_menu(_SITE_YML))
    assert [item["label"] for item in menu] == _LABELS
    assert [item["path"] for item in menu] == _PATHS


def test_live_sidebar_appends_the_herald_group_after_the_quadrants(gen):
    map_path = REPO_ROOT / "docs" / "map.yaml"
    docs_dir = REPO_ROOT / "docs"
    plain, errors = gen.build_sidebar(map_path, docs_dir)
    assert errors == []
    with_herald, errors = gen.build_sidebar(map_path, docs_dir, _SITE_YML)
    assert errors == []
    assert [group["label"] for group in with_herald] == ["Tutorials", "How-to", "Reference", "Explanation", "Herald"]
    assert with_herald[:-1] == plain
    herald = with_herald[-1]
    assert [item["label"] for item in herald["items"]] == _LABELS[1:]
    assert [item["link"] for item in herald["items"]] == [f"/{path}" for path in _PATHS[1:]]


def test_site_yml_without_a_docs_entry_is_refused(gen, tmp_path: Path):
    data = yaml.safe_load(_SITE_YML.read_text(encoding="utf-8"))
    data["nav"] = [item for item in data["nav"] if item.get("key") != "docs"]
    site = tmp_path / "site.yml"
    site.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="docs"):
        gen.load_site_menu(site)


def test_a_new_site_yml_entry_appears_in_every_menu(gen, tmp_path: Path):
    data = yaml.safe_load(_SITE_YML.read_text(encoding="utf-8"))
    data["nav"].append({"key": "fixture", "label": "Fixture page", "href": "fixture/index.html"})
    site = tmp_path / "site.yml"
    site.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    menu = gen.load_site_menu(site)
    assert {"label": "Fixture page", "path": "herald/fixture/"} in gen.top_menu(menu)
    assert {"link": "/herald/fixture/", "label": "Fixture page"} in gen.herald_sidebar_group(menu)["items"]

    rendered = _render_shell(data, rel="", page_key="index")
    assert 'data-pf-menu-link href="fixture/index.html">Fixture page</a>' in rendered


def test_generator_writes_the_top_menu_json(gen, tmp_path: Path):
    out = tmp_path / "sidebar.json"
    topnav = tmp_path / "topnav.json"
    assert gen.main(["-o", str(out), "--topnav-output", str(topnav)]) == 0
    assert [item["label"] for item in json.loads(topnav.read_text(encoding="utf-8"))] == _LABELS
    assert json.loads(out.read_text(encoding="utf-8"))[-1]["label"] == "Herald"


def test_the_docs_site_hardcodes_no_menu_label_or_target():
    """The top menu component takes every label and target from the generated list; the config
    names no menu label and no host base (its /kedro-viz/ redirect is CAP-52's, not the menu)."""
    menu = _SITE_TITLE.read_text(encoding="utf-8")
    config = _ASTRO_CONFIG.read_text(encoding="utf-8")
    for label in _LABELS:
        for text in (menu, config):
            assert f">{label}<" not in text and f"'{label}'" not in text and f'"{label}"' not in text, label
    for path in _PATHS[1:]:
        assert path not in menu, path
    for text in (menu, config):
        assert "/local-recipes/" not in text
    assert "topnav.generated.json" in menu


def _render_shell(data: dict, *, rel: str, page_key: str) -> str:
    """Render herald's shell with an empty page body."""
    return (
        _herald_env()
        .get_template("shell_page.html.j2")
        .render(site=data, rel=rel, page_key=page_key, built_at="2026-10-12", commit="")
    )


def test_herald_shell_renders_docs_first_and_marks_the_current_page():
    data = yaml.safe_load(_SITE_YML.read_text(encoding="utf-8"))
    rendered = _render_shell(data, rel="../", page_key="dossier")
    positions = [rendered.index(f">{label}</a>") for label in _LABELS]
    assert positions == sorted(positions)
    assert 'data-pf-menu-link href="../../">Docs</a>' in rendered
    assert 'href="../dossier/index.html" aria-current="page">Dossier</a>' in rendered
    assert rendered.count('aria-current="page"') == 1


# --- the pages-check gate ---------------------------------------------------------------------

_EXPECTED = list(
    zip(
        _LABELS,
        [
            "../",
            "index.html",
            "dossier/index.html",
            "infographics/index.html",
            "decks/index.html",
            "../dashboard/kedro-viz/",
        ],
        strict=True,
    )
)
_HERALD_PAGES = ("", "dossier/", "infographics/", "decks/")


def _artifact(tmp_path: Path, base: str) -> Path:
    """A minimal artifact that passes the gate: docs root and 404 with the top menu and the Herald
    sidebar links, herald's four shell pages with the relative menu, the Kedro-Viz export, a raw
    infographic and a redirect stub (neither of which carries the menu)."""
    root = tmp_path / "site"
    top = "".join(
        f'<a data-pf-menu-link href="{base}{path}">{label}</a>' for label, path in zip(_LABELS, _PATHS, strict=True)
    )
    sidebar = "".join(
        f'<a href="{base}{path}">{label}</a>' for label, path in zip(_LABELS[1:], _PATHS[1:], strict=True)
    )
    root.mkdir(parents=True)
    for rel in ("index.html", "404.html"):
        (root / rel).write_text(f"<html>{top}{sidebar}</html>", encoding="utf-8")
    for sub in _HERALD_PAGES:
        rel = "../" if sub else ""
        menu = "".join(f'<a data-pf-menu-link href="{rel}{href}">{label}</a>' for label, href in _EXPECTED)
        (root / "herald" / sub).mkdir(parents=True, exist_ok=True)
        (root / "herald" / sub / "index.html").write_text(f"<html>{menu}</html>", encoding="utf-8")
    (root / "dashboard" / "kedro-viz").mkdir(parents=True)
    (root / "dashboard" / "kedro-viz" / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "herald" / "infographics" / "atlas.html").write_text("<html>raw export</html>", encoding="utf-8")
    (root / "kedro-viz").mkdir()
    (root / "kedro-viz" / "index.html").write_text(
        '<meta http-equiv="refresh" content="0; url=../dashboard/kedro-viz/">', encoding="utf-8"
    )
    return root


def _gate(assemble, root: Path, site_url: str) -> None:
    assemble._check_menu_links(root, site_url, _EXPECTED)


@pytest.mark.parametrize(
    ("site_url", "base"),
    [
        ("https://rxm7706.github.io/local-recipes", "/local-recipes/"),
        ("https://pages.example.com/pages/acme/docs", "/pages/acme/docs/"),
        ("https://example.github.io", "/"),
    ],
)
def test_menu_gate_passes_when_every_page_carries_the_menu(assemble, tmp_path: Path, site_url, base):
    _gate(assemble, _artifact(tmp_path, base), site_url)


def test_menu_gate_reads_the_live_site_yml(assemble):
    assert assemble._expected_menu() == _EXPECTED


def _replace(page: Path, old: str, new: str) -> None:
    text = page.read_text(encoding="utf-8")
    assert old in text
    page.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_menu_gate_fails_on_a_broken_docs_link(assemble, tmp_path: Path, capsys):
    root = _artifact(tmp_path, "/local-recipes/")
    _replace(root / "404.html", 'href="/local-recipes/herald/decks/"', 'href="/local-recipes/herald/missing/"')
    with pytest.raises(SystemExit) as exc:
        _gate(assemble, root, "https://rxm7706.github.io/local-recipes")
    assert exc.value.code == 1
    assert "herald/missing/" in capsys.readouterr().err


def test_menu_gate_fails_on_a_broken_herald_link(assemble, tmp_path: Path):
    root = _artifact(tmp_path, "/local-recipes/")
    _replace(root / "herald" / "decks" / "index.html", 'href="../decks/index.html"', 'href="../gone/index.html"')
    with pytest.raises(SystemExit):
        _gate(assemble, root, "https://rxm7706.github.io/local-recipes")


def test_menu_gate_fails_on_a_hardcoded_base_under_another_host(assemble, tmp_path: Path, capsys):
    root = _artifact(tmp_path, "/local-recipes/")
    with pytest.raises(SystemExit):
        _gate(assemble, root, "https://pages.example.com/pages/acme/docs")
    assert "/pages/acme/docs/" in capsys.readouterr().err


def test_menu_gate_fails_when_a_shell_page_lost_its_menu(assemble, tmp_path: Path, capsys):
    root = _artifact(tmp_path, "/local-recipes/")
    (root / "herald" / "dossier" / "index.html").write_text("<html></html>", encoding="utf-8")
    with pytest.raises(SystemExit):
        _gate(assemble, root, "https://rxm7706.github.io/local-recipes")
    assert "herald/dossier/index.html" in capsys.readouterr().err


def test_menu_gate_fails_when_one_link_is_dropped(assemble, tmp_path: Path):
    root = _artifact(tmp_path, "/local-recipes/")
    _replace(root / "404.html", '<a data-pf-menu-link href="/local-recipes/herald/decks/">Decks</a>', "")
    with pytest.raises(SystemExit):
        _gate(assemble, root, "https://rxm7706.github.io/local-recipes")


def test_menu_gate_fails_on_a_fragment_only_link(assemble, tmp_path: Path):
    root = _artifact(tmp_path, "/local-recipes/")
    _replace(root / "herald" / "index.html", 'href="decks/index.html"', 'href="#"')
    with pytest.raises(SystemExit):
        _gate(assemble, root, "https://rxm7706.github.io/local-recipes")


def test_menu_gate_fails_without_the_herald_sidebar_links(assemble, tmp_path: Path, capsys):
    root = _artifact(tmp_path, "/local-recipes/")
    _replace(root / "index.html", '<a href="/local-recipes/herald/decks/">Decks</a>', "")
    with pytest.raises(SystemExit):
        _gate(assemble, root, "https://rxm7706.github.io/local-recipes")
    assert "sidebar" in capsys.readouterr().err
