"""Parse-only measure: every live Marp deck loses zero notes and zero body lines (Story 32.2)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyforge.herald import pptx_native

_REPO_ROOT = Path(__file__).resolve().parents[5]
_MARP_GLOB = "presentations/*/src/marp/*-deck-*.md"
_IMAGE_ONLY = re.compile(r"^!\[[^\]]*\]\([^)]+\)\s*$")
_FENCE = re.compile(r"^```")
_HEADING = re.compile(r"^#{1,6}\s+")


def _deck_paths() -> list[Path]:
    return sorted(_REPO_ROOT.glob(_MARP_GLOB))


def _slide_source_lines(chunk: str) -> tuple[list[str], list[str]]:
    """Return (note_inners, body_lines) from raw slide chunk before parsing."""
    lines = chunk.splitlines()
    note_inners: list[str] = []
    body: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if "<!--" not in stripped:
            body.append(line)
            idx += 1
            continue
        open_pos = stripped.find("<!--")
        before = stripped[:open_pos]
        if before:
            body.append(before)
        comment_start = stripped[open_pos:]
        if "-->" in comment_start[4:]:
            inner = pptx_native._extract_comment_inner(comment_start, [], comment_start)
            if inner and not pptx_native._is_marp_directive_comment(inner):
                note_inners.append(inner)
            idx += 1
            continue
        rest: list[str] = []
        idx += 1
        while idx < len(lines):
            if "-->" in lines[idx]:
                inner = pptx_native._extract_comment_inner(comment_start, rest, lines[idx])
                if inner and not pptx_native._is_marp_directive_comment(inner):
                    note_inners.append(inner)
                idx += 1
                break
            rest.append(lines[idx])
            idx += 1
    return note_inners, body


def _body_line_counts_toward_text(line: str, *, first_heading_seen: bool) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("<!--"):
        return False
    if _FENCE.match(stripped):
        return False
    if re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", stripped):
        return False
    if _IMAGE_ONLY.match(stripped):
        return False
    cleaned = pptx_native._strip_inline_html(stripped)
    if not cleaned:
        return False
    if _HEADING.match(stripped) and not first_heading_seen:
        return True
    return True


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


def test_live_decks_zero_lost_notes_and_body_lines() -> None:
    paths = _deck_paths()
    assert paths, "expected live Marp decks under presentations/"
    lost_notes = 0
    lost_lines = 0
    slide_total = 0
    for path in paths:
        slug = path.parent.parent.parent.name
        text = path.read_text(encoding="utf-8")
        body = pptx_native._strip_front_matter(text)
        chunks = [part.strip() for part in body.split("\n---\n") if part.strip()]
        slides = pptx_native.parse_marp_deck(text, marp_dir=path.parent)
        assert len(slides) == len(chunks)
        for chunk, slide in zip(chunks, slides, strict=True):
            slide_total += 1
            note_inners, body_lines = _slide_source_lines(chunk)
            model_blob = _model_text_blobs(slide)
            for inner in note_inners:
                for fragment in inner.splitlines():
                    frag = fragment.strip()
                    if frag and frag not in model_blob and frag not in slide.notes:
                        lost_notes += 1
            first_heading = True
            for line in body_lines:
                if _HEADING.match(line.strip()):
                    if first_heading:
                        first_heading = False
                        continue
                if not _body_line_counts_toward_text(line, first_heading_seen=not first_heading):
                    continue
                cleaned = pptx_native._strip_inline_html(line.strip())
                if not cleaned:
                    continue
                if cleaned not in model_blob and cleaned not in slide.title:
                    lost_lines += 1
    assert lost_notes == 0, f"lost {lost_notes} note fragments across live decks"
    assert lost_lines == 0, f"lost {lost_lines} body lines across live decks"
    assert slide_total >= 200
