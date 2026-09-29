#!/usr/bin/env python
"""Mutator: regenerate docs/MAP.md's generated "## Page registry" section
from docs/map.yaml (Story 30.2, spec-pyforge-doctor CAP-84).

The only sanctioned way to edit the content between the
`docs-map:registry:begin`/`docs-map:registry:end` markers in docs/MAP.md --
hand-editing that section is exactly what docs-currency's map-render check
(`pyforge.doctor.sources.docs_currency`) catches. Everything outside the
markers is left untouched, byte-for-byte.

Reads + schema-validates docs/map.yaml via docs_currency's own
`load_map_yaml` (the SAME validation the doctor check's `gather()` relies
on), then calls its pure `render_map_registry` and splices the result in
via its `splice_registry_section` -- both the marker bounds and the render
are shared with the read side, so the two can never independently drift
from each other, and a malformed map.yaml is refused here exactly as it is
there, never silently written past.

    python scripts/docs_map_render.py

Exit 0 on a successful write (or when the file is already current), 1 on
any failure (map.yaml missing/invalid/schema-violating, MAP.md missing,
markers absent from MAP.md). This is a plain mutator, not a detector: no
DETECTOR marker, not scanned by scripts/detectors.py's AST discovery --
invoked directly by its own pixi task (`docs-map-render`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"))

from pyforge.doctor.sources.docs_currency import (  # noqa: E402
    load_map_yaml,
    render_map_registry,
    splice_registry_section,
)

_MAP_YAML = REPO_ROOT / "docs" / "map.yaml"
_MAP_MD = REPO_ROOT / "docs" / "MAP.md"


def main() -> int:
    try:
        data = load_map_yaml(REPO_ROOT)
    except (ValueError, yaml.YAMLError, jsonschema.ValidationError) as exc:
        print(f"[docs-map-render] {_MAP_YAML} is missing or invalid: {exc}", file=sys.stderr)
        return 1
    pages = data["pages"]

    if not _MAP_MD.is_file():
        print(f"[docs-map-render] {_MAP_MD} does not exist", file=sys.stderr)
        return 1
    text = _MAP_MD.read_text(encoding="utf-8")

    rendered = render_map_registry(pages)
    new_text = splice_registry_section(text, rendered)
    if new_text is None:
        print(
            f"[docs-map-render] {_MAP_MD} is missing its "
            "docs-map:registry:begin/end marker(s)",
            file=sys.stderr,
        )
        return 1

    if new_text != text:
        _MAP_MD.write_text(new_text, encoding="utf-8")
        print(f"[docs-map-render] {_MAP_MD} updated ({len(pages)} pages)")
    else:
        print(f"[docs-map-render] {_MAP_MD} already current ({len(pages)} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
