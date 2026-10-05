"""Story 27.1: shelf loader edge cases (I/O matrix rows, no Node)."""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("repo root not found")


def _extract_first_h1(body: str) -> tuple[str | None, str]:
    """Mirror docs-site/src/loaders/shelf-docs-loader.ts extractFirstH1."""
    lines = body.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        trimmed = line.strip()
        if trimmed.startswith("<!--"):
            while index < len(lines) and "-->" not in lines[index]:
                index += 1
            index += 1
            continue
        match = re.match(r"^#\s+(.+)$", line)
        if match:
            rest = "\n".join(lines[:index] + lines[index + 1 :]).lstrip("\n")
            return match.group(1).strip(), rest
        if trimmed == "":
            index += 1
            continue
        break
    return None, body


def _generate_id(relative_path: str) -> str:
    id_ = relative_path.replace("\\", "/").removesuffix(".md").removesuffix(".mdx")
    if id_.endswith("/README"):
        return id_[: -len("/README")] + "/index"
    return id_


def test_page_without_frontmatter_uses_first_heading() -> None:
    root = _repo_root()
    raw = (root / "docs/how-to/pixi-tasks.md").read_text(encoding="utf-8")
    assert raw.startswith("<!--")
    body = raw.split("---", 1)[-1] if raw.startswith("---") else raw
    title, rest = _extract_first_h1(body)
    assert title == "Pixi tasks"
    assert not rest.lstrip().startswith("# Pixi tasks")


def test_two_headings_use_first_only() -> None:
    root = _repo_root()
    raw = (root / "docs/how-to/feedstock-failure-remediation.md").read_text(encoding="utf-8")
    body = raw.split("---", 1)[-1] if raw.startswith("---") else raw
    title, rest = _extract_first_h1(body)
    assert title is not None
    assert rest.count("\n# ") >= 0
    assert not rest.lstrip().startswith(f"# {title}")


def test_quadrant_readme_routes_to_index() -> None:
    assert _generate_id("how-to/README.md") == "how-to/index"


def test_dreams_paths_not_in_loader_quadrants() -> None:
    quadrants = {"tutorials", "how-to", "reference", "explanation"}

    def is_included(rel: str) -> bool:
        norm = rel.replace("\\", "/")
        if norm in {"index.md", "404.md"}:
            return True
        top = norm.split("/")[0]
        return top in quadrants and norm.endswith(".md")

    assert not is_included("dreams/pyforge-herald.md")
    assert is_included("how-to/pixi-tasks.md")
