"""Story 27.3: sidebar_from_map.py reads docs/map.yaml order."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]
_SCRIPT = REPO_ROOT / "docs-site" / "scripts" / "sidebar_from_map.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("sidebar_from_map_under_test", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sidebar_mod():
    return _load_module()


def _write_map(tmp_path: Path, pages: list[dict]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    map_path = tmp_path / "map.yaml"
    map_path.write_text(
        yaml.safe_dump({"schema_version": 1, "pages": pages}, sort_keys=False),
        encoding="utf-8",
    )
    return map_path


def _touch_docs(docs_dir: Path, rel: str, body: str = "# x\n") -> None:
    path = docs_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_live_map_generates_with_no_finding(sidebar_mod, capsys):
    repo_docs = REPO_ROOT / "docs"
    map_path = repo_docs / "map.yaml"
    sidebar, errors = sidebar_mod.build_sidebar(map_path, repo_docs)
    assert errors == []
    assert sidebar
    assert capsys.readouterr().err == ""


def test_order_preserved_in_fixture(sidebar_mod, tmp_path: Path):
    docs = tmp_path / "docs"
    pages = [
        {"path": "tutorials/README.md", "quadrant": "tutorials"},
        {"path": "tutorials/alpha.md", "quadrant": "tutorials"},
        {"path": "tutorials/beta.md", "quadrant": "tutorials"},
    ]
    for rel in ("tutorials/README.md", "tutorials/alpha.md", "tutorials/beta.md"):
        _touch_docs(docs, rel)
    map_path = _write_map(tmp_path, pages)
    sidebar, errors = sidebar_mod.build_sidebar(map_path, docs)
    assert errors == []
    slugs = [item["slug"] for item in sidebar[0]["items"] if "slug" in item]
    assert slugs == ["tutorials/alpha", "tutorials/beta"]


def test_swapping_two_entries_swaps_output(sidebar_mod, tmp_path: Path):
    docs = tmp_path / "docs"
    base = [
        {"path": "how-to/README.md", "quadrant": "how-to"},
        {"path": "how-to/first.md", "quadrant": "how-to"},
        {"path": "how-to/second.md", "quadrant": "how-to"},
    ]
    for rel in ("how-to/README.md", "how-to/first.md", "how-to/second.md"):
        _touch_docs(docs, rel)
    map_a = _write_map(tmp_path / "a", base)
    map_b = _write_map(
        tmp_path / "b",
        [base[0], base[2], base[1]],
    )
    side_a, _ = sidebar_mod.build_sidebar(map_a, docs)
    side_b, _ = sidebar_mod.build_sidebar(map_b, docs)
    slugs_a = [i["slug"] for i in side_a[0]["items"] if "slug" in i]
    slugs_b = [i["slug"] for i in side_b[0]["items"] if "slug" in i]
    assert slugs_a == ["how-to/first", "how-to/second"]
    assert slugs_b == ["how-to/second", "how-to/first"]


def test_missing_mapped_page_exits_one(sidebar_mod, tmp_path: Path, capsys):
    docs = tmp_path / "docs"
    _touch_docs(docs, "reference/README.md")
    map_path = _write_map(
        tmp_path,
        [
            {"path": "reference/README.md", "quadrant": "reference"},
            {"path": "reference/missing.md", "quadrant": "reference"},
        ],
    )
    _, errors = sidebar_mod.build_sidebar(map_path, docs)
    assert any("missing on disk" in e and "reference/missing.md" in e for e in errors)
    rc = sidebar_mod.main(["--map", str(map_path), "--docs", str(docs), "--check"])
    assert rc == 1
    assert "reference/missing.md" in capsys.readouterr().err


def test_unmapped_quadrant_page_exits_one(sidebar_mod, tmp_path: Path):
    docs = tmp_path / "docs"
    _touch_docs(docs, "explanation/README.md")
    _touch_docs(docs, "explanation/orphan.md")
    map_path = _write_map(
        tmp_path,
        [{"path": "explanation/README.md", "quadrant": "explanation"}],
    )
    _, errors = sidebar_mod.build_sidebar(map_path, docs)
    assert any("missing from map.yaml" in e and "explanation/orphan.md" in e for e in errors)


def test_duplicate_map_entry_exits_one(sidebar_mod, tmp_path: Path):
    docs = tmp_path / "docs"
    _touch_docs(docs, "tutorials/README.md")
    _touch_docs(docs, "tutorials/dup.md")
    dup = {"path": "tutorials/dup.md", "quadrant": "tutorials"}
    map_path = _write_map(
        tmp_path,
        [
            {"path": "tutorials/README.md", "quadrant": "tutorials"},
            dup,
            dup,
        ],
    )
    _, errors = sidebar_mod.build_sidebar(map_path, docs)
    assert any("duplicate" in e and "tutorials/dup.md" in e for e in errors)


def test_quadrant_readme_is_group_index_not_sibling(sidebar_mod, tmp_path: Path):
    docs = tmp_path / "docs"
    _touch_docs(docs, "how-to/README.md")
    _touch_docs(docs, "how-to/step.md")
    map_path = _write_map(
        tmp_path,
        [
            {"path": "how-to/README.md", "quadrant": "how-to"},
            {"path": "how-to/step.md", "quadrant": "how-to"},
        ],
    )
    sidebar, errors = sidebar_mod.build_sidebar(map_path, docs)
    assert errors == []
    group = sidebar[0]
    assert group["collapsed"] is False
    assert group["items"][0] == {"link": "/how-to/", "label": "How-to"}
    assert group["items"][1:] == [{"slug": "how-to/step"}]
