"""`scripts/commit_msg_hook.py` -- the Co-Authored-By/AI-attribution refusal
(steward Story 66.2, `spec-pyforge-steward` CAP-154) plus the Story 59.6 /
CAP-137 commit-subject shape WARNING (Ruling 17, never a refusal -- see the
module docstring for why it stays advisory).

Runs under `pixi run -e pyforge-ci pyforge-doctor-scripts-test` (`pytest
tests/scripts -q`) -- the hook is stdlib-only by design (``subprocess`` is
stdlib), matching every other `tests/scripts/` fixture's dependency-free env.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "commit_msg_hook.py"


@pytest.fixture(scope="module")
def hook():
    spec = importlib.util.spec_from_file_location("commit_msg_hook_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --- offending_lines (pre-existing Co-Authored-By/AI-attribution rule) -----


def test_clean_message_has_no_offending_lines(hook) -> None:
    assert hook.offending_lines("Fix the widget\n\nBody text here.\n") == []


def test_co_authored_by_is_offending(hook) -> None:
    hits = hook.offending_lines("Fix the widget\n\nCo-Authored-By: Someone <x@example.com>\n")
    assert any(name == "Co-Authored-By trailer" for _n, name, _line in hits)


def test_comment_lines_are_ignored(hook) -> None:
    assert hook.offending_lines("Fix the widget\n\n# Co-Authored-By: not real\n") == []


# --- subject_line -------------------------------------------------------------


def test_subject_line_skips_comments_and_blanks(hook) -> None:
    message = "\n# a leading comment\n\nFix the widget\n\nBody.\n"
    assert hook.subject_line(message) == "Fix the widget"


# --- subject_shape_warning (Story 59.6 / CAP-137, Ruling 17) ----------------


def test_capitalized_no_period_subject_is_clean(hook) -> None:
    assert hook.subject_shape_warning("Fix the widget", staged=[]) is None


def test_lowercase_subject_warns(hook) -> None:
    warning = hook.subject_shape_warning("fix the widget", staged=[])
    assert warning is not None
    assert "Capitalized sentence" in warning


def test_trailing_period_warns(hook) -> None:
    warning = hook.subject_shape_warning("Fix the widget.", staged=[])
    assert warning is not None
    assert "trailing period" in warning


def test_auto_checkpoint_marker_is_exempt(hook) -> None:
    assert hook.subject_shape_warning("wip: 59.6 (auto-checkpoint)", staged=[]) is None


def test_conventional_subject_outside_recipes_warns(hook) -> None:
    warning = hook.subject_shape_warning("fix(scribe): repair the thing", staged=["src/foo.py"])
    assert warning is not None
    assert "recipes/" in warning


def test_conventional_subject_under_recipes_is_clean(hook) -> None:
    staged = ["recipes/foo/recipe.yaml"]
    assert hook.subject_shape_warning("fix(foo): bump version", staged=staged) is None


def test_conventional_subject_mixed_paths_still_warns(hook) -> None:
    staged = ["recipes/foo/recipe.yaml", "docs/dreams/foo.md"]
    warning = hook.subject_shape_warning("fix(foo): bump version", staged=staged)
    assert warning is not None


def test_conventional_subject_cfe_changelog_is_clean(hook) -> None:
    staged = [".claude/skills/conda-forge-expert/CHANGELOG.md"]
    assert hook.subject_shape_warning("fix: note a gotcha", staged=staged) is None


def test_conventional_subject_no_staged_info_warns(hook) -> None:
    warning = hook.subject_shape_warning("fix(foo): bump version", staged=None)
    assert warning is not None


def test_empty_subject_is_not_warned(hook) -> None:
    assert hook.subject_shape_warning("", staged=[]) is None


# --- main() end-to-end: shape rule warns but never refuses ------------------


def test_main_warns_on_bad_shape_but_exits_zero(hook, tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(hook, "_staged_paths", lambda: [])
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text("fix the widget\n", encoding="utf-8")
    rc = hook.main([str(msg_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "commit-msg warning" in out


def test_main_still_refuses_co_authored_by(hook, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(hook, "_staged_paths", lambda: [])
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text("Fix the widget\n\nCo-Authored-By: Someone <x@example.com>\n", encoding="utf-8")
    rc = hook.main([str(msg_file)])
    assert rc == 1
