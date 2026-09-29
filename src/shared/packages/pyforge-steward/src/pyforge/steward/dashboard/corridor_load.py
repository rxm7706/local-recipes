"""Corridor loads — PostgreSQL / Django ORM half (Story 61.1).

Imports `django` lazily, inside `record_corridor_load`, so the base
package's `corridor.load_extract` can reach it without the `[dashboard]`
extra being a base dependency. Idempotent on `(direction, batch_sha,
waybill)`: a repeat drop reports the ORIGINALLY recorded transport, never
creates a second row -- see `corridor.py`'s module docstring for the wider
picture.

Since Story 61.4 (the signed-outbound-slice gate), `slice_name`/`signer` are
threaded through every branch alongside `transport`: recorded on create,
and -- on an idempotent hit -- read back from the EXISTING row, never from
the incoming call's own arguments (identical provenance rule to
`transport`). `corridor.py::load_extract` is what actually enforces the
default-deny (non-blank) requirement for an outbound create; this module
only persists and reports whatever it is given.
"""

from __future__ import annotations

import os
from typing import Any, Dict

_SETTINGS_UNSET = (
    "DJANGO_SETTINGS_MODULE is unset and django settings are not configured "
    "(pyforge-steward[dashboard] extra needs a configured Django project)"
)


def _refused(
    direction: str,
    batch_sha: str,
    waybill: str,
    transport: str,
    exc: BaseException,
    *,
    slice_name: str = "",
    signer: str = "",
) -> Dict[str, Any]:
    return {
        "status": "refused",
        "direction": direction,
        "batch_sha": batch_sha,
        "waybill": waybill,
        "transport": transport,
        "slice_name": slice_name,
        "signer": signer,
        "message": f"Django ORM unavailable ({type(exc).__name__}: {exc})",
    }


def _idempotent(
    direction: str,
    batch_sha: str,
    waybill: str,
    transport: str,
    *,
    slice_name: str = "",
    signer: str = "",
) -> Dict[str, Any]:
    return {
        "status": "idempotent",
        "direction": direction,
        "batch_sha": batch_sha,
        "waybill": waybill,
        "transport": transport,
        "slice_name": slice_name,
        "signer": signer,
    }


def record_corridor_load(
    *,
    direction: str,
    batch_sha: str,
    waybill: str,
    transport: str,
    create_if_missing: bool = True,
    slice_name: str = "",
    signer: str = "",
) -> Dict[str, Any]:
    """Record one corridor load, or (``create_if_missing=False``) only check
    whether one already exists.

    Returns `status: loaded` (a new row was created); `status: idempotent`
    (a row for this `(direction, batch_sha, waybill)` already existed -- no
    new row, and `transport`/`slice_name`/`signer` in the payload are the
    ORIGINALLY recorded ones, never the values this call was invoked with);
    `status: not_found` (only possible with `create_if_missing=False`: no row
    exists yet, and none was created); `status: refused` when the ORM is
    unavailable (django missing, settings unconfigured, database unreachable
    or unmigrated); `status: error` with the message for a genuine data
    error.

    `create_if_missing=False` is the read-only probe `corridor.load_extract`
    uses to decide whether this call would create a NEW row -- the one path
    that needs a transport declared `state: on` in `corridor.yaml`, a
    concept this module knows nothing about (and should not have to): an
    idempotent hit must never depend on the transport named on the repeat
    call.

    `slice_name`/`signer` (Story 61.4) are persisted verbatim on create and
    read back from the existing row on every idempotent/race path -- this
    module does not validate them (the default-deny non-blank requirement is
    `corridor.py::load_extract`'s job, before this function is ever called
    on the create path).
    """
    try:
        import django
        from django.apps import apps
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
    except ImportError as exc:
        return _refused(direction, batch_sha, waybill, transport, exc, slice_name=slice_name, signer=signer)

    if not settings.configured and not os.environ.get("DJANGO_SETTINGS_MODULE"):
        return {
            "status": "refused",
            "direction": direction,
            "batch_sha": batch_sha,
            "waybill": waybill,
            "transport": transport,
            "slice_name": slice_name,
            "signer": signer,
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
        return _refused(direction, batch_sha, waybill, transport, exc, slice_name=slice_name, signer=signer)

    try:
        existing = CorridorLoad.objects.filter(direction=direction, batch_sha=batch_sha, waybill=waybill).first()
    except (ImproperlyConfigured, OperationalError, ProgrammingError) as exc:
        return _refused(direction, batch_sha, waybill, transport, exc, slice_name=slice_name, signer=signer)

    if existing is not None:
        return _idempotent(
            direction,
            batch_sha,
            waybill,
            existing.transport,
            slice_name=existing.slice_name,
            signer=existing.signer,
        )

    if not create_if_missing:
        return {
            "status": "not_found",
            "direction": direction,
            "batch_sha": batch_sha,
            "waybill": waybill,
            "transport": transport,
            "slice_name": slice_name,
            "signer": signer,
        }

    try:
        CorridorLoad.objects.create(
            direction=direction,
            batch_sha=batch_sha,
            waybill=waybill,
            transport=transport,
            slice_name=slice_name,
            signer=signer,
        )
    except IntegrityError:
        # A genuine concurrent race: another writer's `.create()` landed
        # between our `.filter().first()` miss above and this `.create()`,
        # and the `UniqueConstraint` caught it. The loser of that race must
        # still report the idempotent outcome the caller actually gets, not
        # a data-integrity failure -- re-query and return the winner's row.
        existing = CorridorLoad.objects.filter(direction=direction, batch_sha=batch_sha, waybill=waybill).first()
        if existing is not None:
            return _idempotent(
                direction,
                batch_sha,
                waybill,
                existing.transport,
                slice_name=existing.slice_name,
                signer=existing.signer,
            )
        # Vanishingly unlikely (the row that raised the constraint is gone
        # by the time we re-queried), but never silently swallow it.
        return {
            "status": "error",
            "direction": direction,
            "batch_sha": batch_sha,
            "waybill": waybill,
            "transport": transport,
            "slice_name": slice_name,
            "signer": signer,
            "message": "IntegrityError: unique constraint violated but no matching row found on re-query",
        }
    except (ImproperlyConfigured, OperationalError, ProgrammingError) as exc:
        return _refused(direction, batch_sha, waybill, transport, exc, slice_name=slice_name, signer=signer)
    except DataError as exc:
        return {
            "status": "error",
            "direction": direction,
            "batch_sha": batch_sha,
            "waybill": waybill,
            "transport": transport,
            "slice_name": slice_name,
            "signer": signer,
            "message": f"{type(exc).__name__}: {exc}",
        }
    return {
        "status": "loaded",
        "direction": direction,
        "batch_sha": batch_sha,
        "waybill": waybill,
        "transport": transport,
        "slice_name": slice_name,
        "signer": signer,
    }
