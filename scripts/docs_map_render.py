#!/usr/bin/env python
"""Mutator: regenerate docs/MAP.md's generated "## Page registry" section
from docs/map.yaml (Story 30.2, spec-pyforge-doctor CAP-84).

The only sanctioned way to edit the content between the
`docs-map:registry:begin`/`docs-map:registry:end` markers in docs/MAP.md --
hand-editing that section is exactly what docs-currency's map-render check
(`pyforge.doctor.sources.docs_currency`) catches. Everything outside the
markers is left untouched, byte-for-byte.

Reads docs/map.yaml and calls docs_currency's pure `render_map_registry` --
the SAME function the doctor check reads against -- so the write side and
the read side can never independently drift from each other.

    python scripts/docs_map_render.py

Exit 0 on a successful write (or when the file is already current), 1 on
any failure (map.yaml missing/invalid, markers absent from MAP.md). This is
a plain mutator, not a detector: no DETECTOR marker, not scanned by
scripts/detectors.py's AST discovery -- invoked directly by its own pixi
task (`docs-map-render`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"))

from pyforge.doctor.sources.docs_currency import render_map_registry  # noqa: E402

_MAP_YAML = REPO_ROOT / "docs" / "map.yaml"
_MAP_MD = REPO_ROOT / "docs" / "MAP.md"
_BEGIN = "<!-- docs-map:registry:begin"
_END = "<!-- docs-map:registry:end -->"


def main() -> int:
    if not _MAP_YAML.is_file():
        print(f"[docs-map-render] {_MAP_YAML} does not exist", file=sys.stderr)
        return 1
    data = yaml.safe_load(_MAP_YAML.read_text(encoding="utf-8"))
    pages = data.get("pages", []) if isinstance(data, dict) else []

    if not _MAP_MD.is_file():
        print(f"[docs-map-render] {_MAP_MD} does not exist", file=sys.stderr)
        return 1
    text = _MAP_MD.read_text(encoding="utf-8")

    begin_idx = text.find(_BEGIN)
    if begin_idx == -1:
        print(f"[docs-map-render] {_MAP_MD} has no {_BEGIN!r} marker", file=sys.stderr)
        return 1
    begin_line_end = text.find("\n", begin_idx)
    if begin_line_end == -1:
        print(
            f"[docs-map-render] {_MAP_MD}'s begin marker has no trailing newline",
            file=sys.stderr,
        )
        return 1
    end_idx = text.find(_END, begin_line_end)
    if end_idx == -1:
        print(f"[docs-map-render] {_MAP_MD} has no {_END!r} marker", file=sys.stderr)
        return 1

    rendered = render_map_registry(pages)
    new_text = text[: begin_line_end + 1] + rendered + text[end_idx:]
    if new_text != text:
        _MAP_MD.write_text(new_text, encoding="utf-8")
        print(f"[docs-map-render] {_MAP_MD} updated ({len(pages)} pages)")
    else:
        print(f"[docs-map-render] {_MAP_MD} already current ({len(pages)} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
