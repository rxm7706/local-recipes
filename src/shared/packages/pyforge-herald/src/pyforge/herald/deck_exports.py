"""Deck export list/stream handlers for herald's v1 station API (CAP-54 FR-10.2)."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from pyforge.core.flags import read_boolean
from pyforge.herald.deck_publish import DECK_PUBLISH_FLAG
from pyforge.herald.deck_store import DeckStore

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_CHUNK_BYTES = 1024 * 1024
_LIST_PREFIX = "/stations/herald/api/v1/deck-exports"
_STREAM_PREFIX = f"{_LIST_PREFIX}/"


@dataclass(frozen=True, slots=True)
class ExportRow:
    slug: str
    topic: str
    kind: str
    date: str
    size: int
    content_type: str
    sha256: str
    source_commit: str
    published_at: str


class AuthError(Exception):
    """Base for deck-export auth failures."""

    status_code: int = 401


class Unauthorized(AuthError):
    status_code = 401


class Forbidden(AuthError):
    status_code = 403


class NotFound(Exception):
    """Route or object missing (404)."""


class StoreError(Exception):
    """Object store refused mid-stream (502)."""


class ListRecords(Protocol):
    def __call__(self) -> list[ExportRow]: ...


class OpenStoreStream(Protocol):
    def __call__(self, sha256: str) -> tuple[ExportRow, Iterator[bytes]]: ...


def deck_publish_enabled(*, flags_path: str | None = None) -> bool:
    return read_boolean(DECK_PUBLISH_FLAG, default=False, flags_path=flags_path)


def normalize_sha256(raw: str) -> str:
    value = raw.strip().lower()
    if _SHA256_HEX.fullmatch(value) is None:
        raise NotFound
    return value


def export_filename(row: ExportRow) -> str:
    return f"{row.slug}-{row.kind}-{row.date}"


def list_exports_json(*, list_records: ListRecords, flags_path: str | None = None) -> list[dict[str, Any]]:
    if not deck_publish_enabled(flags_path=flags_path):
        raise NotFound
    rows = list_records()
    return [
        {
            "slug": row.slug,
            "topic": row.topic,
            "kind": row.kind,
            "date": row.date,
            "size": row.size,
            "content_type": row.content_type,
            "sha256": row.sha256,
            "source_commit": row.source_commit,
            "published_at": row.published_at,
        }
        for row in rows
    ]


def stream_export_chunks(
    sha256: str,
    *,
    open_stream: OpenStoreStream,
    flags_path: str | None = None,
) -> tuple[ExportRow, Iterator[bytes]]:
    if not deck_publish_enabled(flags_path=flags_path):
        raise NotFound
    key = normalize_sha256(sha256)
    try:
        row, chunks = open_stream(key)
    except KeyError as exc:
        raise NotFound from exc
    except OSError as exc:
        raise StoreError(str(exc)) from exc
    return row, chunks


def default_list_records() -> list[ExportRow]:
    from django_herald_portal.models import DeckExport  # noqa: PLC0415

    rows: list[ExportRow] = []
    for item in DeckExport.objects.all().order_by("slug", "kind", "-export_date"):
        rows.append(
            ExportRow(
                slug=item.slug,
                topic=item.topic,
                kind=item.kind,
                date=item.export_date.isoformat(),
                size=int(item.size),
                content_type=item.content_type,
                sha256=item.sha256,
                source_commit=item.source_commit,
                published_at=item.published_at.isoformat(),
            )
        )
    return rows


def default_open_store_stream(sha256: str) -> tuple[ExportRow, Iterator[bytes]]:
    from django_herald_portal.models import DeckExport  # noqa: PLC0415

    from pyforge.herald import deck_store  # noqa: PLC0415

    try:
        item = DeckExport.objects.get(sha256=sha256)
    except DeckExport.DoesNotExist as exc:
        raise KeyError(sha256) from exc
    row = ExportRow(
        slug=item.slug,
        topic=item.topic,
        kind=item.kind,
        date=item.export_date.isoformat(),
        size=int(item.size),
        content_type=item.content_type,
        sha256=item.sha256,
        source_commit=item.source_commit,
        published_at=item.published_at.isoformat(),
    )
    store: DeckStore = deck_store.open_deck_store()
    key = f"sha256/{sha256}"

    def _iter() -> Iterator[bytes]:
        try:
            yield from store.open_stream(key)
        except KeyError as exc:
            raise StoreError(str(exc)) from exc
        except OSError as exc:
            raise StoreError(str(exc)) from exc

    return row, _iter()


def resolve_herald_roles(headers: Mapping[str, str], cookies: Mapping[str, str]) -> frozenset[str]:
    """Bearer service assertion or portal session ``IDP_TOKEN_CLAIMS`` (Story 29.2)."""
    from django_pyforge.assertion.crypto import verify_assertion  # noqa: PLC0415
    from django_pyforge.assertion.exceptions import AssertionRefusedError  # noqa: PLC0415
    from django_pyforge.assertion.schema import audience_for  # noqa: PLC0415
    from django_pyforge.roles import (  # noqa: PLC0415
        IDP_TOKEN_CLAIMS_SESSION_KEY,
        parse_role_claims,
        role_names,
        roles_from_request,
        station_roles_from_parsed,
    )

    auth = headers.get("authorization") or headers.get("Authorization")
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            try:
                claims = verify_assertion(token, audience=audience_for("herald"))
            except AssertionRefusedError as exc:
                raise Unauthorized(str(exc)) from exc
            roles_raw = claims.get("roles")
            parsed = parse_role_claims(role_names(roles_raw))
            return station_roles_from_parsed(parsed)

    from django.conf import settings  # noqa: PLC0415
    from django.contrib.sessions.backends.db import SessionStore  # noqa: PLC0415

    cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
    session_key = cookies.get(cookie_name)
    if not session_key:
        raise Unauthorized("identity required")
    store = SessionStore(session_key=session_key)
    claims = store.get(IDP_TOKEN_CLAIMS_SESSION_KEY)
    if not isinstance(claims, dict):
        raise Unauthorized("identity required")

    class _Req:
        idp_token_claims = claims

    return roles_from_request(_Req())  # type: ignore[arg-type]


def require_herald_role(roles: frozenset[str]) -> None:
    if "herald" not in roles:
        raise Forbidden("herald role required")


def assert_herald_access(headers: Mapping[str, str], cookies: Mapping[str, str]) -> None:
    roles = resolve_herald_roles(headers, cookies)
    require_herald_role(roles)


def attach_deck_export_routes(app: Any) -> None:
    """Register list/stream routes on herald's FastAPI sub-app."""
    import asyncio

    from fastapi import HTTPException, Request  # noqa: PLC0415
    from fastapi.responses import JSONResponse, StreamingResponse  # noqa: PLC0415

    @app.get(_LIST_PREFIX)
    async def list_deck_exports(request: Request) -> JSONResponse:
        try:
            await asyncio.to_thread(assert_herald_access, request.headers, request.cookies)
            payload = await asyncio.to_thread(list_exports_json, list_records=default_list_records)
        except NotFound as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        except Forbidden as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except Unauthorized as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return JSONResponse(payload)

    @app.get(_STREAM_PREFIX + "{sha256}")
    async def stream_deck_export(sha256: str, request: Request) -> StreamingResponse:
        try:
            await asyncio.to_thread(assert_herald_access, request.headers, request.cookies)
            row, chunks = await asyncio.to_thread(
                stream_export_chunks,
                sha256,
                open_stream=default_open_store_stream,
            )
        except NotFound as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        except Forbidden as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except Unauthorized as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except StoreError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        async def _async_chunks() -> Any:
            it = iter(chunks)

            def _next() -> bytes | None:
                try:
                    return next(it)
                except StopIteration:
                    return None

            while True:
                block = await asyncio.to_thread(_next)
                if block is None:
                    break
                yield block

        filename = export_filename(row)
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        return StreamingResponse(
            _async_chunks(),
            media_type=row.content_type,
            headers=headers,
        )
