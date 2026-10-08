"""Shared helpers for django-herald deck viewer pages (Story 30.2)."""

from __future__ import annotations

from dataclasses import dataclass

from django_herald_portal.models import DeckExport

from pyforge.herald.deck_twins import NotFound, iframe_twin_path

from django_herald_portal.deck_twin_routes import load_deck_twins_manifest


@dataclass(frozen=True, slots=True)
class PublishedDeck:
    slug: str
    topic: str


@dataclass(frozen=True, slots=True)
class DeckViewerContext:
    slug: str
    topic: str
    twin_iframe_path: str | None
    pptx_stream_path: str | None


def list_published_decks() -> list[PublishedDeck]:
    seen: set[str] = set()
    rows: list[PublishedDeck] = []
    for item in DeckExport.objects.all().order_by("slug", "topic"):
        if item.slug in seen:
            continue
        seen.add(item.slug)
        rows.append(PublishedDeck(slug=item.slug, topic=item.topic))
    return rows


def viewer_context(slug: str) -> DeckViewerContext | None:
    topic_row = (
        DeckExport.objects.filter(slug=slug).order_by("-export_date").values("topic").first()
    )
    if topic_row is None:
        return None
    topic = str(topic_row["topic"])
    try:
        twins = load_deck_twins_manifest(slug)
    except NotFound:
        twins = {}
    rel = iframe_twin_path(twins) if twins else None
    if rel is None:
        twin_iframe_path = None
    elif rel == "":
        twin_iframe_path = f"/stations/herald/api/v1/deck-twins/{slug}"
    else:
        twin_iframe_path = f"/stations/herald/api/v1/deck-twins/{slug}/{rel}"
    pptx = (
        DeckExport.objects.filter(slug=slug, kind="pptx")
        .order_by("-export_date")
        .values("sha256")
        .first()
    )
    pptx_path = None
    if pptx is not None:
        sha = str(pptx["sha256"])
        pptx_path = f"/stations/herald/api/v1/deck-exports/{sha}"
    return DeckViewerContext(
        slug=slug,
        topic=topic,
        twin_iframe_path=twin_iframe_path,
        pptx_stream_path=pptx_path,
    )
