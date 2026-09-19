"""Unit tests for dispatch landing (Story 22.4, CAP-4)."""

from __future__ import annotations

from pathlib import Path

from pyforge.core.process import ProcessError, ProcessResult
from pyforge.marshal.core import policy, promotion
from pyforge.marshal.core.dispatch_landing import (
    DispatchLandingVerdict,
    ledger_status_precedence,
    may_attempt_dispatch_landing,
    merge_subject_is_marshal_native,
    refuse_unverified_landing,
    union_sprint_ledger_maps,
)
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.identity import normalize, render_merge_subject
from pyforge.marshal.dispatch_land import execute_dispatch_land
from pyforge.marshal.ports.forge import ForgeCommandError, PrInfo


def test_refuse_unverified_landing() -> None:
    assert refuse_unverified_landing(DispatchVerificationVerdict.REFUSED) is True
    assert refuse_unverified_landing(DispatchVerificationVerdict.VERIFIED) is False


def test_union_sprint_ledger_maps_done_beats_backlog() -> None:
    merged = union_sprint_ledger_maps(
        {"a": "done", "b": "backlog"},
        {"a": "backlog", "c": "done"},
    )
    assert merged["a"] == "done"
    assert merged["b"] == "backlog"
    assert merged["c"] == "done"
    assert ledger_status_precedence("backlog", "done") == "done"


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
    subject = render_merge_subject(story_key, template, "pyforge-marshal")
    assert merge_subject_is_marshal_native(subject, template, "pyforge-marshal")
    native = promotion.marshal_native_merged_keys(
        (subject,), template, "pyforge-marshal"
    )
    assert story_key in native


class FakeVcs:
    def __init__(
        self,
        *,
        merged: bool = False,
        branches: set[str] | None = None,
        worktrees: dict[str, Path] | None = None,
        conflict_paths: tuple[str, ...] | None = None,
    ) -> None:
        self._merged = merged
        self.pushed: list[str] = []
        # Story 22.9: branch resolution reads which branches exist and where
        # git has each checked out.
        self.branches: set[str] = set(branches or ())
        self.worktrees: dict[str, Path] = dict(worktrees or {})
        self.conflict_paths = conflict_paths if conflict_paths is not None else ()

    def merge_tree_conflict_paths(self, repo_root: Path, base: str, branch: str):
        return self.conflict_paths

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str):
        return None

    def commit_subjects(self, repo_root: Path, ref: str):
        if self._merged:
            effective, _ = policy.compose(
                project_slug="pyforge-marshal", project={}, flags={}
            )
            key = normalize("22-4-example")
            subject = render_merge_subject(
                key, effective.merge_subject_template.value, "pyforge-marshal"
            )
            return (subject,)
        return ()

    def branch_exists(self, _repo_root: Path, branch: str) -> bool:
        return branch in self.branches

    def worktree_path_for_branch(self, _repo_root: Path, branch: str) -> Path | None:
        return self.worktrees.get(branch)

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

    def pr_merge_state(self, repo, number):
        return "MERGEABLE"

    def close_pr(self, repo, number):
        return None


class FakeProcess:
    def run(self, tokens, *, cwd: Path):
        return ProcessResult(returncode=0, stdout="", stderr="")


class BrokenProcess:
    """Story 51.2: a ``ProcessPort`` whose ``.run()`` always raises --
    simulates ``dispatch_land_finalize`` failing as a subprocess AFTER the
    PR has already been merged (``data["merged"] = True``)."""

    def run(self, tokens, *, cwd: Path):
        raise ProcessError("dispatch land finalize subprocess failed")


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


def test_execute_dispatch_land_refuses_unknown_merge_conflicts(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcs(
        merged=False,
        conflict_paths=("recipes/foo/recipe.yaml",),
    )
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=BrokenForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    disp038 = [f for f in envelope.findings if f.code == "MRS-DISP-038"]
    assert len(disp038) == 1
    assert "recipes/foo/recipe.yaml" in disp038[0].message


def _ledger_yaml(*pairs: tuple[str, str]) -> str:
    lines = ["development_status:"]
    for key, status in pairs:
        lines.append(f"  {key}: {status}")
    lines.append("")
    return "\n".join(lines)


class HealCapableVcs(FakeVcs):
    def __init__(
        self,
        *,
        conflict_paths: tuple[str, ...],
        main_ledger: str,
        branch_ledger: str,
    ) -> None:
        super().__init__(merged=False, conflict_paths=conflict_paths)
        self.main_ledger = main_ledger
        self.branch_ledger = branch_ledger
        self.commits: list[tuple[Path, tuple[Path, ...], str]] = []
        self._head_sha = "abc123"

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str):
        if path.endswith("sprint-status-ledger.yaml"):
            if ref == "main":
                return self.main_ledger
            return self.branch_ledger
        return None

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: str):
        self.commits.append((repo_root, paths, message))
        self._head_sha = "healed222"
        return self._head_sha

    def resolve_ref(self, repo_root: Path, ref: str) -> str:
        return self._head_sha


class HealRetryForge(BrokenForge):
    def __init__(self) -> None:
        self.merge_calls = 0

    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        self.merge_calls += 1
        if self.merge_calls == 1:
            raise ForgeCommandError("pull request is not mergeable")


class DirtyHealVcs(FakeVcs):
    def __init__(self) -> None:
        super().__init__(merged=False, conflict_paths=())
        self.merged: list[tuple[str, str, str]] = []
        self.deleted: list[str] = []

    def merge_branch(self, repo_root: Path, branch: str, *, into: str, subject: str) -> str:
        self.merged.append((branch, into, subject))
        return "localmerge999"

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        self.deleted.append(branch)


class DirtyHealForge(BrokenForge):
    def __init__(self) -> None:
        super().__init__()
        self.closed: list[int] = []

    def pr_merge_state(self, repo, number: int) -> str:
        return "DIRTY"

    def close_pr(self, repo, number: int) -> None:
        self.closed.append(number)


def test_execute_dispatch_land_advances_main_when_merge_tree_clean_and_github_dirty(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = DirtyHealVcs()
    forge = DirtyHealForge()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge,
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data.get("local_main_advance") is True
    assert vcs.merged == [("dispatch/pyforge-marshal/28.20", "main", result.subject)]
    assert "main" in vcs.pushed
    assert forge.closed == [42]


def test_execute_dispatch_land_heals_ledger_only_conflict(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    ledger_rel = (
        "_bmad-output/projects/pyforge-marshal/planning-artifacts/"
        "sprint-status-ledger.yaml"
    )
    vcs = HealCapableVcs(
        conflict_paths=(ledger_rel,),
        main_ledger=_ledger_yaml(("28-19-x", "done")),
        branch_ledger=_ledger_yaml(("28-20-y", "backlog")),
    )
    forge = HealRetryForge()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge,
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data.get("ledger_union_heal") is True
    assert forge.merge_calls == 2
    assert len(vcs.commits) == 1
    assert vcs.commits[0][0] == worktree
    written = (worktree / ledger_rel).read_text(encoding="utf-8")
    assert "28-19-x: done" in written
    assert "28-20-y: backlog" in written


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
    assert vcs.pushed == ["dispatch/pyforge-marshal/22.4"]
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert result.marshal_native is True
    assert result.pr_number == 42


def test_execute_dispatch_land_refused_result_keeps_pr_facts_after_merge(
    tmp_path: Path,
) -> None:
    """Story 51.2: when the PR is already merged (``data["merged"] = True``)
    but the ``dispatch_land_finalize`` subprocess then raises
    ``ProcessError``, the REFUSED result must still carry the ``pr_number``
    and ``subject`` that were already known at that point in execution, and
    ``marshal_native=True`` (the check that gates ``merge_pr`` already
    passed) -- not the dataclass's ``None``/``False`` defaults."""
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
        process=BrokenProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert result.pr_number == 42
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    expected_subject = render_merge_subject(
        normalize("22-4-example"), effective.merge_subject_template.value, "pyforge-marshal"
    )
    assert result.subject == expected_subject
    assert result.marshal_native is True
    assert any(f.code == "MRS-DISP-020" for f in envelope.findings)
    assert envelope.data.get("merged") is True


def test_execute_dispatch_land_refused_result_keeps_pr_facts_before_merge_native_check(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 51.2: when the rendered merge subject fails the marshal-native
    check (``MRS-DISP-019``, before any merge is attempted), the REFUSED
    result must still carry the ``pr_number``/``subject`` already known at
    that point -- but ``marshal_native`` stays the dataclass default
    ``False``, since that's the check's real (failed) outcome here, not a
    guess."""
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land.merge_subject_is_marshal_native",
        lambda *args, **kwargs: False,
    )
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=FakeVcs(merged=False),
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert result.pr_number == 42
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    expected_subject = render_merge_subject(
        normalize("22-4-example"), effective.merge_subject_template.value, "pyforge-marshal"
    )
    assert result.subject == expected_subject
    assert result.marshal_native is False
    assert any(f.code == "MRS-DISP-019" for f in envelope.findings)


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


# --------------------------------------------------------------------------
# Story 22.9: landing resolves the station-scoped branch, and still finds an
# in-flight run left on the pre-22.9 `marshal/<key>` name.
# --------------------------------------------------------------------------


def test_execute_dispatch_land_lands_an_in_flight_legacy_branch(tmp_path: Path) -> None:
    """A run that started before 22.9 lands from `marshal/<key>` -- git has
    that branch checked out at THIS run's worktree, so it is attributable."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcs(merged=False, worktrees={"marshal/22.4": worktree})
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
    assert envelope.data["branch"] == "marshal/22.4"
    assert result.verdict == DispatchLandingVerdict.LANDED


def test_execute_dispatch_land_refuses_another_stations_legacy_branch(
    tmp_path: Path,
) -> None:
    """A legacy branch checked out somewhere that is NOT this run's worktree
    is never pushed and merged under this station's story key."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    theirs = tmp_path / "someone-elses-tree"
    theirs.mkdir()
    vcs = FakeVcs(merged=False, worktrees={"marshal/22.4": theirs})
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
    assert vcs.pushed == []
    assert result.verdict == DispatchLandingVerdict.REFUSED
    refusals = [f for f in envelope.findings if f.code == "MRS-DISP-030"]
    assert len(refusals) == 1
    assert "marshal/22.4" in refusals[0].message
    assert "Land that branch first" in refusals[0].message


def test_execute_dispatch_land_refuses_an_unattributable_preserved_branch(
    tmp_path: Path,
) -> None:
    """A preserved legacy branch with no worktree cannot be attributed, so
    landing refuses rather than pushing a branch it did not verify."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcs(merged=False, branches={"marshal/22.4"})
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
    assert vcs.pushed == []
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert any(f.code == "MRS-DISP-030" for f in envelope.findings)
