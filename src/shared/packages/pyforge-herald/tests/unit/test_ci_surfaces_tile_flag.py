"""ON/OFF tests for the CI surfaces tile flag read (Story 39.1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.testing_kit.flags import flagd_tree

from pyforge.herald.ci_surfaces_tile import CI_SURFACES_TILE_FLAG, ci_surfaces_tile_enabled


def test_the_key_is_the_one_the_tree_declares() -> None:
    assert CI_SURFACES_TILE_FLAG == "pyforge.herald.ci_surfaces_tile"


def test_on_and_off_trees_read_through_flags_path(tmp_path: Path) -> None:
    on = flagd_tree(tmp_path, {CI_SURFACES_TILE_FLAG: "on"}, name="on.json")
    off = flagd_tree(tmp_path, {CI_SURFACES_TILE_FLAG: "off"}, name="off.json")
    assert ci_surfaces_tile_enabled(flags_path=on) is True
    assert ci_surfaces_tile_enabled(flags_path=off) is False


def test_on_and_off_trees_read_through_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {CI_SURFACES_TILE_FLAG: "on"}, name="on.json")))
    assert ci_surfaces_tile_enabled() is True
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {CI_SURFACES_TILE_FLAG: "off"}, name="off.json")))
    assert ci_surfaces_tile_enabled() is False
