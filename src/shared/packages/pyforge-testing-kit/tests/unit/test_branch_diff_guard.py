"""Unit tests for `branch_diff_guard` (retro-pyforge-steward-2026-09-04.md
action item 11) against a throwaway git repo, not this checkout."""

from __future__ import annotations

import re
import subprocess
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest
from pyforge.core.process import PosixProcess, ProcessResult

from pyforge.testing_kit import (
    changed_paths_since,
    commit_files,
    commit_subject,
    commits_since,
    diff_text_since,
    existed_at_ref,
    pyforge_import_offenders,
    unsanctioned_commits,
)


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "base.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "branch", "main")
    _git(root, "branch", "origin_main_ref")
    return root


def _make_origin_main(root: Path) -> None:
    # Simulate a remote-tracking `origin/main` ref without a real remote.
    (root / ".git" / "refs" / "remotes" / "origin").mkdir(parents=True, exist_ok=True)
    sha = _git(root, "rev-parse", "HEAD").strip()
    (root / ".git" / "refs" / "remotes" / "origin" / "main").write_text(sha + "\n")


def test_changed_paths_since_skips_loudly_without_base_ref(repo: Path):
    with pytest.raises(pytest.skip.Exception):
        changed_paths_since(repo, base="origin/main", pathspec="src")


def test_changed_paths_since_reports_changed_files(repo: Path):
    _make_origin_main(repo)
    (repo / "src").mkdir()
    (repo / "src" / "new.py").write_text("y = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "add src/new.py")
    changed = changed_paths_since(repo, base="origin/main", pathspec="src")
    assert changed == ["src/new.py"]


def test_changed_paths_since_includes_untracked_when_asked(repo: Path):
    _make_origin_main(repo)
    (repo / "src").mkdir()
    (repo / "src" / "untracked.py").write_text("z = 3\n", encoding="utf-8")
    changed = changed_paths_since(repo, base="origin/main", pathspec="src", include_untracked=True)
    assert changed == ["src/untracked.py"]
    assert changed_paths_since(repo, base="origin/main", pathspec="src") == []


def test_changed_paths_since_always_include(repo: Path):
    _make_origin_main(repo)
    changed = changed_paths_since(repo, base="origin/main", always_include=("self.py",))
    assert changed == ["self.py"]


def test_diff_text_since_skips_loudly_without_base_ref(repo: Path):
    with pytest.raises(pytest.skip.Exception):
        diff_text_since(repo, base="origin/main")


def test_diff_text_since_returns_patch(repo: Path):
    _make_origin_main(repo)
    (repo / "base.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "change base")
    text = diff_text_since(repo, base="origin/main", pathspec="base.py")
    assert "-x = 1" in text
    assert "+x = 2" in text


def test_existed_at_ref(repo: Path):
    _make_origin_main(repo)
    assert existed_at_ref(repo, "base.py", ref="origin/main") is True
    assert existed_at_ref(repo, "does-not-exist.py", ref="origin/main") is False


def test_pyforge_import_offenders_finds_top_level_imports(repo: Path):
    (repo / "clean.py").write_text("import os\n", encoding="utf-8")
    (repo / "dirty_import.py").write_text("import pyforge.core\n", encoding="utf-8")
    (repo / "dirty_from.py").write_text("from pyforge.core import x\n", encoding="utf-8")
    offenders = pyforge_import_offenders(["clean.py", "dirty_import.py", "dirty_from.py", "missing.py"], repo)
    assert offenders == ["dirty_import.py:1", "dirty_from.py:1"]


def test_commits_since_and_commit_metadata(repo: Path):
    _make_origin_main(repo)
    (repo / "a.py").write_text("a = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "add a.py")
    shas = commits_since(repo, base="origin/main")
    assert len(shas) == 1
    assert commit_subject(repo, shas[0]) == "add a.py"
    assert commit_files(repo, shas[0]) == ["a.py"]


def test_a_failing_git_call_still_raises_called_process_error(repo: Path):
    # The git calls run through pyforge.core.process.PosixProcess, whose `run` never raises for a
    # non-zero exit; the guard re-raises it so a failing git is loud, as `check_output` was.
    with pytest.raises(subprocess.CalledProcessError) as caught:
        commit_subject(repo, "0" * 40)
    assert caught.value.returncode != 0
    assert caught.value.cmd[:2] == ["git", "log"]


_BAD_PATHSPEC = ":(bogus)x"  # git refuses an unknown pathspec magic with exit 128


def _unsanctioned_commits_with_a_corrupt_index(repo: Path) -> list[str]:
    # `git log` passes with a corrupt index and `git diff HEAD` does not, so this reaches only the
    # dirty-path call at the end of unsanctioned_commits.
    (repo / ".git" / "index").write_text("not an index\n", encoding="utf-8")
    return unsanctioned_commits(repo, pathspec="surface", changelog_path="surface/CHANGELOG.md")


# One row per `_git_out` call site: swapping any of them for the non-raising `_git` would turn a git
# failure into a silent empty result. Each row makes its own git call fail for real.
_FAILING_CALLS: dict[str, Callable[[Path], object]] = {
    "diff_text_since": lambda repo: diff_text_since(repo, base="origin/main", pathspec=_BAD_PATHSPEC),
    "changed_paths_since": lambda repo: changed_paths_since(repo, base="origin/main", pathspec=_BAD_PATHSPEC),
    "commits_since": lambda repo: commits_since(repo, base="origin/main", pathspec=_BAD_PATHSPEC),
    "commit_files": lambda repo: commit_files(repo, "0" * 40),
    "unsanctioned_commits_history": lambda repo: unsanctioned_commits(
        repo, pathspec=_BAD_PATHSPEC, changelog_path="x/CHANGELOG.md"
    ),
    "unsanctioned_commits_dirty": _unsanctioned_commits_with_a_corrupt_index,
}


@pytest.mark.parametrize("call", _FAILING_CALLS, ids=list(_FAILING_CALLS))
def test_every_guard_raises_called_process_error_on_a_git_failure(repo: Path, call: str):
    _make_origin_main(repo)
    with pytest.raises(subprocess.CalledProcessError) as caught:
        _FAILING_CALLS[call](repo)
    assert caught.value.returncode != 0
    assert caught.value.cmd[0] == "git"


def test_a_failing_untracked_listing_raises_called_process_error(repo: Path, monkeypatch: pytest.MonkeyPatch):
    # No input makes `git ls-files --others` fail (git only warns) while the `git diff` before it passes,
    # so fail that one call at the process seam.
    real_run = PosixProcess.run

    def run(self: PosixProcess, argv: Sequence[str], **kwargs: Any) -> ProcessResult:
        if "ls-files" in argv:
            return ProcessResult(returncode=128, stdout="", stderr="fatal: forced")
        return real_run(self, argv, **kwargs)

    monkeypatch.setattr(PosixProcess, "run", run)
    _make_origin_main(repo)
    with pytest.raises(subprocess.CalledProcessError) as caught:
        changed_paths_since(repo, base="origin/main", include_untracked=True)
    assert caught.value.returncode == 128
    assert caught.value.cmd[:2] == ["git", "ls-files"]


def _dist_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", requirement)
    assert match, f"unparseable requirement {requirement!r}"
    return match.group(0)


def test_the_kit_declares_the_runtime_dependencies_it_imports():
    """`tests/packaging/test_dependency_completeness.py` skips the `pyforge` namespace, so nothing else
    pins that both manifests name the two packages the kit imports (`pyforge.core.process` in
    `branch_diff_guard`, `openfeature` in `flags`)."""
    kit = Path(__file__).resolve().parents[2]
    with (kit / "pyproject.toml").open("rb") as handle:
        pyproject = {_dist_name(dep) for dep in tomllib.load(handle)["project"]["dependencies"]}
    with (kit / "pixi.toml").open("rb") as handle:
        pixi = set(tomllib.load(handle)["package"]["run-dependencies"])
    for name in ("pyforge-core", "openfeature-sdk"):
        assert name in pyproject, f"{name} is not in pyproject.toml [project] dependencies"
        assert name in pixi, f"{name} is not in pixi.toml [package.run-dependencies]"


def test_unsanctioned_commits_accepts_a_sanctioned_retro(repo: Path):
    _make_origin_main(repo)
    surface = "surface"
    changelog = "surface/CHANGELOG.md"
    (repo / surface).mkdir()
    (repo / changelog).write_text("v1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "retro: bump surface")
    assert unsanctioned_commits(repo, pathspec=surface, changelog_path=changelog) == []


def test_unsanctioned_commits_flags_an_unsanctioned_edit(repo: Path):
    _make_origin_main(repo)
    surface = "surface"
    (repo / surface).mkdir()
    (repo / surface / "file.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "story: touch surface")
    bad = unsanctioned_commits(repo, pathspec=surface, changelog_path=f"{surface}/CHANGELOG.md")
    assert len(bad) == 1
    assert "story: touch surface" in bad[0]


def test_unsanctioned_commits_flags_uncommitted_dirt(repo: Path):
    _make_origin_main(repo)
    surface = "surface"
    changelog = f"{surface}/CHANGELOG.md"
    (repo / surface).mkdir()
    (repo / changelog).write_text("v1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "retro: seed surface")
    (repo / changelog).write_text("v2\n", encoding="utf-8")  # uncommitted edit, not staged
    bad = unsanctioned_commits(repo, pathspec=surface, changelog_path=changelog)
    assert any(entry.startswith("uncommitted:") for entry in bad)


def test_unsanctioned_commits_reads_every_path_of_a_tuple_pathspec(repo: Path):
    # Story 83.19: the CFE surface is three pathspecs; both the history and the dirty-path read
    # must cover the second one, not only the first.
    _make_origin_main(repo)
    first, second = "surface", "scripts"
    changelog = f"{first}/CHANGELOG.md"
    (repo / first).mkdir()
    (repo / second).mkdir()
    (repo / changelog).write_text("v1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "retro: seed surface")
    (repo / second / "tool.sh").write_text("echo 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "story: touch scripts")
    (repo / second / "tool.sh").write_text("echo 2\n", encoding="utf-8")

    bad = unsanctioned_commits(repo, pathspec=(first, second), changelog_path=changelog)

    assert [entry.split(" ", 1)[1] for entry in bad] == ["story: touch scripts", f"{second}/tool.sh"]
    assert bad[-1] == f"uncommitted: {second}/tool.sh"


# --- marshal Story 62.1 (CAP-272): a local `origin/main` never stands in for the remote ------------


def _branch_work_with_a_shadow(repo: Path, kind: str) -> None:
    """`refs/remotes/origin/main` at the fork point; one commit of branch work adding
    `src/new.py`; and the trap -- a local branch or tag named `origin/main` at HEAD."""
    _make_origin_main(repo)
    (repo / "src").mkdir()
    (repo / "src" / "new.py").write_text("y = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "story: add src/new.py")
    _git(repo, kind, "origin/main", "HEAD")


def test_the_default_base_is_the_remote_tracking_ref() -> None:
    from pyforge.testing_kit import ORIGIN_MAIN

    assert ORIGIN_MAIN == "refs/remotes/origin/main"


@pytest.mark.parametrize("kind", ["branch", "tag"])
@pytest.mark.parametrize("explicit", [False, True])
def test_every_guard_reads_the_remote_past_a_local_origin_main(repo: Path, kind: str, explicit: bool) -> None:
    _branch_work_with_a_shadow(repo, kind)
    base = {"base": "origin/main"} if explicit else {}

    # The trap, for the record: the short name is the shadow, so the branch's work vanishes.
    assert _git(repo, "diff", "--name-only", "origin/main").strip() == ""
    assert changed_paths_since(repo, pathspec="src", **base) == ["src/new.py"]
    assert "+y = 2" in diff_text_since(repo, pathspec="src", **base)
    assert [commit_subject(repo, sha) for sha in commits_since(repo, **base)] == ["story: add src/new.py"]
    ref = {"ref": "origin/main"} if explicit else {}
    assert existed_at_ref(repo, "base.py", **ref) is True  # the ref resolves: the False below is not a miss
    assert existed_at_ref(repo, "src/new.py", **ref) is False
    assert unsanctioned_commits(repo, pathspec="src", changelog_path="src/CHANGELOG.md", **base) != []


def test_a_full_ref_head_or_local_branch_passes_through(repo: Path) -> None:
    _make_origin_main(repo)
    (repo / "a.py").write_text("a = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "add a.py")

    assert changed_paths_since(repo, base="refs/remotes/origin/main") == ["a.py"]
    assert changed_paths_since(repo, base="main") == ["a.py"]  # the fixture's local `main`, at the base
    assert changed_paths_since(repo, base="HEAD") == []


def test_the_skip_names_the_full_ref_it_looked_for(repo: Path) -> None:
    with pytest.raises(pytest.skip.Exception, match="refs/remotes/origin/main is not available"):
        changed_paths_since(repo)
