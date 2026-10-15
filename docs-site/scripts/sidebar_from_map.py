#!/usr/bin/env python3
"""Generate Starlight sidebar JSON from docs/map.yaml (Story 27.3, CAP-52 D1).

Story 40.1 (CAP-58): after the four quadrants the sidebar gains a first-level Herald group, and a
second output, ``topnav.generated.json``, carries the top menu shared by the docs and herald pages.
Both come from herald's one navigation list, ``docsite/content/site.yml`` (``nav`` then
``neighbours``), read here as data. Herald hrefs are relative to the ``/herald/`` mount; they are
turned into site-root paths (``herald/``, ``dashboard/kedro-viz/``, ``""`` for the docs root) so the
Starlight build can prefix whichever base path the host gives it.

Story 42.2 (CAP-60): an entry carrying ``mount: kedro-viz`` is kept only when atlas's Kedro-Viz export
is in the build input (``docs/dashboard/kedro-viz/``, decided by ``docsite/tools/kedro_viz_export.py``
as the herald build decides it); the top-menu JSON marks the kept entry with its ``mount`` so the Astro
config writes the ``/kedro-viz/`` redirect only when the mount exists."""

from __future__ import annotations

import argparse
import json
import posixpath
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "docsite" / "tools"))
import kedro_viz_export as kv  # noqa: E402

_QUADRANTS = ("tutorials", "how-to", "reference", "explanation")
_QUADRANT_LABELS = {
    "tutorials": "Tutorials",
    "how-to": "How-to",
    "reference": "Reference",
    "explanation": "Explanation",
}

_HERALD_GROUP_LABEL = "Herald"
#: Where docsite's output is mounted in the Pages artifact (assemble_pages.HERALD_PREFIX).
_HERALD_MOUNT = "herald"
#: The site.yml nav key of the link back to the docs root; it is in the top menu, not the Herald group.
_DOCS_KEY = "docs"


def _repo_root(docs_site_dir: Path) -> Path:
    return docs_site_dir.parent


def _docs_dir(repo_root: Path) -> Path:
    return repo_root / "docs"


def _default_output(docs_site_dir: Path) -> Path:
    return docs_site_dir / "src" / "sidebar.generated.json"


def _default_topnav_output(docs_site_dir: Path) -> Path:
    return docs_site_dir / "src" / "topnav.generated.json"


def _default_site_yml(repo_root: Path) -> Path:
    return repo_root / "docsite" / "content" / "site.yml"


def _site_root_path(herald_href: str) -> str:
    """A site.yml href (relative to the ``/herald/`` mount) as a path relative to the site root.

    ``index.html`` -> ``herald/``; ``dossier/index.html`` -> ``herald/dossier/``;
    ``../dashboard/kedro-viz/`` -> ``dashboard/kedro-viz/``; ``../`` -> ``""`` (the docs root).
    A path that climbs above the site root is refused."""
    href = herald_href.strip()
    if not href or href.startswith(("/", "#")) or "://" in href:
        raise ValueError(f"site.yml href must be relative to the herald mount: {herald_href!r}")
    is_dir = href.endswith(("/", "index.html"))
    href = href.removesuffix("index.html")
    joined = posixpath.normpath(posixpath.join(_HERALD_MOUNT, href))
    if joined == ".":
        return ""
    if joined.startswith(".."):
        raise ValueError(f"site.yml href leaves the site root: {herald_href!r}")
    return f"{joined}/" if is_dir else joined


def load_site_menu(site_yml: Path, *, kedro_viz: bool = True) -> list[dict[str, str]]:
    """The shared menu, in order: site.yml ``nav`` then ``neighbours``, as ``{label, path}``.

    ``kedro_viz=False`` (no export in the build input) drops the entries that need the mount."""
    data = yaml.safe_load(site_yml.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("nav"), list):
        raise ValueError(f"{site_yml}: expected a nav list")
    menu: list[dict[str, str]] = []
    for item in kv.menu_entries([*data["nav"], *(data.get("neighbours") or [])], present=kedro_viz):
        label, href = item.get("label"), item.get("href")
        if not isinstance(label, str) or not isinstance(href, str):
            raise ValueError(f"{site_yml}: menu entry needs a label and an href: {item!r}")
        menu.append(
            {
                "label": label,
                "path": _site_root_path(href),
                "key": str(item.get("key") or ""),
                "mount": str(item.get(kv.MOUNT_KEY) or ""),
            }
        )
    if not any(entry["key"] == _DOCS_KEY for entry in menu):
        raise ValueError(f"{site_yml}: nav has no '{_DOCS_KEY}' entry linking back to the docs")
    return menu


def herald_sidebar_group(menu: list[dict[str, str]]) -> dict[str, Any]:
    """The first-level Herald group: every menu entry except the link back to the docs."""
    return {
        "label": _HERALD_GROUP_LABEL,
        "collapsed": False,
        "items": [
            {"link": f"/{entry['path']}", "label": entry["label"]}
            for entry in menu
            if entry["key"] != _DOCS_KEY
        ],
    }


def top_menu(menu: list[dict[str, str]]) -> list[dict[str, str]]:
    """The top menu, in site.yml order, as ``{label, path}`` (path relative to the site root), plus
    ``mount`` on an entry that exists only with a mounted export (Story 42.2)."""
    return [
        {"label": entry["label"], "path": entry["path"], **({"mount": entry["mount"]} if entry.get("mount") else {})}
        for entry in menu
    ]


def _quadrant_index_path(quadrant: str) -> str:
    return f"{quadrant}/README.md"


def _path_to_slug(docs_relative: str) -> str:
    """Match docs-site/src/loaders/shelf-docs-loader.ts ``generateId``."""
    path = docs_relative
    if path.endswith(".md"):
        path = path[: -len(".md")]
    elif path.endswith(".mdx"):
        path = path[: -len(".mdx")]
    if path.endswith("/README"):
        return f"{path[: -len('/README')]}/index"
    return path


def _index_link_path(index_slug: str) -> str:
    if index_slug.endswith("/index"):
        return f"/{index_slug[: -len('/index')]}/"
    return f"/{index_slug}/"


def _quadrant_pages_on_disk(docs_dir: Path) -> set[str]:
    pages: set[str] = set()
    for quadrant in _QUADRANTS:
        qdir = docs_dir / quadrant
        if not qdir.is_dir():
            continue
        for page in qdir.rglob("*.md"):
            if page.parent == qdir and page.name == "README.md":
                continue
            pages.add(page.relative_to(docs_dir).as_posix())
    return pages


def _load_map(map_path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(map_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("pages"), list):
        raise ValueError(f"{map_path}: expected top-level pages list")
    return data["pages"]


def _validate_and_build(
    pages: list[dict[str, Any]],
    docs_dir: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (sidebar groups, error messages)."""
    errors: list[str] = []
    seen: set[str] = set()
    by_quadrant: dict[str, list[str]] = defaultdict(list)
    quadrant_order: list[str] = []

    for entry in pages:
        path = entry.get("path")
        quadrant = entry.get("quadrant")
        if not isinstance(path, str) or not path:
            errors.append("map entry missing path")
            continue
        if path in seen:
            errors.append(f"duplicate map entry: {path}")
            continue
        seen.add(path)
        if not isinstance(quadrant, str) or quadrant not in _QUADRANTS:
            errors.append(f"{path}: invalid quadrant")
            continue
        if quadrant not in quadrant_order:
            quadrant_order.append(quadrant)
        by_quadrant[quadrant].append(path)

    mapped_paths = seen
    for path in sorted(mapped_paths):
        if not (docs_dir / path).is_file():
            errors.append(f"mapped page missing on disk: {path}")

    for rel in sorted(_quadrant_pages_on_disk(docs_dir) - mapped_paths):
        errors.append(f"quadrant page missing from map.yaml: {rel}")

    if errors:
        return [], errors

    sidebar: list[dict[str, Any]] = []
    for quadrant in quadrant_order:
        index_path = _quadrant_index_path(quadrant)
        items: list[dict[str, str]] = []
        for path in by_quadrant[quadrant]:
            if path == index_path:
                continue
            items.append({"slug": _path_to_slug(path)})
        index_slug = _path_to_slug(index_path)
        group: dict[str, Any] = {
            "label": _QUADRANT_LABELS[quadrant],
            "collapsed": False,
            "items": [
                {
                    "link": _index_link_path(index_slug),
                    "label": _QUADRANT_LABELS[quadrant],
                },
                *items,
            ],
        }
        sidebar.append(group)
    return sidebar, []


def build_sidebar(
    map_path: Path, docs_dir: Path, site_yml: Path | None = None, *, kedro_viz: bool = True
) -> tuple[list[dict[str, Any]], list[str]]:
    """The quadrant groups in map.yaml order, then the Herald group when ``site_yml`` is given."""
    pages = _load_map(map_path)
    sidebar, errors = _validate_and_build(pages, docs_dir)
    if errors or site_yml is None:
        return sidebar, errors
    try:
        menu = load_site_menu(site_yml, kedro_viz=kedro_viz)
    except ValueError as exc:
        return [], [str(exc)]
    return [*sidebar, herald_sidebar_group(menu)], []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--map",
        type=Path,
        help="Path to docs/map.yaml (default: <repo>/docs/map.yaml)",
    )
    parser.add_argument(
        "--docs",
        type=Path,
        help="Path to docs/ directory (default: <repo>/docs)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON path (default: docs-site/src/sidebar.generated.json)",
    )
    parser.add_argument(
        "--site",
        type=Path,
        help="Path to herald's docsite/content/site.yml (default: <repo>/docsite/content/site.yml)",
    )
    parser.add_argument(
        "--topnav-output",
        type=Path,
        help="Top-menu JSON path (default: docs-site/src/topnav.generated.json)",
    )
    parser.add_argument(
        "--kedro-viz-export",
        type=Path,
        help="The Kedro-Viz build input (default: <repo>/docs/dashboard/kedro-viz); absent or empty = no menu entry",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate only; exit 1 on any finding without writing output",
    )
    args = parser.parse_args(argv)

    docs_site_dir = Path(__file__).resolve().parent.parent
    repo_root = _repo_root(docs_site_dir)
    map_path = args.map or (repo_root / "docs" / "map.yaml")
    docs_dir = args.docs or _docs_dir(repo_root)
    output = args.output or _default_output(docs_site_dir)
    site_yml = args.site or _default_site_yml(repo_root)
    topnav_output = args.topnav_output or _default_topnav_output(docs_site_dir)
    kedro_viz = kv.is_present(args.kedro_viz_export or kv.input_dir(repo_root))

    if not map_path.is_file():
        print(f"map not found: {map_path}", file=sys.stderr)
        return 1
    if not site_yml.is_file():
        print(f"site.yml not found: {site_yml}", file=sys.stderr)
        return 1

    sidebar, errors = build_sidebar(map_path, docs_dir, site_yml, kedro_viz=kedro_viz)
    if errors:
        for msg in errors:
            print(msg, file=sys.stderr)
        return 1

    if args.check:
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sidebar, indent=2) + "\n", encoding="utf-8")
    topnav_output.parent.mkdir(parents=True, exist_ok=True)
    topnav_output.write_text(
        json.dumps(top_menu(load_site_menu(site_yml, kedro_viz=kedro_viz)), indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
