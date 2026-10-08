"""Quarantine shelf admit — PostgreSQL / Django ORM half (Story 61.5).

Imports ``django`` lazily inside ``record_quarantine_admit`` and
``list_quarantine_shelf_rows`` so the base package's ``quarantine`` duty
can reach this without the ``[dashboard]`` extra being a base dependency.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

_SETTINGS_UNSET = (
    "DJANGO_SETTINGS_MODULE is unset and django settings are not configured "
    "(pyforge-steward[dashboard] extra needs a configured Django project)"
)


def _refused(vendor_id: str, exc: BaseException) -> dict[str, Any]:
    return {
        "status": "refused",
        "vendor_id": vendor_id,
        "message": f"Django ORM unavailable ({type(exc).__name__}: {exc})",
    }


def _days_since_arrival(arrived_at: datetime, *, now: datetime) -> int:
    if arrived_at.tzinfo is None:
        arrived_at = arrived_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now.date() - arrived_at.date()).days


def record_quarantine_admit(
    *,
    vendor_id: str,
    jira_key: str | None,
    github_item_id: str | None,
    title: str,
    arrived_at: datetime,
    missing_passport_window_days: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Admit one inbound row without a passport onto the quarantine shelf.

    Inside the configured window: mint a vendor passport and record
    ``passport_id`` on the shelf row. After the window: refuse to mint but
    still quarantine the row with ``passport_id`` null.
    """
    reference_now = now if now is not None else datetime.now(timezone.utc)
    try:
        import django
        from django.apps import apps
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
    except ImportError as exc:
        return _refused(vendor_id, exc)

    if not getattr(settings, "configured", False):
        return {"status": "refused", "vendor_id": vendor_id, "message": _SETTINGS_UNSET}

    try:
        if not apps.ready:
            django.setup()
        from django.db import DataError, IntegrityError, OperationalError, ProgrammingError

        from pyforge.steward.dashboard import passport_mint
        from pyforge.steward.dashboard.models import QuarantineShelfRow
    except (ImportError, ImproperlyConfigured) as exc:
        return _refused(vendor_id, exc)

    row_id = str(uuid.uuid4())
    days = _days_since_arrival(arrived_at, now=reference_now)
    within_window = days < missing_passport_window_days

    passport_id: str | None = None
    mint_status = "refused"
    message = "missing-passport window elapsed; no mint"

    if within_window:
        mint_outcome = passport_mint.record_vendor_passport(
            vendor_id=vendor_id,
            jira_key=jira_key,
            github_item_id=github_item_id,
            title=title,
        )
        if mint_outcome.get("status") != "minted":
            return {
                "status": "error",
                "vendor_id": vendor_id,
                "message": mint_outcome.get("message", "passport mint failed"),
            }
        passport_id = mint_outcome["passport_id"]
        mint_status = "minted"
        message = "minted into quarantine"

    try:
        QuarantineShelfRow.objects.create(
            row_id=row_id,
            vendor_id=vendor_id,
            jira_key=jira_key,
            github_item_id=github_item_id,
            title=title,
            passport_id=passport_id,
            arrived_at=arrived_at,
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
        "status": "quarantined",
        "row_id": row_id,
        "vendor_id": vendor_id,
        "passport_id": passport_id,
        "mint_status": mint_status,
        "days_since_arrival": days,
        "message": message,
    }


def list_quarantine_shelf_rows(*, include_linked: bool = False) -> dict[str, Any]:
    """Return unlinked quarantine shelf rows (newest first)."""
    try:
        import django
        from django.apps import apps
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
    except ImportError as exc:
        return {"status": "refused", "message": f"Django ORM unavailable ({type(exc).__name__}: {exc})"}

    if not getattr(settings, "configured", False):
        return {"status": "refused", "message": _SETTINGS_UNSET}

    try:
        if not apps.ready:
            django.setup()
        from django.db import OperationalError, ProgrammingError

        from pyforge.steward.dashboard.models import QuarantineShelfRow
    except (ImportError, ImproperlyConfigured) as exc:
        return {"status": "refused", "message": f"Django ORM unavailable ({type(exc).__name__}: {exc})"}

    try:
        qs = QuarantineShelfRow.objects.all()
        if not include_linked:
            qs = qs.filter(linked_at__isnull=True)
        rows = [
            {
                "row_id": row.row_id,
                "vendor_id": row.vendor_id,
                "jira_key": row.jira_key,
                "github_item_id": row.github_item_id,
                "title": row.title,
                "passport_id": row.passport_id,
                "arrived_at": row.arrived_at.isoformat(),
                "linked_at": row.linked_at.isoformat() if row.linked_at else None,
            }
            for row in qs
        ]
    except (OperationalError, ProgrammingError) as exc:
        return {"status": "refused", "message": f"{type(exc).__name__}: {exc}"}

    return {"status": "ok", "rows": rows, "count": len(rows)}
