"""Twin publishing behind ``pyforge.herald.deck_viewer`` (Story 30.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.testing_kit.flags import flagd_tree

from pyforge.herald.deck_publish import publish_deck
from pyforge.herald.deck_store import MemoryDeckStore
from pyforge.herald.twins import DECK_VIEWER_FLAG, TwinOriginError


def _minimal_deck(tmp_path: Path, slug: str = "demo-deck") -> Path:
    pptx_dir = tmp_path / "presentations" / slug / "src" / "pptx"
    pptx_dir.mkdir(parents=True, exist_ok=True)
    (pptx_dir / f"{slug}-deck-2026-09-01.pptx").write_bytes(b"pptx")
    marp_dir = tmp_path / "presentations" / slug / "src" / "marp"
    marp_dir.mkdir(parents=True, exist_ok=True)
    standalone = marp_dir / f"{slug}-infographic-standalone-2026-09-01.html"
    standalone.write_text("<html><body>local twin</body></html>", encoding="utf-8")
    return tmp_path


def test_publish_refuses_planted_external_origin(tmp_path: Path):
    slug = "demo-deck"
    _minimal_deck(tmp_path, slug)
    standalone = (
        tmp_path
        / "presentations"
        / slug
        / "src"
        / "marp"
        / f"{slug}-infographic-standalone-2026-09-01.html"
    )
    standalone.write_text(
        '<html><head><link href="https://fonts.googleapis.com/css" rel="stylesheet"></head>'
        "<body></body></html>",
        encoding="utf-8",
    )
    store = MemoryDeckStore()
    with pytest.raises(TwinOriginError, match="fonts.googleapis.com"):
        publish_deck(slug, repo_root=tmp_path, store=store, include_twins=True)


def test_publish_twins_on_records_manifest(tmp_path: Path):
    slug = "demo-deck"
    _minimal_deck(tmp_path, slug)
    store = MemoryDeckStore()
    publish_deck(slug, repo_root=tmp_path, store=store, include_twins=True)
    raw = b"".join(store.open_stream(f"manifests/{slug}.json"))
    data = json.loads(raw.decode("utf-8"))
    assert "twins" in data
    assert "standalone" in data["twins"]
    assert data["twins"]["standalone"]["sha256"]


def test_publish_twins_off_omits_manifest_section(tmp_path: Path):
    slug = "demo-deck"
    _minimal_deck(tmp_path, slug)
    store = MemoryDeckStore()
    publish_deck(slug, repo_root=tmp_path, store=store, include_twins=False)
    raw = b"".join(store.open_stream(f"manifests/{slug}.json"))
    data = json.loads(raw.decode("utf-8"))
    assert "twins" not in data


def test_deck_viewer_flag_constant():
    assert DECK_VIEWER_FLAG == "pyforge.herald.deck_viewer"


def test_flagd_tree_deck_viewer(tmp_path: Path):
    tree = flagd_tree(tmp_path, {"pyforge.herald.deck_viewer": "on"})
    assert tree  # fixture returns path string
