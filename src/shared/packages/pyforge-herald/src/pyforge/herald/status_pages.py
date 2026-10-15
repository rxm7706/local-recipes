"""Status pages flag read (Story 42.1, CAP-60).

The fleet board (``/status/``) and the guild status page (``/status/ci/``) render at build in
``docsite/build.py``; their stdlib reading lives in ``docsite/tools/status_pages.py`` so the ``site``
env gains no pyforge dependency. The Guild env hands the build this flag's resolved value through
``docsite/tools/export_status_pages_env.py`` (``PYFORGE_STATUS_PAGES``).
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.flags import read_boolean

STATUS_PAGES_FLAG = "pyforge.herald.status_pages"


def status_pages_enabled(*, flags_path: Path | str | None = None) -> bool:
    return read_boolean(STATUS_PAGES_FLAG, default=False, flags_path=flags_path)
