"""Story 83.19: the CFE retro commit, read against this checkout's conda-forge-expert skill version.

Story 116.2 (spec-pyforge-marshal:CAP-305): every ``test_dispatch_cfe_commit.py`` test whose expected retro subject
reads the root's conda-forge-expert skill version (``read_cfe_skill_version``), or that hands the root to
``evaluate_dispatch_verification``, moved here, marked ``live_tree``; the root is found when a test runs, never at
import. Every other CFE-commit test stays in ``test_dispatch_cfe_commit.py``, which keeps the fixture repository and
the git helpers both files use.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess, ProcessResult
from test_dispatch_cfe_commit import (
    _CFE_RENAME_DST,
    _CFE_RENAME_SRC,
    _CFE_TEST,
    _CFE_TOOL,
    _STORY_FILE,
    _branch_commits,
    _commit_all,
    _git,
    _kit_verdict,
    _marshal_verdict,
    _story_repo,
    _write,
)

from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.core import dispatch_cfe_commit as cfe
from pyforge.marshal.core import policy
from pyforge.marshal.core.dispatch_cfe_commit import (
    CFE_BRANCH_COMMIT_GATE_CODE,
    CFE_CHANGELOG_PATH,
    CFE_COMMIT_GATE_CODE,
    commit_pending_cfe_retro,
    is_cfe_surface_path,
    paths_excluding_cfe,
    read_cfe_skill_version,
    retro_cfe_commit_subject,
)
from pyforge.marshal.core.dispatch_verification import (
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    judge_dispatch_verification,
)
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.worktree_checkpoint import auto_checkpoint_message, commit_worktree_checkpoint
from pyforge.marshal.dispatch_verify import evaluate_dispatch_verification

pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    # tests/unit -> tests -> pyforge-marshal -> packages -> shared -> src -> this checkout's root, found when a
    # test runs (it was the nearest ancestor holding scripts/commit_msg_hook.py, which is the same directory)
    return Path(__file__).resolve().parents[6]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _story_repo(tmp_path)


@pytest.fixture
def vcs() -> GitVcs:
    return GitVcs()


_STORY_KEY = normalize("83-19-dispatch-never-commits-the-cfe-surface-outside-a-sanctioned-retro")


def _retro_subject(story_key: str) -> str:
    return retro_cfe_commit_subject(
        story_key=story_key,
        cfe_version=read_cfe_skill_version(_repo_root()),
    )


class _GitThenGreen:
    """Real git for the repository reads; every verify command reads green."""

    def __init__(self) -> None:
        self._git = PosixProcess()

    def run(self, tokens, *, cwd: Path) -> ProcessResult:
        tokens = list(tokens)
        if tokens and tokens[0] == "git":
            return self._git.run(tokens, cwd=cwd)
        return ProcessResult(returncode=0, stdout="ok", stderr="")


def _verify(repo: Path, vcs: GitVcs):
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={"verify_commands": ["true"]}, flags={})
    return evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=_STORY_KEY,
        worktree=repo,
        repo_root=_repo_root(),
        effective=effective,
        spec_text=None,
        process=_GitThenGreen(),
        vcs=vcs,
        committing_vcs=vcs,
    )


def _cfe_findings(envelope) -> list:
    return [
        finding for finding in envelope.findings if finding.code in (CFE_COMMIT_GATE_CODE, CFE_BRANCH_COMMIT_GATE_CODE)
    ]


def test_verify_commits_the_cfe_surface_once_as_retro_cfe(vcs: GitVcs, repo: Path) -> None:
    _write(repo, _STORY_FILE, "x = 2\n")
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")
    _write(repo, CFE_CHANGELOG_PATH, "# Changelog\n\n## 9.1.0\n")
    commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key="83.19")

    envelope = _verify(repo, vcs)

    expected_subject = _retro_subject("83.19")
    cfe_commits = [(s, f) for s, f in _branch_commits(repo) if any(is_cfe_surface_path(p) for p in f)]
    assert cfe_commits == [(expected_subject, sorted([CFE_CHANGELOG_PATH, _CFE_TEST]))]
    assert expected_subject.startswith("retro(cfe): v")
    assert _kit_verdict(repo) == []
    assert _cfe_findings(envelope) == []
    assert envelope.data["cfe_retro_commit"] == {
        "checked": True,
        "committed": True,
        "paths": sorted([CFE_CHANGELOG_PATH, _CFE_TEST]),
    }
    assert envelope.data["cfe_unsanctioned_commits_check"]["unsanctioned"] == []


def test_verify_refuses_a_cfe_edit_without_a_changelog_naming_rule_2(vcs: GitVcs, repo: Path) -> None:
    _write(repo, _STORY_FILE, "x = 2\n")
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")
    commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key="83.19")

    envelope = _verify(repo, vcs)

    assert judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings)) == (
        DispatchVerificationVerdict.REFUSED
    )
    rule2 = [finding for finding in _cfe_findings(envelope) if "pending CFE paths" in finding.message]
    assert len(rule2) == 1
    assert "Rule 2" in rule2[0].message and CFE_CHANGELOG_PATH in rule2[0].message
    assert _CFE_TEST in rule2[0].message
    # Nothing CFE was committed, so nothing CFE can be pushed; the edit is still in the worktree.
    assert all(not is_cfe_surface_path(path) for _subject, files in _branch_commits(repo) for path in files)
    assert envelope.data["cfe_retro_commit"]["committed"] is False
    assert _CFE_TEST in vcs.changed_files(repo, repo, base="HEAD")


def test_verify_refuses_naming_a_commit_that_already_touched_the_cfe_surface(vcs: GitVcs, repo: Path) -> None:
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")
    sha = _commit_all(repo, auto_checkpoint_message("41.1"))

    envelope = _verify(repo, vcs)

    findings = _cfe_findings(envelope)
    assert len(findings) == 1
    assert findings[0].code == CFE_BRANCH_COMMIT_GATE_CODE
    assert f"{sha[:10]} wip: 41.1 (auto-checkpoint)" in findings[0].message
    assert "Rule 2" in findings[0].message
    assert judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings)) == (
        DispatchVerificationVerdict.REFUSED
    )


def test_a_story_with_no_cfe_path_commits_exactly_as_before(vcs: GitVcs, repo: Path) -> None:
    _write(repo, "src/b.py", "b = 1\n")
    _write(repo, _STORY_FILE, "x = 2\n")
    changed = vcs.changed_files(repo, repo, base="HEAD")

    assert paths_excluding_cfe(changed) == tuple(Path(path) for path in changed)
    result = commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key="83.19")
    assert result.committed is True
    assert _branch_commits(repo) == [("wip: 83.19 (auto-checkpoint)", sorted(["src/b.py", _STORY_FILE]))]

    envelope = _verify(repo, vcs)

    assert _cfe_findings(envelope) == []
    assert envelope.data["cfe_retro_commit"] == {"checked": True, "committed": False, "paths": []}
    assert envelope.data["cfe_unsanctioned_commits_check"]["commits_scanned"] == 0
    assert len(_branch_commits(repo)) == 1


def test_mutation_verify_without_the_branch_check_lets_an_unsanctioned_commit_through(
    vcs: GitVcs, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(repo, _CFE_TEST, "def test_ok():\n    assert False\n")
    _commit_all(repo, auto_checkpoint_message("41.1"))
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_verify.check_unsanctioned_cfe_commits",
        lambda **_kwargs: ((), {"checked": False, "reason": "mutation: check removed"}),
    )

    without = _verify(repo, vcs)
    monkeypatch.undo()
    with_check = _verify(repo, vcs)

    assert _cfe_findings(without) == []
    assert len(_cfe_findings(with_check)) == 1


def test_commit_pending_cfe_retro_is_a_no_op_without_cfe_paths(vcs: GitVcs, repo: Path) -> None:
    _write(repo, _STORY_FILE, "x = 2\n")

    outcome = commit_pending_cfe_retro(
        vcs, worktree=repo, changed_paths=(_STORY_FILE,), story_key="83.19", repo_root=_repo_root()
    )

    assert outcome == cfe.CfeRetroCommitResult(committed=False)
    assert _branch_commits(repo) == []


def test_commit_pending_cfe_retro_reports_a_failed_commit() -> None:
    class _FailingCommit:
        def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message) -> str:
            raise RuntimeError("index.lock exists")

    outcome = commit_pending_cfe_retro(
        _FailingCommit(),
        worktree=Path("/nonexistent"),
        changed_paths=(_CFE_TEST, CFE_CHANGELOG_PATH),
        story_key="83.19",
        repo_root=_repo_root(),
    )

    assert outcome.committed is False
    assert outcome.paths == tuple(sorted((_CFE_TEST, CFE_CHANGELOG_PATH)))
    assert outcome.finding is not None and outcome.finding.code == CFE_COMMIT_GATE_CODE
    assert "index.lock exists" in outcome.finding.message


def test_verify_refuses_when_the_dirty_paths_cannot_be_read(repo: Path) -> None:
    class _UnreadableDirt(GitVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
            if base == "HEAD":
                raise RuntimeError("git status failed")
            return super().changed_files(repo_root, worktree_path, base=base)

    envelope = _verify(repo, _UnreadableDirt())

    unreadable = [f for f in envelope.findings if f.code == "MRS-GATE-009" and "dirty paths" in f.message]
    assert len(unreadable) == 1 and "git status failed" in unreadable[0].message
    assert envelope.data["cfe_retro_commit"] == {"checked": False, "reason": "git status failed"}


def test_the_retro_commit_subject_passes_the_guards_own_rule(vcs: GitVcs, repo: Path) -> None:
    _write(repo, _CFE_TOOL, "SERVER = 3\n")
    _write(repo, CFE_CHANGELOG_PATH, "# Changelog\n\n## 9.2.0\n")

    outcome = commit_pending_cfe_retro(
        vcs,
        worktree=repo,
        changed_paths=(_CFE_TOOL, CFE_CHANGELOG_PATH),
        story_key="83.24",
        repo_root=_repo_root(),
    )

    assert outcome.committed is True
    expected = _retro_subject("83.24")
    assert _branch_commits(repo) == [(expected, sorted([CFE_CHANGELOG_PATH, _CFE_TOOL]))]
    assert _kit_verdict(repo) == [] == _marshal_verdict(repo)


def test_verify_retro_commit_carries_both_sides_of_a_cfe_rename(vcs: GitVcs, repo: Path) -> None:
    _write(repo, _STORY_FILE, "x = 2\n")
    _commit_all(repo, "story progress outside the CFE surface")
    _write(repo, _CFE_RENAME_SRC, "helper = 1\n")
    _git(repo, "add", _CFE_RENAME_SRC)
    _git(repo, "mv", _CFE_RENAME_SRC, _CFE_RENAME_DST)
    _write(repo, CFE_CHANGELOG_PATH, "# Changelog\n\n## 9.2.2\n")

    envelope = _verify(repo, vcs)

    expected = _retro_subject("83.19")
    cfe_commits = [(s, f) for s, f in _branch_commits(repo) if s.startswith("retro(cfe):")]
    assert len(cfe_commits) == 1 and cfe_commits[0][0] == expected
    assert CFE_CHANGELOG_PATH in cfe_commits[0][1]
    assert not (repo / _CFE_RENAME_SRC).exists()
    assert (repo / _CFE_RENAME_DST).is_file()
    assert _kit_verdict(repo) == []
    assert _cfe_findings(envelope) == []
