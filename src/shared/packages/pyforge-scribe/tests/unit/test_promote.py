"""Unit tests for pyforge.scribe.promote — the promotion boundary (Story 1.3).

Every test uses `tmp_path` for both the fake user-local source directory and
the `.claude/memory/` target — never the real
`~/.claude/projects/<encoded-path>/memory/` tree — matching the I/O &
Edge-Case Matrix in
spec-1-3-promotion-workflow-proposal-then-confirm-team-voice-rewrite.md.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyforge.scribe.promote import (
    apply_promotion,
    classify_and_draft,
    default_user_local_root,
    rewrite_team_voice,
)

_MEMORY_MD_STARTER = """# Team Memory Index

## Feedback

## Project

## Reference
"""


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    return root


@pytest.fixture()
def memory_root(repo_root: Path) -> Path:
    root = repo_root / ".claude" / "memory"
    root.mkdir(parents=True)
    (root / "MEMORY.md").write_text(_MEMORY_MD_STARTER, encoding="utf-8")
    return root


@pytest.fixture()
def source_root(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    return root


def _write(source_root: Path, filename: str, content: str) -> Path:
    path = source_root / filename
    path.write_text(content, encoding="utf-8")
    return path


# --- classification -----------------------------------------------------


def test_classify_team_relevant_flat_frontmatter(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_run_tests_first.md",
        "---\n"
        "name: run-tests-first\n"
        "description: Run the test suite before opening a PR.\n"
        "type: feedback\n"
        "---\n"
        "Always run the full test suite before opening a PR.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert len(proposal.entries) == 1
    entry = proposal.entries[0]
    assert entry.classification == "team-relevant"
    assert entry.capture_type == "feedback"
    assert entry.slug == "run-tests-first"
    assert entry.target_path == memory_root / "feedback" / "run-tests-first.md"
    assert "Always run the full test suite" in entry.rewritten_text
    assert entry.memory_index_line.startswith("- [run-tests-first](feedback/run-tests-first.md)")


def test_classify_team_relevant_nested_metadata_frontmatter(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "project_widget_status.md",
        "---\n"
        "name: widget-status\n"
        "description: Widget project is in progress.\n"
        "metadata:\n"
        "  node_type: memory\n"
        "  type: project\n"
        "  originSessionId: abc-123\n"
        "---\n"
        "Widget project status: in progress, resume at wave B.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert len(proposal.entries) == 1
    entry = proposal.entries[0]
    assert entry.classification == "team-relevant"
    assert entry.capture_type == "project"
    assert entry.slug == "widget-status"


def test_classify_mixed_shapes_in_one_source_dir(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_flat_shape.md",
        "---\nname: a\ndescription: A flat-shape rule.\ntype: feedback\n---\nBody A.\n",
    )
    _write(
        source_root,
        "feedback_nested_shape.md",
        "---\nname: b\ndescription: A nested-shape rule.\nmetadata:\n  type: feedback\n---\nBody B.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert len(proposal.entries) == 2
    classifications = {e.source_path.name: e.classification for e in proposal.entries}
    assert classifications == {
        "feedback_flat_shape.md": "team-relevant",
        "feedback_nested_shape.md": "team-relevant",
    }


def test_classify_already_promoted_flat(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_done.md",
        "---\n"
        "name: done\n"
        "description: Already handled.\n"
        "type: feedback\n"
        "promoted: true\n"
        "---\n"
        "Promoted to .claude/memory/feedback/done.md.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert len(proposal.entries) == 1
    assert proposal.entries[0].classification == "already-promoted"
    assert proposal.promotable == ()


def test_classify_already_promoted_nested_any_indentation(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_done2.md",
        "---\n"
        "name: done2\n"
        "description: Already handled too.\n"
        "metadata:\n"
        "    type: feedback\n"
        "    promoted: true\n"
        "---\n"
        "Promoted to .claude/memory/feedback/done2.md.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert proposal.entries[0].classification == "already-promoted"


def test_classify_personal_description_keyword(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_tone.md",
        "---\n"
        "name: tone\n"
        "description: Keep responses terse and to the point.\n"
        "type: feedback\n"
        "---\n"
        "Personal preference about response length.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert len(proposal.entries) == 1
    entry = proposal.entries[0]
    assert entry.classification == "personal"
    assert "terse" in entry.reason
    assert proposal.promotable == ()


def test_classify_stale_missing_referenced_path(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_stale_path.md",
        "---\n"
        "name: stale-path\n"
        "description: References a module that no longer exists.\n"
        "type: feedback\n"
        "---\n"
        "See `src/pyforge/scribe/nonexistent_module.py` for details.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert len(proposal.entries) == 1
    entry = proposal.entries[0]
    assert entry.classification == "stale"
    assert "src/pyforge/scribe/nonexistent_module.py" in entry.reason


def test_classify_stale_when_referenced_path_exists_is_not_stale(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    (repo_root / "src").mkdir()
    (repo_root / "src" / "real_module.py").write_text("# real\n", encoding="utf-8")
    _write(
        source_root,
        "feedback_real_path.md",
        "---\n"
        "name: real-path\n"
        "description: References a module that exists.\n"
        "type: feedback\n"
        "---\n"
        "See `src/real_module.py` for details.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert proposal.entries[0].classification == "team-relevant"


def test_classify_malformed_frontmatter_missing_closing_delimiter_never_crashes(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_broken.md",
        "---\nname: broken\ndescription: no closing delimiter\ntype: feedback\nBody text.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert len(proposal.entries) == 1
    entry = proposal.entries[0]
    assert entry.classification == "stale"
    assert "malformed" in entry.reason


def test_classify_malformed_frontmatter_missing_type_never_crashes(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_no_type.md",
        "---\nname: no-type\ndescription: has no type field\n---\nBody text.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    assert len(proposal.entries) == 1
    entry = proposal.entries[0]
    assert entry.classification == "stale"
    assert "malformed" in entry.reason


def test_classify_missing_source_dir_raises_value_error_before_any_read(
    memory_root: Path, repo_root: Path, tmp_path: Path
) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="does not exist"):
        classify_and_draft(missing, memory_root, repo_root)


def test_classify_slug_collision_within_one_batch_previews_distinct_slugs(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    """Two different filenames whose Q9 transform derives the *same* base
    slug (`dup-case`) must preview as distinct slugs, in filename-sort
    order, matching what `apply_promotion()` will actually do."""
    _write(
        source_root,
        "feedback_dup-case.md",
        "---\nname: a\ndescription: First entry.\ntype: feedback\n---\nFirst body.\n",
    )
    _write(
        source_root,
        "feedback_dup_case.md",
        "---\nname: b\ndescription: Second entry.\ntype: feedback\n---\nSecond body.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)

    slugs = [e.slug for e in proposal.entries]
    assert slugs == ["dup-case", "dup-case-2"]


# --- team-voice rewrite ---------------------------------------------------


def test_rewrite_strips_i_prefer_framing() -> None:
    result = rewrite_team_voice("I prefer to keep the build script simple.")
    assert "I prefer" not in result
    assert "keep the build script simple" in result


def test_rewrite_strips_i_want_framing() -> None:
    result = rewrite_team_voice("I want new contributors to run tests first.")
    assert "I want" not in result
    assert "new contributors to run tests first" in result


def test_rewrite_drops_user_prefers_framing() -> None:
    result = rewrite_team_voice("The user prefers no upstream commitment yet.")
    assert "user prefers" not in result
    assert "no upstream commitment yet" in result


def test_rewrite_drops_bare_user_prefers_without_the() -> None:
    result = rewrite_team_voice("user prefers a smaller batch size.")
    assert "user prefers" not in result
    assert "a smaller batch size" in result


def test_rewrite_drops_parenthetical_git_short_hash() -> None:
    result = rewrite_team_voice("Confirmed cleanly (commit `31eb4e6bba`) and shipped.")
    assert "31eb4e6bba" not in result
    assert result == "Confirmed cleanly and shipped."


def test_rewrite_preserves_paths_commands_and_labels() -> None:
    text = (
        "**Why:** keeps CI green.\n\n"
        "**How to apply:** run `pixi run -e local-recipes pyforge-scribe-test` "
        "and check `src/pyforge/scribe/capture.py`."
    )
    result = rewrite_team_voice(text)
    assert result == text


def test_rewrite_does_not_touch_unrelated_parenthetical() -> None:
    text = "Use the fast path (see the README) when possible."
    assert rewrite_team_voice(text) == text


# --- apply_promotion ------------------------------------------------------


def test_apply_promotion_writes_via_capture_and_source_is_untouched(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    source_path = _write(
        source_root,
        "feedback_run_tests_first.md",
        "---\n"
        "name: run-tests-first\n"
        "description: I prefer running tests before opening a PR.\n"
        "type: feedback\n"
        "---\n"
        "I prefer that contributors run the full test suite (commit `31eb4e6bba`) "
        "before opening a PR.\n",
    )
    original_source_bytes = source_path.read_bytes()

    proposal = classify_and_draft(source_root, memory_root, repo_root)
    results = apply_promotion(memory_root, proposal)

    assert len(results) == 1
    written_path = results[0].path
    assert written_path == memory_root / "feedback" / "run-tests-first.md"
    content = written_path.read_text(encoding="utf-8")
    assert "I prefer" not in content
    assert "31eb4e6bba" not in content
    assert "run the full test suite" in content

    memory_md = (memory_root / "MEMORY.md").read_text(encoding="utf-8")
    assert memory_md.count(results[0].memory_index_line) == 1

    # Source is byte-for-byte unchanged (Story 1.4 owns the pointer stub).
    assert source_path.read_bytes() == original_source_bytes


def test_apply_promotion_is_a_no_op_when_nothing_is_promotable(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_tone.md",
        "---\nname: tone\ndescription: Keep responses terse.\ntype: feedback\n---\nBody.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)
    results = apply_promotion(memory_root, proposal)

    assert results == []
    assert list((memory_root / "feedback").glob("*.md")) == []


def test_apply_promotion_resolves_in_batch_collision_to_distinct_files(
    source_root: Path, memory_root: Path, repo_root: Path
) -> None:
    _write(
        source_root,
        "feedback_dup-case.md",
        "---\nname: a\ndescription: First entry.\ntype: feedback\n---\nFirst body.\n",
    )
    _write(
        source_root,
        "feedback_dup_case.md",
        "---\nname: b\ndescription: Second entry.\ntype: feedback\n---\nSecond body.\n",
    )

    proposal = classify_and_draft(source_root, memory_root, repo_root)
    results = apply_promotion(memory_root, proposal)

    written = sorted(p.name for p in (memory_root / "feedback").glob("*.md"))
    assert written == ["dup-case-2.md", "dup-case.md"]
    assert [r.path.name for r in results] == ["dup-case.md", "dup-case-2.md"]


# --- default_user_local_root ----------------------------------------------


def test_default_user_local_root_encodes_non_alnum_chars(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    project_dir = tmp_path / "work" / ".bmad-loop" / "my-repo"
    project_dir.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.chdir(project_dir)

    result = default_user_local_root()

    expected_encoded = re.sub(r"[^A-Za-z0-9]", "-", str(Path.cwd()))
    assert result == fake_home / ".claude" / "projects" / expected_encoded / "memory"
    # The '/' immediately before the dotted ".bmad-loop" segment doubles up
    # with the '.' itself -- both become '-', landing as "--bmad-loop-".
    assert "--bmad-loop-" in expected_encoded
