"""Unit tests for ``pyforge.herald.deck_exports`` (Story 29.2)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pyforge.core.errors import PyforgeError
from pyforge.testing_kit.flags import flagd_tree

from pyforge.herald.deck_exports import (
    ExportRow,
    NotFound,
    StoreError,
    attach_deck_export_routes,
    deck_publish_enabled,
    export_filename,
    list_exports_json,
    normalize_sha256,
    stream_export_chunks,
)
from pyforge.herald.deck_publish import DECK_PUBLISH_FLAG

_SAMPLE = ExportRow(
    slug="pyforge-herald",
    topic="pyforge-herald",
    kind="html",
    date="2026-09-28",
    size=12,
    content_type="text/html",
    sha256="a" * 64,
    source_commit="abc123",
    published_at="2026-09-28T12:00:00+00:00",
)


def _bool_tree(tmp_path: Path, *, enabled: bool) -> Path:
    return flagd_tree(tmp_path, {DECK_PUBLISH_FLAG: "on" if enabled else "off"})


def test_flag_off_list_and_stream_raise_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _bool_tree(tmp_path, enabled=False)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))

    def _list() -> list[ExportRow]:
        return [_SAMPLE]

    def _open(_sha: str) -> tuple[ExportRow, Iterator[bytes]]:
        return _SAMPLE, iter([b"x"])

    with pytest.raises(NotFound):
        list_exports_json(list_records=_list, flags_path=tree)
    with pytest.raises(NotFound):
        stream_export_chunks("a" * 64, open_stream=_open, flags_path=tree)


def test_flag_on_list_returns_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _bool_tree(tmp_path, enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert deck_publish_enabled(flags_path=tree) is True
    payload = list_exports_json(list_records=lambda: [_SAMPLE], flags_path=tree)
    assert payload[0]["sha256"] == "a" * 64


def test_stream_yields_chunks_from_fake_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _bool_tree(tmp_path, enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    body = b"deck-bytes-chunked"

    def _open(_sha: str) -> tuple[ExportRow, Iterator[bytes]]:
        return _SAMPLE, iter([body[:4], body[4:]])

    row, chunks = stream_export_chunks("a" * 64, open_stream=_open, flags_path=tree)
    assert row.slug == "pyforge-herald"
    assert b"".join(chunks) == body
    assert export_filename(row) == "pyforge-herald-html-2026-09-28"


def test_normalize_sha256_rejects_bad_hex() -> None:
    with pytest.raises(NotFound):
        normalize_sha256("not-hex")


def test_list_json_shape(tmp_path: Path) -> None:
    tree = _bool_tree(tmp_path, enabled=True)
    payload = list_exports_json(list_records=lambda: [_SAMPLE], flags_path=tree)
    assert json.loads(json.dumps(payload))[0]["kind"] == "html"


def test_exception_roots_inherit_pyforge_error() -> None:
    assert issubclass(NotFound, PyforgeError)
    assert issubclass(StoreError, PyforgeError)


def test_stream_key_error_maps_to_not_found(tmp_path: Path) -> None:
    tree = _bool_tree(tmp_path, enabled=True)

    def _open(_sha: str) -> tuple[ExportRow, Iterator[bytes]]:
        raise KeyError("missing")

    with pytest.raises(NotFound):
        stream_export_chunks("a" * 64, open_stream=_open, flags_path=tree)


def test_stream_os_error_maps_to_store_error(tmp_path: Path) -> None:
    tree = _bool_tree(tmp_path, enabled=True)

    def _open(_sha: str) -> tuple[ExportRow, Iterator[bytes]]:
        raise OSError("store down")

    with pytest.raises(StoreError, match="store down"):
        stream_export_chunks("a" * 64, open_stream=_open, flags_path=tree)


class _Unauthorized(Exception):
    status_code = 401


class _Forbidden(Exception):
    status_code = 403


def _run_async(coro):
    return asyncio.run(coro)


def _herald_app(
    tmp_path: Path,
    *,
    list_records,
    open_stream,
    gate=None,
) -> FastAPI:
    tree = _bool_tree(tmp_path, enabled=True)
    app = FastAPI()

    def _gate(_headers, _cookies) -> None:
        if gate is not None:
            gate(_headers, _cookies)

    attach_deck_export_routes(
        app,
        gate=_gate,
        list_records=list_records,
        open_stream=open_stream,
        auth_errors=(_Unauthorized, _Forbidden),
    )
    app.state.flags_path = tree
    return app


@pytest.fixture
def _patch_deck_flag_path(monkeypatch: pytest.MonkeyPatch):
    def _apply(app: FastAPI) -> None:
        monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(app.state.flags_path))

    return _apply


def test_attach_routes_list_and_stream(tmp_path: Path, _patch_deck_flag_path) -> None:
    app = _herald_app(
        tmp_path,
        list_records=lambda: [_SAMPLE],
        open_stream=lambda _sha: (_SAMPLE, iter([b"ab", b"cd"])),
    )
    _patch_deck_flag_path(app)

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            listed = await client.get("/stations/herald/api/v1/deck-exports")
            streamed = await client.get(f"/stations/herald/api/v1/deck-exports/{'a' * 64}")
            return listed, streamed

    listed, streamed = _run_async(_call())
    assert listed.status_code == 200
    assert listed.json()[0]["slug"] == "pyforge-herald"
    assert streamed.status_code == 200
    assert streamed.content == b"abcd"
    assert "attachment" in streamed.headers.get("content-disposition", "")


def test_attach_routes_forbidden_when_gate_refuses(tmp_path: Path, _patch_deck_flag_path) -> None:
    def _deny(_headers, _cookies) -> None:
        raise _Forbidden("nope")

    app = _herald_app(
        tmp_path,
        list_records=lambda: [_SAMPLE],
        open_stream=lambda _sha: (_SAMPLE, iter([b"x"])),
        gate=_deny,
    )
    _patch_deck_flag_path(app)

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/stations/herald/api/v1/deck-exports")

    response = _run_async(_call())
    assert response.status_code == 403


def test_attach_routes_missing_object_is_404(tmp_path: Path, _patch_deck_flag_path) -> None:
    def _open(_sha: str) -> tuple[ExportRow, Iterator[bytes]]:
        raise KeyError(_sha)

    app = _herald_app(
        tmp_path,
        list_records=lambda: [_SAMPLE],
        open_stream=_open,
    )
    _patch_deck_flag_path(app)

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(f"/stations/herald/api/v1/deck-exports/{'b' * 64}")

    response = _run_async(_call())
    assert response.status_code == 404


def test_attach_routes_store_error_is_502(tmp_path: Path, _patch_deck_flag_path) -> None:
    def _open(_sha: str) -> tuple[ExportRow, Iterator[bytes]]:
        raise OSError("broken pipe")

    app = _herald_app(tmp_path, list_records=lambda: [_SAMPLE], open_stream=_open)
    _patch_deck_flag_path(app)

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(f"/stations/herald/api/v1/deck-exports/{'a' * 64}")

    response = _run_async(_call())
    assert response.status_code == 502
    assert "broken pipe" in response.text


def test_attach_routes_mid_stream_store_error_closes_body(tmp_path: Path, _patch_deck_flag_path) -> None:
    def _open(_sha: str) -> tuple[ExportRow, Iterator[bytes]]:
        def _chunks() -> Iterator[bytes]:
            yield b"partial"
            raise OSError("store refused mid-stream")

        return _SAMPLE, _chunks()

    app = _herald_app(tmp_path, list_records=lambda: [_SAMPLE], open_stream=_open)
    _patch_deck_flag_path(app)

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(f"/stations/herald/api/v1/deck-exports/{'a' * 64}")

    response = _run_async(_call())
    assert response.status_code == 200
    assert response.content == b"partial"
