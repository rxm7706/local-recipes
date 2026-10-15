"""Story 43.7 AC3 (spec-pyforge-herald CAP-61 on doctor CAP-90): the nav comes from one registry.

``docs/map.yaml``'s ``pages`` give the docs sidebar its quadrant groups and its ``sections`` give the docs sidebar,
the top menu every page carries and the home's doors their entries, in ``order`` (``docs-site/src/lib/nav.ts``,
read once per build by ``src/lib/site-nav.ts``). Replaces Stories 27.3 and 40.1's ``sidebar_from_map.py`` tests and
``site.yml``'s nav list. The model runs through node (no ``node_modules``); the built-site test needs docs-site
installed and skips naming the command otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "meta"))
from pages_astro import (  # noqa: E402 -- the shared Pages helpers live beside the meta tests
    DOCS_SITE,
    REPO_ROOT,
    astro_build,
    fixture_tree,
    needs_astro,
    needs_node,
    site_yml,
    ts,
    write,
)

NAV_TS = DOCS_SITE / "src" / "lib" / "nav.ts"
MAP = yaml.safe_load((REPO_ROOT / "docs" / "map.yaml").read_text(encoding="utf-8"))
#: What the three menus are made of in one build, from a registry: ``(sidebar, menu, doors)`` as label lists.
_THREE = """
const reg = m.registry(inp.map);
const presence = { mounted: (name) => inp.mounted.includes(name), flag: (key) => inp.flags.includes(key) };
const sections = m.siteSections(reg.sections, presence);
return {
  sidebar: m.sectionGroups(sections).map((g) => ('items' in g ? [g.label, ...g.items.map((i) => i.label)] : [g.label])),
  menu: m.topMenu(sections).map((i) => [i.label, i.path]),
  doors: m.doors(sections).map((d) => [d.label, d.path, ...d.entries.map((e) => e.label)]),
};
"""

pytestmark = needs_node


def three(registry: dict, *, mounted: tuple[str, ...] = (), flags: tuple[str, ...] = ()) -> dict:
    result = ts(NAV_TS, _THREE, map=registry, mounted=list(mounted), flags=list(flags))
    assert isinstance(result, dict) and "error" not in result, result
    return result


def _labels(result: dict) -> tuple[list[str], list[str], list[str]]:
    flat = lambda rows: [label for row in rows for label in row if isinstance(label, str) and label[:1].isupper()]  # noqa: E731
    return flat(result["sidebar"]), [label for label, _ in result["menu"]], flat(result["doors"])


def test_the_live_registry_gives_the_three_menus_in_its_order() -> None:
    result = three(MAP)
    assert result["menu"] == [
        ["Docs", ""],
        ["Overview", "herald/"],
        ["Dossier", "herald/dossier/"],
        ["Infographics", "herald/infographics/"],
        ["Decks", "herald/decks/"],
        ["Changes", "changes/"],
    ]
    assert result["sidebar"] == [["Herald", "Overview", "Dossier", "Infographics", "Decks"], ["Changes"]]
    assert [door[:2] for door in result["doors"]] == [["Docs", ""], ["Herald", "herald/"], ["Changes", "changes/"]]


def test_a_mounted_export_and_the_status_flag_add_their_sections_in_order() -> None:
    result = three(MAP, mounted=("kedro-viz", "vizro"), flags=("pyforge.herald.status_pages",))
    assert [label for label, _ in result["menu"]] == [
        "Docs",
        "Overview",
        "Dossier",
        "Infographics",
        "Decks",
        "Status",
        "Kedro-Viz",
        "Dashboards",
        "Changes",
    ]
    assert [door[0] for door in result["doors"]] == ["Docs", "Herald", "Status", "Kedro-Viz", "Dashboards", "Changes"]
    assert ["Kedro-Viz"] in result["sidebar"] and ["Status"] in result["sidebar"]


@pytest.mark.parametrize(
    ("edit", "label"),
    [
        ("add", "Extra"),
        ("add-entry", "Gallery two"),
        ("drop", "Changes"),
    ],
)
def test_ac3_one_registry_edit_reaches_all_three_menus_and_nothing_else_does(edit: str, label: str) -> None:
    """A fixture registry with one entry added shows it in the sidebar, the top menu and the doors, with no other
    edit; one removed (the Changes entry, the story's mutation) leaves all three."""
    registry = json.loads(json.dumps(MAP))
    if edit == "add":
        registry["sections"].append({"key": "extra", "label": label, "href": "extra/", "owner": "herald", "order": 45})
    elif edit == "add-entry":
        registry["sections"][0]["entries"].append({"key": "gallery-two", "label": label, "href": "herald/two/"})
    else:
        registry["sections"] = [s for s in registry["sections"] if s["key"] != "changes"]
    sidebar, menu, doors = _labels(three(registry))
    shown = [label in sidebar, label in menu, label in doors]
    assert shown == ([False] * 3 if edit == "drop" else [True] * 3), (sidebar, menu, doors)
    if edit == "add":
        assert menu.index("Extra") == menu.index("Decks") + 1  # order 45: after herald's entries, before Changes 50


def test_the_registry_without_sections_fails_the_build_naming_the_key() -> None:
    registry = {k: v for k, v in MAP.items() if k != "sections"}
    result = ts(NAV_TS, "return m.registry(inp.map, 'docs/map.yaml');", map=registry)
    assert result == {"error": "Error", "message": result["message"]}
    assert "docs/map.yaml: no sections list" in result["message"]


def test_site_yml_has_no_nav_list_and_no_source_lists_a_menu() -> None:
    """AC3: ``site.yml``'s nav retired; the menu components take every label and target from the registry."""
    assert "nav" not in site_yml(REPO_ROOT)
    labels = [e["label"] for s in MAP["sections"] for e in [s, *s.get("entries", [])]]
    for rel in (
        "src/components/SiteTitle.astro",
        "src/components/MarkdownContent.astro",
        "src/layouts/HeraldLayout.astro",
        "src/layouts/HeraldDossierLayout.astro",
        "astro.config.mjs",
    ):
        text = (DOCS_SITE / rel).read_text(encoding="utf-8")
        assert "siteNav()" in text, rel
        for label in labels:
            assert f">{label}<" not in text and f"'{label}'" not in text and f'"{label}"' not in text, (rel, label)
        assert "/local-recipes/" not in text, rel
    assert not (DOCS_SITE / "scripts" / "sidebar_from_map.py").exists()


# --- the quadrant groups (Story 27.3's rules, now nav.ts's) --------------------------------------------------------

_QUADRANTS = """
const out = m.quadrantGroups(inp.pages, inp.docs);
return { errors: out.errors, groups: out.groups.map((g) => [g.label, ...g.items.map((i) => i.slug ?? i.link)]) };
"""


def _docs(root: Path, pages: list[str]) -> Path:
    for rel in pages:
        write(root / rel, f"# {rel}\n")
    return root


def _map(*paths: str) -> list[dict[str, str]]:
    return [{"path": p, "quadrant": p.split("/")[0]} for p in paths]


def test_the_live_map_and_docs_agree() -> None:
    result = ts(NAV_TS, _QUADRANTS, pages=MAP["pages"], docs=str(REPO_ROOT / "docs"))
    assert result["errors"] == []
    assert [g[0] for g in result["groups"]] == ["Tutorials", "How-to", "Reference", "Explanation"]


def test_map_order_is_sidebar_order_and_a_quadrant_readme_is_its_index(tmp_path: Path) -> None:
    docs = _docs(tmp_path / "docs", ["how-to/README.md", "how-to/b.md", "how-to/a.md", "tutorials/x/README.md"])
    pages = _map("how-to/README.md", "how-to/b.md", "how-to/a.md", "tutorials/x/README.md")
    result = ts(NAV_TS, _QUADRANTS, pages=pages, docs=str(docs))
    assert result == {
        "errors": [],
        "groups": [["How-to", "/how-to/", "how-to/b", "how-to/a"], ["Tutorials", "/tutorials/", "tutorials/x/index"]],
    }


@pytest.mark.parametrize(
    ("pages", "on_disk", "error"),
    [
        (["how-to/a.md", "how-to/gone.md"], ["how-to/a.md"], "mapped page missing on disk: how-to/gone.md"),
        (["how-to/a.md"], ["how-to/a.md", "how-to/new.md"], "quadrant page missing from map.yaml: how-to/new.md"),
        (["how-to/a.md", "how-to/a.md"], ["how-to/a.md"], "duplicate map entry: how-to/a.md"),
        (["blog/a.md"], ["blog/a.md"], "blog/a.md: invalid quadrant"),
    ],
)
def test_a_map_that_disagrees_with_docs_names_each_defect(
    tmp_path: Path, pages: list[str], on_disk: list[str], error: str
) -> None:
    docs = _docs(tmp_path / "docs", on_disk)
    result = ts(NAV_TS, _QUADRANTS, pages=_map(*pages), docs=str(docs))
    assert error in result["errors"], result


# --- the built site: one registry edit, three menus ----------------------------------------------------------------


@pytest.fixture(scope="module")
def extra_build(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The site built over a fixture tree whose registry gains one section, ``Extra`` at order 45."""
    tmp = tmp_path_factory.mktemp("nav")
    root = fixture_tree(tmp / "tree")
    registry = json.loads(json.dumps(MAP))
    registry["sections"].append(
        {"key": "extra", "label": "Extra", "href": "herald/decks/", "owner": "herald", "order": 45}
    )
    write(root / "docs" / "map.yaml", yaml.safe_dump(registry, sort_keys=False))
    out = tmp / "site"
    done = astro_build(out, root=root)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    return out


@needs_astro
def test_ac3_the_built_sidebar_menu_and_doors_show_a_new_registry_entry(extra_build: Path) -> None:
    home = (extra_build / "index.html").read_text(encoding="utf-8")
    menu = home[home.index("pf-top-menu") : home.index("</nav>", home.index("pf-top-menu"))]
    doors = home[home.index("data-pf-doors") : home.index("</nav>", home.index("data-pf-doors"))]
    sidebar = home[home.index('id="starlight__sidebar"') :]
    for region in (menu, doors, sidebar):
        assert ">Extra<" in region.replace("\n", "").replace(" <", "<").replace("> ", ">"), region[:400]
    herald = (extra_build / "herald" / "index.html").read_text(encoding="utf-8")
    assert "data-pf-menu-link" in herald and ">Extra<" in herald.replace("\n", "").replace(" <", "<").replace("> ", ">")
