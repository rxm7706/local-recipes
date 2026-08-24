"""Unit tests for dispatch landing (Story 22.4, CAP-4)."""

from __future__ import annotations

from pathlib import Path

from pyforge.core.process import ProcessResult
from pyforge.marshal.core import policy, promotion
from pyforge.marshal.core.dispatch_landing import (
    DispatchLandingVerdict,
    may_attempt_dispatch_landing,
    merge_subject_is_marshal_native,
    refuse_unverified_landing,
)
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.identity import normalize, render_merge_subject
from pyforge.marshal.dispatch_land import execute_dispatch_land
from pyforge.marshal.ports.forge import ForgeCommandError, PrInfo


def test_refuse_unverified_landing() -> None:
    assert refuse_unverified_landing(DispatchVerificationVerdict.REFUSED) is True
    assert refuse_unverified_landing(DispatchVerificationVerdict.VERIFIED) is False


def test_may_attempt_only_when_verified_and_not_merged() -> None:
    assert may_attempt_dispatch_landing(
        DispatchVerificationVerdict.VERIFIED, story_merged_on_main=False
    )
    assert not may_attempt_dispatch_landing(
        DispatchVerificationVerdict.REFUSED, story_merged_on_main=False
    )
    assert not may_attempt_dispatch_landing(
        DispatchVerificationVerdict.VERIFIED, story_merged_on_main=True
    )


def test_merge_subject_is_marshal_native_with_policy_template() -> None:
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={},
        flags={},
    )
    template = effective.merge_subject_template.value
    story_key = normalize(
        "22-4-a-verified-story-lands-through-the-existing-machinery-classified-marshal-native"
    )
    subject = render_merge_subject(story_key, template)
    assert merge_subject_is_marshal_native(subject, template, "pyforge-marshal")
    native = promotion.marshal_native_merged_keys(
        (subject,), template, "pyforge-marshal"
    )
    assert story_key in native


class FakeVcs:
    def __init__(self, *, merged: bool = False) -> None:
        self._merged = merged
        self.pushed: list[str] = []

    def commit_subjects(self, repo_root: Path, ref: str):
        if self._merged:
            effective, _ = policy.compose(
                project_slug="pyforge-marshal", project={}, flags={}
            )
            key = normalize("22-4-example")
            subject = render_merge_subject(
                key, effective.merge_subject_template.value
            )
            return (subject,)
        return ()

    def push(self, repo_root: Path, branch: str) -> None:
        self.pushed.append(branch)

    def resolve_ref(self, repo_root: Path, ref: str) -> str:
        return "abc123"


class FakeForge:
    def find_open_pr(self, repo, head_branch):
        return None

    def create_pr(self, repo, base, head_branch, title, body):
        return PrInfo(number=42, url="https://example/pr/42", state="open", base="main")

    def update_pr(self, repo, number, title, body):
        return PrInfo(number=number, url="https://example/pr/42", state="open", base="main")

    def add_labels(self, repo, number, labels):
        return None

    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        return None


class FakeProcess:
    def run(self, tokens, *, cwd: Path):
        return ProcessResult(returncode=0, stdout="", stderr="")


class BrokenForge(FakeForge):
    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        raise ForgeCommandError("merge blocked")


def test_execute_dispatch_land_refuses_unverified(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.REFUSED,
        vcs=FakeVcs(),
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.SKIPPED_UNVERIFIED
    assert any(f.code == "MRS-DISP-014" for f in envelope.findings)


def test_execute_dispatch_land_skips_when_already_on_main(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=FakeVcs(merged=True),
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.ALREADY_LANDED
    assert envelope.data.get("already_landed") is True


def test_execute_dispatch_land_pushes_branch_when_verified(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcs(merged=False)
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert vcs.pushed == ["marshal/22.4"]
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert result.marshal_native is True
    assert result.pr_number == 42


def test_unverified_never_lands(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, _ = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.REFUSED,
        vcs=FakeVcs(),
        forge=BrokenForge(),
        process=FakeProcess(),
    )
    assert result.verdict != DispatchLandingVerdict.LANDED
    assert result.pr_number is None
