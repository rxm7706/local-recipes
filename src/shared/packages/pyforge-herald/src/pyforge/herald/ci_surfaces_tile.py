"""CI surfaces tile flag read (Story 39.1, CAP-59).

The tile's rows are shaped at build in ``docs-site/src/lib/status.ts`` (Story 43.7 ported them from the retired Jinja
path), which reads this flag's resolved value from ``PYFORGE_CI_SURFACES_TILE``; the Guild env hands it over through
``python -m pyforge.herald.pages_env``.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.flags import read_boolean

CI_SURFACES_TILE_FLAG = "pyforge.herald.ci_surfaces_tile"


def ci_surfaces_tile_enabled(*, flags_path: Path | str | None = None) -> bool:
    return read_boolean(CI_SURFACES_TILE_FLAG, default=False, flags_path=flags_path)
