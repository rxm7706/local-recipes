"""Parse-only measure: every live Marp deck loses zero notes and zero body lines (Story 32.2)."""

from __future__ import annotations

import re
from pathlib import Path

from pyforge.herald import pptx_native
from pyforge.herald.errors import HeraldError

_REPO_ROOT = Path(__file__).resolve().parents[6]
_IMAGE_ONLY = re.compile(r"^!\[[^\]]*\]\([^)]+\)\s*$")
_FENCE = re.compile(r"^```")
_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")


def _current_deck_paths() -> list[Path]:
    paths: list[Path] = []
    for marp_dir in sorted(_REPO_ROOT.glob("presentations/*/src/marp")):
        slug = marp_dir.parent.parent.name
        try:
            paths.append(pptx_native.find_current_deck_marp(slug, _REPO_ROOT))
        except HeraldError:
            continue
    return paths


def _model_text_blobs(slide: pptx_native.SlideModel) -> str:
    parts: list[str] = [slide.title, slide.notes]
    for block in slide.blocks:
        if isinstance(block, pptx_native.HeadingBlock):
            parts.append(block.text)
        elif isinstance(block, pptx_native.ParagraphBlock):
            parts.append(block.text)
        elif isinstance(block, pptx_native.BulletListBlock):
            parts.extend(item.text for item in block.items)
        elif isinstance(block, pptx_native.NumberedListBlock):
            parts.extend(item.text for item in block.items)
        elif isinstance(block, pptx_native.TableBlock):
            for row in block.rows:
                parts.extend(row)
        elif isinstance(block, pptx_native.CodeBlock):
            parts.append(block.text)
        elif isinstance(block, pptx_native.QuoteBlock):
            parts.append(block.text)
    return "\n".join(parts)


def _text_fragments_from_body_line(line: str, *, first_heading: bool) -> list[str]:
    stripped = line.strip()
    if not stripped:
        return []
    if _FENCE.match(stripped):
        return []
    if re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", stripped):
        return []
    if _IMAGE_ONLY.match(stripped):
        return []
    heading = _HEADING.match(stripped)
    if heading:
        text = heading.group(2).strip()
        if first_heading:
            return [text]
        return [text]
    bullet = _BULLET.match(line)
    if bullet:
        return [bullet.group(2).strip()]
    numbered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
    if numbered:
        return [numbered.group(2).strip()]
    if "|" in stripped:
        return [cell.strip() for cell in stripped.strip("|").split("|") if cell.strip()]
    cleaned = pptx_native._strip_inline_html(stripped)
    if not cleaned:
        return []
    return [cleaned]


def test_live_decks_zero_lost_notes_and_body_lines() -> None:
    paths = _current_deck_paths()
    assert len(paths) == 15, f"expected 15 current Marp decks, found {len(paths)}"
    slide_total = 0
    lost_notes = 0
    lost_lines = 0
    lost_line_samples: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        body = pptx_native._strip_front_matter(text)
        chunks = [part.strip() for part in body.split("\n---\n") if part.strip()]
        slides = pptx_native.parse_marp_deck(text, marp_dir=path.parent)
        assert len(slides) == len(chunks)
        for chunk, slide in zip(chunks, slides, strict=True):
            slide_total += 1
            model_blob = _model_text_blobs(slide)
            notes, body_lines = pptx_native._partition_notes_and_body(chunk.splitlines())
            for fragment in notes.splitlines():
                frag = fragment.strip()
                if frag and frag not in model_blob and frag not in slide.notes:
                    lost_notes += 1
            first_heading = True
            in_fence = False
            for line in body_lines:
                stripped = line.strip()
                if _FENCE.match(stripped):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    if stripped and stripped not in model_blob:
                        lost_lines += 1
                        if len(lost_line_samples) < 5:
                            lost_line_samples.append(f"{path.name}: {stripped!r}")
                    continue
                frags = _text_fragments_from_body_line(line, first_heading=first_heading)
                if _HEADING.match(stripped) and first_heading:
                    first_heading = False
                for frag in frags:
                    if frag in model_blob or frag == slide.title:
                        continue
                    lost_lines += 1
                    if len(lost_line_samples) < 5:
                        lost_line_samples.append(f"{path.name}: {frag!r}")
    assert lost_notes == 0, f"lost {lost_notes} note fragments across live decks"
    assert lost_lines == 0, (
        f"lost {lost_lines} body text fragments across live decks: {lost_line_samples}"
    )
    assert slide_total >= 200
