"""Unit tests for ``pyforge.herald.deck_twins`` (Story 30.2)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pyforge.testing_kit.flags import flagd_tree

from pyforge.herald.deck_twins import (
    NotFound,
    StoreError,
    attach_deck_twin_routes,
    deck_viewer_enabled,
    iframe_twin_path,
    normalize_twin_path,
    parse_twins_section,
    resolve_twin_sha256,
    stream_twin_bytes,
)
from pyforge.herald.twins import DECK_VIEWER_FLAG

_STANDALONE_MANIFEST = {
    "twins": {
        "standalone": {
            "sha256": "a" * 64,
            "content_type": "text/html",
            "size": 10,
            "path": "presentations/demo/x.html",
        }
    }
}

_BUNDLE_MANIFEST = {
    "twins": {
        "bundle": {
            "files": {
                "index.html": "b" * 64,
                "assets/app.js": "c" * 64,
            }
        }
    }
}


def _tree(tmp_path: Path, *, enabled: bool) -> Path:
    return flagd_tree(tmp_path, {DECK_VIEWER_FLAG: "on" if enabled else "off"})


def test_normalize_twin_path_rejects_traversal() -> None:
    with pytest.raises(NotFound):
        normalize_twin_path("../secret")
    with pytest.raises(NotFound):
        normalize_twin_path("assets/../../x")


def test_normalize_twin_path_empty_means_entry_document() -> None:
    assert normalize_twin_path("") == ""
    assert normalize_twin_path("  /  ") == ""


def test_resolve_standalone_and_bundle_paths() -> None:
    sha, media = resolve_twin_sha256(_STANDALONE_MANIFEST["twins"], "")
    assert sha == "a" * 64
    assert media == "text/html"
    sha2, _ = resolve_twin_sha256(_BUNDLE_MANIFEST["twins"], "assets/app.js")
    assert sha2 == "c" * 64
    with pytest.raises(NotFound):
        resolve_twin_sha256(_STANDALONE_MANIFEST["twins"], "extra.js")


def test_resolve_bundle_missing_file_raises_not_found() -> None:
    with pytest.raises(NotFound):
        resolve_twin_sha256(_BUNDLE_MANIFEST["twins"], "missing.js")


def test_resolve_standalone_invalid_sha_raises_not_found() -> None:
    twins = {"standalone": {"sha256": "too-short", "content_type": "text/html"}}
    with pytest.raises(NotFound):
        resolve_twin_sha256(twins, "")


def test_flag_off_stream_raises_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, enabled=False)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert deck_viewer_enabled(flags_path=tree) is False

    def _open(_slug: str, _path: str) -> tuple[str, Iterator[bytes]]:
        return "text/html", iter([b"x"])

    with pytest.raises(NotFound):
        stream_twin_bytes("demo", "", open_stream=_open, flags_path=tree)


def test_parse_twins_section() -> None:
    raw = json.dumps(_BUNDLE_MANIFEST).encode()
    twins = parse_twins_section(raw)
    assert twins is not None
    assert "bundle" in twins


def test_parse_twins_section_rejects_non_object_manifest() -> None:
    assert parse_twins_section(b"[]") is None
    assert parse_twins_section(json.dumps({"twins": "not-a-map"}).encode()) is None


def test_iframe_twin_path_for_bundle_and_standalone() -> None:
    assert iframe_twin_path(_BUNDLE_MANIFEST["twins"]) == "index.html"
    assert iframe_twin_path(_STANDALONE_MANIFEST["twins"]) == ""
    assert iframe_twin_path({}) is None


def test_deck_viewer_enabled_when_flag_on(tmp_path: Path) -> None:
    tree = _tree(tmp_path, enabled=True)
    assert deck_viewer_enabled(flags_path=tree) is True


class _Forbidden(Exception):
    status_code = 403


def _run_async(coro):
    return asyncio.run(coro)


def test_route_sets_csp_and_streams(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    app = FastAPI()

    def _gate(_headers, _cookies) -> None:
        return None

    def _open(_slug: str, _path: str) -> tuple[str, Iterator[bytes]]:
        return "text/html", iter([b"<html></html>"])

    attach_deck_twin_routes(app, gate=_gate, open_stream=_open, auth_errors=())

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/stations/herald/api/v1/deck-twins/demo-deck/index.html")

    response = asyncio.run(_call())
    assert response.status_code == 200
    csp = response.headers.get("content-security-policy", "")
    assert "'self'" in csp
    assert "https://" not in csp
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_route_streams_twin_root_without_path_segment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    app = FastAPI()

    def _gate(_headers, _cookies) -> None:
        return None

    def _open(_slug: str, path: str) -> tuple[str, Iterator[bytes]]:
        assert path == ""
        return "text/html", iter([b"root"])

    attach_deck_twin_routes(app, gate=_gate, open_stream=_open, auth_errors=(_Forbidden,))

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/stations/herald/api/v1/deck-twins/demo-deck")

    response = _run_async(_call())
    assert response.status_code == 200
    assert response.content == b"root"


def test_route_returns_404_when_flag_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, enabled=False)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    app = FastAPI()
    attach_deck_twin_routes(
        app,
        gate=lambda _h, _c: None,
        open_stream=lambda _s, _p: ("text/html", iter([b"x"])),
        auth_errors=(),
    )

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/stations/herald/api/v1/deck-twins/demo-deck/")

    response = _run_async(_call())
    assert response.status_code == 404


def test_route_maps_gate_forbidden_to_403(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    app = FastAPI()

    def _deny(_headers, _cookies) -> None:
        raise _Forbidden("nope")

    attach_deck_twin_routes(
        app,
        gate=_deny,
        open_stream=lambda _s, _p: ("text/html", iter([b"x"])),
        auth_errors=(_Forbidden,),
    )

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/stations/herald/api/v1/deck-twins/demo-deck/x.html")

    response = _run_async(_call())
    assert response.status_code == 403


def test_route_open_stream_not_found_is_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    app = FastAPI()

    def _open(_slug: str, _path: str) -> tuple[str, Iterator[bytes]]:
        raise NotFound("missing twin object")

    attach_deck_twin_routes(
        app,
        gate=lambda _h, _c: None,
        open_stream=_open,
        auth_errors=(),
    )

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/stations/herald/api/v1/deck-twins/demo-deck/x.html")

    response = _run_async(_call())
    assert response.status_code == 404


def test_route_store_error_from_open_is_502(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = _tree(tmp_path, enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    app = FastAPI()

    def _open(_slug: str, _path: str) -> tuple[str, Iterator[bytes]]:
        raise StoreError("store down")

    attach_deck_twin_routes(
        app,
        gate=lambda _h, _c: None,
        open_stream=_open,
        auth_errors=(),
    )

    async def _call():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/stations/herald/api/v1/deck-twins/demo-deck/x.html")

    response = _run_async(_call())
    assert response.status_code == 502
