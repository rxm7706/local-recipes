"""Unit tests for pyforge.scribe.capture — the direct-capture write path.

Every test uses `tmp_path` as the injected memory root (never the real repo
`.claude/memory/` tree) — matching the I/O & Edge-Case Matrix in
spec-1-1-package-scaffold-direct-capture-into-team-memory.md.
"""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

import pytest

from pyforge.scribe.capture import capture
from pyforge.scribe.models import CaptureRecord, parse_capture_file

_MEMORY_MD_STARTER = """# Team Memory Index

## Feedback

## Project

## Reference
"""


@pytest.fixture()
def memory_root(tmp_path: Path) -> Path:
    root = tmp_path / ".claude" / "memory"
    root.mkdir(parents=True)
    (root / "MEMORY.md").write_text(_MEMORY_MD_STARTER, encoding="utf-8")
    return root


def _other_files(root: Path, exclude: Path) -> list[Path]:
    """Every file under tmp_path's parent that is NOT under `root` or `exclude`."""
    tmp_root = root.parent.parent  # tmp_path
    return [
        p
        for p in tmp_root.rglob("*")
        if p.is_file() and root not in p.parents and p != exclude
    ]


def test_happy_path_writes_file_and_one_index_line(memory_root: Path) -> None:
    result = capture(memory_root, "project", "ADR-005b: in-house gateway replaces LiteLLM")

    assert result.path.exists()
    assert result.path.parent == memory_root / "project"

    content = result.path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "name: " in content
    assert "metadata:\n  type: project\n" in content
    assert "ADR-005b: in-house gateway replaces LiteLLM" in content

    memory_md = (memory_root / "MEMORY.md").read_text(encoding="utf-8")
    assert memory_md.count(result.memory_index_line) == 1
    # Exactly one new line landed under "## Project" and no other section grew.
    project_section = memory_md.split("## Project", 1)[1].split("## Reference", 1)[0]
    assert project_section.count("- [") == 1


def test_frontmatter_round_trips_through_from_frontmatter(memory_root: Path) -> None:
    result = capture(memory_root, "reference", "some reference note")
    content = result.path.read_text(encoding="utf-8")
    frontmatter, _, body = content.partition("---\n")[2].partition("---\n")
    parsed = CaptureRecord.from_frontmatter("---\n" + frontmatter + "---\n", text=body.strip())

    assert parsed.type == "reference"
    assert parsed.name == result.record.name
    assert parsed.description == result.record.description


def test_slug_collision_appends_numeric_suffix_without_clobbering(memory_root: Path) -> None:
    first = capture(memory_root, "feedback", "same text every time")
    second = capture(memory_root, "feedback", "same text every time")

    assert first.path != second.path
    assert second.path.name.endswith("-2.md")
    assert first.path.exists()
    assert second.path.exists()

    # Original untouched.
    original_content = first.path.read_text(encoding="utf-8")
    assert "same text every time" in original_content

    memory_md = (memory_root / "MEMORY.md").read_text(encoding="utf-8")
    assert memory_md.count(first.record.name) >= 1
    assert memory_md.count(second.record.name) >= 1
    feedback_section = memory_md.split("## Feedback", 1)[1].split("## Project", 1)[0]
    assert feedback_section.count("- [") == 2


def test_write_boundary_touches_only_memory_root(memory_root: Path) -> None:
    memory_md_path = memory_root / "MEMORY.md"
    capture(memory_root, "project", "write-boundary check")

    # Nothing outside memory_root itself was created (the only writes are the
    # new capture file and MEMORY.md, both inside memory_root).
    assert _other_files(memory_root, memory_md_path) == []


def test_concurrent_captures_lose_no_entries(memory_root: Path) -> None:
    """Regression: 20 threads racing capture() must produce 20 files AND
    20 surviving index lines, with no exception -- the unlocked
    read-modify-write of MEMORY.md previously dropped entries and could
    corrupt the section heading under this exact load."""

    def _do(i: int) -> None:
        capture(memory_root, "project", f"entry number {i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_do, range(20)))

    written = list((memory_root / "project").glob("*.md"))
    assert len(written) == 20

    memory_md = (memory_root / "MEMORY.md").read_text(encoding="utf-8")
    project_section = memory_md.split("## Project", 1)[1].split("## Reference", 1)[0]
    assert project_section.count("- [") == 20


def test_frontmatter_name_is_quoted_and_survives_type_coercing_content(memory_root: Path) -> None:
    """Regression: text that slugifies to a bare '404'/'2026-07-25'/etc.
    must not parse back as a YAML int/date -- name must always be str.

    No PyYAML dependency is available in this lean env by design (see
    models.py's docstring), so this asserts the on-disk shape directly
    (quoted) rather than round-tripping through a YAML parser.
    """
    result = capture(memory_root, "project", "404")
    content = result.path.read_text(encoding="utf-8")
    assert 'name: "404"' in content
    assert "name: 404\n" not in content  # the unquoted, type-coercing form

    parsed = parse_capture_file(result.path)
    assert parsed.name == "404"


def test_embedded_horizontal_rule_round_trips_via_parse_capture_file(memory_root: Path) -> None:
    """Regression: a bare '---' line inside the captured body must not be
    mistaken for the frontmatter's closing delimiter."""
    text = "Decision.\n\n---\n\nRationale follows the divider above."
    result = capture(memory_root, "project", text)

    parsed = parse_capture_file(result.path)
    assert parsed.type == "project"
    assert parsed.text.strip() == text.strip()


def test_blank_text_is_rejected(memory_root: Path) -> None:
    with pytest.raises(ValueError, match="blank"):
        capture(memory_root, "feedback", "   ")
    assert list((memory_root / "feedback").glob("*.md")) == []


def test_invalid_capture_type_is_rejected_before_any_write(memory_root: Path) -> None:
    with pytest.raises(ValueError, match="invalid capture type"):
        capture(memory_root, "decision", "some text")  # type: ignore[arg-type]
    # No stray directory materialized for the bogus type.
    assert not (memory_root / "decision").exists()


def test_missing_memory_root_fails_loudly_instead_of_auto_creating(tmp_path: Path) -> None:
    missing_root = tmp_path / "nope" / ".claude" / "memory"
    with pytest.raises(ValueError, match="does not exist"):
        capture(missing_root, "project", "some text")
    assert not missing_root.exists()


def test_different_types_land_in_matching_subdirectory_and_section(memory_root: Path) -> None:
    feedback_result = capture(memory_root, "feedback", "a feedback entry")
    project_result = capture(memory_root, "project", "a project entry")
    reference_result = capture(memory_root, "reference", "a reference entry")

    assert feedback_result.path.parent.name == "feedback"
    assert project_result.path.parent.name == "project"
    assert reference_result.path.parent.name == "reference"

    memory_md = (memory_root / "MEMORY.md").read_text(encoding="utf-8")
    assert feedback_result.memory_index_line in memory_md
    assert project_result.memory_index_line in memory_md
    assert reference_result.memory_index_line in memory_md
