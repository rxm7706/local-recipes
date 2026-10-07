"""Story 68.1 landing: the `workspace` module's edges -- renderers, the repo-sets.yaml
refusals, the slug refusals, the confirm prompt and the duty's error mapping.

The touched-module unit floor (80%) measured `pyforge.steward.workspace` at 73.9% when
Story 68.1 changed it; these paths had no test of their own. None needs git.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest

import pyforge.steward.workspace as ws
from pyforge.steward.workspace import (
    RepoSetMemberStatus,
    RepoSetStartResult,
    WorkspaceDuty,
    WorkspaceError,
    WorkspaceRecord,
    WorkspaceStatus,
    clean_workspaces,
    format_clean,
    format_ls,
    format_repo_set_start,
    format_repo_set_status,
    format_status,
    load_repo_sets,
    resolve_repo_path,
    save_bookkeeping,
    start_repo_set,
)

_RECORD = WorkspaceRecord("alpha", "/wt/alpha", "alpha", "origin/main", "2026-09-27T00:00:00+00:00")


def _status(**over: object) -> WorkspaceStatus:
    fields: dict[str, object] = {
        "slug": "alpha",
        "path": "/wt/alpha",
        "branch": "alpha",
        "source": "origin/main",
        "dirty": False,
        "ahead": 0,
        "behind": 2,
        "merged": True,
    }
    fields.update(over)
    return WorkspaceStatus(**fields)  # type: ignore[arg-type]


# --- renderers ------------------------------------------------------------------------


def test_format_ls_renders_empty_rows_and_json():
    assert format_ls((), as_json=False) == "workspace ls: no scratch workspaces open"
    assert format_ls((_RECORD,), as_json=False) == "alpha\talpha\t/wt/alpha"
    assert json.loads(format_ls((_RECORD,), as_json=True)) == [_RECORD.to_dict()]


def test_format_status_renders_empty_an_error_row_and_a_health_row():
    assert format_status((), as_json=False) == "workspace status: no scratch workspaces open"
    errored = _status(dirty=None, ahead=None, behind=None, merged=None, error="path missing")
    text = format_status((errored, _status(dirty=True, merged=False)), as_json=False).splitlines()
    assert text[0] == "alpha\terror\tpath missing\t/wt/alpha"
    assert text[1] == "alpha\tdirty\tahead=0\tbehind=2\tunmerged\t/wt/alpha"
    assert json.loads(format_status((errored,), as_json=True))[0]["error"] == "path missing"


def test_format_repo_set_status_names_each_member_and_whether_it_is_pushed():
    assert format_repo_set_status((), as_json=False) == "workspace status: no open members for repo set"
    rows = (
        RepoSetMemberStatus("api", _status(ahead=1)),
        RepoSetMemberStatus("web", _status()),
        RepoSetMemberStatus("docs", _status(dirty=None, ahead=None, behind=None, merged=None, error="git failed")),
    )
    text = format_repo_set_status(rows, as_json=False).splitlines()
    assert text[0] == "api\talpha\tclean\tunpushed\tahead=1\tbehind=2\tmerged\t/wt/alpha"
    assert text[1] == "web\talpha\tclean\tpushed\tahead=0\tbehind=2\tmerged\t/wt/alpha"
    assert text[2] == "docs\talpha\terror\tgit failed\t/wt/alpha"
    assert json.loads(format_repo_set_status(rows[:1], as_json=True))[0]["member"] == "api"


def test_format_repo_set_start_lists_the_workspace_file_then_each_member():
    result = RepoSetStartResult("feat", "f-feat", "/x/f-feat.code-workspace", (_RECORD,))
    assert format_repo_set_start(result, as_json=False) == "/x/f-feat.code-workspace\n/wt/alpha\talpha"
    payload = json.loads(format_repo_set_start(result, as_json=True))
    assert payload["branch"] == "f-feat" and payload["members"] == [_RECORD.to_dict()]


def test_format_clean_renders_nothing_archived_and_skipped_rows_with_members():
    assert format_clean({"archived": [], "deleted": [], "skipped": []}, as_json=False) == "workspace clean: nothing to do"
    result = {
        "archived": [
            {"slug": "a", "archive": "/arch/a.tar.gz"},
            {"slug": "b", "archive": "/arch/b.tar.gz", "member": "api"},
        ],
        "skipped": [{"slug": "c", "reason": "not-merged"}, {"slug": "d", "member": "web"}],
    }
    assert format_clean(result, as_json=False).splitlines() == [
        "archived a -> /arch/a.tar.gz",
        "archived api/b -> /arch/b.tar.gz",
        "skipped c (not-merged)",
        "skipped web/d (?)",
    ]
    assert json.loads(format_clean(result, as_json=True)) == result


# --- repo-sets.yaml refusals ------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("projects: [unclosed\n", "invalid YAML"),
        ("- a list\n", "top-level YAML must be a mapping"),
        ("projects: [a, b]\n", "'projects' must be a mapping"),
        ("projects:\n  feat: [x]\n", "projects['feat'] must be a mapping"),
        ("projects:\n  feat:\n    repos: [x]\n", "projects['feat'].repos must be a mapping"),
        ("projects:\n  feat:\n    repos:\n      api: nope\n", "projects['feat'].repos['api'] must be a mapping"),
        ("projects:\n  feat:\n    repos:\n      api: {branch: x}\n", "projects['feat'].repos['api'] missing path"),
    ],
)
def test_load_repo_sets_refuses_a_malformed_file_naming_the_problem(tmp_path: Path, body: str, message: str):
    config = tmp_path / "repo-sets.yaml"
    config.write_text(body, encoding="utf-8")
    with pytest.raises(WorkspaceError, match=message.replace("[", r"\[").replace("]", r"\]")):
        load_repo_sets(config)


def test_load_repo_sets_treats_a_missing_or_empty_file_as_no_sets(tmp_path: Path):
    assert load_repo_sets(tmp_path / "absent.yaml") == {}
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    assert load_repo_sets(empty) == {}


def test_resolve_repo_path_anchors_a_relative_path_and_keeps_an_absolute_one(tmp_path: Path):
    assert resolve_repo_path("sibling", anchor=tmp_path) == (tmp_path / "sibling").resolve()
    assert resolve_repo_path(str(tmp_path / "abs"), anchor=Path("/elsewhere")) == (tmp_path / "abs").resolve()


def test_start_repo_set_refuses_an_unknown_or_empty_set(tmp_path: Path):
    config = tmp_path / "repo-sets.yaml"
    config.write_text("projects:\n  empty: {}\n", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="repo set 'missing' not found"):
        start_repo_set("missing", repo_sets_path=config, anchor=tmp_path)
    with pytest.raises(WorkspaceError, match="repo set 'empty' has no registered repos"):
        start_repo_set("empty", repo_sets_path=config, anchor=tmp_path)


# --- clean: slug refusals -----------------------------------------------------------------


def test_clean_refuses_an_empty_unknown_or_ambiguous_slug(tmp_path: Path):
    bookkeeping = tmp_path / "workspaces.yaml"
    save_bookkeeping(bookkeeping, (_RECORD, _RECORD))
    kwargs = {"root": tmp_path, "bookkeeping": bookkeeping, "archive_dir": tmp_path / "archive"}
    with pytest.raises(WorkspaceError, match="invalid slug ''"):
        clean_workspaces(slug="", **kwargs)
    with pytest.raises(WorkspaceError, match="workspace 'nope' not in bookkeeping"):
        clean_workspaces(slug="nope", **kwargs)
    with pytest.raises(WorkspaceError, match="ambiguous slug 'alpha': 2 bookkeeping rows"):
        clean_workspaces(slug="alpha", **kwargs)


# --- the confirm prompt -------------------------------------------------------------------


class _Stdin:
    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def test_confirm_archive_needs_a_terminal_and_an_explicit_yes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ws.sys, "stdin", _Stdin(False))
    assert ws._confirm_archive("alpha") is False

    monkeypatch.setattr(ws.sys, "stdin", _Stdin(True))
    monkeypatch.setattr("builtins.input", lambda prompt: " Yes ")
    assert ws._confirm_archive("alpha") is True
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    assert ws._confirm_archive("alpha") is False

    def _eof(prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", _eof)
    assert ws._confirm_archive("alpha") is False


# --- the duty's error mapping ----------------------------------------------------------------


def test_duty_lists_its_verbs_when_none_is_given():
    result = WorkspaceDuty().run(argparse.Namespace())
    assert result.ok and result.summary == "workspace: available verbs are start, ls, status, clean"


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (RuntimeError("could not locate scripts/bmad-loop-worktree"), "could not locate scripts/bmad-loop-worktree"),
        (OSError("disk full"), "disk full"),
        (
            subprocess.CalledProcessError(128, ["git"], stderr="fatal: bad ref\n"),
            "workspace ls: git failed: fatal: bad ref",
        ),
    ],
)
def test_duty_reports_an_environment_failure_as_a_failed_duty(
    monkeypatch: pytest.MonkeyPatch, exc: BaseException, expected: str
):
    def _raise() -> None:
        raise exc

    monkeypatch.setattr(ws, "list_workspaces", _raise)
    text = WorkspaceDuty().run(argparse.Namespace(workspace_verb="ls", json=False))
    assert not text.ok and text.summary == expected
    as_json = WorkspaceDuty().run(argparse.Namespace(workspace_verb="ls", json=True))
    assert not as_json.ok and json.loads(as_json.summary) == {"error": expected}
