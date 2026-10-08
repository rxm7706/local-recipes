"""Wire deck-twin API routes with portal session or bearer auth (Story 30.2)."""

from __future__ import annotations

from collections.abc import Iterator

from django_herald_portal.deck_export_routes import Forbidden, Unauthorized, assert_herald_access
from pyforge.herald.deck_twins import NotFound, StoreError, parse_twins_section, resolve_twin_sha256
from pyforge.herald.deck_twins import attach_deck_twin_routes as attach_routes


def load_deck_twins_manifest(slug: str) -> dict[str, object]:
    from pyforge.herald.deck_store import open_deck_store  # noqa: PLC0415

    store = open_deck_store()
    key = f"manifests/{slug}.json"
    if store.head(key) is None:
        raise NotFound
    raw = b"".join(store.open_stream(key))
    twins = parse_twins_section(raw)
    if twins is None:
        raise NotFound
    return twins


def open_deck_twin_stream(slug: str, path: str) -> tuple[str, Iterator[bytes]]:
    from pyforge.herald.deck_store import open_deck_store  # noqa: PLC0415

    twins = load_deck_twins_manifest(slug)
    sha256, media_type = resolve_twin_sha256(twins, path)
    store = open_deck_store()
    object_key = f"sha256/{sha256}"

    def _iter() -> Iterator[bytes]:
        try:
            yield from store.open_stream(object_key)
        except KeyError as exc:
            raise OSError(str(exc)) from exc

    return media_type, _iter()


def wire_deck_twin_routes(app: object) -> None:
    attach_routes(
        app,
        gate=assert_herald_access,
        open_stream=open_deck_twin_stream,
        auth_errors=(Unauthorized, Forbidden),
    )
