"""The Pages build's flag environment (herald Story 43.7, spec-pyforge-herald CAP-61).

The ``site`` env that builds the Pages artifact carries no pyforge package, so the Guild env resolves herald's two
build flags and hands their states to the build as environment variables, which ``docs-site/src/lib/flags.ts``
reads -- one ``NAME=1|0`` line each, for a workflow step to append to ``$GITHUB_ENV``::

    pixi run --frozen -e pyforge-guild python -m pyforge.herald.pages_env >> "$GITHUB_ENV"

``pyforge.herald.status_pages`` is ``PYFORGE_STATUS_PAGES`` (Story 42.1: the ``/status/`` prefix and its menu
entry); ``pyforge.herald.ci_surfaces_tile`` is ``PYFORGE_CI_SURFACES_TILE`` (Story 39.1: the dossier's CI surfaces
tile). Replaces the three ``docsite/tools/export_*_env.py`` scripts the retired Jinja path carried.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from pyforge.herald.ci_surfaces_tile import ci_surfaces_tile_enabled
from pyforge.herald.status_pages import status_pages_enabled

#: Each build flag's environment variable and its reader, in the order the lines are printed.
BUILD_FLAGS: tuple[tuple[str, Callable[..., bool]], ...] = (
    ("PYFORGE_STATUS_PAGES", status_pages_enabled),
    ("PYFORGE_CI_SURFACES_TILE", ci_surfaces_tile_enabled),
)


def build_env(*, flags_path: Path | str | None = None) -> dict[str, str]:
    """``{NAME: "1" | "0"}`` for each build flag, read from the flag tree (``flags_path`` for a test's tree)."""
    return {name: "1" if read(flags_path=flags_path) else "0" for name, read in BUILD_FLAGS}


def main(argv: list[str] | None = None) -> int:
    del argv
    for name, value in build_env().items():
        sys.stdout.write(f"{name}={value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
