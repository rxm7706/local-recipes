"""Vendor Work Passport minting — PostgreSQL / Django ORM half (Story 61.2).

Imports `django` lazily, inside `record_vendor_passport`, so the base
package's `passport.mint_vendor_passport` can reach it without the
`[dashboard]` extra being a base dependency. Never idempotent: every call
mints a FRESH random UUID and creates a new row -- see `passport.py`'s
module docstring for the wider picture (the identity rule this story
exists to enforce is that a Jira key or GitHub number must never merge two
rows).
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

_SETTINGS_UNSET = (
    "DJANGO_SETTINGS_MODULE is unset and django settings are not configured "
    "(pyforge-steward[dashboard] extra needs a configured Django project)"
)


def _refused(vendor_id: str, exc: BaseException) -> Dict[str, Any]:
    return {
        "status": "refused",
        "vendor_id": vendor_id,
        "message": f"Django ORM unavailable ({type(exc).__name__}: {exc})",
    }


def record_vendor_passport(
    *,
    vendor_id: str,
    jira_key: Optional[str],
    github_item_id: Optional[str],
    title: str,
) -> Dict[str, Any]:
    """Mint one vendor Work Passport: a fresh random UUID, never a lookup.

    Returns `status: minted` with the new `passport_id`; `status: refused`
    when the ORM is unavailable (django missing, settings unconfigured,
    database unreachable or unmigrated); `status: error` with the message
    for a genuine data error.

    Deliberately no `.filter(...).first()` probe before `.create()` --
    unlike `corridor_load.record_corridor_load`'s idempotent load, the
    identity rule here is the opposite: the same `jira_key` or
    `github_item_id` must never resolve to the same row twice.
    """
    try:
        import django
        from django.apps import apps
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
    except ImportError as exc:
        return _refused(vendor_id, exc)

    if not settings.configured and not os.environ.get("DJANGO_SETTINGS_MODULE"):
        return {"status": "refused", "vendor_id": vendor_id, "message": _SETTINGS_UNSET}

    try:
        if not apps.ready:
            # The CLI path: DJANGO_SETTINGS_MODULE names a project nobody has
            # set up yet in this process (a test module's `django.setup()` has).
            django.setup()
        from django.db import DataError, IntegrityError, OperationalError, ProgrammingError

        from pyforge.steward.dashboard.models import WorkPassport
    except (ImportError, ImproperlyConfigured) as exc:
        return _refused(vendor_id, exc)

    passport_id = str(uuid.uuid4())
    try:
        WorkPassport.objects.create(
            passport_id=passport_id,
            vendor_id=vendor_id,
            jira_key=jira_key,
            github_item_id=github_item_id,
            title=title,
        )
    except (ImproperlyConfigured, OperationalError, ProgrammingError) as exc:
        return _refused(vendor_id, exc)
    except (DataError, IntegrityError) as exc:
        return {
            "status": "error",
            "vendor_id": vendor_id,
            "message": f"{type(exc).__name__}: {exc}",
        }

    return {
        "status": "minted",
        "passport_id": passport_id,
        "vendor_id": vendor_id,
        "jira_key": jira_key,
        "github_item_id": github_item_id,
    }
