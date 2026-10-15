"""Status pages flag read (Story 42.1, CAP-60).

The fleet board (``/status/``), the guild status page (``/status/ci/``) and the runs page (``/status/runs/``) render
at build in ``docs-site/`` (Story 43.7 ported the first two from the retired Jinja path), which reads this flag's
resolved value from ``PYFORGE_STATUS_PAGES``; the Guild env hands it over through ``python -m
pyforge.herald.pages_env``, so the ``site`` env gains no pyforge dependency.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.flags import read_boolean

STATUS_PAGES_FLAG = "pyforge.herald.status_pages"


def status_pages_enabled(*, flags_path: Path | str | None = None) -> bool:
    return read_boolean(STATUS_PAGES_FLAG, default=False, flags_path=flags_path)
