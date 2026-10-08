"""Native editable PPTX export via pptxgenjs-plus (Story 32.1, CAP-57)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyforge.core.flags import read_boolean

from . import deck_versions, stamps
from .deck_pipeline import _newest_dated_match
from .errors import HeraldError

DECK_EXPORT_NATIVE_FLAG = "pyforge.herald.deck_export_native"

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_MARP_DIRECTIVE_COMMENT = re.compile(r"^\s*<!--\s*_[^>]*-->\s*$")


@dataclass(frozen=True, slots=True)
class SlideImage:
    alt: str
    path: str


@dataclass(frozen=True, slots=True)
class SlideModel:
    title: str = ""
    bullets: tuple[str, ...] = ()
    table: tuple[tuple[str, ...], ...] | None = None
    notes: str = ""
    images: tuple[SlideImage, ...] = ()


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
            f"pptx-native: no Marp deck source for {slug!r} under {marp_dir} "
            f"(expected {slug}-deck-<YYYY-MM-DD>.md)"
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


def _extract_notes_and_body(lines: list[str]) -> tuple[str, list[str]]:
    notes: list[str] = []
    body: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            if _MARP_DIRECTIVE_COMMENT.match(stripped):
                continue
            inner = stripped[4:-3].strip()
            if inner:
                notes.append(inner)
            continue
        body.append(line)
    return "\n".join(notes).strip(), body


def parse_slide_chunk(chunk: str, *, marp_dir: Path) -> SlideModel:
    lines = chunk.splitlines()
    notes, body_lines = _extract_notes_and_body(lines)
    title = ""
    bullets: list[str] = []
    images: list[SlideImage] = []
    table: tuple[tuple[str, ...], ...] | None = None

    idx = 0
    while idx < len(body_lines):
        line = body_lines[idx]
        img = _IMAGE_RE.search(line)
        if img:
            alt, rel = img.group(1), img.group(2)
            resolved = (marp_dir / rel).resolve() if not rel.startswith(("http://", "https://")) else Path(rel)
            images.append(SlideImage(alt=alt, path=str(resolved)))
            idx += 1
            continue
        heading = _HEADING_RE.match(line)
        if heading and not title:
            title = heading.group(2).strip()
            idx += 1
            continue
        if _is_table_row(line):
            parsed, idx = _parse_table_rows(body_lines, idx)
            if parsed:
                table = parsed
            continue
        bullet = line.strip()
        if bullet.startswith(("- ", "* ")):
            bullets.append(bullet[2:].strip())
        idx += 1

    return SlideModel(
        title=title,
        bullets=tuple(bullets),
        table=table,
        notes=notes,
        images=tuple(images),
    )


def parse_marp_deck(text: str, *, marp_dir: Path) -> tuple[SlideModel, ...]:
    body = _strip_front_matter(text)
    chunks = [part.strip() for part in body.split("\n---\n") if part.strip()]
    return tuple(parse_slide_chunk(chunk, marp_dir=marp_dir) for chunk in chunks)


def slide_model_to_json(slides: tuple[SlideModel, ...]) -> dict[str, Any]:
    return {
        "slides": [
            {
                **{k: v for k, v in asdict(slide).items() if k != "images"},
                "images": [{"alt": img.alt, "path": img.path} for img in slide.images],
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
