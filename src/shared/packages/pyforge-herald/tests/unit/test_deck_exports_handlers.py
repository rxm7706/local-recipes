"""Unit tests for ``pyforge.herald.deck_exports`` (Story 29.2)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from pyforge.herald.deck_exports import ExportRow
from pyforge.herald.deck_exports import Forbidden
from pyforge.herald.deck_exports import NotFound
from pyforge.herald.deck_exports import Unauthorized
from pyforge.herald.deck_exports import assert_herald_access
from pyforge.herald.deck_exports import deck_publish_enabled
from pyforge.herald.deck_exports import export_filename
from pyforge.herald.deck_exports import list_exports_json
from pyforge.herald.deck_exports import normalize_sha256
from pyforge.herald.deck_exports import require_herald_role
from pyforge.herald.deck_exports import stream_export_chunks
from pyforge.herald.deck_publish import DECK_PUBLISH_FLAG
from pyforge.testing_kit.flags import flagd_tree

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


def test_require_herald_role_forbids_other_stations() -> None:
    with pytest.raises(Forbidden):
        require_herald_role(frozenset({"steward"}))


def test_anonymous_headers_raise_unauthorized() -> None:
    with pytest.raises(Unauthorized):
        assert_herald_access({}, {})


def test_list_json_shape(tmp_path: Path) -> None:
    tree = _bool_tree(tmp_path, enabled=True)
    payload = list_exports_json(list_records=lambda: [_SAMPLE], flags_path=tree)
    assert json.loads(json.dumps(payload))[0]["kind"] == "html"
