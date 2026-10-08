"""Unit tests for ``pyforge.herald.pptx_native`` slide-model parsing (Story 32.1)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pyforge.herald import pptx_native
from pyforge.herald.errors import HeraldError


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def _copy_modernist_tokens(dest_root: Path, *, source_root: Path | None = None) -> Path:
    src_root = source_root or _repo_root()
    src = src_root / pptx_native.MODERNIST_DESIGN_SYSTEM_REL
    dst = dest_root / pptx_native.MODERNIST_DESIGN_SYSTEM_REL
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def test_load_modernist_design_tokens_live_modernist() -> None:
    tokens = pptx_native.load_modernist_design_tokens(_repo_root())
    assert tokens.heading_family == "Archivo"
    assert tokens.body_family == "Archivo"
    assert tokens.heading_bold is True
    assert tokens.palette_bg == "#f3f2f2"
    assert tokens.palette_surface == "#eae9e9"
    assert tokens.palette_text == "#201e1d"
    assert tokens.palette_accent == "#ec3013"
    assert tokens.type_title_px == 64
    assert tokens.type_subtitle_px == 40
    assert tokens.type_body_px == 34
    assert tokens.type_small_px == 28
    assert tokens.type_kicker_px == 24
    assert tokens.pad_x_px == 120
    assert tokens.pad_top_px == 96
    assert tokens.pad_bottom_px == 120
    assert tokens.baseline_px == 48


def test_load_modernist_tokens_missing_theme_json(tmp_path: Path) -> None:
    base = _copy_modernist_tokens(tmp_path)
    (base / "theme.json").unlink()
    with pytest.raises(HeraldError, match="theme.json"):
        pptx_native.load_modernist_design_tokens(tmp_path, design_system_dir=base)


def test_load_modernist_tokens_missing_type_title(tmp_path: Path) -> None:
    base = _copy_modernist_tokens(tmp_path)
    template = base / "templates" / "deck" / "index.html"
    text = template.read_text(encoding="utf-8").replace("--type-title: 64px;", "")
    template.write_text(text, encoding="utf-8")
    with pytest.raises(HeraldError, match="type-title"):
        pptx_native.load_modernist_design_tokens(tmp_path, design_system_dir=base)


def test_load_modernist_tokens_malformed_theme_json(tmp_path: Path) -> None:
    base = _copy_modernist_tokens(tmp_path)
    theme = base / "theme.json"
    theme.write_text("{not json", encoding="utf-8")
    with pytest.raises(HeraldError, match="theme.json"):
        pptx_native.load_modernist_design_tokens(tmp_path, design_system_dir=base)


def test_load_modernist_tokens_malformed_pad_x(tmp_path: Path) -> None:
    base = _copy_modernist_tokens(tmp_path)
    template = base / "templates" / "deck" / "index.html"
    text = template.read_text(encoding="utf-8").replace("--pad-x: 120px;", "--pad-x: wide;")
    template.write_text(text, encoding="utf-8")
    with pytest.raises(HeraldError, match="pad-x"):
        pptx_native.load_modernist_design_tokens(tmp_path, design_system_dir=base)


def test_heading_weight_below_600_not_bold(tmp_path: Path) -> None:
    base = _copy_modernist_tokens(tmp_path)
    styles = base / "styles.css"
    styles.write_text(
        styles.read_text(encoding="utf-8").replace("--font-heading-weight: 800;", "--font-heading-weight: 400;"),
        encoding="utf-8",
    )
    tokens = pptx_native.load_modernist_design_tokens(tmp_path, design_system_dir=base)
    assert tokens.heading_bold is False


def test_slide_model_to_json_includes_tokens(tmp_path: Path) -> None:
    tokens = pptx_native.load_modernist_design_tokens(_repo_root())
    payload = pptx_native.slide_model_to_json((), tokens=tokens)
    assert "tokens" in payload
    assert payload["tokens"]["fonts"]["heading"] == "Archivo"
    assert payload["tokens"]["type"]["title"] == 64


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
    text = """# Image slide

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


def test_multiline_note_and_two_notes_joined(tmp_path: Path) -> None:
    marp_dir = tmp_path / "marp"
    marp_dir.mkdir()
    text = """# Slide

<!--
Line one.
Line two.
-->

<!-- second note -->

"""
    slides = pptx_native.parse_marp_deck(text, marp_dir=marp_dir)
    assert len(slides) == 1
    assert "Line one.\nLine two." in slides[0].notes
    assert "second note" in slides[0].notes
    assert "\n\n" in slides[0].notes


def test_directive_comments_are_not_notes(tmp_path: Path) -> None:
    marp_dir = tmp_path / "marp"
    marp_dir.mkdir()
    text = """<!-- _class: lead -->

# Title

<!-- paginate: false -->
"""
    slides = pptx_native.parse_marp_deck(text, marp_dir=marp_dir)
    assert slides[0].notes == ""


def test_todo_comment_is_a_note(tmp_path: Path) -> None:
    marp_dir = tmp_path / "marp"
    marp_dir.mkdir()
    text = """# T

<!-- todo: fix the chart -->
"""
    slides = pptx_native.parse_marp_deck(text, marp_dir=marp_dir)
    assert slides[0].notes == "todo: fix the chart"


def test_note_with_pipe_and_dash_stays_in_notes(tmp_path: Path) -> None:
    marp_dir = tmp_path / "marp"
    marp_dir.mkdir()
    text = """# T

<!-- a | b
- not a bullet -->
"""
    slides = pptx_native.parse_marp_deck(text, marp_dir=marp_dir)
    assert "|" in slides[0].notes
    assert slides[0].bullets == ()
    assert not any(isinstance(b, pptx_native.TableBlock) for b in slides[0].blocks)


def test_body_blocks_all_kinds_in_order(tmp_path: Path) -> None:
    marp_dir = tmp_path / "marp"
    marp_dir.mkdir()
    text = """###### KICKER

## Real title

Intro paragraph line.

1. first
2. second

| A | B |
|---|---|
| 1 | 2 |

| C | D |
|---|---|
| 3 | 4 |

```
code line
```

> quoted text

<div>Inline HTML</div>
"""
    slides = pptx_native.parse_marp_deck(text, marp_dir=marp_dir)
    slide = slides[0]
    assert slide.title == "KICKER"
    kinds = [type(b).__name__ for b in slide.blocks]
    assert kinds[0] == "HeadingBlock"
    assert kinds[1] == "ParagraphBlock"
    assert kinds[2] == "NumberedListBlock"
    assert kinds[3] == "TableBlock"
    assert kinds[4] == "TableBlock"
    assert kinds[5] == "CodeBlock"
    assert kinds[6] == "QuoteBlock"
    assert kinds[7] == "ParagraphBlock"
    assert slide.blocks[7].text == "Inline HTML"


def test_export_native_pptx_missing_modernist_raises_and_leaves_stub(tmp_path: Path, monkeypatch) -> None:
    slug = "no-tokens"
    marp_dir = tmp_path / "presentations" / slug / "src" / "marp"
    marp_dir.mkdir(parents=True)
    (marp_dir / f"{slug}-deck-2026-09-01.md").write_text("# One\n", encoding="utf-8")
    older = tmp_path / "presentations" / slug / "src" / "pptx" / f"{slug}-deck-native-2026-09-01.pptx"
    older.parent.mkdir(parents=True, exist_ok=True)
    older.write_bytes(b"keep-me")
    monkeypatch.setattr("pyforge.herald.stamps.write_stamp", lambda *_a, **_k: None)
    with pytest.raises(HeraldError, match="theme.json"):
        pptx_native.export_native_pptx(slug, tmp_path, export_date="2026-09-20")
    assert older.read_bytes() == b"keep-me"
    assert not (older.parent / f"{slug}-deck-native-2026-09-20.pptx").exists()


def test_run_node_driver_refuses_missing_node(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pptx_native.shutil, "which", lambda _name: None)
    model = tmp_path / "model.json"
    model.write_text('{"slides":[]}', encoding="utf-8")
    out = tmp_path / "out.pptx"
    with pytest.raises(HeraldError, match="node not on PATH"):
        pptx_native.run_node_driver(model, out)
