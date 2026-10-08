"""The Pages second-host flag (Story 31.1, CAP-56).

``docsite/tools/pages_second_host.py`` asks this module, from the Guild env, whether the
deploying host's ``configure-pages`` inputs apply to the build. The read goes through
``pyforge.core.flags.read_boolean`` (steward Story 75.1); herald never parses the tree.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.flags import read_boolean

PAGES_SECOND_HOST_FLAG = "pyforge.herald.pages_second_host"


def pages_second_host_enabled(*, flags_path: Path | str | None = None) -> bool:
    return read_boolean(PAGES_SECOND_HOST_FLAG, default=False, flags_path=flags_path)
