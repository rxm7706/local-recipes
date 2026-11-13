"""Story 83.19: dispatch never commits the CFE surface outside a sanctioned retro.

Real git repositories throughout (the spec's "test with a real git repository"). The
station guards' own ``branch_diff_guard.unsanctioned_commits`` is imported here, at test
time only, to check marshal's runtime mirror against it: marshal never imports the testing
kit from ``src/``.

Story 116.2 (spec-pyforge-marshal:CAP-305): the tests that read this checkout's
conda-forge-expert skill version moved to ``test_dispatch_cfe_commit_live_tree.py``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult
from pyforge.testing_kit import branch_diff_guard, cfe_surface

from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.core import dispatch_cfe_commit as cfe
from pyforge.marshal.core.dispatch_cfe_commit import (
    CFE_BRANCH_COMMIT_GATE_CODE,
    CFE_CHANGELOG_PATH,
    CFE_COMMIT_GATE_CODE,
    findings_for_unsanctioned_cfe_entries,
    is_cfe_surface_path,
    paths_excluding_cfe,
    pending_cfe_paths_from_status,
    unsanctioned_cfe_entries,
)
from pyforge.marshal.core.dispatch_ruff_format import apply_dispatch_ruff_format_before_verify
from pyforge.marshal.core.refs import ORIGIN_MAIN
from pyforge.marshal.core.worktree_checkpoint import auto_checkpoint_message, commit_worktree_checkpoint
from pyforge.marshal.dispatch_verify import check_unsanctioned_cfe_commits

# Story 116.2 (spec-pyforge-marshal:CAP-305): a path literal that names a tracked file is joined from its
# segments, so steward's trigger-map derivation does not read it as a file this suite opens -- each is a
# fixture path or a value the code under test names, never a read of the tracked tree.

_CFE_TEST = ".claude/skills/conda-forge-expert/tests/meta/test_example.py"
_CFE_SCRIPT = "/".join((".claude", "scripts", "conda-forge-expert", "native-build.sh"))
_CFE_TOOL = "/".join((".claude", "tools", "conda_forge_server.py"))
_STORY_FILE = "src/story.py"
_CFE_RENAME_SRC = ".claude/skills/conda-forge-expert/helper.py"
_CFE_RENAME_DST = "src/helper.py"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit_all(repo: Path, subject: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", subject)
    return _git(repo, "rev-parse", "HEAD").strip()


def _story_repo(tmp_path: Path) -> Path:
    """A story branch forked from ``refs/remotes/origin/main``, with the CFE surface seeded on main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _write(repo, _CFE_TEST, "def test_ok():\n    assert True\n")
    _write(repo, _CFE_SCRIPT, "echo build\n")
    _write(repo, _CFE_TOOL, "SERVER = 1\n")
    _write(repo, CFE_CHANGELOG_PATH, "# Changelog\n")
    _write(repo, _STORY_FILE, "x = 1\n")
    _commit_all(repo, "initial")
    _git(repo, "update-ref", ORIGIN_MAIN, "HEAD")
    _git(repo, "checkout", "-q", "-b", "story")
    return repo


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _story_repo(tmp_path)


@pytest.fixture
def vcs() -> GitVcs:
    return GitVcs()


def _branch_commits(repo: Path) -> list[tuple[str, list[str]]]:
    """``(subject, files)`` for each commit on ``origin/main..HEAD``, oldest first."""
    shas = _git(repo, "rev-list", "--reverse", f"{ORIGIN_MAIN}..HEAD").split()
    return [
        (
            _git(repo, "log", "-1", "--format=%s", sha).strip(),
            _git(repo, "show", "--format=", "--name-only", sha).split(),
        )
        for sha in shas
    ]


def _kit_verdict(repo: Path) -> list[str]:
    return branch_diff_guard.unsanctioned_commits(
        repo, pathspec=cfe_surface.CFE_GIT_PATHSPECS, changelog_path=cfe_surface.CFE_CHANGELOG_PATH
    )


def _marshal_verdict(repo: Path) -> list[str]:
    findings, report = check_unsanctioned_cfe_commits(worktree=repo, process=PosixProcess(), base=ORIGIN_MAIN)
    assert report["checked"] is True, report
    entries = report["unsanctioned"]
    assert isinstance(entries, list)
    assert bool(findings) is bool(entries)
    return entries


# --- one owner: marshal's runtime mirror equals the testing kit's definition -------------------


def test_marshal_mirrors_the_kits_cfe_surface() -> None:
    assert cfe.CFE_CHANGELOG_PATH == cfe_surface.CFE_CHANGELOG_PATH
    assert cfe.CFE_SURFACE_PREFIXES == cfe_surface.CFE_SURFACE_PREFIXES
    assert cfe.CFE_SURFACE_FILES == cfe_surface.CFE_SURFACE_FILES
    assert cfe.CFE_GIT_PATHSPECS == cfe_surface.CFE_GIT_PATHSPECS


def test_marshal_retro_subject_is_branch_diff_guards() -> None:
    assert cfe.RETRO_SUBJECT.pattern == branch_diff_guard._RETRO_SUBJECT.pattern
    assert cfe.RETRO_SUBJECT.flags == branch_diff_guard._RETRO_SUBJECT.flags


@pytest.mark.parametrize(
    "path",
    [
        _CFE_TEST,
        _CFE_SCRIPT,
        _CFE_TOOL,
        CFE_CHANGELOG_PATH,
        ".claude\\skills\\conda-forge-expert\\SKILL.md",
        ".claude/skills/conda-forge-expert-fork/SKILL.md",
        ".claude/tools/conda_forge_server.py.bak",
        ".claude/skills/pyforge-marshal/SKILL.md",
        _STORY_FILE,
    ],
)
def test_marshal_classifies_every_path_as_the_kit_does(path: str) -> None:
    assert is_cfe_surface_path(path) is cfe_surface.is_cfe_surface_path(path)


def _scenario_clean(repo: Path) -> None:
    _write(repo, _STORY_FILE, "x = 2\n")
    _commit_all(repo, "Story work outside the surface")


def _scenario_wip_checkpoint(repo: Path) -> None:
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")
    _commit_all(repo, auto_checkpoint_message("83.19"))


def _scenario_retro_cfe_with_changelog(repo: Path) -> None:
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")
    _write(repo, CFE_CHANGELOG_PATH, "# Changelog\n\n## 9.0.0\n")
    _commit_all(repo, "retro(cfe): v9.0.0")


def _scenario_bare_retro_with_changelog(repo: Path) -> None:
    _write(repo, _CFE_SCRIPT, "echo build2\n")
    _write(repo, CFE_CHANGELOG_PATH, "# Changelog\n\n## 9.0.1\n")
    _commit_all(repo, "retro: v9.0.1")


def _scenario_retro_without_changelog(repo: Path) -> None:
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")
    _commit_all(repo, "retro(cfe): forgot the changelog")


def _scenario_changelog_without_retro_subject(repo: Path) -> None:
    _write(repo, CFE_CHANGELOG_PATH, "# Changelog\n\n## 9.0.2\n")
    _commit_all(repo, "Bump the CFE changelog")


def _scenario_scripts_and_tool(repo: Path) -> None:
    _write(repo, _CFE_SCRIPT, "echo build3\n")
    _commit_all(repo, "Touch the CFE scripts tree")
    _write(repo, _CFE_TOOL, "SERVER = 2\n")
    _commit_all(repo, "Touch the CFE MCP server")


def _scenario_uncommitted(repo: Path) -> None:
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")
    _write(repo, _CFE_SCRIPT, "echo dirty\n")


def _scenario_sanctioned_retro_through_a_merge(repo: Path) -> None:
    _git(repo, "checkout", "-q", "-b", "side")
    _scenario_retro_cfe_with_changelog(repo)
    _git(repo, "checkout", "-q", "story")
    _scenario_clean(repo)
    _git(repo, "merge", "-q", "--no-ff", "-m", "Merge side into story", "side")


_SCENARIOS = {
    "clean": _scenario_clean,
    "wip-checkpoint": _scenario_wip_checkpoint,
    "retro-cfe-with-changelog": _scenario_retro_cfe_with_changelog,
    "bare-retro-with-changelog": _scenario_bare_retro_with_changelog,
    "retro-without-changelog": _scenario_retro_without_changelog,
    "changelog-without-retro-subject": _scenario_changelog_without_retro_subject,
    "scripts-and-tool": _scenario_scripts_and_tool,
    "uncommitted": _scenario_uncommitted,
    "sanctioned-retro-through-a-merge": _scenario_sanctioned_retro_through_a_merge,
}

_EXPECTED_UNSANCTIONED = {
    "clean": [],
    "wip-checkpoint": ["wip: 83.19 (auto-checkpoint)"],
    "retro-cfe-with-changelog": [],
    "bare-retro-with-changelog": [],
    "retro-without-changelog": ["retro(cfe): forgot the changelog"],
    "changelog-without-retro-subject": ["Bump the CFE changelog"],
    "scripts-and-tool": ["Touch the CFE MCP server", "Touch the CFE scripts tree"],
    "uncommitted": [f"uncommitted: {_CFE_SCRIPT}, {_CFE_TEST}"],
    "sanctioned-retro-through-a-merge": [],
}


def _subjects(entries: list[str]) -> list[str]:
    return [entry if entry.startswith("uncommitted:") else entry.split(" ", 1)[1] for entry in entries]


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=list(_SCENARIOS))
def test_marshal_branch_check_agrees_with_branch_diff_guard(repo: Path, scenario: str) -> None:
    _SCENARIOS[scenario](repo)

    marshal = _marshal_verdict(repo)

    assert marshal == _kit_verdict(repo)
    assert _subjects(marshal) == _EXPECTED_UNSANCTIONED[scenario]


# --- AC1: dispatch's own commits never carry a CFE-surface path ---------------------------------


def test_auto_checkpoint_leaves_the_cfe_surface_uncommitted(vcs: GitVcs, repo: Path) -> None:
    _write(repo, _STORY_FILE, "x = 2\n")
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")
    _write(repo, ".claude/skills/conda-forge-expert/new_reference.md", "new\n")

    result = commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key="83.19")

    assert result.committed is True
    assert _branch_commits(repo) == [("wip: 83.19 (auto-checkpoint)", [_STORY_FILE])]
    assert pending_cfe_paths_from_status(vcs, worktree=repo) == (
        ".claude/skills/conda-forge-expert/new_reference.md",
        _CFE_TEST,
    )


def test_auto_checkpoint_skips_a_worktree_whose_only_dirt_is_the_cfe_surface(vcs: GitVcs, repo: Path) -> None:
    _write(repo, _CFE_SCRIPT, "echo dirty\n")

    result = commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key="83.19")

    assert result.committed is False
    assert result.skipped_reason == "only CFE surface dirty"
    assert _branch_commits(repo) == []


def test_ruff_format_commit_never_carries_the_cfe_surface(vcs: GitVcs, repo: Path) -> None:
    story_py = "src/shared/packages/pyforge-marshal/src/pyforge/marshal/sample.py"
    cfe_py = ".claude/skills/conda-forge-expert/scripts/helper.py"
    _write(repo, "src/shared/packages/pyforge-marshal/pyproject.toml", "[tool.ruff]\n")
    _write(repo, story_py, "x=1\n")
    _write(repo, cfe_py, "y=1\n")
    _commit_all(repo, "Seed the story file and a CFE helper")

    class _FormatterTouchingEverything:
        """A formatter that rewrites the story file AND the CFE helper -- the worst case."""

        def run(self, tokens, *, cwd: Path) -> ProcessResult:
            if list(tokens[:2]) == ["ruff", "format"]:
                _write(repo, story_py, "x = 1\n")
                _write(repo, cfe_py, "y = 1\n")
            return ProcessResult(returncode=0, stdout="", stderr="")

    result = apply_dispatch_ruff_format_before_verify(
        worktree=repo, repo_root=repo, vcs=vcs, process=_FormatterTouchingEverything()
    )

    assert result.committed is True
    subject, files = _branch_commits(repo)[-1]
    assert subject.startswith("marshal: ruff check --fix and format")
    assert files == [story_py]
    assert pending_cfe_paths_from_status(vcs, worktree=repo) == (cfe_py,)


# --- AC2: the CFE edit plus its CHANGELOG lands in exactly one retro(cfe): commit ----------------


# --- AC3: a CFE edit without a CHANGELOG change refuses, naming Rule 2, and commits nothing ----


# --- AC4: a branch already carrying an unsanctioned CFE commit refuses, naming it ---------------


# --- AC5: a story touching no CFE path commits exactly as before --------------------------------


# --- AC6: removing the exclusion or the verification check fails these tests (mutation) ---------


def test_mutation_the_checkpoint_without_the_exclusion_commits_the_cfe_surface(
    vcs: GitVcs, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pyforge.marshal.core.worktree_checkpoint as checkpoint

    def _commit_everything(vcs, *, worktree, extra_paths=(), repo_root=None):
        root = repo_root or worktree
        changed = vcs.changed_files(root, worktree, base="HEAD")
        return tuple(Path(p) for p in changed)

    monkeypatch.setattr(checkpoint, "non_retro_commit_paths", _commit_everything)
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")

    commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key="83.19")

    assert _branch_commits(repo) == [("wip: 83.19 (auto-checkpoint)", [_CFE_TEST])]
    assert _kit_verdict(repo) != []


# --- the pure halves and the failure paths -------------------------------------------------------


def test_paths_excluding_cfe_keeps_the_callers_order() -> None:
    paths = ("src/z.py", _CFE_TEST, "docs/a.md", _CFE_TOOL)
    assert paths_excluding_cfe(paths) == (Path("src/z.py"), Path("docs/a.md"))


def test_unsanctioned_cfe_entries_needs_both_the_retro_subject_and_the_changelog() -> None:
    sha = "a" * 40
    commits = [
        (sha, "retro(cfe): ok", (CFE_CHANGELOG_PATH, _CFE_TEST)),
        (sha, "retro(cfe): no changelog", (_CFE_TEST,)),
        (sha, "Retro: wrong case", (CFE_CHANGELOG_PATH,)),
        (sha, "not retro: changelog", (CFE_CHANGELOG_PATH,)),
    ]

    entries = unsanctioned_cfe_entries(commits, dirty=[])

    assert entries == [
        f"{sha[:10]} retro(cfe): no changelog",
        f"{sha[:10]} Retro: wrong case",
        f"{sha[:10]} not retro: changelog",
    ]
    assert unsanctioned_cfe_entries([], dirty=[_CFE_TOOL]) == [f"uncommitted: {_CFE_TOOL}"]
    branch_only = findings_for_unsanctioned_cfe_entries([f"{sha[:10]} bad subject"], base=ORIGIN_MAIN)
    assert len(branch_only) == 1 and branch_only[0].code == CFE_BRANCH_COMMIT_GATE_CODE
    dirty_only = findings_for_unsanctioned_cfe_entries([f"uncommitted: {_CFE_TOOL}"], base=ORIGIN_MAIN)
    assert len(dirty_only) == 1 and dirty_only[0].code == CFE_COMMIT_GATE_CODE
    assert findings_for_unsanctioned_cfe_entries([], base=ORIGIN_MAIN) == ()


class _ScriptedProcess:
    def __init__(self, *results: ProcessResult | ProcessError) -> None:
        self._results = list(results)
        self.calls: list[list[str]] = []

    def run(self, tokens, *, cwd: Path) -> ProcessResult:
        self.calls.append(list(tokens))
        result = self._results.pop(0)
        if isinstance(result, ProcessError):
            raise result
        return result


_OK_EMPTY = ProcessResult(returncode=0, stdout="", stderr="")


@pytest.mark.parametrize(
    ("results", "detail"),
    [
        ((ProcessResult(128, "", "fatal: bad revision"),), "exit 128: fatal: bad revision"),
        ((ProcessError("git not found"),), "git not found"),
        ((_OK_EMPTY, ProcessResult(128, "", "fatal: bad index")), "exit 128: fatal: bad index"),
        ((_OK_EMPTY, ProcessError("diff killed")), "diff killed"),
    ],
    ids=["log-exit", "log-raises", "diff-exit", "diff-raises"],
)
def test_a_failed_git_read_refuses_never_reads_clean(
    tmp_path: Path, results: tuple[ProcessResult | ProcessError, ...], detail: str
) -> None:
    findings, report = check_unsanctioned_cfe_commits(
        worktree=tmp_path, process=_ScriptedProcess(*results), base=ORIGIN_MAIN
    )

    assert [finding.code for finding in findings] == ["MRS-GATE-009"]
    assert detail in findings[0].message
    assert report == {"checked": False, "reason": detail, "rev_range": f"{ORIGIN_MAIN}..HEAD"}


def test_a_missing_base_ref_refuses_rather_than_skipping(tmp_path: Path) -> None:
    repo = tmp_path / "bare-history"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _write(repo, "a.txt", "a\n")
    _commit_all(repo, "initial")

    findings, report = check_unsanctioned_cfe_commits(worktree=repo, process=PosixProcess(), base=ORIGIN_MAIN)

    assert [finding.code for finding in findings] == ["MRS-GATE-009"]
    assert report["checked"] is False


def test_the_branch_check_reads_the_whole_surface_through_the_process_seam(tmp_path: Path) -> None:
    process = _ScriptedProcess(_OK_EMPTY, _OK_EMPTY)

    findings, report = check_unsanctioned_cfe_commits(worktree=tmp_path, process=process, base=ORIGIN_MAIN)

    assert findings == ()
    assert report == {"checked": True, "rev_range": f"{ORIGIN_MAIN}..HEAD", "commits_scanned": 0, "unsanctioned": []}
    log_call, diff_call = process.calls
    assert f"{ORIGIN_MAIN}..HEAD" in log_call and "--no-merges" in log_call
    assert log_call[log_call.index("--") + 1 :] == list(cfe.CFE_GIT_PATHSPECS)
    assert diff_call[diff_call.index("--") + 1 :] == list(cfe.CFE_GIT_PATHSPECS)


def test_auto_checkpoint_leaves_a_cfe_rename_out_of_the_wip_commit(vcs: GitVcs, repo: Path) -> None:
    _write(repo, _CFE_RENAME_SRC, "helper = 1\n")
    _write(repo, _STORY_FILE, "x = 2\n")
    _commit_all(repo, "seed helper on the CFE surface")
    _git(repo, "mv", _CFE_RENAME_SRC, _CFE_RENAME_DST)
    _write(repo, _STORY_FILE, "x = 3\n")

    result = commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key="83.24")

    assert result.committed is True
    subject, files = _branch_commits(repo)[-1]
    assert subject == "wip: 83.24 (auto-checkpoint)"
    assert files == [_STORY_FILE]
    assert set(pending_cfe_paths_from_status(vcs, worktree=repo)) == {_CFE_RENAME_DST, _CFE_RENAME_SRC}
