"""``registry.py``'s register/read round-trip over a deck README's
§ *Design project* section (Story 1.5, AD-8).

Every case writes a real file via ``tmp_path`` / ``Path.write_text`` --
``registry.py`` never assumes a cwd, so no test here may either.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from pyforge.herald.errors import HeraldError
from pyforge.herald.registry import DesignProject, read, register

_HEADING = "## Design project (the bridge's far end)"


def test_register_into_a_readme_with_no_section_appends_it(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\nSome existing content.\n")

    register(readme_path, "PyForge Herald deck", "proj-1", "https://example.com/p")

    text = readme_path.read_text()
    assert text == (
        "# My Deck\n\nSome existing content.\n\n"
        "## Design project (the bridge's far end)\n"
        'Prototype lives in Claude Design project **"PyForge Herald deck"** '
        "(`proj-1`):\n"
        "https://example.com/p\n"
    )


def test_register_appends_with_no_leading_blank_line_against_an_empty_readme(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("")

    register(readme_path, "Name", "id-1", "https://example.com/p")

    assert readme_path.read_text() == (
        "## Design project (the bridge's far end)\n"
        'Prototype lives in Claude Design project **"Name"** (`id-1`):\n'
        "https://example.com/p\n"
    )


def test_read_after_register_round_trips_the_same_fields(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    register(readme_path, "PyForge Herald deck", "proj-1", "https://example.com/p")

    assert read(readme_path) == DesignProject(
        project_name="PyForge Herald deck",
        project_id="proj-1",
        file_url="https://example.com/p",
    )


def test_register_updates_in_place_without_duplicating_the_heading(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    register(readme_path, "Name A", "id-a", "https://example.com/a")
    register(readme_path, "Name B", "id-b", "https://example.com/b")

    text = readme_path.read_text()
    assert text.count(_HEADING) == 1
    assert read(readme_path) == DesignProject(
        project_name="Name B", project_id="id-b", file_url="https://example.com/b"
    )


def test_register_replaces_span_up_to_the_next_heading_leaving_it_intact(
    tmp_path: Path,
):
    """Pins the exact replacement text, not just substring presence -- a
    weaker version of this assertion previously let a real bug through: the
    blank line separating the section from the following heading was
    silently swallowed on replace."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "# My Deck\n\n"
        "## Design project (the bridge's far end)\n"
        'Prototype lives in Claude Design project **"Old"** (`old-id`):\n'
        "https://example.com/old\n\n"
        "## Quick start\n"
        "Some instructions.\n"
    )

    register(readme_path, "New", "new-id", "https://example.com/new")

    text = readme_path.read_text()
    assert text.count(_HEADING) == 1
    assert text == (
        "# My Deck\n\n"
        "## Design project (the bridge's far end)\n"
        'Prototype lives in Claude Design project **"New"** (`new-id`):\n'
        "https://example.com/new\n\n"
        "## Quick start\n"
        "Some instructions.\n"
    )
    assert read(readme_path) == DesignProject(
        project_name="New", project_id="new-id", file_url="https://example.com/new"
    )


def test_read_of_a_readme_with_no_section_returns_none(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\nNothing about design projects here.\n")

    assert read(readme_path) is None


def test_read_of_a_missing_file_returns_none(tmp_path: Path):
    readme_path = tmp_path / "does-not-exist" / "README.md"

    assert read(readme_path) is None


def test_register_against_a_missing_file_raises_herald_error(tmp_path: Path):
    readme_path = tmp_path / "does-not-exist" / "README.md"

    with pytest.raises(HeraldError, match=str(readme_path)):
        register(readme_path, "Name", "id-1", "https://example.com/p")
    assert not readme_path.exists()


def test_read_of_a_two_line_body_not_matching_the_canonical_first_line_raises(
    tmp_path: Path,
):
    """Exactly two body lines (so the line-count check does not fire first),
    with the first failing ``_BODY_LINE1_RE`` -- the one failure branch the
    original version of this test did not actually exercise (it wrote only
    one body line, which tripped the line-count check instead)."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "## Design project (the bridge's far end)\n"
        "not the canonical shape\n"
        "https://example.com/p\n"
    )

    with pytest.raises(HeraldError, match="does not match the canonical"):
        read(readme_path)


def test_read_of_a_section_with_only_one_body_line_raises_herald_error(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("## Design project (the bridge's far end)\nonly one line\n")

    with pytest.raises(HeraldError, match="expected exactly two body lines"):
        read(readme_path)


def test_read_of_a_section_with_three_body_lines_raises_herald_error(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "## Design project (the bridge's far end)\n"
        'Prototype lives in Claude Design project **"N"** (`i`):\n'
        "https://example.com/p\n"
        "one line too many\n"
    )

    with pytest.raises(HeraldError, match="expected exactly two body lines"):
        read(readme_path)


def test_read_tolerates_trailing_blank_lines_at_end_of_file(tmp_path: Path):
    """A section with no following heading pulls every trailing blank line
    at EOF into its span -- those must not count as extra body lines and
    falsely trip the two-line check."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "## Design project (the bridge's far end)\n"
        'Prototype lives in Claude Design project **"N"** (`i`):\n'
        "https://example.com/p\n\n\n"
    )

    assert read(readme_path) == DesignProject(
        project_name="N", project_id="i", file_url="https://example.com/p"
    )


@pytest.mark.parametrize(
    ("project_name", "project_id", "file_url"),
    [
        ("", "id-1", "https://example.com/p"),
        ("Name", "", "https://example.com/p"),
        ("Name", "id-1", ""),
        ("Multi\nLine", "id-1", "https://example.com/p"),
        ("Name", "id\r-1", "https://example.com/p"),
        ("Uni\u2028code", "id-1", "https://example.com/p"),
        ("Name", "id-1", "https://example.com/p\x0b"),
        ("Name\n", "id-1", "https://example.com/p"),
        (123, "id-1", "https://example.com/p"),
    ],
)
def test_register_refuses_an_empty_multiline_or_non_string_field(
    tmp_path: Path, project_name, project_id, file_url
):
    """An empty, newline-carrying, or non-string field would write a body
    ``read`` could not parse back -- refused up front instead, so
    ``register`` can never unilaterally break its own round-trip guarantee.
    "Multiline" means every boundary ``str.splitlines`` recognizes
    (``\\u2028``, ``\\x0b``, a trailing ``\\n``), not just the literal
    ``\\n``/``\\r`` -- both functions parse with ``splitlines``, so those
    are the boundaries that matter. The non-string case mirrors
    ``state.py``'s refusal of annotation-violating inputs as
    ``HeraldError``, never a raw ``TypeError``."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    with pytest.raises(HeraldError, match="non-empty, single-line"):
        register(readme_path, project_name, project_id, file_url)
    assert read(readme_path) is None


@pytest.mark.parametrize(
    ("project_name", "project_id"),
    [
        ('A"** (`B`):', "C"),
        ('A"** (`B', "C"),
    ],
)
def test_register_refuses_fields_embedding_the_template_delimiters(
    tmp_path: Path, project_name, project_id
):
    """A ``project_name`` embedding the template's closing envelope
    (``"** (`` + backtick) shifts the non-greedy parse: register would
    succeed and read would return *silently wrong* fields -- worse than any
    raise. register re-parses the line it is about to write and refuses
    fields that do not read back as themselves. (An id embedding the same
    delimiters mid-string round-trips exactly -- the id group is anchored
    between the first backtick and the line-final `` `): `` -- so only
    genuinely diverging inputs are refused.)"""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    with pytest.raises(HeraldError, match="would not read back as themselves"):
        register(readme_path, project_name, project_id, "https://example.com/p")
    assert readme_path.read_text() == "# My Deck\n"


def test_register_refuses_a_file_url_starting_with_a_hash(tmp_path: Path):
    """The URL sits on a line of its own, so a '#'-leading value would read
    back as the heading that ends the section -- read would then find one
    body line, and a re-register would strand the old URL line below the
    replaced span."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    with pytest.raises(HeraldError, match="must not start with '#'"):
        register(readme_path, "Name", "id-1", "#fragment-only")
    assert readme_path.read_text() == "# My Deck\n"


def test_register_refuses_a_field_with_a_lone_surrogate(tmp_path: Path):
    """A lone surrogate (``json.loads('\"\\\\ud800\"')`` can produce one)
    passes the single-line checks but cannot be UTF-8-encoded -- refused
    before the filesystem is touched, never leaked as a raw
    ``UnicodeEncodeError`` mid-write."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    with pytest.raises(HeraldError, match="not encodable as UTF-8"):
        register(readme_path, "Name\ud800", "id-1", "https://example.com/p")
    assert readme_path.read_text() == "# My Deck\n"


def test_register_preserves_the_readme_file_permissions(tmp_path: Path):
    """mkstemp creates the temp file private (0600); os.replace would carry
    that onto the README, silently stripping group/other read from a
    pre-existing tracked file this module did not create."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")
    os.chmod(readme_path, 0o644)

    register(readme_path, "Name", "id-1", "https://example.com/p")

    assert stat.S_IMODE(readme_path.stat().st_mode) == 0o644


def test_register_collapses_multiple_trailing_blank_lines_before_appending(
    tmp_path: Path,
):
    """The append path's docstring promises trimming of *any* pre-existing
    trailing blank lines, not just none -- pinned here with more than one."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\n\n\n")

    register(readme_path, "Name", "id-1", "https://example.com/p")

    assert readme_path.read_text() == (
        "# My Deck\n\n"
        "## Design project (the bridge's far end)\n"
        'Prototype lives in Claude Design project **"Name"** (`id-1`):\n'
        "https://example.com/p\n"
    )


def test_both_functions_wrap_a_binary_corrupt_readme_as_herald_error(
    tmp_path: Path,
):
    """A non-UTF-8 README must fail structurally (AD-6), never leak a raw
    ``UnicodeDecodeError`` -- from either side of the round trip."""
    readme_path = tmp_path / "README.md"
    readme_path.write_bytes(b"\x80\x81 not utf-8")

    with pytest.raises(HeraldError, match="could not be read from"):
        read(readme_path)
    with pytest.raises(HeraldError, match="could not be registered"):
        register(readme_path, "Name", "id-1", "https://example.com/p")


def test_register_wraps_a_failed_replace_and_leaks_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A filesystem refusal mid-write surfaces as ``HeraldError``, leaves
    the original README byte-identical, and unlinks the temp file."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    def _refuse(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("pyforge.herald.registry.os.replace", _refuse)
    with pytest.raises(HeraldError, match="disk full"):
        register(readme_path, "Name", "id-1", "https://example.com/p")

    assert readme_path.read_text() == "# My Deck\n"
    assert list(tmp_path.iterdir()) == [readme_path]


def test_read_of_a_heading_with_no_body_at_end_of_file_raises(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\n## Design project (the bridge's far end)\n")

    with pytest.raises(HeraldError, match="expected exactly two body lines, found 0"):
        read(readme_path)


def test_read_counts_a_blank_line_under_the_heading_as_a_body_line(
    tmp_path: Path,
):
    """The standard-markdown hand-edit (a blank line after the heading) is
    outside the canonical shape and raises -- pinned as intended behavior,
    with the message naming the invisible reason for the surprising count."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "## Design project (the bridge's far end)\n"
        "\n"
        'Prototype lives in Claude Design project **"N"** (`i`):\n'
        "https://example.com/p\n"
    )

    with pytest.raises(
        HeraldError, match=r"found 3 \(blank lines inside the section count"
    ):
        read(readme_path)
