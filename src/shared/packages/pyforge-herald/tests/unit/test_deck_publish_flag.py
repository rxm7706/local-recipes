"""ON/OFF tests for ``pyforge.herald.deck_publish`` (CAP-54, feature-flag-governance Q3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.herald.cli import main
from pyforge.herald.deck_publish import DECK_PUBLISH_FLAG
from pyforge.herald.deck_store import MemoryDeckStore
from pyforge.testing_kit.cli_runner import invoke_cli
from pyforge.testing_kit.flags import flagd_tree


@pytest.fixture
def deck_tree(tmp_path: Path) -> Path:
    slug = "demo-deck"
    pptx = tmp_path / "presentations" / slug / "src" / "pptx" / "demo-deck-deck-2026-09-01.pptx"
    pptx.parent.mkdir(parents=True, exist_ok=True)
    pptx.write_bytes(b"export-bytes")
    return tmp_path


def test_publish_flag_off_lists_disabled_and_exits_usage(deck_tree: Path, tmp_path: Path, monkeypatch):
    monkeypatch.chdir(deck_tree)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {DECK_PUBLISH_FLAG: "off"})))
    help_out = invoke_cli(main, ["deck", "--help"]).output
    assert "publish" in help_out
    assert "disabled" in help_out.lower()
    result = invoke_cli(main, ["deck", "publish", "demo-deck", "--repo-root", str(deck_tree)])
    assert result.exit_code == 2
    assert "flag" in result.output.lower()


def test_publish_succeeds_when_flag_on(deck_tree: Path, tmp_path: Path, monkeypatch):
    monkeypatch.chdir(deck_tree)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {DECK_PUBLISH_FLAG: "on"})))
    mem = MemoryDeckStore()
    monkeypatch.setattr("pyforge.herald.deck_store.open_deck_store", lambda **_: mem)
    assert main(["deck", "publish", "demo-deck", "--repo-root", str(deck_tree)]) == 0
    assert mem.head("manifests/demo-deck.json") is not None
