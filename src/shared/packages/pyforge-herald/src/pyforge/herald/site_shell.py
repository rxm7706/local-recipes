"""Site shell flag read (Story 53.1, spec-pyforge-herald CAP-63).

The one header on every page of the Pages site, the dark default, the home doors' descriptions and the closed sidebar
groups render at build in ``docs-site/``, which reads this flag's resolved value from ``PYFORGE_SITE_SHELL``; the
Guild env hands it over through ``python -m pyforge.herald.pages_env``, so the ``site`` env gains no pyforge
dependency. Off, each shell keeps the header and the theme rule it had.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.flags import read_boolean

SITE_SHELL_FLAG = "pyforge.herald.site_shell"


def site_shell_enabled(*, flags_path: Path | str | None = None) -> bool:
    return read_boolean(SITE_SHELL_FLAG, default=False, flags_path=flags_path)
