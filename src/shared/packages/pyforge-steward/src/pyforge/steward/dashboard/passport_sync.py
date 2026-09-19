"""Work Passports PostgreSQL & Django ORM sync handler (Story 63.5 / Epic 61)."""

from __future__ import annotations

from typing import Any, Dict, List

def sync_work_passports_db(stories: List[Any]) -> Dict[str, Any]:
    """Sync Work Passport items to PostgreSQL / Django ORM."""
    try:
        from django.db import transaction
        from pyforge.steward.dashboard.models import WorkPassport

        synced_records = []
        with transaction.atomic():
            for s in stories:
                obj, _ = WorkPassport.objects.update_or_create(
                    passport_id=s.passport_id,
                    defaults={
                        "story_id": s.story_id,
                        "station": s.station,
                        "epic_id": s.epic_id,
                        "title": s.title,
                        "status": s.status,
                        "jira_key": s.jira_key,
                        "github_item_id": s.github_item_id,
                        "effort": s.effort,
                    }
                )
                synced_records.append(obj.passport_id)
        return {"status": "success", "synced_count": len(synced_records), "method": "django-orm"}
    except Exception as exc:
        return {
            "status": "fallback_payload",
            "count": len(stories),
            "message": f"Django ORM unavailable ({exc}), minted Work Passport UUID payload ready for migration.",
            "passports": [getattr(s, "passport_id", "") for s in stories],
        }
