"""Work Passports PostgreSQL / Django ORM sync (Story 65.1).

Imports `django` lazily, inside `sync_work_passports_db`, so the base package's
`sprint_ledger_query.sync_to_postgres` can reach it without the `[dashboard]`
extra being a base dependency. Outcomes are reported, never raised, for the
environmental failures (`status: fallback_payload`) and the data failures
(`status: error`); anything else propagates.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

_SETTINGS_UNSET = (
    "DJANGO_SETTINGS_MODULE is unset and django settings are not configured "
    "(pyforge-steward[dashboard] extra needs a configured Django project)"
)


def _passport_defaults(story: Any) -> Dict[str, Any]:
    """Fields `update_or_create` writes. An alias the ledger does not carry
    (`jira_key` / `github_item_id` of None) is LEFT OUT, so an alias entered in
    the admin survives the next sync instead of being overwritten with NULL."""
    defaults: Dict[str, Any] = {
        "story_id": story.story_id,
        "station": story.station,
        "epic_id": story.epic_id,
        "title": story.title,
        "status": story.status,
        "effort": story.effort,
    }
    if story.jira_key is not None:
        defaults["jira_key"] = story.jira_key
    if story.github_item_id is not None:
        defaults["github_item_id"] = story.github_item_id
    return defaults


def sync_work_passports_db(stories: List[Any]) -> Dict[str, Any]:
    """Sync Work Passport items to PostgreSQL / Django ORM.

    Returns `status: success` with `synced_count`; `status: refused` when django
    is importable but no settings are configured; `status: fallback_payload`
    (the minted UUIDs, ready for a later migration) when the ORM is unavailable
    -- django missing, settings misconfigured, database unreachable or
    unmigrated; `status: error` with the message for a data error.
    """
    try:
        import django
        from django.apps import apps
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
    except ImportError as exc:
        return _fallback(stories, exc)

    if not settings.configured and not os.environ.get("DJANGO_SETTINGS_MODULE"):
        return {"status": "refused", "count": len(stories), "message": _SETTINGS_UNSET}

    try:
        if not apps.ready:
            # The CLI path: DJANGO_SETTINGS_MODULE names a project nobody has
            # set up yet in this process (a test module's `django.setup()` has).
            django.setup()
        from django.db import DataError, IntegrityError, OperationalError, ProgrammingError, transaction

        from pyforge.steward.dashboard.models import WorkPassport
    except (ImportError, ImproperlyConfigured) as exc:
        return _fallback(stories, exc)

    try:
        synced_records = []
        with transaction.atomic():
            for s in stories:
                obj, _ = WorkPassport.objects.update_or_create(
                    passport_id=s.passport_id,
                    defaults=_passport_defaults(s),
                )
                synced_records.append(obj.passport_id)
    except (ImproperlyConfigured, OperationalError, ProgrammingError) as exc:
        return _fallback(stories, exc)
    except (DataError, IntegrityError) as exc:
        return {"status": "error", "count": len(stories), "message": f"{type(exc).__name__}: {exc}"}
    return {"status": "success", "synced_count": len(synced_records), "method": "django-orm"}


def _fallback(stories: List[Any], exc: BaseException) -> Dict[str, Any]:
    return {
        "status": "fallback_payload",
        "count": len(stories),
        "message": f"Django ORM unavailable ({type(exc).__name__}: {exc}), minted Work Passport UUID payload ready for migration.",
        "passports": [getattr(s, "passport_id", "") for s in stories],
    }
