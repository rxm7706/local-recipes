"""``state.py``'s read/write round-trip (Story 1.4, AD-5).

Every case uses an explicit ``tmp_path``-derived ``state_path`` -- ``state.py``
never assumes a cwd, so no test here may either.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from pyforge.herald import state as state_module
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
    write(state_path, "x", DeckState(project_id="p1", etags={"a": "E1"}, last_pull=None))
    updated = DeckState(project_id="p1", etags={"a": "E2"}, last_pull="2026-07-30T00:00:00Z")
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


def test_read_of_a_binary_corrupt_file_raises_herald_error(tmp_path: Path):
    """UnicodeDecodeError is JSONDecodeError's sibling under ValueError, not
    a subclass -- a truncated or wrong-encoding write must not leak it raw."""
    state_path = tmp_path / "bridge-state.json"
    state_path.write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(HeraldError, match="could not be read"):
        read(state_path, "x")


def test_read_of_a_state_path_that_is_a_directory_raises_herald_error(
    tmp_path: Path,
):
    state_path = tmp_path / "bridge-state.json"
    state_path.mkdir()
    with pytest.raises(HeraldError, match="could not be read"):
        read(state_path, "x")


def test_read_of_an_entry_with_a_non_string_etag_value_raises_herald_error(
    tmp_path: Path,
):
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text('{"x": {"project_id": "p1", "etags": {"prototype": 5}}}')
    with pytest.raises(HeraldError, match="x"):
        read(state_path, "x")


def test_read_of_an_entry_with_a_non_string_last_pull_raises_herald_error(
    tmp_path: Path,
):
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text('{"x": {"project_id": "p1", "etags": {}, "last_pull": 123}}')
    with pytest.raises(HeraldError, match="x"):
        read(state_path, "x")


def test_write_blocked_by_a_plain_file_in_the_parent_path_raises_herald_error(
    tmp_path: Path,
):
    """A plain file where the `.herald` directory should be must surface as
    a HeraldError, not a bare FileExistsError/NotADirectoryError. The lock
    acquisition (Story 13.1) now trips first -- it needs the same parent
    directory to hold the sidecar `.lock` file -- and wraps the mkdir
    failure as "could not be acquired" itself."""
    blocker = tmp_path / ".herald"
    blocker.write_text("not a directory")
    state_path = blocker / "bridge-state.json"
    with pytest.raises(HeraldError, match="could not be acquired"):
        write(state_path, "x", DeckState(project_id="p1", etags={}))


def test_write_over_a_corrupt_existing_file_raises_and_leaves_it_untouched(
    tmp_path: Path,
):
    """A corrupt file blocks writes deliberately (clobbering would destroy
    every other slug's entry) -- and the corrupt file must survive intact."""
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text("{not valid json")
    with pytest.raises(HeraldError, match="could not be read"):
        write(state_path, "x", DeckState(project_id="p1", etags={}))
    assert state_path.read_text() == "{not valid json"


def test_read_of_an_explicit_null_entry_raises_herald_error(tmp_path: Path):
    """A hand-edited ``"slug": null`` is a malformed entry, not an absent
    one -- a plain ``.get(slug)`` would silently read it as no-state."""
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text('{"x": null}')
    with pytest.raises(HeraldError, match="not a JSON object"):
        read(state_path, "x")


def test_read_names_the_offending_field(tmp_path: Path):
    """The operator hand-editing this file (the module docstring's headline
    failure mode) needs to know *which* field broke, not just that one
    did."""
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text('{"x": {"project_id": 123, "etags": {}}}')
    with pytest.raises(HeraldError, match="project_id"):
        read(state_path, "x")


def test_read_with_a_plain_file_as_a_parent_path_component_raises_herald_error(
    tmp_path: Path,
):
    """``Path.exists`` returns False whenever the stat fails, so an
    ``exists()`` pre-check would misread this as "no state yet" -- ``open()``
    is the authority, and its ``NotADirectoryError`` must surface
    structurally."""
    blocker = tmp_path / ".herald"
    blocker.write_text("not a directory")
    with pytest.raises(HeraldError, match="could not be read"):
        read(blocker / "bridge-state.json", "x")


def test_read_of_absurdly_nested_json_raises_herald_error(tmp_path: Path):
    """Past the parser's nesting limit ``json.load`` raises
    ``RecursionError`` -- a ``ValueError`` *cousin*, not subclass, that must
    not leak raw. Which HeraldError message surfaces depends on whether this
    interpreter's C-accelerated json parser actually hits the recursion
    limit at this depth (it did not on every CI runner observed, unlike a
    typical local build) -- a clean parse then fails the top-level-dict
    check instead. Both are safe, non-leaking HeraldError outcomes proving
    the same invariant; only a raw RecursionError escaping would be a bug."""
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text("[" * 100_000 + "]" * 100_000)
    with pytest.raises(HeraldError, match="could not be read|does not hold a JSON object"):
        read(state_path, "x")


def test_write_refuses_a_type_lying_deck_state(tmp_path: Path):
    """``json.dump`` would either crash with a raw ``TypeError`` (an
    unserializable etags value) or silently launder an ``int`` key into its
    string -- both refused up front, so ``read`` never has to reject
    Herald's own write as corruption."""
    state_path = tmp_path / "bridge-state.json"
    with pytest.raises(HeraldError, match="etags"):
        write(state_path, "x", DeckState(project_id="p1", etags={"a": 5}))
    with pytest.raises(HeraldError, match="etags"):
        write(state_path, "x", DeckState(project_id="p1", etags={1: "E1"}))
    assert not state_path.exists()


def test_write_refuses_a_non_string_slug(tmp_path: Path):
    """``json.dump(sort_keys=True)`` would launder ``5`` into ``"5"`` in an
    otherwise-empty document, or crash comparing ``int`` to ``str`` beside
    an existing entry -- refused up front instead."""
    state_path = tmp_path / "bridge-state.json"
    with pytest.raises(HeraldError, match="slug must be a string"):
        write(state_path, 5, DeckState(project_id="p1", etags={}))
    assert not state_path.exists()


def test_write_where_state_path_is_a_directory_raises_herald_error(tmp_path: Path):
    """The docstring's ``state_path``-is-a-directory refusal, exercised:
    the load trips first (``open()`` on a directory), and the write-side
    wrap covers a directory racing into place after it identically."""
    state_path = tmp_path / "bridge-state.json"
    state_path.mkdir()
    with pytest.raises(HeraldError, match="could not be read"):
        write(state_path, "x", DeckState(project_id="p1", etags={}))


def test_read_refuses_a_non_string_slug(tmp_path: Path):
    """``write`` refuses a non-string slug structurally; ``read`` must not
    mask the identical caller bug as "no state yet" (JSON keys are strings,
    so ``.get(5)`` could never match -- that is silence, not absence)."""
    state_path = tmp_path / "bridge-state.json"
    with pytest.raises(HeraldError, match="slug must be a string"):
        read(state_path, 5)


def test_read_of_an_entry_with_an_unknown_field_raises_herald_error(tmp_path: Path):
    """A typoed field name in a hand-edit (``"lastpull"``) would otherwise
    be silently ignored -- the intended value lost, the entry still "valid",
    and the stray key dropped wholesale by the next same-slug ``write``."""
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text('{"x": {"project_id": "p1", "etags": {}, "lastpull": "t1"}}')
    with pytest.raises(HeraldError, match="lastpull"):
        read(state_path, "x")


def test_read_of_a_document_with_duplicate_keys_raises_herald_error(tmp_path: Path):
    """``json.load``'s default is silent last-wins on a duplicated key --
    which would discard the earlier of two hand-edited duplicate slug
    blocks on read and erase it permanently on the next ``write``. An
    ambiguous hand-edit must fail structurally like every other one."""
    state_path = tmp_path / "bridge-state.json"
    state_path.write_text('{"x": {"project_id": "OLD", "etags": {}}, "x": {"project_id": "NEW", "etags": {}}}')
    with pytest.raises(HeraldError, match="duplicate"):
        read(state_path, "x")


def test_write_refuses_a_state_that_is_not_a_deck_state(tmp_path: Path):
    """A duck-typed stand-in (right attributes, wrong type) would crash
    ``asdict()`` raw, and a plain dict would crash the attribute access --
    both the same annotation violation the slug check already refuses."""
    state_path = tmp_path / "bridge-state.json"
    with pytest.raises(HeraldError, match="must be a DeckState"):
        write(state_path, "x", {"project_id": "p1", "etags": {}})
    assert not state_path.exists()


def test_two_concurrent_writers_for_different_slugs_both_land(tmp_path: Path, monkeypatch):
    """Story 13.1 regression: two ``write`` calls for different slugs
    racing the same file must both survive -- forced, deterministic
    interleaving (not a timing-dependent sleep race). A monkeypatched delay
    is inserted right after ``_load_document`` reads the (pre-write)
    document, so whichever writer reads first pauses long enough for the
    other writer's own full read-modify-write cycle to run during that
    pause -- unlocked, both readers see a document missing the other's
    slug, and one writer's ``os.replace`` clobbers the other's; locked, a
    second writer cannot even begin its read until the first has released
    the lock (finished its own write), so both survive regardless of the
    pause. Fails against the pre-fix (unlocked) code, passes against the
    fixed code -- confirmed locally by commenting out ``write``'s
    ``locking.locked`` call."""
    state_path = tmp_path / "bridge-state.json"
    original_load_document = state_module._load_document

    def delayed_load_document(path):
        document = original_load_document(path)
        time.sleep(0.2)
        return document

    monkeypatch.setattr(state_module, "_load_document", delayed_load_document)

    barrier = threading.Barrier(2)

    def writer(slug: str, deck_state: DeckState) -> None:
        barrier.wait(timeout=5)
        write(state_path, slug, deck_state)

    state_a = DeckState(project_id="p-a", etags={}, last_pull=None)
    state_b = DeckState(project_id="p-b", etags={}, last_pull=None)
    t1 = threading.Thread(target=writer, args=("a", state_a))
    t2 = threading.Thread(target=writer, args=("b", state_b))
    t1.start()
    t2.start()
    # Bounded joins plus an explicit liveness assertion: without it a genuine
    # deadlock regression fails below with a confusing content mismatch that
    # reads as a lost update rather than a hang, and leaves two abandoned
    # threads still holding the lock for the rest of the session.
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive(), "a writer deadlocked on the lock"

    assert read(state_path, "a") == state_a
    assert read(state_path, "b") == state_b
