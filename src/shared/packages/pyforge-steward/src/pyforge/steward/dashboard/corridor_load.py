"""Corridor loads — PostgreSQL / Django ORM half (Story 61.1).

Imports `django` lazily, inside `record_corridor_load`, so the base
package's `corridor.load_extract` can reach it without the `[dashboard]`
extra being a base dependency. Idempotent on `(direction, batch_sha,
waybill)`: a repeat drop reports the ORIGINALLY recorded transport, never
creates a second row -- see `corridor.py`'s module docstring for the wider
picture.
"""

from __future__ import annotations

import os
from typing import Any, Dict

_SETTINGS_UNSET = (
    "DJANGO_SETTINGS_MODULE is unset and django settings are not configured "
    "(pyforge-steward[dashboard] extra needs a configured Django project)"
)


def _refused(
    direction: str, batch_sha: str, waybill: str, transport: str, exc: BaseException
) -> Dict[str, Any]:
    return {
        "status": "refused",
        "direction": direction,
        "batch_sha": batch_sha,
        "waybill": waybill,
        "transport": transport,
        "message": f"Django ORM unavailable ({type(exc).__name__}: {exc})",
    }


def record_corridor_load(
    *, direction: str, batch_sha: str, waybill: str, transport: str
) -> Dict[str, Any]:
    """Record one corridor load.

    Returns `status: loaded` (a new row was created); `status: idempotent`
    (a row for this `(direction, batch_sha, waybill)` already existed -- no
    new row, and `transport` in the payload is the ORIGINALLY recorded one,
    never the one this call was invoked with); `status: refused` when the
    ORM is unavailable (django missing, settings unconfigured, database
    unreachable or unmigrated); `status: error` with the message for a data
    error.
    """
    try:
        import django
        from django.apps import apps
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
    except ImportError as exc:
        return _refused(direction, batch_sha, waybill, transport, exc)

    if not settings.configured and not os.environ.get("DJANGO_SETTINGS_MODULE"):
        return {
            "status": "refused",
            "direction": direction,
            "batch_sha": batch_sha,
            "waybill": waybill,
            "transport": transport,
            "message": _SETTINGS_UNSET,
        }

    try:
        if not apps.ready:
            # The CLI path: DJANGO_SETTINGS_MODULE names a project nobody has
            # set up yet in this process (a test module's `django.setup()` has).
            django.setup()
        from django.db import DataError, IntegrityError, OperationalError, ProgrammingError

        from pyforge.steward.dashboard.models import CorridorLoad
    except (ImportError, ImproperlyConfigured) as exc:
        return _refused(direction, batch_sha, waybill, transport, exc)

    try:
        existing = CorridorLoad.objects.filter(
            direction=direction, batch_sha=batch_sha, waybill=waybill
        ).first()
        if existing is not None:
            return {
                "status": "idempotent",
                "direction": direction,
                "batch_sha": batch_sha,
                "waybill": waybill,
                "transport": existing.transport,
            }
        CorridorLoad.objects.create(
            direction=direction, batch_sha=batch_sha, waybill=waybill, transport=transport
        )
    except (ImproperlyConfigured, OperationalError, ProgrammingError) as exc:
        return _refused(direction, batch_sha, waybill, transport, exc)
    except (DataError, IntegrityError) as exc:
        return {
            "status": "error",
            "direction": direction,
            "batch_sha": batch_sha,
            "waybill": waybill,
            "transport": transport,
            "message": f"{type(exc).__name__}: {exc}",
        }
    return {
        "status": "loaded",
        "direction": direction,
        "batch_sha": batch_sha,
        "waybill": waybill,
        "transport": transport,
    }
