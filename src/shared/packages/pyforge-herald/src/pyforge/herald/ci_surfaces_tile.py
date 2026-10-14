"""CI surfaces tile flag read (Story 39.1, CAP-59).

Row logic lives in ``docsite/tools/ci_surfaces_tile.py`` (stdlib-only for the ``site`` build).
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.flags import read_boolean

CI_SURFACES_TILE_FLAG = "pyforge.herald.ci_surfaces_tile"


def ci_surfaces_tile_enabled(*, flags_path: Path | str | None = None) -> bool:
    return read_boolean(CI_SURFACES_TILE_FLAG, default=False, flags_path=flags_path)
