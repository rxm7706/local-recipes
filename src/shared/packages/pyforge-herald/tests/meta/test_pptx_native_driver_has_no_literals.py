"""Meta: native PPTX driver must not hardcode layout or theme literals (Story 32.3)."""

from __future__ import annotations

import re
from pathlib import Path

_DRIVER = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "herald" / "node" / "pptx_native.mjs"

_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_FONT_FACE_STRING = re.compile(r"""fontFace\s*:\s*['"][^'"]+['"]""")
_NUMERIC_LAYOUT = re.compile(
    r"\b(fontSize|x|y|w|h|margin)\s*:\s*-?\d+(?:\.\d+)?\b",
)


def test_pptx_native_driver_has_no_theme_or_layout_literals() -> None:
    source = _DRIVER.read_text(encoding="utf-8")
    hex_hits = _HEX_COLOR.findall(source)
    assert not hex_hits, f"hex colour literals in driver: {hex_hits}"
    font_hits = _FONT_FACE_STRING.findall(source)
    assert not font_hits, f"fontFace string literals in driver: {font_hits}"
    layout_hits = _NUMERIC_LAYOUT.findall(source)
    assert not layout_hits, f"numeric layout literals in driver: {layout_hits}"
