#!/usr/bin/env python3
"""Generate Starlight sidebar JSON from docs/map.yaml (Story 27.3, CAP-52 D1)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

_QUADRANTS = ("tutorials", "how-to", "reference", "explanation")
_QUADRANT_LABELS = {
    "tutorials": "Tutorials",
    "how-to": "How-to",
    "reference": "Reference",
    "explanation": "Explanation",
}


def _repo_root(docs_site_dir: Path) -> Path:
    return docs_site_dir.parent


def _docs_dir(repo_root: Path) -> Path:
    return repo_root / "docs"


def _default_output(docs_site_dir: Path) -> Path:
    return docs_site_dir / "src" / "sidebar.generated.json"


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


def build_sidebar(map_path: Path, docs_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    pages = _load_map(map_path)
    return _validate_and_build(pages, docs_dir)


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

    if not map_path.is_file():
        print(f"map not found: {map_path}", file=sys.stderr)
        return 1

    sidebar, errors = build_sidebar(map_path, docs_dir)
    if errors:
        for msg in errors:
            print(msg, file=sys.stderr)
        return 1

    if args.check:
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sidebar, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
