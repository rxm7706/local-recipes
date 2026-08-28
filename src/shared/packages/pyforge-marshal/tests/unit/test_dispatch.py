"""Unit tests for ``marshal factory dispatch`` (Story 22.1)."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli.dispatch import run_dispatch
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.status import FleetHomeFacts, build_fleet_row
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.build_harness import (
    DispatchLaunchResult,
    HarnessCandidateSkip,
    HarnessResolution,
)


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "dispatch@test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "dispatch"],
        cwd=path,
        check=True,
        capture_output=True,
    )


class FakeFs:
    def __init__(self) -> None:
        self.dirs: set[Path] = set()
        self.files: dict[Path, str] = {}
        self.appended: list[tuple[Path, str, bool]] = []

    def is_dir(self, path: Path) -> bool:
        return path in self.dirs

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def create_dir_exclusive(self, path: Path) -> None:
        self.dirs.add(path)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content

    def read_text(self, path: Path) -> str | None:
        return self.files.get(path)


class FakeVcs:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.added: list[tuple[Path, Path, str, str]] = []
        # Story 22.9: which branches git already has, and where each is
        # checked out -- the two facts branch resolution reads.
        self.branches: set[str] = set()
        self.worktrees: dict[str, Path] = {}

    def repo_common_root(self, _cwd: Path) -> Path:
        return self.repo_root

    def branch_exists(self, _repo_root: Path, branch: str) -> bool:
        return branch in self.branches or branch in self.worktrees

    def worktree_path_for_branch(self, _repo_root: Path, branch: str) -> Path | None:
        return self.worktrees.get(branch)

    def add_worktree(
        self, repo_root: Path, home: Path, branch: str, *, base: str
    ) -> None:
        self.added.append((repo_root, home, branch, base))
        self.worktrees[branch] = home
        home.mkdir(parents=True, exist_ok=True)

    def worktree_head_sha(self, _worktree: Path) -> str:
        return "baseline0001"


class FakeBuildHarness:
    def __init__(self, *, present: bool = True, pid: int = 4242) -> None:
        self.present = present
        self.pid = pid
        self.calls: list[dict[str, object]] = []
        self.preference_seen: tuple[str, ...] | None = None

    def binary_present(self, preference=(), repo_root=None) -> HarnessResolution:
        self.preference_seen = tuple(preference)
        if not self.present:
            return HarnessResolution(
                profile=None,
                skipped=tuple(
                    HarnessCandidateSkip(
                        profile=name, reason=f"binary {name!r} not found on PATH"
                    )
                    for name in preference
                ),
            )
        chosen = next(iter(preference), "claude")
        return HarnessResolution(profile=chosen, binary_path=f"/usr/bin/{chosen}")

    def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
        self.calls.append({"worktree": worktree, **kwargs})
        resolution = kwargs.get("resolution")
        return DispatchLaunchResult(
            pid=self.pid,
            command=("fake-harness",),
            model=kwargs.get("model"),
            budget_env=dict(kwargs.get("budget_env") or {}),
            profile=resolution.profile if resolution is not None else None,
        )


class FakeProcess:
    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive

    def is_alive(self, _pid: int) -> bool:
        return self.alive

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        return 4243


def test_resolve_story_spec_path_finds_tracked_spec(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text("---\ndifficulty: medium\n---\n", encoding="utf-8")
    resolved = dispatch_core.resolve_story_spec_path(tmp_path, slug, story)
    assert resolved == spec


def test_build_fleet_row_surfaces_live_dispatch(tmp_path: Path) -> None:
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="22-1-example",
        dispatch_engine_alive=True,
        dispatch_elapsed_seconds=12.5,
        dispatch_run_id="pyforge-marshal-20260823T000000000Z-deadbeef",
    )
    row, finding = build_fleet_row(facts)
    assert finding is None
    assert row["state"] == "running"
    assert row["current_story"] == "22-1-example"
    assert row["elapsed_seconds"] == 12.5


def test_run_dispatch_journals_and_returns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    slug = "pyforge-marshal"
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text("---\ndifficulty: medium\n---\n# spec\n", encoding="utf-8")

    fs = FakeFs()
    vcs = FakeVcs(tmp_path)
    harness = FakeBuildHarness()
    process = FakeProcess()

    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=vcs,
        build_harness=harness,
        process=process,
    )
    assert code == EXIT_OK
    assert harness.calls
    assert harness.calls[0]["project_slug"] == slug
    assert fs.appended
    assert any("dispatch-launch" in line for _, line, _ in fs.appended)


def test_run_dispatch_refuses_missing_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    slug = "pyforge-marshal"
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    args = argparse.Namespace(slug=slug, story=story, format="text")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(present=False),
        process=FakeProcess(),
    )
    assert code != EXIT_OK


def test_run_dispatch_carries_profile_and_reports_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Story 22.8: the envelope names the resolved profile; every skipped
    preference candidate surfaces as a structured MRS-DISP-027 WARN."""
    _init_git_repo(tmp_path)
    slug = "pyforge-marshal"
    story = "22-8-the-session-harness-is-profile-driven-across-agent-clis"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    import json

    from pyforge.marshal.ports.build_harness import (
        HarnessCandidateSkip as Skip,
    )
    from pyforge.marshal.ports.build_harness import (
        HarnessResolution as Resolution,
    )

    class SkippingHarness(FakeBuildHarness):
        def binary_present(self, preference=(), repo_root=None):
            self.preference_seen = tuple(preference)
            return Resolution(
                profile="claude",
                binary_path="/usr/bin/claude",
                skipped=(
                    Skip(profile="cursor", reason="authcheck exited 1 (auth required)"),
                ),
            )

    harness = SkippingHarness()
    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert code == EXIT_OK
    # the policy default preference reached the resolution profile-first
    assert harness.preference_seen == ("claude", "cursor", "copilot", "gemini", "devin")
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["harness_profile"] == "claude"
    skips = [f for f in payload["findings"] if f["code"] == "MRS-DISP-027"]
    assert len(skips) == 1 and "cursor" in skips[0]["message"]
    assert harness.calls and harness.calls[0]["resolution"].profile == "claude"


def test_run_dispatch_refusal_names_every_candidate_tried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """MRS-DISP-003 must say what was tried and why each candidate was
    skipped -- the 2026-08-27 silent cursor-auth death, made loud."""
    _init_git_repo(tmp_path)
    slug = "pyforge-marshal"
    story = "22-8-the-session-harness-is-profile-driven-across-agent-clis"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    import json

    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(present=False),
        process=FakeProcess(),
    )
    assert code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    refusals = [f for f in payload["findings"] if f["code"] == "MRS-DISP-003"]
    assert len(refusals) == 1
    message = refusals[0]["message"]
    assert "no dispatchable session-harness profile" in message
    for name in ("claude", "cursor", "copilot", "gemini", "devin"):
        assert name in message


# --------------------------------------------------------------------------
# Story 22.9: a dispatch branch names its station
# --------------------------------------------------------------------------


_ATLAS = "pyforge-atlas"
_DOCTOR = "pyforge-doctor"
_SHARED_STORY = "20-1-a-story-key-two-stations-both-happen-to-use"
_SHARED_FEED_KEY = "20.1"


def _seed_spec(repo_root: Path, slug: str, story: str) -> Path:
    specs = dispatch_core.planning_specs_dir(repo_root, slug)
    specs.mkdir(parents=True, exist_ok=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text("---\ndifficulty: medium\n---\n# spec\n", encoding="utf-8")
    return spec


def _dispatch(
    repo_root: Path,
    slug: str,
    story: str,
    *,
    vcs: FakeVcs,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    _seed_spec(repo_root, slug, story)
    monkeypatch.chdir(repo_root)
    args = argparse.Namespace(slug=slug, story=story, format="json")
    run_dispatch(
        args,
        fs=FakeFs(),
        vcs=vcs,
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    return {}


def test_dispatch_branch_carries_its_station() -> None:
    assert (
        dispatch_core.dispatch_worktree_branch(_ATLAS, "20.2")
        == "dispatch/pyforge-atlas/20.2"
    )
    assert dispatch_core.legacy_dispatch_worktree_branch("20.2") == "marshal/20.2"


def test_dispatch_branch_requires_its_station() -> None:
    """The pre-22.9 one-argument call must not silently keep working."""
    with pytest.raises(TypeError):
        dispatch_core.dispatch_worktree_branch("20.2")  # type: ignore[call-arg]


def test_two_stations_sharing_a_story_key_never_reuse_one_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The motivating defect: ``_ensure_dispatch_worktree`` resolved by
    branch name, so a station-less ``marshal/20.1`` handed the second
    station the first station's tree. Two stations, one story key, zero
    reuse -- collision is impossible by construction."""
    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    _dispatch(tmp_path, _DOCTOR, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)

    branches = [branch for _root, _home, branch, _base in vcs.added]
    homes = [home for _root, home, _branch, _base in vcs.added]
    assert branches == [
        dispatch_core.dispatch_worktree_branch(_ATLAS, _SHARED_FEED_KEY),
        dispatch_core.dispatch_worktree_branch(_DOCTOR, _SHARED_FEED_KEY),
    ]
    assert len(set(branches)) == 2
    assert len(set(homes)) == 2


def test_legacy_branch_at_this_stations_worktree_is_still_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """An in-flight run started before 22.9 keeps its ``marshal/<key>``
    branch: git has it checked out at THIS station's dispatch worktree, so
    it is attributable and reused -- under a loud MRS-DISP-031 advisory,
    never silently."""
    import json

    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    legacy = dispatch_core.legacy_dispatch_worktree_branch(_SHARED_FEED_KEY)
    ours = dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, _SHARED_FEED_KEY)
    ours.mkdir(parents=True)
    vcs.worktrees[legacy] = ours

    _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    payload = json.loads(capsys.readouterr().out)

    assert vcs.added == []  # the existing tree was reused, not re-provisioned
    assert payload["data"]["branch"] == legacy
    assert payload["data"]["worktree_path"] == str(ours)
    advisories = [f for f in payload["findings"] if f["code"] == "MRS-DISP-031"]
    assert len(advisories) == 1
    assert legacy in advisories[0]["message"]


def test_legacy_branch_of_another_station_is_refused_land_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """The refusal names the legacy branch and the land-first remedy --
    never a silent reuse of another station's tree."""
    import json

    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    legacy = dispatch_core.legacy_dispatch_worktree_branch(_SHARED_FEED_KEY)
    theirs = dispatch_core.dispatch_worktree_path(tmp_path, _DOCTOR, _SHARED_FEED_KEY)
    theirs.mkdir(parents=True)
    vcs.worktrees[legacy] = theirs

    _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    payload = json.loads(capsys.readouterr().out)

    assert vcs.added == []
    refusals = [f for f in payload["findings"] if f["code"] == "MRS-DISP-030"]
    assert len(refusals) == 1
    message = refusals[0]["message"]
    assert legacy in message
    assert str(theirs) in message
    assert "Land that branch first" in message
    # No session was launched off another station's tree.
    assert "session_pid" not in payload["data"]


def test_preserved_legacy_branch_without_a_worktree_is_refused_not_stranded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A preserved ``marshal/<key>`` branch (pushed 2026-08-27, no worktree)
    cannot be attributed to a station, so dispatch refuses with the
    land-first remedy rather than minting a fresh branch beside it and
    stranding the work."""
    import json

    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    legacy = dispatch_core.legacy_dispatch_worktree_branch(_SHARED_FEED_KEY)
    vcs.branches.add(legacy)

    _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    payload = json.loads(capsys.readouterr().out)

    assert vcs.added == []
    refusals = [f for f in payload["findings"] if f["code"] == "MRS-DISP-030"]
    assert len(refusals) == 1
    assert legacy in refusals[0]["message"]
    assert "Land that branch first" in refusals[0]["message"]


def test_station_scoped_branch_wins_over_a_same_key_legacy_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Once a station has migrated, an unrelated station's leftover legacy
    branch under the same key neither blocks it nor is adopted by it."""
    import json

    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    branch = dispatch_core.dispatch_worktree_branch(_ATLAS, _SHARED_FEED_KEY)
    ours = dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, _SHARED_FEED_KEY)
    ours.mkdir(parents=True)
    vcs.worktrees[branch] = ours
    vcs.branches.add(dispatch_core.legacy_dispatch_worktree_branch(_SHARED_FEED_KEY))

    _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    payload = json.loads(capsys.readouterr().out)

    assert payload["data"]["branch"] == branch
    assert [f["code"] for f in payload["findings"] if f["code"].startswith("MRS-DISP-03")] == []


def test_every_branch_consumer_agrees_on_the_one_derivation(tmp_path: Path) -> None:
    """Worktree provisioning, the completion supervisor's git facts, and
    landing must all render the SAME branch for the same station+story."""
    from pyforge.marshal.cli.dispatch import _ensure_dispatch_worktree
    from pyforge.marshal.dispatch_supervisor.__main__ import gather_dispatch_git_facts

    expected = dispatch_core.dispatch_worktree_branch(_ATLAS, _SHARED_FEED_KEY)

    class RecordingVcs(FakeVcs):
        def __init__(self, repo_root: Path) -> None:
            super().__init__(repo_root)
            self.merge_checked: list[str] = []

        def changed_files(self, _repo_root: Path, _worktree: Path, *, base: str):
            return ()

        def is_branch_merged(self, _repo_root: Path, branch: str, *, into: str) -> bool:
            self.merge_checked.append(branch)
            return False

        def commit_subjects(self, _repo_root: Path, _ref: str):
            return ()

    # 1. worktree provisioning
    provision_vcs = RecordingVcs(tmp_path)
    provisioned = _ensure_dispatch_worktree(
        provision_vcs, tmp_path, _ATLAS, _SHARED_FEED_KEY
    )
    assert provisioned.branch == expected
    assert [b for _r, _h, b, _base in provision_vcs.added] == [expected]

    # 2. the completion supervisor's git facts (feeds the CAP-2 zombie
    #    refusal and the CAP-5 in-flight guard)
    facts_vcs = RecordingVcs(tmp_path)
    gather_dispatch_git_facts(
        facts_vcs,
        repo_root=tmp_path,
        worktree=dispatch_core.dispatch_worktree_path(
            tmp_path, _ATLAS, _SHARED_FEED_KEY
        ),
        story_key=_SHARED_FEED_KEY,
        project_slug=_ATLAS,
        baseline_head_sha="baseline0001",
        merge_subject_template="Story {key}",
    )
    assert facts_vcs.merge_checked == [expected]

    # 3. landing pushes that same branch (covered live by
    #    tests/unit/test_dispatch_landing.py's push assertion)
    assert (
        dispatch_core.resolve_dispatch_branch(
            RecordingVcs(tmp_path), tmp_path, slug=_ATLAS, story_key=_SHARED_FEED_KEY
        ).effective_branch
        == expected
    )


def test_only_one_dispatch_branch_derivation_site() -> None:
    """AC-3's guard: fail on a SECOND site that builds a dispatch branch
    string. ``core/dispatch.py`` owns both the station-scoped and the legacy
    spellings; anywhere else must import them."""
    import re

    import pyforge.marshal

    package_file = pyforge.marshal.__file__
    assert package_file is not None
    package_dir = Path(package_file).resolve().parent
    owner = package_dir / "core" / "dispatch.py"

    # Two shapes a second derivation site can take:
    # (a) a quoted literal that OPENS with a branch prefix and interpolates
    #     -- f"dispatch/{slug}...", f"marshal/{key}", "marshal/%s" % key --
    #     but NOT a path such as ".marshal/plan.json", which does not start
    #     with the prefix;
    # (b) importing the owner's private prefix constants and rebuilding the
    #     name from them.
    derivation = re.compile(
        r"""["'](?:dispatch|marshal)/(?:\{|%s)"""
        r"""|_(?:LEGACY_)?DISPATCH_BRANCH_PREFIX"""
    )

    offenders = sorted(
        str(path.relative_to(package_dir))
        for path in package_dir.rglob("*.py")
        if path != owner and derivation.search(path.read_text(encoding="utf-8"))
    )
    assert offenders == [], (
        "dispatch branch names must be derived only by "
        f"core/dispatch.py::dispatch_worktree_branch; second site(s) in {offenders}"
    )
    # The guard genuinely fires on every shape it claims to catch, and does
    # not fire on the `.marshal/` state-dir paths that live all over seed/.
    for caught in (
        'f"dispatch/{slug}/{story_key}"',
        'f"marshal/{story_key}"',
        '"marshal/%s" % story_key',
        'f"{_DISPATCH_BRANCH_PREFIX}/{slug}/{key}"',
        "_LEGACY_DISPATCH_BRANCH_PREFIX",
    ):
        assert derivation.search(caught), caught
    assert derivation.search('".marshal/plan.json"') is None
