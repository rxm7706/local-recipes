"""Upsert ``DeckExport`` rows from ``herald deck exports --json`` output."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from typing import Any

from django_herald_portal.models import DeckExport


def parse_export_records(payload: str) -> list[dict[str, Any]]:
    """Parse JSON from ``herald deck exports <slug> --json``."""
    data = json.loads(payload)
    if not isinstance(data, list):
        msg = "deck exports JSON must be a list of records"
        raise ValueError(msg)
    out: list[dict[str, Any]] = []
    for row in data:
        if isinstance(row, dict):
            out.append(row)
    return out


def sync_slug_exports(slug: str, payload: str, *, published_at: datetime | None = None) -> int:
    """Replace ``slug``'s projection rows with *payload*; return rows written."""
    when = published_at or datetime.now(tz=UTC)
    records = parse_export_records(payload)
    seen_sha: set[str] = set()
    for row in records:
        sha = str(row["sha256"])
        seen_sha.add(sha)
        export_day = datetime.strptime(str(row["date"]), "%Y-%m-%d").date()
        DeckExport.objects.update_or_create(
            sha256=sha,
            defaults={
                "slug": slug,
                "topic": str(row.get("topic", slug)),
                "kind": str(row["kind"]),
                "export_date": export_day,
                "size": int(row["size"]),
                "content_type": str(row["content_type"]),
                "source_commit": str(row["source_commit"]),
                "published_at": when,
            },
        )
    DeckExport.objects.filter(slug=slug).exclude(sha256__in=seen_sha).delete()
    return len(seen_sha)
