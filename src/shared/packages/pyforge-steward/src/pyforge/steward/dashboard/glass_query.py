"""As-of glass — PostgreSQL / Django ORM read-only half (Story 61.3).

Imports `django` lazily, inside `read_latest_corridor_load`, so the base
package's `glass.compute_glass_reading` can reach it without the
`[dashboard]` extra being a base dependency. Read-only: relies on
`CorridorLoad.Meta.ordering` (`["-loaded_at", "-id"]`) to answer "the most
recent load for this direction" with no explicit `.order_by()` -- see
`corridor_load.py` for the sibling idiom this mirrors. No lookup mutation:
unlike `corridor_load.py`/`passport_mint.py`, this module never writes.
"""

from __future__ import annotations

import os
from typing import Any, Dict

_SETTINGS_UNSET = (
    "DJANGO_SETTINGS_MODULE is unset and django settings are not configured "
    "(pyforge-steward[dashboard] extra needs a configured Django project)"
)


def _refused(direction: str, exc: BaseException) -> Dict[str, Any]:
    return {
        "status": "refused",
        "direction": direction,
        "message": f"Django ORM unavailable ({type(exc).__name__}: {exc})",
    }


def read_latest_corridor_load(*, direction: str) -> Dict[str, Any]:
    """Return the most recent `CorridorLoad` row for `direction`.

    Returns `status: ok, found: False` when no row has ever loaded for this
    direction; `status: ok, found: True` with `waybill`/`batch_sha`/
    `loaded_at` (ISO 8601) otherwise; `status: refused` when the ORM is
    unavailable (django missing, settings unconfigured, database
    unreachable or unmigrated).
    """
    try:
        import django
        from django.apps import apps
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
    except ImportError as exc:
        return _refused(direction, exc)

    if not settings.configured and not os.environ.get("DJANGO_SETTINGS_MODULE"):
        return {"status": "refused", "direction": direction, "message": _SETTINGS_UNSET}

    try:
        if not apps.ready:
            # The CLI path: DJANGO_SETTINGS_MODULE names a project nobody has
            # set up yet in this process (a test module's `django.setup()` has).
            django.setup()
        from django.db import DataError, OperationalError, ProgrammingError

        from pyforge.steward.dashboard.models import CorridorLoad
    except (ImportError, ImproperlyConfigured) as exc:
        return _refused(direction, exc)

    try:
        row = CorridorLoad.objects.filter(direction=direction).first()
    except (DataError, OperationalError, ProgrammingError) as exc:
        return _refused(direction, exc)

    if row is None:
        return {"status": "ok", "direction": direction, "found": False}

    return {
        "status": "ok",
        "direction": direction,
        "found": True,
        "waybill": row.waybill,
        "batch_sha": row.batch_sha,
        "loaded_at": row.loaded_at.isoformat(),
    }
