"""Unit tests for ``pyforge.herald.pptx_native`` slide-model parsing (Story 32.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.herald import pptx_native
from pyforge.herald.errors import HeraldError


def test_parse_marp_deck_title_bullets_table_and_notes(tmp_path: Path) -> None:
    marp_dir = tmp_path / "marp"
    marp_dir.mkdir()
    text = """---
marp: true
---

# First slide

- one
- two

<!-- Speaker note for slide one -->

---

## Table slide

| A | B |
|---|---|
| 1 | 2 |

<!-- table notes -->
"""
    slides = pptx_native.parse_marp_deck(text, marp_dir=marp_dir)
    assert len(slides) == 2
    assert slides[0].title == "First slide"
    assert slides[0].bullets == ("one", "two")
    assert slides[0].notes == "Speaker note for slide one"
    assert slides[0].table is None
    assert slides[1].title == "Table slide"
    assert slides[1].table == (("A", "B"), ("1", "2"))
    assert slides[1].notes == "table notes"


def test_parse_marp_skips_marp_directive_comments(tmp_path: Path) -> None:
    marp_dir = tmp_path / "marp"
    marp_dir.mkdir()
    text = """---
marp: true
---

<!-- _class: lead -->

# Title only

<!-- real note -->
"""
    slides = pptx_native.parse_marp_deck(text, marp_dir=marp_dir)
    assert len(slides) == 1
    assert slides[0].title == "Title only"
    assert slides[0].notes == "real note"


def test_parse_marp_image_path_resolves_relative_to_marp_dir(tmp_path: Path) -> None:
    marp_dir = tmp_path / "marp"
    marp_dir.mkdir()
    img = marp_dir / "pic.png"
    img.write_bytes(b"png")
    text = f"""# Image slide

![diagram](pic.png)
"""
    slides = pptx_native.parse_marp_deck(text, marp_dir=marp_dir)
    assert len(slides) == 1
    assert len(slides[0].images) == 1
    assert slides[0].images[0].path == str(img.resolve())


def test_find_current_deck_marp_picks_newest_date(tmp_path: Path) -> None:
    slug = "demo"
    marp_dir = tmp_path / "presentations" / slug / "src" / "marp"
    marp_dir.mkdir(parents=True)
    older = marp_dir / f"{slug}-deck-2026-09-01.md"
    newer = marp_dir / f"{slug}-deck-2026-09-15.md"
    older.write_text("# old\n", encoding="utf-8")
    newer.write_text("# new\n", encoding="utf-8")
    assert pptx_native.find_current_deck_marp(slug, tmp_path) == newer


def test_find_current_deck_marp_missing_raises() -> None:
    with pytest.raises(HeraldError, match="no Marp deck source"):
        pptx_native.find_current_deck_marp("missing", Path("/nonexistent/root"))


def test_run_node_driver_refuses_missing_node(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pptx_native.shutil, "which", lambda _name: None)
    model = tmp_path / "model.json"
    model.write_text('{"slides":[]}', encoding="utf-8")
    out = tmp_path / "out.pptx"
    with pytest.raises(HeraldError, match="node not on PATH"):
        pptx_native.run_node_driver(model, out)
