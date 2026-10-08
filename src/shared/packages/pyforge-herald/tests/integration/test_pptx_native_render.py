"""Integration: Marp model -> Node driver -> python-pptx read-back (Story 32.1)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pptx import Presentation
from pptx.enum.dml import MSO_FILL
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

from pyforge.herald import pptx_native
from pyforge.herald.tests.unit.test_pptx_native import _copy_modernist_tokens, _repo_root


def _node_and_pptxgenjs_available() -> bool:
    if shutil.which("node") is None:
        return False
    prefix = __import__("os").environ.get("CONDA_PREFIX", "")
    if not prefix:
        return False
    return (Path(prefix) / "lib" / "node_modules" / "pptxgenjs-plus").is_dir()


@pytest.fixture
def _no_stamp_git(monkeypatch):
    monkeypatch.setattr("pyforge.herald.stamps.write_stamp", lambda *_a, **_k: None)


def _normalize_ws(text: str) -> str:
    return " ".join((text or "").split())


def _rgb_hex(rgb) -> str:
    if rgb is None:
        return ""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _slide_width_pt(prs: Presentation) -> float:
    return float(prs.slide_width) / 12700


def _expected_title_pt(tokens: pptx_native.ModernistDesignTokens, prs: Presentation) -> float:
    return tokens.type_title_px * (_slide_width_pt(prs) / tokens.canvas_width_px)


def _expected_pad_x_in(tokens: pptx_native.ModernistDesignTokens, prs: Presentation) -> float:
    slide_w_in = float(prs.slide_width) / 914400
    return tokens.pad_x_px * slide_w_in / tokens.canvas_width_px


def _first_run_with_text(slide, needle: str):
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                if needle in (run.text or ""):
                    return run
    return None


def _title_shape(slide):
    for shape in slide.shapes:
        if shape.has_text_frame and (shape.text_frame.text or "").strip():
            return shape
    return None


def _slide_text_surfaces_in_order(slide) -> str:
    parts: list[str] = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            chunk = shape.text_frame.text or ""
            if chunk.strip():
                parts.append(chunk)
        if shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    if cell.text and cell.text.strip():
                        parts.append(cell.text)
    return "\n".join(parts)


@pytest.mark.skipif(not _node_and_pptxgenjs_available(), reason="node or pptxgenjs-plus not installed")
def test_fixture_render_read_back_with_python_pptx(tmp_path: Path, monkeypatch, _no_stamp_git) -> None:
    _copy_modernist_tokens(tmp_path)
    slug = "fixture-deck"
    marp_dir = tmp_path / "presentations" / slug / "src" / "marp"
    marp_dir.mkdir(parents=True)
    marp_path = marp_dir / f"{slug}-deck-2026-09-01.md"
    marp_path.write_text(
        """---
marp: true
---

# Slide one

- alpha
- beta

Intro paragraph for slide one.

<!--
Multi-line
speaker note.
-->

---

###### Kicker

## Metrics

1. first metric
2. second metric

| K | V |
|---|---|
| a | 1 |

```
print("code")
```

> A quoted line

<!-- metrics notes -->
""",
        encoding="utf-8",
    )
    marp_text = marp_path.read_text(encoding="utf-8")
    expected_slides = pptx_native.parse_marp_deck(marp_text, marp_dir=marp_dir)
    fixed = datetime(2026, 9, 20, tzinfo=timezone.utc)
    result = pptx_native.export_native_pptx(
        slug,
        tmp_path,
        export_date="2026-09-20",
        now=fixed,
    )
    assert result.output_path.name == f"{slug}-deck-native-2026-09-20.pptx"
    prs = Presentation(str(result.output_path))
    assert len(prs.slides) == len(expected_slides)
    for slide, model in zip(prs.slides, expected_slides, strict=True):
        for shape in slide.shapes:
            assert shape.shape_type != MSO_SHAPE_TYPE.PICTURE
        if model.notes:
            notes_text = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
            assert _normalize_ws(model.notes) in _normalize_ws(notes_text)
        joined_frames = _slide_text_surfaces_in_order(slide)
        for block in model.blocks:
            if isinstance(block, pptx_native.ParagraphBlock):
                assert block.text in joined_frames
            elif isinstance(block, pptx_native.HeadingBlock):
                assert block.text in joined_frames
            elif isinstance(block, pptx_native.BulletListBlock):
                for item in block.items:
                    assert item.text in joined_frames
            elif isinstance(block, pptx_native.NumberedListBlock):
                for item in block.items:
                    assert item.text in joined_frames
            elif isinstance(block, pptx_native.TableBlock):
                for row in block.rows:
                    for cell in row:
                        assert cell in joined_frames
            elif isinstance(block, pptx_native.CodeBlock):
                assert block.text.splitlines()[0] in joined_frames
            elif isinstance(block, pptx_native.QuoteBlock):
                assert block.text in joined_frames
        assert model.title in joined_frames


@pytest.mark.skipif(not _node_and_pptxgenjs_available(), reason="node or pptxgenjs-plus not installed")
def test_second_run_retires_older_native_kind(tmp_path: Path, _no_stamp_git) -> None:
    slug = "retire-deck"
    marp_dir = tmp_path / "presentations" / slug / "src" / "marp"
    marp_dir.mkdir(parents=True)
    (marp_dir / f"{slug}-deck-2026-09-01.md").write_text("# One\n", encoding="utf-8")
    older = tmp_path / "presentations" / slug / "src" / "pptx" / f"{slug}-deck-native-2026-09-01.pptx"
    older.parent.mkdir(parents=True, exist_ok=True)
    older.write_bytes(b"old-native")
    pptx_native.export_native_pptx(slug, tmp_path, export_date="2026-09-20")
    remaining = list(older.parent.glob(f"{slug}-deck-native-*.pptx"))
    assert len(remaining) == 1
    assert remaining[0].name == f"{slug}-deck-native-2026-09-20.pptx"
