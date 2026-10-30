"""Shared listings, flag trees and marketplace directories for the marketplace test modules (Story 109.8).

``test_marketplace_pages.py`` held these until it was split by subject (``DW-steward-109-3-7``). Not a test module.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from pyforge.steward.marketplace_pages import FLAG_KEY, INDEX_VERSION, SCHEMA_ID


def _flags_tree(tmp_path: Path, *, dev: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    flags = {
        "flags": {
            FLAG_KEY: {
                "state": "ENABLED",
                "variants": {"on": True, "off": False},
                "defaultVariant": "off",
                "metadata": {
                    "owner": "steward",
                    "story": "109-3-a-marketplace-tree-renders-a-pages-index-from-listings",
                    "created": "2026-10-21",
                    "on_everywhere": "",
                    "cleanup_by": "",
                },
            }
        }
    }
    overlays = {
        "dev": {FLAG_KEY: dev},
        "staging": {FLAG_KEY: "off"},
        "production": {FLAG_KEY: "off"},
    }
    tree = tmp_path / "flags.json"
    tree.write_text(json.dumps(flags), encoding="utf-8")
    (tmp_path / "flag-overlays.json").write_text(json.dumps(overlays), encoding="utf-8")
    return tree


def _skill() -> dict:
    return {
        "id": "mason/environment",
        "kind": "skill",
        "scope": "mason",
        "slug": "environment",
        "name": "@mason/environment",
        "title": "Lock one environment",
        "description": "Resolve manifests into one lockfile.",
        "version": "0.1.0",
        "trust_tier": "unverified",
        "source": "estate-listings",
        "jobs": ["find", "install"],
        "path": "skills/mason/environment",
        "contribution_lane": "code-backed",
        "requires": {
            "packages": [
                {
                    "name": "pyforge-mason",
                    "published": False,
                    "note": "not on PyPI or conda-forge",
                }
            ]
        },
    }


def _marketplace(tmp_path: Path, rows: list[dict] | None = None, *, steps: str = "# Steps\n\nRun `x`.\n") -> Path:
    """A marketplace directory with ``index.yaml`` and one folder per skill row."""
    root = tmp_path / "marketplace"
    rows = [_skill()] if rows is None else rows
    for row in rows:
        if row.get("kind") == "skill":
            folder = root / row["path"]
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "SKILL.md").write_text(
                f"---\nname: {row['scope']}-{row['slug']}\n---\n\n# skill\n", encoding="utf-8"
            )
            (folder / "steps.md").write_text(steps, encoding="utf-8")
            (folder / "listing.yaml").write_text(yaml.safe_dump(row, sort_keys=False), encoding="utf-8")
    root.mkdir(parents=True, exist_ok=True)
    document = {"schema": SCHEMA_ID, "index_version": INDEX_VERSION, "listings": rows}
    (root / "index.yaml").write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return root


def _listing() -> dict:
    """``_skill()`` as the committed listings are shaped: the list form of ``requires`` and ``docs.steps``."""
    row = _skill()
    row["requires"] = [{"kind": "package", "name": "pyforge-mason", "published": False, "note": "404 on 2026-10-21"}]
    row["docs"] = {"steps": "steps.md", "card": "skills/mason/environment.html"}
    return row


def _module(name: str, **extra: object) -> dict:
    row = {
        "id": f"module/{name}",
        "kind": "module",
        "name": name,
        "trust_tier": "unverified",
        "source": "estate-listings",
    }
    row.update(extra)
    return row


def _tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
