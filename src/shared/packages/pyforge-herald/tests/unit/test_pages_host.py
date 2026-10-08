"""ON/OFF tests for the Pages second-host flag read (Story 31.1, CAP-56)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.testing_kit.flags import flagd_tree

from pyforge.herald.pages_host import PAGES_SECOND_HOST_FLAG, pages_second_host_enabled


def test_the_key_is_the_one_the_tree_declares() -> None:
    assert PAGES_SECOND_HOST_FLAG == "pyforge.herald.pages_second_host"


def test_on_and_off_trees_read_through_flags_path(tmp_path: Path) -> None:
    on = flagd_tree(tmp_path, {PAGES_SECOND_HOST_FLAG: "on"}, name="on.json")
    off = flagd_tree(tmp_path, {PAGES_SECOND_HOST_FLAG: "off"}, name="off.json")
    assert pages_second_host_enabled(flags_path=on) is True
    assert pages_second_host_enabled(flags_path=off) is False


def test_on_and_off_trees_read_through_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {PAGES_SECOND_HOST_FLAG: "on"}, name="on.json")))
    assert pages_second_host_enabled() is True
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {PAGES_SECOND_HOST_FLAG: "off"}, name="off.json"))
    )
    assert pages_second_host_enabled() is False
