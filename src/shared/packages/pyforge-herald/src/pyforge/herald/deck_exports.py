"""Deck export list/stream handlers for herald's v1 station API (CAP-54 FR-10.2)."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from asgiref.sync import sync_to_async
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pyforge.core.flags import read_boolean

from pyforge.herald.deck_publish import DECK_PUBLISH_FLAG

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
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


class NotFound(Exception):
    """Route or object missing (404)."""


class StoreError(Exception):
    """Object store refused mid-stream (502)."""


class ListRecords(Protocol):
    def __call__(self) -> list[ExportRow]: ...


class OpenStoreStream(Protocol):
    def __call__(self, sha256: str) -> tuple[ExportRow, Iterator[bytes]]: ...


AccessGate = Callable[[Mapping[str, str], Mapping[str, str]], None]


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


def attach_deck_export_routes(
    app: Any,
    *,
    gate: AccessGate,
    list_records: ListRecords,
    open_stream: OpenStoreStream,
    auth_errors: tuple[type[Exception], ...],
) -> None:
    """Register list/stream routes; ``auth_errors`` maps gate failures to HTTP status."""

    def _http_for_auth(exc: Exception) -> HTTPException:
        for kind in auth_errors:
            if isinstance(exc, kind):
                code = getattr(kind, "status_code", 401)
                return HTTPException(status_code=code, detail=str(exc))
        return HTTPException(status_code=401, detail=str(exc))

    def _header_map(request: Request) -> dict[str, str]:
        return dict(request.headers)

    def _cookie_map(request: Request) -> dict[str, str]:
        return dict(request.cookies)

    def _list_payload(request: Request) -> list[dict[str, Any]]:
        gate(_header_map(request), _cookie_map(request))
        return list_exports_json(list_records=list_records)

    @app.get(_LIST_PREFIX, response_model=None)
    async def list_deck_exports(request: Request):
        try:
            payload = await sync_to_async(_list_payload)(request)
        except NotFound as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        except auth_errors as exc:
            raise _http_for_auth(exc) from exc
        return JSONResponse(payload)

    def _stream_open(sha256: str, request: Request) -> tuple[ExportRow, Iterator[bytes]]:
        gate(_header_map(request), _cookie_map(request))
        return stream_export_chunks(sha256, open_stream=open_stream)

    @app.get(_STREAM_PREFIX + "{sha256}", response_model=None)
    async def stream_deck_export(sha256: str, request: Request):
        try:
            row, chunks = await sync_to_async(_stream_open)(sha256, request)
        except NotFound as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        except auth_errors as exc:
            raise _http_for_auth(exc) from exc
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
