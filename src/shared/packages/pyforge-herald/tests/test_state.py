"""``state.py``'s read/write round-trip (Story 1.4, AD-5).

Every case uses an explicit ``tmp_path``-derived ``state_path`` -- ``state.py``
never assumes a cwd, so no test here may either.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.herald.errors import HeraldError
from pyforge.herald.state import DEFAULT_STATE_PATH, DeckState, read, write


def test_default_state_path_is_the_ad5_default():
    assert DEFAULT_STATE_PATH == Path(".herald/bridge-state.json")


def test_state_round_trips_field_for_field(tmp_path: Path):
    state_path = tmp_path / ".herald" / "bridge-state.json"
    original = DeckState(project_id="p1", etags={"prototype": "E1"}, last_pull=None)
    write(state_path, "x", original)
    assert read(state_path, "x") == original


def test_read_of_an_unknown_slug_returns_none(tmp_path: Path):
    state_path = tmp_path / "bridge-state.json"
    write(state_path, "a", DeckState(project_id="p1", etags={}, last_pull=None))
    assert read(state_path, "b") is None


def test_read_of_a_missing_file_returns_none(tmp_path: Path):
    state_path = tmp_path / "does-not-exist" / "bridge-state.json"
    assert read(state_path, "x") is None


def test_write_preserves_another_slug_already_present(tmp_path: Path):
    state_path = tmp_path / "bridge-state.json"
    state_a = DeckState(project_id="p-a", etags={"prototype": "E1"}, last_pull="t1")
    state_b = DeckState(project_id="p-b", etags={"prototype": "E2"}, last_pull=None)
    write(state_path, "a", state_a)
    write(state_path, "b", state_b)
    assert read(state_path, "a") == state_a
    assert read(state_path, "b") == state_b


def test_write_creates_the_parent_directory(tmp_path: Path):
    state_path = tmp_path / "nested" / "dir" / "bridge-state.json"
    write(state_path, "x", DeckState(project_id="p1", etags={}, last_pull=None))
    assert state_path.exists()


def test_overwriting_the_same_slug_replaces_its_entry(tmp_path: Path):
    state_path = tmp_path / "bridge-state.json"
    write(
        state_path, "x", DeckState(project_id="p1", etags={"a": "E1"}, last_pull=None)
    )
    updated = DeckState(
        project_id="p1", etags={"a": "E2"}, last_pull="2026-07-30T00:00:00Z"
    )
    write(state_path, "x", updated)
    assert read(state_path, "x") == updated


def test_read_of_invalid_json_raises_herald_error(tmp_path: Path):
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text("{not valid json")
    with pytest.raises(HeraldError, match=str(state_path)):
        read(state_path, "x")


def test_read_of_a_non_object_top_level_document_raises_herald_error(tmp_path: Path):
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text("[1, 2, 3]")
    with pytest.raises(HeraldError, match=str(state_path)):
        read(state_path, "x")


def test_read_of_a_malformed_entry_raises_herald_error(tmp_path: Path):
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text('{"x": {"project_id": "p1"}}')  # missing "etags"
    with pytest.raises(HeraldError, match="x"):
        read(state_path, "x")


def test_read_of_an_entry_with_the_wrong_field_types_raises_herald_error(
    tmp_path: Path,
):
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text('{"x": {"project_id": 123, "etags": {}}}')
    with pytest.raises(HeraldError, match="x"):
        read(state_path, "x")
