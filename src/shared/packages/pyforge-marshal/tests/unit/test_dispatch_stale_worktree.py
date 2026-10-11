"""Story 92.1 AC8: a run whose worktree vanished is never live, and no reader raises on it.

The fixture is shaped like run ``pyforge-marshal-20261004T165202766Z-fc6ece35`` (marshal 86.6, quarantined on
2026-10-11): its launch journaled a worktree an operator sweep has since removed, its session pid 63830 reads alive
(a reused pid whose start time cannot be read -- Story 83.1 lets it through), and it never completed. Every reader
runs against the real git adapter on a ``tmp_path`` repository, the adapter whose ``git rev-parse HEAD`` raised
``VcsCommandError`` out of the in-flight guard and crashed marshal 47.1's launch.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal import dispatch_verify
from pyforge.marshal.adapters.clock_system import SystemClock
from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.cli import dispatch as dispatch_cli
from pyforge.marshal.cli import status as status_cli
from pyforge.marshal.cli.dispatch import (
    _compose_policy,
    _live_dispatch_story_keys,
    gather_dispatch_journal_facts,
    resolve_dispatch_session_verdict,
    spin_loop_home_in_flight_conflict,
    station_finalize_pending_story,
    station_in_flight_conflict,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import dispatch_stale
from pyforge.marshal.core import status as status_core
from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.dispatch_supervisor.__main__ import gather_dispatch_git_facts
from pyforge.marshal.ports.session_group import SessionGroupReadError

_SLUG = "pyforge-marshal"
_STALE_RUN = "pyforge-marshal-20261004T165202766Z-fc6ece35"
_STALE_STORY = "86.6"
_SESSION_PID = 63830
_SUPERVISOR_PID = 63831


class _ReusedPids:
    """``ProcessPort``: the run's session and supervisor pids read alive -- reused, start time unreadable."""

    def __init__(self, alive: frozenset[int] = frozenset({_SESSION_PID, _SUPERVISOR_PID})) -> None:
        self._alive = alive

    def is_alive(self, pid: int) -> bool:
        return pid in self._alive

    def process_start_time(self, _pid: int) -> float | None:
        return None


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "stale@example.invalid")
    _git(repo, "config", "user.name", "stale")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/main", base)
    return repo, base


def _entry(counter: int, kind: str, phase: Phase, payload: dict, *, ts: str, intent: int | None = None) -> str:
    return prepare_for_write(
        build_entry(
            id=JournalEntryId("dispatch-launcher-1", counter),
            ts=ts,
            run_id=_STALE_RUN,
            kind=kind,
            phase=phase,
            payload=payload,
            intent_id=JournalEntryId("dispatch-launcher-1", intent) if intent is not None else None,
        )
    ).line


def _seed_stale_run(repo: Path, *, worktree: Path, baseline: str) -> Path:
    """The 86.6 run dir: launch INTENT + OUTCOME, supervisor attach + heartbeats, a dispatch-push pair, and no
    dispatch-completion."""
    run_dir = dispatch_core.dispatch_run_dir(repo, _SLUG, _STALE_RUN)
    run_dir.mkdir(parents=True)
    lines = [
        _entry(
            0,
            dispatch_core.KIND_DISPATCH_LAUNCH,
            Phase.INTENT,
            {"story_key": _STALE_STORY, "worktree_path": str(worktree), "baseline_head_sha": baseline},
            ts="2026-10-04T16:52:02.938Z",
        ),
        _entry(
            1,
            dispatch_core.KIND_DISPATCH_LAUNCH,
            Phase.OUTCOME,
            {"ok": True, "session_pid": _SESSION_PID, "supervisor_pid": _SUPERVISOR_PID, "harness_profile": "cursor"},
            ts="2026-10-04T16:52:03.100Z",
            intent=0,
        ),
        _entry(
            2,
            dispatch_core.KIND_DISPATCH_SUPERVISOR_ATTACH,
            Phase.OBSERVATION,
            {"pid": _SUPERVISOR_PID, "session_pid": _SESSION_PID, "baseline_head_sha": baseline},
            ts="2026-10-04T16:52:03.400Z",
        ),
        *(
            _entry(
                3 + index,
                dispatch_core.KIND_DISPATCH_SUPERVISOR_ATTACH,
                Phase.OBSERVATION,
                {"heartbeat": True, "session_alive": True, "current_head_sha": baseline, "changed_path_count": index},
                ts=f"2026-10-04T16:5{3 + index}:03.400Z",
            )
            for index in range(3)
        ),
        _entry(
            6,
            dispatch_core.KIND_DISPATCH_PUSH,
            Phase.INTENT,
            {"branch": dispatch_core.dispatch_worktree_branch(_SLUG, _STALE_STORY)},
            ts="2026-10-04T17:01:00.000Z",
        ),
        _entry(
            7,
            dispatch_core.KIND_DISPATCH_PUSH,
            Phase.OUTCOME,
            {"ok": True, "branch": dispatch_core.dispatch_worktree_branch(_SLUG, _STALE_STORY)},
            ts="2026-10-04T17:01:02.000Z",
            intent=6,
        ),
    ]
    (run_dir / "journal.jsonl").write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    return run_dir


@pytest.fixture
def stale(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    """``(repo, run_dir, missing_worktree, baseline)``: the worktree existed at launch and was swept since."""
    repo, base = _repo(tmp_path)
    worktree = dispatch_core.dispatch_worktree_path(repo, _SLUG, _STALE_STORY)
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(
        repo, "worktree", "add", "-q", "-b", dispatch_core.dispatch_worktree_branch(_SLUG, _STALE_STORY), str(worktree)
    )
    run_dir = _seed_stale_run(repo, worktree=worktree, baseline=base)
    shutil.rmtree(worktree)  # the operator sweep -- git still lists the worktree, the directory is gone
    return repo, run_dir, worktree, base


def _guard(repo: Path, *, story_key: str, advisories: list[Finding] | None, process=None):
    return station_in_flight_conflict(
        fs=LocalFs(),
        vcs=GitVcs(),
        process=process if process is not None else _ReusedPids(),
        repo_root=repo,
        slug=_SLUG,
        story_key=story_key,
        effective_policy=_compose_policy(_SLUG),
        preflight_advisories=advisories,
    )


def test_the_fixture_is_the_crash_the_base_raised(stale) -> None:
    """The crash this story fixes, reproduced: on this fixture the git facts gather raises ``VcsCommandError``. At
    commit ``6b5182c155`` (this story's ``baseline_revision``; the 90.1 revert ``a085cd0344`` is its ancestor)
    ``_live_dispatch_evidence`` made that call with no ``try`` (``cli/dispatch.py:1905``), so
    ``station_in_flight_conflict`` raised ``VcsCommandError: git rev-parse HEAD failed`` on this run -- marshal
    47.1's launch crash of 2026-10-11."""
    repo, _run_dir, worktree, base = stale
    with pytest.raises(VcsCommandError, match="rev-parse HEAD failed"):
        gather_dispatch_git_facts(
            GitVcs(),
            fs=LocalFs(),
            repo_root=repo,
            worktree=worktree,
            story_key=_STALE_STORY,
            project_slug=_SLUG,
            baseline_head_sha=base,
            merge_subject_template="Merge {slug}/{key} into main",
        )


def test_the_guard_neither_raises_nor_refuses_on_a_stale_run_and_warns_mrs_disp_064(stale) -> None:
    repo, run_dir, worktree, _base = stale
    advisories: list[Finding] = []

    conflict = _guard(repo, story_key="92.1", advisories=advisories)

    assert conflict is None
    assert [finding.code for finding in advisories] == ["MRS-DISP-064"]
    warning = advisories[0]
    assert warning.severity is Severity.WARN
    assert run_dir.name in warning.message
    assert repr(_STALE_STORY) in warning.message
    assert str(worktree) in warning.message
    assert f"_bmad-output/projects/{_SLUG}/implementation-artifacts/dispatch-runs-quarantine/" in warning.message
    assert "README.md" in warning.message


def test_the_stale_runs_own_story_is_not_refused_as_a_live_session(stale) -> None:
    repo, _run_dir, _worktree, _base = stale
    advisories: list[Finding] = []

    assert _guard(repo, story_key=_STALE_STORY, advisories=advisories) is None
    assert [finding.code for finding in advisories] == ["MRS-DISP-064"]


def test_no_reader_reads_the_stale_run_live_or_raises(stale) -> None:
    repo, run_dir, _worktree, _base = stale
    fs, vcs, process = LocalFs(), GitVcs(), _ReusedPids()
    policy = _compose_policy(_SLUG)
    journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)

    verdict = resolve_dispatch_session_verdict(
        fs=fs, vcs=vcs, process=process, repo_root=repo, slug=_SLUG, journal=journal, effective_policy=policy
    )
    keys = _live_dispatch_story_keys(
        fs=fs, vcs=vcs, process=process, repo_root=repo, slug=_SLUG, effective_policy=policy
    )
    listed = status_cli.list_live_dispatch_stories(
        fs=fs, vcs=vcs, process=process, repo_root=repo, slug=_SLUG, effective_policy=policy
    )
    facts = status_cli._merge_dispatch_overlay(
        fs=fs,
        process=process,
        clock=SystemClock(),
        vcs=vcs,
        repo_root=repo,
        slug=_SLUG,
        facts=status_core.FleetHomeFacts(slug=_SLUG, branch=f"loop/{_SLUG}"),
    )

    assert verdict is not DispatchSessionVerdict.LIVE
    assert keys == ()
    assert listed == ()
    # No overlay for a stale latest run: the row never reads `running` because of it (AC9).
    assert facts.dispatch_story is None
    assert status_core.derive_dispatch_phase(facts) is None


def test_a_stale_latest_run_never_holds_the_drain_as_mid_finalize(stale) -> None:
    """The finalize-pending shape: the session has exited, the run's supervisor pid reads alive (reused), its story
    is on the backlog and nothing completed -- but a run with no worktree has nothing left to finalize, so the drain
    is never held on it."""
    repo, _run_dir, worktree, _base = stale

    def _pending(fs) -> tuple[str, str] | None:
        return station_finalize_pending_story(
            fs=fs,
            process=_ReusedPids(frozenset({_SUPERVISOR_PID})),
            repo_root=repo,
            slug=_SLUG,
            backlog=(_STALE_STORY,),
            effective_policy=_compose_policy(_SLUG),
        )

    class _WorktreeStillThere(LocalFs):
        def exists(self, path: Path) -> bool:
            return path == worktree or super().exists(path)

    # The oracle: the same run with its worktree present IS finalize-pending ...
    assert _pending(_WorktreeStillThere()) is not None
    # ... and with the worktree gone it is not.
    assert _pending(LocalFs()) is None


def test_without_the_vanished_worktree_rule_the_same_run_refuses_the_station(
    stale, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation proof for the rule: read as not stale, the run's reused pid makes it LIVE, and the serial guard
    refuses every other story on the station (MRS-DISP-021) -- the rule is what keeps it from blocking."""
    repo, _run_dir, _worktree, _base = stale
    monkeypatch.setattr(dispatch_stale, "dispatch_run_is_stale", lambda **_kwargs: False)

    conflict = _guard(repo, story_key="92.1", advisories=[])

    assert conflict is not None and conflict.code == "MRS-DISP-021"
    assert "git facts unreadable" in conflict.message


def test_a_broken_worktree_that_still_exists_is_reported_in_the_evidence_never_raised(tmp_path: Path) -> None:
    """Review M9b/m3: a live run whose worktree directory exists but is no longer a git worktree. The guard refuses
    the same story as live (MRS-DISP-011) and names the git failure in its evidence; the failure never escapes."""
    repo, base = _repo(tmp_path)
    broken = tmp_path / "not-a-worktree"
    broken.mkdir()
    _seed_stale_run(repo, worktree=broken, baseline=base)

    conflict = _guard(repo, story_key=_STALE_STORY, advisories=[])

    assert conflict is not None and conflict.code == "MRS-DISP-011"
    assert f"git facts unreadable for worktree {str(broken)!r}" in conflict.message
    assert "rev-parse HEAD failed" in conflict.message


def test_the_spin_guard_forwards_the_stale_run_warning(stale) -> None:
    repo, _run_dir, _worktree, _base = stale
    advisories: list[Finding] = []

    conflict = spin_loop_home_in_flight_conflict(
        fs=LocalFs(),
        vcs=GitVcs(),
        process=_ReusedPids(),
        harness=object(),  # no spin runs under this home: the harness is never asked
        home=repo,
        slug=_SLUG,
        story_key="92.1",
        effective_policy=_compose_policy(_SLUG),
        preflight_advisories=advisories,
    )

    assert conflict is None
    assert [finding.code for finding in advisories] == ["MRS-DISP-064"]


def test_a_stale_run_is_listed_with_its_remedy(stale) -> None:
    repo, run_dir, worktree, _base = stale
    journal = gather_dispatch_journal_facts(LocalFs(), run_dir, run_dir.name)

    report = dispatch_stale.stale_dispatch_run(fs=LocalFs(), journal=journal, run_id=run_dir.name, slug=_SLUG)

    assert report is not None
    assert dispatch_stale.stale_dispatch_run_payload(report) == {
        "run_id": _STALE_RUN,
        "story_key": _STALE_STORY,
        "worktree_path": str(worktree),
        "remedy": (
            f"move the run dir to _bmad-output/projects/{_SLUG}/implementation-artifacts/dispatch-runs-quarantine/ "
            "and list it in implementation-artifacts/dispatch-runs-quarantine/README.md; moving it back reverses it"
        ),
    }


@pytest.mark.parametrize(
    ("completion", "landing"),
    [("completed", None), ("failed", None), ("stopped_externally", None), ("blocked", None), (None, "landed")],
)
def test_a_finished_run_whose_worktree_is_gone_is_not_stale(
    completion: str | None, landing: str | None, tmp_path: Path
) -> None:
    journal = dispatch_core.DispatchJournalFacts(
        story_key=_STALE_STORY,
        session_pid=None,
        model=None,
        launched_at=None,
        worktree_path=str(tmp_path / "gone"),
        completion_verdict=completion,
        landing_verdict=landing,
    )

    assert dispatch_stale.dispatch_run_is_stale(fs=LocalFs(), journal=journal) is False


def test_the_stale_read_goes_through_the_fs_port(tmp_path: Path) -> None:
    """Review m2 (AD-4): ``core/`` asks ``FsPort.exists``; it never reads the filesystem itself."""
    asked: list[Path] = []

    class _Fs:
        def exists(self, path: Path) -> bool:
            asked.append(path)
            return True

    journal = dispatch_core.DispatchJournalFacts(
        story_key=_STALE_STORY, session_pid=None, model=None, launched_at=None, worktree_path=str(tmp_path / "gone")
    )

    assert dispatch_stale.dispatch_run_is_stale(fs=_Fs(), journal=journal) is False
    assert asked == [tmp_path / "gone"]


def test_the_harness_profile_and_the_liveness_error_are_read_off_the_journal(stale) -> None:
    _repo_root, run_dir, _worktree, _base = stale
    journal_path = run_dir / "journal.jsonl"
    journal_path.write_text(
        journal_path.read_text(encoding="utf-8")
        + _entry(
            8,
            dispatch_core.KIND_DISPATCH_SUPERVISOR_ATTACH,
            Phase.OBSERVATION,
            {"heartbeat": True, "session_alive": True, "session_liveness_error": "psutil: boom"},
            ts="2026-10-04T17:02:00.000Z",
        )
        + "\n",
        encoding="utf-8",
    )

    journal = gather_dispatch_journal_facts(LocalFs(), run_dir, run_dir.name)

    assert journal.harness_profile == "cursor"
    assert journal.session_liveness_error == "psutil: boom"
    assert dispatch_cli._is_dispatch_session_alive(_ReusedPids(frozenset()), journal) is False


class _RaisingGroup:
    def iter_session_group_members(self, _session_leader_pid: int):
        raise SessionGroupReadError("psutil: boom")


@pytest.mark.parametrize(
    ("cmdline", "alive"),
    [
        ("node /home/op/.local/share/cursor-agent/versions/2026.10/index.js --print", True),
        ("/usr/lib/firefox/firefox -contentproc", False),
    ],
)
def test_every_cli_reader_checks_the_leader_against_its_runs_harness_binary(
    stale, monkeypatch: pytest.MonkeyPatch, cmdline: str, alive: bool
) -> None:
    """Review M2: the CLI readers' liveness check falls back to the same identity the supervisor's does -- the
    ``binary`` of the harness profile the run's launch journaled (``cursor`` -> ``cursor-agent``)."""
    _repo_root, run_dir, _worktree, _base = stale
    monkeypatch.setattr(dispatch_verify, "_DEFAULT_SESSION_GROUP", _RaisingGroup())
    monkeypatch.setattr(dispatch_verify, "_process_cmdline", lambda _pid: cmdline)
    journal = gather_dispatch_journal_facts(LocalFs(), run_dir, run_dir.name)

    assert dispatch_cli._is_dispatch_session_alive(_ReusedPids(), journal) is alive
