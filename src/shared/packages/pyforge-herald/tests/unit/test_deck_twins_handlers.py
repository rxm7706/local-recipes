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
    attach_deck_twin_routes,
    deck_viewer_enabled,
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


def test_resolve_standalone_and_bundle_paths() -> None:
    sha, media = resolve_twin_sha256(_STANDALONE_MANIFEST["twins"], "")
    assert sha == "a" * 64
    assert media == "text/html"
    sha2, _ = resolve_twin_sha256(_BUNDLE_MANIFEST["twins"], "assets/app.js")
    assert sha2 == "c" * 64
    with pytest.raises(NotFound):
        resolve_twin_sha256(_STANDALONE_MANIFEST["twins"], "extra.js")


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
