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
from pyforge.herald.registry import (
    DESIGN_SYSTEM_PROJECT_NAMES,
    DesignProject,
    append_push_ledger_row,
    read,
    read_exclusions,
    read_potx_template,
    register,
    register_potx_template,
)

_HEADING = "## Design project (the bridge's far end)"
_POTX_HEADING = "## PowerPoint template (the .potx path)"
_EXCLUDED_HEADING = "## Excluded projects (never twinned)"


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
    readme_path.write_text("## Design project (the bridge's far end)\nnot the canonical shape\nhttps://example.com/p\n")

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

    assert read(readme_path) == DesignProject(project_name="N", project_id="i", file_url="https://example.com/p")


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
def test_register_refuses_an_empty_multiline_or_non_string_field(tmp_path: Path, project_name, project_id, file_url):
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
def test_register_refuses_fields_embedding_the_template_delimiters(tmp_path: Path, project_name, project_id):
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


def test_register_wraps_a_failed_replace_and_leaks_no_temp_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A filesystem refusal mid-write surfaces as ``HeraldError``, leaves
    the original README byte-identical, and unlinks the temp file.

    Patches `os.replace` where it actually runs now (Story 14.2, CAP-2:
    `register` delegates to `pyforge.core.atomic_write_text`, which owns the
    `os.replace` call -- `registry.py` itself no longer imports `os` at
    all)."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    def _refuse(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("pyforge.core.atomic_write.os.replace", _refuse)
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

    with pytest.raises(HeraldError, match=r"found 3 \(blank lines inside the section count"):
        read(readme_path)


# --- Story 23.3: § *PowerPoint template* (the .potx path) -------------------


def test_read_potx_template_of_a_readme_with_no_section_returns_none(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\nNothing about a .potx template here.\n")

    assert read_potx_template(readme_path) is None


def test_read_potx_template_of_a_missing_file_returns_none(tmp_path: Path):
    readme_path = tmp_path / "does-not-exist" / "README.md"

    assert read_potx_template(readme_path) is None


def test_register_potx_template_into_a_readme_with_no_section_appends_it(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\nSome existing content.\n")

    register_potx_template(readme_path, "presentations/pyforge-demo/project/deck.potx")

    assert readme_path.read_text() == (
        "# My Deck\n\nSome existing content.\n\n"
        "## PowerPoint template (the .potx path)\n"
        "presentations/pyforge-demo/project/deck.potx\n"
    )


def test_read_after_register_potx_template_round_trips(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    register_potx_template(readme_path, "presentations/pyforge-demo/project/deck.potx")

    assert read_potx_template(readme_path) == "presentations/pyforge-demo/project/deck.potx"


def test_register_potx_template_updates_in_place_without_duplicating_the_heading(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    register_potx_template(readme_path, "presentations/pyforge-demo/project/a.potx")
    register_potx_template(readme_path, "presentations/pyforge-demo/project/b.potx")

    text = readme_path.read_text()
    assert text.count(_POTX_HEADING) == 1
    assert read_potx_template(readme_path) == "presentations/pyforge-demo/project/b.potx"


def test_register_potx_template_replaces_span_up_to_the_next_heading_leaving_it_intact(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "# My Deck\n\n"
        "## PowerPoint template (the .potx path)\n"
        "presentations/pyforge-demo/project/old.potx\n\n"
        "## Quick start\n"
        "Some instructions.\n"
    )

    register_potx_template(readme_path, "presentations/pyforge-demo/project/new.potx")

    text = readme_path.read_text()
    assert text.count(_POTX_HEADING) == 1
    assert text == (
        "# My Deck\n\n"
        "## PowerPoint template (the .potx path)\n"
        "presentations/pyforge-demo/project/new.potx\n\n"
        "## Quick start\n"
        "Some instructions.\n"
    )


def test_potx_template_section_coexists_with_the_design_project_section(
    tmp_path: Path,
):
    """The two sections are separate and additive -- registering one never
    disturbs the other, in either order."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    register(readme_path, "PyForge Demo deck", "proj-1", "https://example.com/p")
    register_potx_template(readme_path, "presentations/pyforge-demo/project/deck.potx")

    assert read(readme_path) == DesignProject(
        project_name="PyForge Demo deck",
        project_id="proj-1",
        file_url="https://example.com/p",
    )
    assert read_potx_template(readme_path) == "presentations/pyforge-demo/project/deck.potx"


def test_register_potx_template_against_a_missing_file_raises_herald_error(
    tmp_path: Path,
):
    readme_path = tmp_path / "does-not-exist" / "README.md"

    with pytest.raises(HeraldError, match=str(readme_path)):
        register_potx_template(readme_path, "presentations/pyforge-demo/deck.potx")
    assert not readme_path.exists()


@pytest.mark.parametrize(
    "template_path",
    ["", "multi\nline", 123],
)
def test_register_potx_template_refuses_an_empty_multiline_or_non_string_path(tmp_path: Path, template_path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    with pytest.raises(HeraldError, match="non-empty, single-line"):
        register_potx_template(readme_path, template_path)
    assert read_potx_template(readme_path) is None


def test_register_potx_template_refuses_a_path_starting_with_a_hash(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    with pytest.raises(HeraldError, match="must not start with '#'"):
        register_potx_template(readme_path, "#fragment-only")
    assert readme_path.read_text() == "# My Deck\n"


@pytest.mark.parametrize(
    "template_path",
    ["/etc/passwd", "../../escape.potx", "presentations/pyforge-demo/../../escape.potx"],
)
def test_register_potx_template_refuses_an_absolute_or_dot_dot_path(tmp_path: Path, template_path):
    """``deck_pipeline.py``'s ``PptxTemplateExporter.export`` does
    ``repo_root / template_rel`` -- for an absolute ``template_rel`` that
    pathlib ``/`` silently discards ``repo_root`` entirely, resolving
    outside the repo. A ``..`` segment has the same effect via traversal."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    with pytest.raises(HeraldError, match="repo-root-relative"):
        register_potx_template(readme_path, template_path)
    assert read_potx_template(readme_path) is None


@pytest.mark.parametrize(
    "template_path",
    ["/etc/passwd", "../../escape.potx", "presentations/pyforge-demo/../../escape.potx"],
)
def test_read_potx_template_refuses_an_absolute_or_dot_dot_path(tmp_path: Path, template_path):
    """``register_potx_template`` guards this at write time, but the
    section can also be hand-edited directly (Story 23.3's own Auto Run
    Result: it has no production caller today) -- bypassing that guard
    entirely. ``read_potx_template`` must re-apply it, since
    ``deck_pipeline.py``'s ``PptxTemplateExporter.export`` joins whatever
    it returns straight onto ``repo_root`` unguarded."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text(f"# My Deck\n\n## PowerPoint template (the .potx path)\n{template_path}\n")

    with pytest.raises(HeraldError, match="repo-root-relative"):
        read_potx_template(readme_path)


def test_read_potx_template_of_a_section_with_two_body_lines_raises_herald_error(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "## PowerPoint template (the .potx path)\npresentations/pyforge-demo/deck.potx\none line too many\n"
    )

    with pytest.raises(HeraldError, match="expected exactly one body line"):
        read_potx_template(readme_path)


def test_read_potx_template_of_a_heading_with_no_body_raises_herald_error(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\n## PowerPoint template (the .potx path)\n")

    with pytest.raises(HeraldError, match="expected exactly one body line, found 0"):
        read_potx_template(readme_path)


def test_both_potx_functions_wrap_a_binary_corrupt_readme_as_herald_error(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_bytes(b"\x80\x81 not utf-8")

    with pytest.raises(HeraldError, match="could not be read from"):
        read_potx_template(readme_path)
    with pytest.raises(HeraldError, match="could not be registered"):
        register_potx_template(readme_path, "presentations/pyforge-demo/deck.potx")


def test_register_potx_template_collapses_multiple_trailing_blank_lines_before_appending(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\n\n\n")

    register_potx_template(readme_path, "presentations/pyforge-demo/deck.potx")

    assert readme_path.read_text() == (
        "# My Deck\n\n## PowerPoint template (the .potx path)\npresentations/pyforge-demo/deck.potx\n"
    )


def test_read_potx_template_tolerates_trailing_blank_lines_at_end_of_file(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("## PowerPoint template (the .potx path)\npresentations/pyforge-demo/deck.potx\n\n\n")

    assert read_potx_template(readme_path) == "presentations/pyforge-demo/deck.potx"


def test_register_potx_template_wraps_a_failed_replace_and_leaks_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    def _refuse(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("pyforge.core.atomic_write.os.replace", _refuse)
    with pytest.raises(HeraldError, match="disk full"):
        register_potx_template(readme_path, "presentations/pyforge-demo/deck.potx")

    assert readme_path.read_text() == "# My Deck\n"
    assert list(tmp_path.iterdir()) == [readme_path]


# --- Story 23.4: § *Ledger* push-and-prove rows ------------------------------

_LEDGER_HEADING_16 = "## Ledger — 2026-09-16 push-and-prove (spec-design-sync-loop CAP-6)"
_LEDGER_HEADING_17 = "## Ledger — 2026-09-17 push-and-prove (spec-design-sync-loop CAP-6)"


def test_append_push_ledger_row_into_a_readme_with_no_section_appends_it(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\nSome existing content.\n")

    append_push_ledger_row(readme_path, date="2026-09-16", rows=[("a.pptx", 1234)])

    assert readme_path.read_text() == (
        "# My Deck\n\nSome existing content.\n\n"
        f"{_LEDGER_HEADING_16}\n\n"
        "| Artifact | Bytes | Read-back |\n"
        "|---|---|---|\n"
        "| a.pptx | 1,234 | identical ✓ |\n"
    )


def test_append_push_ledger_row_with_multiple_rows_in_one_call(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    append_push_ledger_row(
        readme_path,
        date="2026-09-16",
        rows=[("a.html", 100), ("b.pptx", 200), ("c.pptx", 300)],
    )

    assert readme_path.read_text() == (
        "# My Deck\n\n"
        f"{_LEDGER_HEADING_16}\n\n"
        "| Artifact | Bytes | Read-back |\n"
        "|---|---|---|\n"
        "| a.html | 100 | identical ✓ |\n"
        "| b.pptx | 200 | identical ✓ |\n"
        "| c.pptx | 300 | identical ✓ |\n"
    )


def test_append_push_ledger_row_adds_to_todays_existing_section_without_duplicating_the_heading(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    append_push_ledger_row(readme_path, date="2026-09-16", rows=[("a.pptx", 100)])
    append_push_ledger_row(readme_path, date="2026-09-16", rows=[("b.pptx", 200)])

    text = readme_path.read_text()
    assert text.count(_LEDGER_HEADING_16) == 1
    assert text == (
        "# My Deck\n\n"
        f"{_LEDGER_HEADING_16}\n\n"
        "| Artifact | Bytes | Read-back |\n"
        "|---|---|---|\n"
        "| a.pptx | 100 | identical ✓ |\n"
        "| b.pptx | 200 | identical ✓ |\n"
    )


def test_append_push_ledger_row_on_a_later_date_appends_a_new_section(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    append_push_ledger_row(readme_path, date="2026-09-16", rows=[("a.pptx", 100)])
    append_push_ledger_row(readme_path, date="2026-09-17", rows=[("c.pptx", 300)])

    text = readme_path.read_text()
    assert text.count(_LEDGER_HEADING_16) == 1
    assert text.count(_LEDGER_HEADING_17) == 1
    assert text == (
        "# My Deck\n\n"
        f"{_LEDGER_HEADING_16}\n\n"
        "| Artifact | Bytes | Read-back |\n"
        "|---|---|---|\n"
        "| a.pptx | 100 | identical ✓ |\n\n"
        f"{_LEDGER_HEADING_17}\n\n"
        "| Artifact | Bytes | Read-back |\n"
        "|---|---|---|\n"
        "| c.pptx | 300 | identical ✓ |\n"
    )


def test_append_push_ledger_row_to_todays_section_preserves_content_that_follows_it(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "# My Deck\n\n"
        f"{_LEDGER_HEADING_16}\n\n"
        "| Artifact | Bytes | Read-back |\n"
        "|---|---|---|\n"
        "| a.pptx | 100 | identical ✓ |\n\n"
        "## Other Section\n"
        "Some text.\n"
    )

    append_push_ledger_row(readme_path, date="2026-09-16", rows=[("b.pptx", 200)])

    assert readme_path.read_text() == (
        "# My Deck\n\n"
        f"{_LEDGER_HEADING_16}\n\n"
        "| Artifact | Bytes | Read-back |\n"
        "|---|---|---|\n"
        "| a.pptx | 100 | identical ✓ |\n"
        "| b.pptx | 200 | identical ✓ |\n\n"
        "## Other Section\n"
        "Some text.\n"
    )


def test_append_push_ledger_row_against_a_missing_file_raises_herald_error(
    tmp_path: Path,
):
    readme_path = tmp_path / "does-not-exist" / "README.md"

    with pytest.raises(HeraldError, match=str(readme_path)):
        append_push_ledger_row(readme_path, date="2026-09-16", rows=[("a.pptx", 1)])


def test_append_push_ledger_row_refuses_empty_rows(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    with pytest.raises(HeraldError, match="no rows given"):
        append_push_ledger_row(readme_path, date="2026-09-16", rows=[])

    assert readme_path.read_text() == "# My Deck\n"


def test_append_push_ledger_row_wraps_an_unreadable_file(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.mkdir()  # a directory, not a file -- OSError on read

    with pytest.raises(HeraldError, match=str(readme_path)):
        append_push_ledger_row(readme_path, date="2026-09-16", rows=[("a.pptx", 1)])


def test_append_push_ledger_row_collapses_multiple_trailing_blank_lines_before_appending(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n\n\n\n")

    append_push_ledger_row(readme_path, date="2026-09-16", rows=[("a.pptx", 100)])

    assert readme_path.read_text() == (
        "# My Deck\n\n"
        f"{_LEDGER_HEADING_16}\n\n"
        "| Artifact | Bytes | Read-back |\n"
        "|---|---|---|\n"
        "| a.pptx | 100 | identical ✓ |\n"
    )


def test_append_push_ledger_row_wraps_a_failed_replace_and_leaks_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# My Deck\n")

    def _refuse(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("pyforge.core.atomic_write.os.replace", _refuse)
    with pytest.raises(HeraldError, match="disk full"):
        append_push_ledger_row(readme_path, date="2026-09-16", rows=[("a.pptx", 1)])

    assert readme_path.read_text() == "# My Deck\n"
    assert list(tmp_path.iterdir()) == [readme_path]


# --- Story 23.1: read_exclusions / DESIGN_SYSTEM_PROJECT_NAMES (CAP-1) ------


def test_design_system_project_names_names_the_three_known_libraries():
    assert DESIGN_SYSTEM_PROJECT_NAMES == {"Modernist", "Broadsheet", "Nocturne"}


def test_read_exclusions_against_a_missing_file_returns_empty(tmp_path: Path):
    assert read_exclusions(tmp_path / "does-not-exist.md") == {}


def test_read_exclusions_against_a_readme_with_no_section_returns_empty(
    tmp_path: Path,
):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# presentations/\n\nSome prose.\n")
    assert read_exclusions(readme_path) == {}


def test_read_exclusions_parses_the_two_retired_projects(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "# presentations/\n\n"
        f"{_EXCLUDED_HEADING}\n\n"
        "| Project | Reason |\n"
        "|---|---|\n"
        "| REMOVED-PyForge Unifying Strategy | ad-hoc duplicate, retired |\n"
        "| Local recipes repository connection | stale hand-mirrored repo copy |\n"
    )

    assert read_exclusions(readme_path) == {
        "REMOVED-PyForge Unifying Strategy": "ad-hoc duplicate, retired",
        "Local recipes repository connection": "stale hand-mirrored repo copy",
    }


def test_read_exclusions_stops_at_the_next_heading(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        f"{_EXCLUDED_HEADING}\n\n"
        "| Project | Reason |\n"
        "|---|---|\n"
        "| Retired Project | some reason |\n\n"
        "## Something else\n"
        "| Not-excluded | ignored |\n"
    )

    assert read_exclusions(readme_path) == {"Retired Project": "some reason"}


def test_read_exclusions_raises_on_a_malformed_row(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(f"{_EXCLUDED_HEADING}\n\n| Project | Reason |\n|---|---|\n| Missing the reason cell |\n")

    with pytest.raises(HeraldError, match="not a two-cell"):
        read_exclusions(readme_path)


def test_read_exclusions_wraps_an_unreadable_file(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.mkdir()  # a directory, not a file -- OSError on read

    with pytest.raises(HeraldError, match=str(readme_path)):
        read_exclusions(readme_path)


def test_read_exclusions_raises_on_a_duplicate_project_row(tmp_path: Path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        f"{_EXCLUDED_HEADING}\n\n"
        "| Project | Reason |\n"
        "|---|---|\n"
        "| Retired Project | first reason |\n"
        "| Retired Project | second reason |\n"
    )

    with pytest.raises(HeraldError, match="Retired Project.*more than once"):
        read_exclusions(readme_path)
