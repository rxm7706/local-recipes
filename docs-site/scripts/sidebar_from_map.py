#!/usr/bin/env python3
"""Generate Starlight sidebar JSON from docs/map.yaml (Story 27.3, CAP-52 D1).

``--check`` validates map paths, duplicates, and unmapped quadrant pages.
``--write`` emits ``docs-site/src/sidebar.generated.json`` (gitignored).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
MAP_PATH = DOCS_DIR / "map.yaml"
OUTPUT_PATH = REPO_ROOT / "docs-site" / "src" / "sidebar.generated.json"
QUADRANTS = ("tutorials", "how-to", "reference", "explanation")


def _load_map() -> list[dict[str, object]]:
    if not MAP_PATH.is_file():
        print(f"sidebar_from_map: missing {MAP_PATH}", file=sys.stderr)
        sys.exit(1)
    data = yaml.safe_load(MAP_PATH.read_text(encoding="utf-8"))
    pages = data.get("pages") if isinstance(data, dict) else None
    if not isinstance(pages, list):
        print("sidebar_from_map: docs/map.yaml has no pages list", file=sys.stderr)
        sys.exit(1)
    return pages


def _slug_from_path(rel_path: str) -> str:
    """Starlight slug for a docs-relative path (e.g. how-to/foo.md -> how-to/foo)."""
    slug = rel_path.removesuffix(".md")
    return slug


def _quadrant_pages_on_disk() -> set[str]:
    pages: set[str] = set()
    for quadrant in QUADRANTS:
        qdir = DOCS_DIR / quadrant
        if not qdir.is_dir():
            continue
        for page in qdir.rglob("*.md"):
            if page.parent == qdir and page.name == "README.md":
                continue
            pages.add(page.relative_to(DOCS_DIR).as_posix())
    return pages


def run_check(pages: list[dict[str, object]]) -> int:
    seen: dict[str, int] = {}
    mapped: set[str] = set()
    exit_code = 0

    for entry in pages:
        path = entry.get("path")
        if not isinstance(path, str):
            print("sidebar_from_map: page entry missing path", file=sys.stderr)
            exit_code = 1
            continue
        if path in seen:
            print(f"sidebar_from_map: duplicate map entry {path}", file=sys.stderr)
            exit_code = 1
        seen[path] = seen.get(path, 0) + 1
        mapped.add(path)
        target = DOCS_DIR / path
        if not target.is_file():
            print(f"sidebar_from_map: mapped page missing on disk: {path}", file=sys.stderr)
            exit_code = 1

    for rel in sorted(_quadrant_pages_on_disk() - mapped):
        print(f"sidebar_from_map: quadrant page not in map.yaml: {rel}", file=sys.stderr)
        exit_code = 1

    return exit_code


def run_write(pages: list[dict[str, object]]) -> None:
    groups: dict[str, list[str]] = defaultdict(list)
    quadrant_order: list[str] = []
    index_by_quadrant: dict[str, str] = {}

    for entry in pages:
        path = entry.get("path")
        quadrant = entry.get("quadrant")
        if not isinstance(path, str) or not isinstance(quadrant, str):
            continue
        if quadrant not in quadrant_order:
            quadrant_order.append(quadrant)
        if path.endswith(f"{quadrant}/README.md"):
            index_by_quadrant[quadrant] = _slug_from_path(path)
            continue
        groups[quadrant].append(_slug_from_path(path))

    sidebar: list[dict[str, object]] = []
    for quadrant in quadrant_order:
        label = quadrant.replace("-", " ").title()
        if quadrant == "how-to":
            label = "How-to"
        group: dict[str, object] = {"label": label, "items": []}
        if quadrant in index_by_quadrant:
            group["link"] = index_by_quadrant[quadrant]
        for slug in groups.get(quadrant, []):
            group["items"].append(slug)
        sidebar.append(group)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(sidebar, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate map.yaml against on-disk quadrant pages (exit 1 on drift).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write docs-site/src/sidebar.generated.json from map.yaml.",
    )
    args = parser.parse_args()
    if not args.check and not args.write:
        parser.error("specify --check and/or --write")

    pages = _load_map()
    code = 0
    if args.check:
        code = run_check(pages)
    if args.write and code == 0:
        run_write(pages)
    return code


if __name__ == "__main__":
    sys.exit(main())
