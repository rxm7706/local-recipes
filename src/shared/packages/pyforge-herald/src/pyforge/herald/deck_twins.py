"""Deck twin list/stream handlers for herald's v1 station API (CAP-55 FR-10.4)."""

from __future__ import annotations

import asyncio
import json
import mimetypes
from collections.abc import Callable, Iterator, Mapping
from typing import Any, Protocol

from asgiref.sync import sync_to_async
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from pyforge.core.errors import PyforgeError
from pyforge.core.flags import read_boolean

from pyforge.herald.twins import DECK_VIEWER_FLAG

_TWIN_PREFIX = "/stations/herald/api/v1/deck-twins"
_TWIN_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
    "frame-ancestors 'self'; base-uri 'self'"
)


class NotFound(PyforgeError, Exception):
    """Route or twin object missing (404)."""


class StoreError(PyforgeError, Exception):
    """Object store refused mid-stream (502)."""


class OpenTwinStream(Protocol):
    def __call__(self, slug: str, path: str) -> tuple[str, Iterator[bytes]]: ...


AccessGate = Callable[[Mapping[str, str], Mapping[str, str]], None]


def deck_viewer_enabled(*, flags_path: str | None = None) -> bool:
    return read_boolean(DECK_VIEWER_FLAG, default=False, flags_path=flags_path)


def normalize_twin_path(raw: str) -> str:
    """Return a safe relative path within a twin bundle (empty means the entry document)."""
    cleaned = raw.strip().lstrip("/")
    if not cleaned:
        return ""
    parts = cleaned.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise NotFound
    return "/".join(parts)


def content_type_for_path(path: str) -> str:
    name = path.rsplit("/", 1)[-1] if path else "index.html"
    guessed, _ = mimetypes.guess_type(name)
    return guessed or "application/octet-stream"


def resolve_twin_sha256(twins: Mapping[str, object], path: str) -> tuple[str, str]:
    """Map *path* through the manifest twins section to a store sha256 and media type."""
    normalized = normalize_twin_path(path)
    bundle = twins.get("bundle")
    if isinstance(bundle, Mapping):
        files = bundle.get("files")
        if isinstance(files, Mapping):
            rel = normalized or "index.html"
            sha = files.get(rel)
            if isinstance(sha, str) and len(sha) == 64:
                return sha, content_type_for_path(rel)
            raise NotFound
    standalone = twins.get("standalone")
    if isinstance(standalone, Mapping):
        if normalized:
            raise NotFound
        sha = standalone.get("sha256")
        content_type = standalone.get("content_type")
        if isinstance(sha, str) and len(sha) == 64:
            media = content_type if isinstance(content_type, str) and content_type else "text/html"
            return sha, media
    raise NotFound


def parse_twins_section(raw_manifest: bytes) -> dict[str, object] | None:
    data = json.loads(raw_manifest.decode("utf-8"))
    if not isinstance(data, dict):
        return None
    twins = data.get("twins")
    if isinstance(twins, dict):
        return twins
    return None


def iframe_twin_path(twins: Mapping[str, object]) -> str | None:
    """Relative path segment for the viewer iframe's first request."""
    bundle = twins.get("bundle")
    if isinstance(bundle, Mapping) and isinstance(bundle.get("files"), Mapping):
        return "index.html"
    standalone = twins.get("standalone")
    if isinstance(standalone, Mapping) and standalone.get("sha256"):
        return ""
    return None


def stream_twin_bytes(
    slug: str,
    path: str,
    *,
    open_stream: OpenTwinStream,
    flags_path: str | None = None,
) -> tuple[str, Iterator[bytes]]:
    if not deck_viewer_enabled(flags_path=flags_path):
        raise NotFound
    _ = slug  # slug is validated by open_stream
    return open_stream(slug, path)


def attach_deck_twin_routes(
    app: Any,
    *,
    gate: AccessGate,
    open_stream: OpenTwinStream,
    auth_errors: tuple[type[Exception], ...],
) -> None:
    """Register twin stream routes; ``auth_errors`` maps gate failures to HTTP status."""

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

    def _open(slug: str, path: str, request: Request) -> tuple[str, Iterator[bytes]]:
        gate(_header_map(request), _cookie_map(request))
        return stream_twin_bytes(slug, path, open_stream=open_stream)

    async def _respond(slug: str, path: str, request: Request) -> StreamingResponse:
        try:
            media_type, chunks = await sync_to_async(_open)(slug, path, request)
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
                except OSError as exc:
                    raise StoreError(str(exc)) from exc

            while True:
                try:
                    block = await asyncio.to_thread(_next)
                except StoreError:
                    break
                if block is None:
                    break
                yield block

        headers = {
            "Content-Security-Policy": _TWIN_CSP,
        }
        return StreamingResponse(_async_chunks(), media_type=media_type, headers=headers)

    @app.get(_TWIN_PREFIX + "/{slug}", response_model=None)
    async def stream_deck_twin_root(slug: str, request: Request):
        return await _respond(slug, "", request)

    @app.get(_TWIN_PREFIX + "/{slug}/{path:path}", response_model=None)
    async def stream_deck_twin(slug: str, path: str, request: Request):
        return await _respond(slug, path, request)
