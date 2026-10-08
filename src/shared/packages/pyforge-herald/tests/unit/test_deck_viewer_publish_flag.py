"""ON/OFF tests for twin publish via ``pyforge.herald.deck_viewer`` (Story 30.1)."""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.testing_kit.cli_runner import invoke_cli
from pyforge.testing_kit.flags import flagd_tree

from pyforge.herald.cli import main
from pyforge.herald.deck_publish import DECK_PUBLISH_FLAG
from pyforge.herald.deck_store import MemoryDeckStore
from pyforge.herald.twins import DECK_VIEWER_FLAG


def _deck_tree(tmp_path: Path) -> Path:
    slug = "demo-deck"
    pptx_dir = tmp_path / "presentations" / slug / "src" / "pptx"
    pptx_dir.mkdir(parents=True, exist_ok=True)
    (pptx_dir / f"{slug}-deck-2026-09-01.pptx").write_bytes(b"pptx")
    marp_dir = tmp_path / "presentations" / slug / "src" / "marp"
    marp_dir.mkdir(parents=True, exist_ok=True)
    (marp_dir / f"{slug}-infographic-standalone-2026-09-01.html").write_text(
        "<html><body>local</body></html>",
        encoding="utf-8",
    )
    return tmp_path


def test_publish_skips_twins_when_deck_viewer_off(tmp_path: Path, monkeypatch):
    slug = "demo-deck"
    tree = _deck_tree(tmp_path)
    monkeypatch.chdir(tree)
    flags = {
        DECK_PUBLISH_FLAG: "on",
        DECK_VIEWER_FLAG: "off",
    }
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, flags)))
    mem = MemoryDeckStore()
    monkeypatch.setattr("pyforge.herald.deck_store.open_deck_store", lambda **_: mem)
    assert main(["deck", "publish", slug, "--repo-root", str(tree)]) == 0
    raw = b"".join(mem.open_stream(f"manifests/{slug}.json"))
    data = json.loads(raw.decode("utf-8"))
    assert "twins" not in data


def test_publish_includes_twins_when_deck_viewer_on(tmp_path: Path, monkeypatch):
    slug = "demo-deck"
    tree = _deck_tree(tmp_path)
    monkeypatch.chdir(tree)
    flags = {
        DECK_PUBLISH_FLAG: "on",
        DECK_VIEWER_FLAG: "on",
    }
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, flags)))
    mem = MemoryDeckStore()
    monkeypatch.setattr("pyforge.herald.deck_store.open_deck_store", lambda **_: mem)
    assert main(["deck", "publish", slug, "--repo-root", str(tree)]) == 0
    raw = b"".join(mem.open_stream(f"manifests/{slug}.json"))
    data = json.loads(raw.decode("utf-8"))
    assert "twins" in data
    assert "standalone" in data["twins"]
