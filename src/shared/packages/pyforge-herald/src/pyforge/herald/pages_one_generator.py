"""Pages one-generator flag read (Story 43.1, CAP-61).

Build tooling in ``docsite/tools/pages_one_generator.py`` reads the exported env;
the Guild env sets that variable via ``export_pages_one_generator_env.py``.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.flags import read_boolean

PAGES_ONE_GENERATOR_FLAG = "pyforge.herald.pages_one_generator"


def pages_one_generator_enabled(*, flags_path: Path | str | None = None) -> bool:
    return read_boolean(PAGES_ONE_GENERATOR_FLAG, default=False, flags_path=flags_path)
