"""Vizro boards as static exports under ``/dashboard/vizro/`` (Story 30.2, CAP-63): the flag.

Kept apart from ``dashboard.static_export`` so reading the flag never imports vizro: the
producer job's flag step and the unit tests read it without the dashboard closure, the way
``viz_export_artifact`` serves Story 30.1.
"""

from __future__ import annotations

from pyforge.core.flags import read_boolean

FLAG_KEY = "pyforge.atlas.vizro_static_boards"


def boards_enabled(*, flags_path: str | None = None) -> bool:
    """Whether ``vizro-static-export`` may write the export and CI may upload it."""
    return read_boolean(FLAG_KEY, default=False, flags_path=flags_path)
