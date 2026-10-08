"""Native editable PPTX export via pptxgenjs-plus (Story 32.1, CAP-57)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyforge.core.flags import read_boolean

from . import deck_versions, stamps
from .deck_pipeline import _newest_dated_match
from .errors import HeraldError

DECK_EXPORT_NATIVE_FLAG = "pyforge.herald.deck_export_native"

MODERNIST_DESIGN_SYSTEM_REL = Path("presentations") / "_design-systems" / "modernist"
DESIGN_TOKEN_CANVAS_WIDTH_PX = 1920
DESIGN_TOKEN_CANVAS_HEIGHT_PX = 1080

_CSS_CUSTOM_PROPERTY_PX = re.compile(
    r"--(?P<name>[\w-]+)\s*:\s*(?P<value>\d+(?:\.\d+)?)\s*px",
    re.IGNORECASE,
)
_FONT_HEADING_WEIGHT = re.compile(
    r"--font-heading-weight\s*:\s*(?P<value>\d+(?:\.\d+)?)\s*;",
    re.IGNORECASE,
)

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.*)$")
_BULLET_RE = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_FENCE_RE = re.compile(r"^```")

_MARP_GLOBAL_DIRECTIVES = frozenset(
    {
        "theme",
        "style",
        "headingDivider",
        "size",
        "math",
        "title",
        "description",
        "author",
        "image",
        "keywords",
        "url",
        "marp",
        "lang",
    }
)
_MARP_LOCAL_DIRECTIVES = frozenset(
    {
        "paginate",
        "header",
        "footer",
        "class",
        "backgroundColor",
        "backgroundImage",
        "backgroundPosition",
        "backgroundRepeat",
        "backgroundSize",
        "color",
    }
)


@dataclass(frozen=True, slots=True)
class SlideImage:
    alt: str
    path: str


@dataclass(frozen=True, slots=True)
class HeadingBlock:
    level: int
    text: str


@dataclass(frozen=True, slots=True)
class ParagraphBlock:
    text: str


@dataclass(frozen=True, slots=True)
class BulletItem:
    text: str
    depth: int


@dataclass(frozen=True, slots=True)
class BulletListBlock:
    items: tuple[BulletItem, ...]


@dataclass(frozen=True, slots=True)
class NumberedItem:
    number: str
    text: str


@dataclass(frozen=True, slots=True)
class NumberedListBlock:
    items: tuple[NumberedItem, ...]


@dataclass(frozen=True, slots=True)
class TableBlock:
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class CodeBlock:
    text: str


@dataclass(frozen=True, slots=True)
class QuoteBlock:
    text: str


BodyBlock = HeadingBlock | ParagraphBlock | BulletListBlock | NumberedListBlock | TableBlock | CodeBlock | QuoteBlock


@dataclass(frozen=True, slots=True)
class SlideModel:
    title: str = ""
    bullets: tuple[str, ...] = ()
    table: tuple[tuple[str, ...], ...] | None = None
    notes: str = ""
    images: tuple[SlideImage, ...] = ()
    blocks: tuple[BodyBlock, ...] = ()


@dataclass(frozen=True, slots=True)
class DeckNativeExportResult:
    output_path: Path
    marp_source: Path
    slide_count: int


def deck_export_native_enabled(*, flags_path: Path | str | None = None) -> bool:
    return read_boolean(DECK_EXPORT_NATIVE_FLAG, default=False, flags_path=flags_path)


def find_current_deck_marp(slug: str, repo_root: Path) -> Path:
    """Newest ``presentations/<slug>/src/marp/<slug>-deck-<date>.md``."""
    marp_dir = repo_root / "presentations" / slug / "src" / "marp"
    path = _newest_dated_match(marp_dir, f"{slug}-deck-", ".md")
    if path is None:
        raise HeraldError(
            f"pptx-native: no Marp deck source for {slug!r} under {marp_dir} (expected {slug}-deck-<YYYY-MM-DD>.md)"
        )
    return path


def _strip_front_matter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2]


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and "|" in stripped and not stripped.startswith("<!--")


def _parse_table_rows(lines: list[str], start: int) -> tuple[tuple[tuple[str, ...], ...] | None, int]:
    rows: list[tuple[str, ...]] = []
    idx = start
    while idx < len(lines) and _is_table_row(lines[idx]):
        raw = lines[idx].strip()
        if re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", raw):
            idx += 1
            continue
        cells = [cell.strip() for cell in raw.strip("|").split("|")]
        rows.append(tuple(cells))
        idx += 1
    if not rows:
        return None, start
    return tuple(rows), idx


def _directive_key_name(raw_key: str) -> str:
    key = raw_key.strip()
    if key.startswith("_"):
        key = key[1:]
    return key


def _is_marp_directive_comment(inner: str) -> bool:
    lines = [ln.strip() for ln in inner.splitlines() if ln.strip()]
    if not lines:
        return True
    for ln in lines:
        if ":" not in ln:
            return False
        key_part, _, _value_part = ln.partition(":")
        name = _directive_key_name(key_part)
        if name not in _MARP_GLOBAL_DIRECTIVES and name not in _MARP_LOCAL_DIRECTIVES:
            return False
    return True


def _extract_comment_inner(first_line: str, rest_lines: list[str], closing_line: str) -> str:
    open_idx = first_line.find("<!--")
    close_on_first = "-->" in first_line[open_idx:]
    if close_on_first:
        close_idx = first_line.index("-->", open_idx)
        inner = first_line[open_idx + 4 : close_idx]
        return inner.strip()
    inner_parts: list[str] = []
    after_open = first_line[open_idx + 4 :].strip()
    if after_open:
        inner_parts.append(after_open)
    inner_parts.extend(rest_lines)
    close_idx = closing_line.rfind("-->")
    last_text = closing_line[:close_idx].strip() if close_idx >= 0 else closing_line.strip()
    if last_text:
        inner_parts.append(last_text)
    return "\n".join(inner_parts).strip()


def _partition_notes_and_body(lines: list[str]) -> tuple[str, list[str]]:
    note_chunks: list[str] = []
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
            inner = _extract_comment_inner(comment_start, [], comment_start)
            if inner and not _is_marp_directive_comment(inner):
                note_chunks.append(inner)
            idx += 1
            continue
        rest: list[str] = []
        idx += 1
        while idx < len(lines):
            if "-->" in lines[idx]:
                inner = _extract_comment_inner(comment_start, rest, lines[idx])
                if inner and not _is_marp_directive_comment(inner):
                    note_chunks.append(inner)
                idx += 1
                break
            rest.append(lines[idx])
            idx += 1
        else:
            body.append(line)
    notes = "\n\n".join(note_chunks).strip()
    filtered_body: list[str] = []
    for line in body:
        stripped_only = line.strip()
        if stripped_only in ("<!--", "-->"):
            continue
        filtered_body.append(line)
    return notes, filtered_body


def _strip_inline_html(line: str) -> str:
    if not _HTML_TAG_RE.search(line):
        return line.strip()
    text = _HTML_TAG_RE.sub("", line).strip()
    return text


def _bullet_depth(indent: str) -> int:
    spaces = len(indent.replace("\t", "    "))
    return spaces // 2


def _blocks_from_body(
    body_lines: list[str], *, marp_dir: Path
) -> tuple[str, list[str], list[SlideImage], list[BodyBlock], tuple[tuple[str, ...], ...] | None]:
    title = ""
    legacy_bullets: list[str] = []
    images: list[SlideImage] = []
    blocks: list[BodyBlock] = []
    idx = 0
    while idx < len(body_lines):
        line = body_lines[idx]
        stripped = line.strip()
        if not stripped:
            idx += 1
            continue

        img = _IMAGE_RE.search(line)
        if img and stripped == img.group(0).strip():
            alt, rel = img.group(1), img.group(2)
            resolved = (marp_dir / rel).resolve() if not rel.startswith(("http://", "https://")) else Path(rel)
            images.append(SlideImage(alt=alt, path=str(resolved)))
            idx += 1
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            if not title:
                title = text
            else:
                blocks.append(HeadingBlock(level=level, text=text))
            idx += 1
            continue

        if _FENCE_RE.match(stripped):
            code_lines: list[str] = []
            idx += 1
            while idx < len(body_lines) and not _FENCE_RE.match(body_lines[idx].strip()):
                code_lines.append(body_lines[idx])
                idx += 1
            if idx < len(body_lines):
                idx += 1
            blocks.append(CodeBlock(text="\n".join(code_lines)))
            continue

        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while idx < len(body_lines):
                qline = body_lines[idx].strip()
                if not qline.startswith(">"):
                    break
                quote_lines.append(qline.lstrip(">").strip())
                idx += 1
            blocks.append(QuoteBlock(text="\n".join(quote_lines).strip()))
            continue

        if _is_table_row(line):
            parsed, idx = _parse_table_rows(body_lines, idx)
            if parsed:
                blocks.append(TableBlock(rows=parsed))
            continue

        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            items: list[BulletItem] = []
            while idx < len(body_lines):
                bm = _BULLET_RE.match(body_lines[idx])
                if not bm:
                    break
                depth = _bullet_depth(bm.group(1))
                text = bm.group(3).strip()
                items.append(BulletItem(text=text, depth=depth))
                if depth == 0:
                    legacy_bullets.append(text)
                idx += 1
            blocks.append(BulletListBlock(items=tuple(items)))
            continue

        numbered_match = _NUMBERED_RE.match(stripped)
        if numbered_match:
            items_num: list[NumberedItem] = []
            while idx < len(body_lines):
                nm = _NUMBERED_RE.match(body_lines[idx].strip())
                if not nm:
                    break
                items_num.append(NumberedItem(number=nm.group(1), text=nm.group(2).strip()))
                idx += 1
            blocks.append(NumberedListBlock(items=tuple(items_num)))
            continue

        para_lines: list[str] = []
        while idx < len(body_lines):
            pline = body_lines[idx]
            ps = pline.strip()
            if not ps:
                break
            img_break = _IMAGE_RE.search(pline)
            if (
                _HEADING_RE.match(pline)
                or (img_break is not None and ps == img_break.group(0).strip())
                or _FENCE_RE.match(ps)
                or ps.startswith(">")
                or _is_table_row(pline)
                or _BULLET_RE.match(pline)
                or _NUMBERED_RE.match(ps)
            ):
                break
            cleaned = _strip_inline_html(pline)
            if cleaned:
                para_lines.append(cleaned)
            idx += 1
        if para_lines:
            blocks.append(ParagraphBlock(text="\n".join(para_lines)))

    legacy_table: tuple[tuple[str, ...], ...] | None = None
    for block in reversed(blocks):
        if isinstance(block, TableBlock):
            legacy_table = block.rows
            break

    return title, legacy_bullets, images, blocks, legacy_table


def parse_slide_chunk(chunk: str, *, marp_dir: Path) -> SlideModel:
    lines = chunk.splitlines()
    notes, body_lines = _partition_notes_and_body(lines)
    title, legacy_bullets, images, blocks, legacy_table = _blocks_from_body(body_lines, marp_dir=marp_dir)

    return SlideModel(
        title=title,
        bullets=tuple(legacy_bullets),
        table=legacy_table,
        notes=notes,
        images=tuple(images),
        blocks=tuple(blocks),
    )


def parse_marp_deck(text: str, *, marp_dir: Path) -> tuple[SlideModel, ...]:
    body = _strip_front_matter(text)
    chunks = [part.strip() for part in body.split("\n---\n") if part.strip()]
    return tuple(parse_slide_chunk(chunk, marp_dir=marp_dir) for chunk in chunks)


def _body_block_to_json(block: BodyBlock) -> dict[str, Any]:
    if isinstance(block, HeadingBlock):
        return {"kind": "heading", "level": block.level, "text": block.text}
    if isinstance(block, ParagraphBlock):
        return {"kind": "paragraph", "text": block.text}
    if isinstance(block, BulletListBlock):
        return {
            "kind": "bullets",
            "items": [{"text": item.text, "depth": item.depth} for item in block.items],
        }
    if isinstance(block, NumberedListBlock):
        return {
            "kind": "numbered",
            "items": [{"number": item.number, "text": item.text} for item in block.items],
        }
    if isinstance(block, TableBlock):
        return {"kind": "table", "rows": [list(row) for row in block.rows]}
    if isinstance(block, CodeBlock):
        return {"kind": "code", "text": block.text}
    if isinstance(block, QuoteBlock):
        return {"kind": "quote", "text": block.text}
    raise TypeError(f"unknown body block: {type(block)!r}")


def slide_model_to_json(slides: tuple[SlideModel, ...]) -> dict[str, Any]:
    return {
        "slides": [
            {
                "title": slide.title,
                "bullets": list(slide.bullets),
                "table": [list(row) for row in slide.table] if slide.table else None,
                "notes": slide.notes,
                "images": [{"alt": img.alt, "path": img.path} for img in slide.images],
                "blocks": [_body_block_to_json(block) for block in slide.blocks],
            }
            for slide in slides
        ]
    }


def driver_script_path() -> Path:
    return Path(__file__).resolve().parent / "node" / "pptx_native.mjs"


def _node_env() -> dict[str, str]:
    env = os.environ.copy()
    prefix = os.environ.get("CONDA_PREFIX", "")
    if prefix:
        node_path = env.get("NODE_PATH", "")
        module_root = f"{prefix}/lib/node_modules"
        env["NODE_PATH"] = module_root if not node_path else f"{module_root}{os.pathsep}{node_path}"
    return env


def run_node_driver(model_path: Path, output_path: Path, *, driver: Path | None = None) -> None:
    node = shutil.which("node")
    if node is None:
        raise HeraldError("pptx-native: node not on PATH (install nodejs in the pyforge-guild env)")
    script = driver or driver_script_path()
    if not script.is_file():
        raise HeraldError(f"pptx-native: Node driver missing at {script}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [node, str(script), str(model_path), str(output_path)],
        check=False,
        capture_output=True,
        text=True,
        env=_node_env(),
    )
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip()[-2000:]
        raise HeraldError(f"pptx-native: Node driver failed (exit {completed.returncode}): {tail}")


def export_native_pptx(
    slug: str,
    repo_root: Path,
    *,
    export_date: str | None = None,
    now: datetime | None = None,
) -> DeckNativeExportResult:
    marp_path = find_current_deck_marp(slug, repo_root)
    marp_dir = marp_path.parent
    slides = parse_marp_deck(marp_path.read_text(encoding="utf-8"), marp_dir=marp_dir)
    if not slides:
        raise HeraldError(f"pptx-native: Marp source {marp_path} produced no slides")

    when = now or datetime.now(timezone.utc)
    date_str = export_date or when.strftime("%Y-%m-%d")
    out_dir = repo_root / "presentations" / slug / "src" / "pptx"
    out_path = out_dir / f"{slug}-deck-native-{date_str}.pptx"

    model = slide_model_to_json(slides)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(model, handle)
        model_path = Path(handle.name)
    try:
        run_node_driver(model_path, out_path)
    finally:
        model_path.unlink(missing_ok=True)

    stamps.write_stamp(out_path, repo_root=repo_root, slug=slug)
    deck_versions.retire_superseded(out_path)
    return DeckNativeExportResult(output_path=out_path, marp_source=marp_path, slide_count=len(slides))
