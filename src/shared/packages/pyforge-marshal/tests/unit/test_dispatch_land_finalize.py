"""dispatch_land_finalize must pass CAP-5 ``base=`` into ledger promote."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.journal import Phase
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.promotion import PRE_DONE_SPEC_STATUSES, TERMINAL_SPEC_STATUSES
from pyforge.marshal.core.refs import ORIGIN_MAIN
from pyforge.marshal.core.status import render_ledger_advancements
from pyforge.marshal.dispatch_land_finalize.__main__ import (
    _FINALIZE_RESYNC_KIND,
    _run_deferred_work_intake,
    finalize_dispatch_land,
)

#: `origin/main`'s ledger with the landed stories done -- the converged state finalize's readback
#: (Story 68.1, `MRS-DISP-051`) expects; tests that stub the promotion out land `42.5` / `53.2`.
_DONE_LEDGER = "development_status:\n  epic-42: in-progress\n  42-5-x: done\n  epic-53: in-progress\n  53-2-x: done\n"


class _StubVcs:
    """Story 51.9: production now calls ``vcs.has_uncommitted_changes(root)``
    directly, before ever reaching a monkeypatched ``_resync_home_branch`` --
    a bare ``object()`` can't take new attributes, so these tests (which
    aren't exercising vcs behavior itself) need this minimal fake instead.

    Story 68.1: finalize now also reads ``origin/main``'s tracked ledger after the promotion
    step (``fetch`` + ``file_text_at_ref``); ``ledger_text`` is what that read returns
    (``None`` = no such file), and either read can be made to fail."""

    def __init__(
        self,
        *,
        dirty: bool = False,
        ledger_text: str | None = _DONE_LEDGER,
        fetch_raises: bool = False,
        read_raises: bool = False,
    ) -> None:
        self.dirty = dirty
        self.ledger_text = ledger_text
        self.fetch_raises = fetch_raises
        self.read_raises = read_raises
        self.fetch_calls: list[tuple[Path, str, str]] = []
        self.read_calls: list[tuple[Path, str, str]] = []

    def has_uncommitted_changes(self, _worktree_path: Path) -> bool:
        return self.dirty

    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        self.fetch_calls.append((repo_root, remote, ref))
        if self.fetch_raises:
            raise VcsCommandError("git fetch origin refs/heads/main failed: could not read from remote")

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str) -> str | None:
        self.read_calls.append((repo_root, ref, path))
        if self.read_raises:
            raise VcsCommandError(f"git show {ref}:{path} failed: bad object")
        return self.ledger_text

    def commit_subjects(self, _repo_root: Path, _ref: str) -> tuple[str, ...]:
        """Story 79.1: a scan with a plan makes finalize re-read ``origin/main``'s history for the
        landing gate; this fake has none (the tests that need one use ``_PublishVcs``)."""
        return ()


def _read_finalize_resync_entry(tmp_path: Path, slug: str) -> dict:
    """Read back the single ``_FINALIZE_RESYNC_KIND`` journal entry written
    under ``tmp_path``'s real (unstubbed) ``LocalFs`` for this test run."""
    runs_dir = tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs"
    run_dirs = list(runs_dir.iterdir())
    assert len(run_dirs) == 1
    lines = (run_dirs[0] / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines if line]
    matches = [entry for entry in entries if entry["kind"] == _FINALIZE_RESYNC_KIND]
    assert len(matches) == 1
    return matches[0]


def test_finalize_passes_base_main_to_isolated_promote(tmp_path: Path, monkeypatch) -> None:
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    # Story 51.9: `LocalFs` is left unstubbed (real class, real `tmp_path`)
    # because the new `_resync_home_branch` + `deploy_run.write(...)`
    # observation write now exercises real fs operations. `GitVcs` is a
    # minimal `_StubVcs` (clean by default) rather than a bare `object()`,
    # since production now calls `has_uncommitted_changes` directly before
    # `_resync_home_branch` (itself monkeypatched to a no-op below).
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: _StubVcs(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        lambda *args, **kwargs: _Scan(),
    )

    def _capture(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return ()

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        _capture,
    )
    # Story 51.9: a bare `object()`-stubbed `GitVcs` has no `resolve_ref`/
    # `worktree_head_sha` -- an unstubbed `_resync_home_branch` call would
    # raise `AttributeError` and break this test, which isn't exercising
    # the resync behavior at all.
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    assert seen["kwargs"]["base"] == "main"


def test_finalize_forwards_worktree_to_scan_promotions(tmp_path: Path, monkeypatch) -> None:
    """Story 51.2: the landing record follows the session's write, not the
    primary's directory. When a worktree is given, ``finalize_dispatch_land``
    must thread it into ``_scan_promotions`` so a spec written into the
    dispatch worktree's own Tier-3 dir is still discoverable before
    teardown."""
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    # Story 51.9: `LocalFs` is left unstubbed (real class, real `tmp_path`)
    # because the new `_resync_home_branch` + `deploy_run.write(...)`
    # observation write now exercises real fs operations. `GitVcs` is a
    # minimal `_StubVcs` (clean by default) rather than a bare `object()`,
    # since production now calls `has_uncommitted_changes` directly before
    # `_resync_home_branch` (itself monkeypatched to a no-op below).
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: _StubVcs(),
    )

    def _capture_scan(*args, **kwargs):
        seen["scan_kwargs"] = kwargs
        return _Scan()

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        _capture_scan,
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )

    worktree = tmp_path / "some-worktree"
    assert finalize_dispatch_land("pyforge-steward", "42.5", worktree) == 0
    assert seen["scan_kwargs"]["worktree"] == worktree


def test_finalize_defaults_worktree_to_none(tmp_path: Path, monkeypatch) -> None:
    """Omitting ``worktree`` must still thread a literal ``None`` into
    ``_scan_promotions`` (byte-identical to pre-51.2 behavior)."""
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    # Story 51.9: `LocalFs` is left unstubbed (real class, real `tmp_path`)
    # because the new `_resync_home_branch` + `deploy_run.write(...)`
    # observation write now exercises real fs operations. `GitVcs` is a
    # minimal `_StubVcs` (clean by default) rather than a bare `object()`,
    # since production now calls `has_uncommitted_changes` directly before
    # `_resync_home_branch` (itself monkeypatched to a no-op below).
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: _StubVcs(),
    )

    def _capture_scan(*args, **kwargs):
        seen["scan_kwargs"] = kwargs
        return _Scan()

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        _capture_scan,
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    assert seen["scan_kwargs"]["worktree"] is None


def test_finalize_resyncs_the_primary_after_ledger_promotion(tmp_path: Path, monkeypatch) -> None:
    """Story 51.9 (re-mint of 51.3): `_promote_sprint_ledger` never touches
    the primary checkout's own working tree (CAP-5), so nothing else picked
    up that promotion either. `dispatch_land_finalize` must reuse
    `_resync_home_branch` VERBATIM, immediately after the ledger promotion,
    to fast-forward the primary checkout (``root``) onto `origin/main`'s
    tip whenever it is safely a clean `main` at its own tip."""
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    # Story 51.9: `LocalFs` is left unstubbed (real class, real `tmp_path`)
    # because the new `_resync_home_branch` + `deploy_run.write(...)`
    # observation write now exercises real fs operations. `GitVcs` is a
    # minimal `_StubVcs` (clean by default) rather than a bare `object()`,
    # since production now calls `has_uncommitted_changes` directly before
    # `_resync_home_branch` (itself monkeypatched to a no-op below).
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: _StubVcs(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        lambda *args, **kwargs: _Scan(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )

    def _capture_resync(*args, **kwargs):
        seen["resync_args"] = args
        return True

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        _capture_resync,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    assert "resync_args" in seen
    (
        _vcs,
        resync_enabled,
        merge_strategy,
        git_repo_root,
        home,
        base,
        head_branch,
        _findings,
    ) = seen["resync_args"]
    assert resync_enabled is True
    assert merge_strategy == "merge"
    assert git_repo_root == tmp_path
    assert home == tmp_path
    assert base == "main"
    assert head_branch == "main"

    # Group 3 (IA2/BH6, review pass 2026-09-19): assert the actual written
    # journal entry, not just the mocked call's own arguments.
    entry = _read_finalize_resync_entry(tmp_path, "pyforge-steward")
    assert entry["kind"] == _FINALIZE_RESYNC_KIND
    assert entry["phase"] == Phase.OBSERVATION
    assert entry["payload"]["resynced"] is True


def test_finalize_skips_resync_on_a_dirty_primary(tmp_path: Path, monkeypatch) -> None:
    """Story 51.9 (review pass 2026-09-19, Group 1): `_resync_home_branch`
    only checks SHA-match, never dirtiness -- a dirty checkout sitting
    exactly at local `main`'s own tip would pass that check unchanged and
    still get fast-forwarded with the dirty changes in place. Guard on
    `vcs.has_uncommitted_changes(root)` BEFORE ever calling
    `_resync_home_branch`, skip it entirely when dirty, and journal
    `resynced=False`."""
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    # `LocalFs` is left unstubbed (real class, real `tmp_path`) since the
    # unconditional `deploy_run.write(...)` observation write still fires
    # on this skip branch -- only the resync call itself is skipped.
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: _StubVcs(dirty=True),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        lambda *args, **kwargs: _Scan(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )

    def _capture_resync(*args, **kwargs):
        seen["resync_called"] = True
        return True

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        _capture_resync,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    assert "resync_called" not in seen

    entry = _read_finalize_resync_entry(tmp_path, "pyforge-steward")
    assert entry["kind"] == _FINALIZE_RESYNC_KIND
    assert entry["phase"] == Phase.OBSERVATION
    assert entry["payload"]["resynced"] is False


# Story 53.2 (spec-pyforge-marshal CAP-261b): `_run_deferred_work_intake`
# promotes a landed story's `deferred:` entries via
# `scripts/deferred_work_intake.py --fix` -- unit-level coverage of its own
# three branches (clean, refused, could-not-launch), plus one integration
# test proving `finalize_dispatch_land` actually wires its return value
# into the SAME `findings` list that gates the function's own return code.


class _FakeIntakeProcess:
    def __init__(self, *, returncode: int = 0, stderr: str = "", stdout: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, tokens, *, cwd: Path):
        self.calls.append((list(tokens), cwd))
        return ProcessResult(returncode=self.returncode, stdout=self.stdout, stderr=self.stderr)


class _RaisingIntakeProcess:
    def run(self, tokens, *, cwd: Path):
        raise ProcessError("deferred_work_intake.py could not be launched")


class _FakeIntakeVcs:
    """Records ``commit_paths_onto_remote_tip`` calls; never touches a real
    git repo -- these tests never expect it to be called unless noted."""

    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises
        self.calls: list[dict] = []

    def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message, preflight_skip_reason=None):
        self.calls.append(
            {
                "repo_root": repo_root,
                "remote": remote,
                "ref": ref,
                "writes": writes,
                "message": message,
                "preflight_skip_reason": preflight_skip_reason,
            }
        )
        if self.raises:
            from pyforge.marshal.adapters.vcs_git import VcsCommandError

            raise VcsCommandError("push rejected")
        return "new-sha"


def test_run_deferred_work_intake_clean_run_returns_none(tmp_path: Path) -> None:
    """The script runs but the tracked ledger's text is unchanged (the
    fake process never touches the filesystem) -- no commit, no finding."""
    process = _FakeIntakeProcess(returncode=0)
    fs = LocalFs()
    vcs = _FakeIntakeVcs()
    assert _run_deferred_work_intake(process, fs, vcs, tmp_path, "pyforge-steward", "53.2") is None
    [argv], [cwd] = zip(*process.calls)
    assert argv[-2:] == ["--project", "steward"]
    assert "--fix" in argv
    assert cwd == tmp_path
    assert vcs.calls == []


def test_run_deferred_work_intake_refusal_returns_warn_finding(tmp_path: Path) -> None:
    process = _FakeIntakeProcess(returncode=1, stderr="no resolvable location:")
    fs = LocalFs()
    vcs = _FakeIntakeVcs()
    finding = _run_deferred_work_intake(process, fs, vcs, tmp_path, "pyforge-marshal", "53.2")
    assert finding is not None
    assert finding.code == "MRS-DISP-047"
    assert finding.severity == Severity.WARN
    assert "marshal" in finding.message
    assert "no resolvable location:" in finding.message
    assert vcs.calls == []


def test_run_deferred_work_intake_process_error_returns_warn_finding(tmp_path: Path) -> None:
    fs = LocalFs()
    vcs = _FakeIntakeVcs()
    finding = _run_deferred_work_intake(_RaisingIntakeProcess(), fs, vcs, tmp_path, "pyforge-doctor", "53.2")
    assert finding is not None
    assert finding.code == "MRS-DISP-047"
    assert finding.severity == Severity.WARN
    assert "doctor" in finding.message
    assert vcs.calls == []


def test_run_deferred_work_intake_publishes_change_and_restores_local_text(
    tmp_path: Path,
) -> None:
    """Story 53.2 review (B5/B6): when ``--fix`` actually mutates the
    tracked ledger, the new text is published onto ``origin/main`` via
    ``commit_paths_onto_remote_tip`` and ``root``'s own working-tree copy is
    restored to its pre-``--fix`` text -- never left dirty for the next
    finalize's ``has_uncommitted_changes`` gate to trip over."""
    tracked_path = (
        tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "deferred-work-ledger.md"
    )
    tracked_path.parent.mkdir(parents=True)
    tracked_path.write_text("# Deferred Work Ledger\n\nold entry\n", encoding="utf-8")

    class _WritingProcess:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], Path]] = []

        def run(self, tokens, *, cwd: Path):
            self.calls.append((list(tokens), cwd))
            tracked_path.write_text("# Deferred Work Ledger\n\nold entry\n\nnew entry\n", encoding="utf-8")
            return ProcessResult(returncode=0, stdout="", stderr="")

    process = _WritingProcess()
    fs = LocalFs()
    vcs = _FakeIntakeVcs()
    finding = _run_deferred_work_intake(process, fs, vcs, tmp_path, "pyforge-marshal", "53.2")
    assert finding is None
    assert len(vcs.calls) == 1
    call = vcs.calls[0]
    assert call["remote"] == "origin"
    assert call["ref"] == "main"
    assert call["writes"] == (
        (
            "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md",
            "# Deferred Work Ledger\n\nold entry\n\nnew entry\n",
        ),
    )
    # Story 68.1 (CAP-277): the publish names its story in the preflight opt-out's reason.
    assert "53.2" in call["preflight_skip_reason"]
    assert "'marshal'" in call["preflight_skip_reason"]
    # root's own working tree is restored to the pre-`--fix` text.
    assert tracked_path.read_text(encoding="utf-8") == "# Deferred Work Ledger\n\nold entry\n"


def test_run_deferred_work_intake_warns_when_publish_fails(tmp_path: Path) -> None:
    """Story 53.2 review (B5): a failed publish to ``origin/main`` is a
    WARN, never a crash -- and the local working tree is still restored."""
    tracked_path = (
        tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "deferred-work-ledger.md"
    )
    tracked_path.parent.mkdir(parents=True)
    tracked_path.write_text("old\n", encoding="utf-8")

    class _WritingProcess:
        def run(self, tokens, *, cwd: Path):
            tracked_path.write_text("new\n", encoding="utf-8")
            return ProcessResult(returncode=0, stdout="", stderr="")

    fs = LocalFs()
    vcs = _FakeIntakeVcs(raises=True)
    finding = _run_deferred_work_intake(_WritingProcess(), fs, vcs, tmp_path, "pyforge-marshal", "53.2")
    assert finding is not None
    assert finding.code == "MRS-DISP-047"
    assert finding.severity == Severity.WARN
    assert "could not be published" in finding.message
    assert tracked_path.read_text(encoding="utf-8") == "old\n"


def test_finalize_appends_deferred_work_intake_finding_into_the_gating_findings_list(
    tmp_path: Path, monkeypatch
) -> None:
    """Black-box proof that `_run_deferred_work_intake`'s return value
    reaches the SAME `findings` list `finalize_dispatch_land` checks for a
    blocking severity: force it to return an ERROR-severity finding and
    confirm the whole finalize call goes non-zero because of it, exactly
    as it would for any other blocking finding this function collects."""
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: _StubVcs(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        lambda *args, **kwargs: _Scan(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )

    def _fake_intake(process, fs, vcs, root, project_slug, story_key):
        seen["intake_args"] = (root, project_slug, story_key)
        return Finding(code="MRS-DISP-047", severity=Severity.ERROR, message="forced for test")

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._run_deferred_work_intake",
        _fake_intake,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 1
    # Story 68.1: the story key finalize hands the intake is the landed story's, never the slug.
    assert seen["intake_args"] == (tmp_path, "pyforge-steward", "42.5")


def test_finalize_stays_green_when_intake_returns_no_finding(tmp_path: Path, monkeypatch) -> None:
    """The common case: intake ran clean (or found nothing to promote) and
    returned ``None`` -- finalize must not append anything for it and must
    stay green."""
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: _StubVcs(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        lambda *args, **kwargs: _Scan(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )

    def _fake_intake(process, fs, vcs, root, project_slug, story_key):
        seen["called"] = True
        return None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._run_deferred_work_intake",
        _fake_intake,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    assert seen["called"] is True


def test_finalize_journals_the_intake_finding_into_the_resync_payload(tmp_path: Path, monkeypatch) -> None:
    """Story 53.2 review (I2): the intake finding's serialized form must
    reach the ``_FINALIZE_RESYNC_KIND`` journal payload -- a WARN-severity
    intake refusal never blocks the return code, so without this the
    finding would be visible nowhere durable once it prints to stderr."""

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: _StubVcs(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        lambda *args, **kwargs: _Scan(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )

    def _fake_intake(process, fs, vcs, root, project_slug, story_key):
        return Finding(code="MRS-DISP-047", severity=Severity.WARN, message="forced for test")

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._run_deferred_work_intake",
        _fake_intake,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    entry = _read_finalize_resync_entry(tmp_path, "pyforge-steward")
    assert entry["payload"]["deferred_work_intake_finding"] == {
        "code": "MRS-DISP-047",
        "severity": "warn",
        "message": "forced for test",
    }


def test_finalize_journals_a_null_intake_finding_when_intake_is_clean(tmp_path: Path, monkeypatch) -> None:
    """The common (no-op) case journals an explicit ``None``, not an
    absent key -- so a reader never has to distinguish "never ran" from
    "ran clean"."""

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: _StubVcs(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        lambda *args, **kwargs: _Scan(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._run_deferred_work_intake",
        lambda process, fs, vcs, root, project_slug, story_key: None,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    entry = _read_finalize_resync_entry(tmp_path, "pyforge-steward")
    assert entry["payload"]["deferred_work_intake_finding"] is None


# --- 53.2 landing (2026-09-20): the touched-module coverage floor measured this
# module at 77% -- the branches below were the uncovered ones: the CLI entry,
# a malformed story key, a contended deferred-work lock, and the 51.7
# corroboration re-gate over a non-empty promotion plan.


def test_main_parses_argv_and_forwards_the_optional_worktree(monkeypatch, tmp_path: Path) -> None:
    from pyforge.marshal.dispatch_land_finalize import __main__ as mod

    seen: list[tuple] = []
    monkeypatch.setattr(
        mod, "finalize_dispatch_land", lambda slug, key, worktree: seen.append((slug, key, worktree)) or 0
    )
    assert mod.main(["pyforge-marshal", "53.2"]) == 0
    assert mod.main(["pyforge-marshal", "53.2", str(tmp_path)]) == 0
    assert seen == [("pyforge-marshal", "53.2", None), ("pyforge-marshal", "53.2", tmp_path)]


def test_a_malformed_story_key_is_refused_before_any_scan(monkeypatch, tmp_path: Path, capsys) -> None:
    from pyforge.marshal.dispatch_land_finalize import __main__ as mod

    monkeypatch.setattr(mod, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(mod, "_scan_promotions", lambda *a, **k: (_ for _ in ()).throw(AssertionError("scanned")))
    assert mod.finalize_dispatch_land("pyforge-marshal", "not-a-key") == 1
    assert "dispatch land finalize:" in capsys.readouterr().err


def test_a_contended_deferred_work_lock_is_a_warn_finding_not_a_crash(tmp_path: Path) -> None:
    class _LockedFs(LocalFs):
        def acquire_advisory_lock(self, path, *, timeout_s):
            raise FsError(f"lock held: {path}")

    finding = _run_deferred_work_intake(
        _FakeIntakeProcess(), _LockedFs(), _FakeIntakeVcs(), tmp_path, "pyforge-marshal", "53.2"
    )
    assert finding is not None and finding.code == "MRS-DISP-047" and finding.severity == Severity.WARN
    assert "lock" in finding.message and "marshal" in finding.message


def test_promotion_plan_is_regated_through_spec_status_corroboration(monkeypatch, tmp_path: Path) -> None:
    """Story 51.7 / CAP-255 inside finalize: a `to_promote` candidate is
    promoted only when its spec status at `origin/main` corroborates the
    merge; the corroboration reads the spec through `spec_text_at_ref` and
    fails closed on a git read error."""
    from pyforge.marshal.dispatch_land_finalize import __main__ as mod

    good, bad = normalize("53.2"), normalize("53.9")

    class _Candidate:
        def __init__(self, key):
            self.story_key = key

    class _Plan:
        to_promote = (_Candidate(good), _Candidate(bad))

    class _Scan:
        findings: list = []
        plan = _Plan()
        combined_subjects = ("Merge pyforge-marshal/53-2 into main",)
        template = "Merge {slug}/{key} into main"

    executed: list = []
    monkeypatch.setattr(mod, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(mod, "GitVcs", lambda: _StubVcs())
    monkeypatch.setattr(mod, "_scan_promotions", lambda *a, **k: _Scan())
    monkeypatch.setattr(mod, "_promote_sprint_ledger", lambda *a, **k: ())
    monkeypatch.setattr(mod, "_resync_home_branch", lambda *a, **k: True)
    monkeypatch.setattr(mod, "_execute_promotion_plan", lambda plan, **k: executed.extend(plan))

    def _spec_text(vcs, root, slug, key):
        if key == str(bad):
            raise VcsCommandError("no such spec at origin/main")
        return "---\nstatus: 'done'\n---\n"

    monkeypatch.setattr(mod.dispatch_core, "spec_text_at_ref", _spec_text)
    seen: dict = {}

    def _corroborate(subjects, template, slug, *, spec_status_for):
        seen["good"] = spec_status_for(good)
        seen["bad"] = spec_status_for(bad)
        return frozenset({good})

    monkeypatch.setattr(mod.promotion, "corroborated_merged_story_keys", _corroborate)
    assert mod.finalize_dispatch_land("pyforge-marshal", "53.2") == 0
    assert seen == {"good": "done", "bad": None}
    assert [c.story_key for c in executed] == [good]


# --- Story 68.1 (spec-pyforge-marshal CAP-277): a failed promotion is never silent ------------
#
# 64.1 landed (2026-09-28) with `origin/main`'s ledger still reading `64-1 ... backlog`: the promotion
# publish died at the git timeout, `_promote_sprint_ledger` reported it as a WARN, and finalize exited 0.
# Finalize now reads `origin/main`'s ledger itself and journals every finding it collected.

_BACKLOG_LEDGER_64_1 = "development_status:\n  epic-64: in-progress\n  64-1-a-landing-s-ledger-promotion: backlog\n"
_DONE_LEDGER_64_1 = "development_status:\n  epic-64: in-progress\n  64-1-a-landing-s-ledger-promotion: done\n"


class _NoScan:
    findings: list = []
    plan = None


def _stub_finalize(monkeypatch, tmp_path: Path, vcs, *, promote=None) -> None:
    """Everything finalize does around the ledger readback stubbed out, so a test drives exactly the
    promotion step (``promote``) and the readback that follows it."""
    mod = "pyforge.marshal.dispatch_land_finalize.__main__"
    monkeypatch.setattr(f"{mod}.repo_root", lambda: tmp_path)
    monkeypatch.setattr(f"{mod}.GitVcs", lambda: vcs)
    monkeypatch.setattr(f"{mod}._scan_promotions", lambda *a, **k: _NoScan())
    monkeypatch.setattr(f"{mod}._promote_sprint_ledger", promote or (lambda *a, **k: ()))
    monkeypatch.setattr(f"{mod}._resync_home_branch", lambda *a, **k: True)
    monkeypatch.setattr(f"{mod}._run_deferred_work_intake", lambda *a, **k: None)


def _promotion_warns(*args, **kwargs):
    """What `_promote_sprint_ledger` does on 64.1's failure: a WARN finding and an empty tuple."""
    findings = args[6]
    findings.append(
        Finding(
            code="MRS-LAND-011",
            severity=Severity.WARN,
            message="promoted sprint-status ledger keys ['64-1-a-landing-s-ledger-promotion'] could not be committed",
        )
    )
    return ()


def test_finalize_fails_when_the_landed_key_reads_backlog_on_origin_main(tmp_path: Path, monkeypatch, capsys) -> None:
    """AC 5: the promotion warned and returned `()`; `origin/main` still reads `backlog` -- the resync
    observation carries `MRS-LAND-011` and `MRS-DISP-051`, and finalize returns 1."""
    vcs = _StubVcs(ledger_text=_BACKLOG_LEDGER_64_1)
    _stub_finalize(monkeypatch, tmp_path, vcs, promote=_promotion_warns)

    assert finalize_dispatch_land("pyforge-marshal", "64.1") == 1

    entry = _read_finalize_resync_entry(tmp_path, "pyforge-marshal")
    findings = entry["payload"]["findings"]
    assert [f["code"] for f in findings] == ["MRS-LAND-011", "MRS-DISP-051"]
    assert [f["severity"] for f in findings] == ["warn", "error"]
    assert "does not read done on origin/main" in findings[1]["message"]
    assert "64-1-a-landing-s-ledger-promotion reads 'backlog'" in findings[1]["message"]
    # The readback is a fresh fetch and a read of the FULL refname -- never a short name a local
    # branch or tag called `origin/main` could shadow (Stories 57.1 / 60.1).
    assert vcs.fetch_calls == [(tmp_path, "origin", "main")]
    [(_root, ref, path)] = vcs.read_calls
    assert ref == ORIGIN_MAIN == "refs/remotes/origin/main"
    assert path == "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    assert "finding MRS-DISP-051" in capsys.readouterr().err


def test_finalize_is_clean_when_the_landed_key_reads_done_on_origin_main(tmp_path: Path, monkeypatch) -> None:
    """AC 9 / I/O matrix 'key already done': no finding, exit 0, an empty findings list journaled."""
    vcs = _StubVcs(ledger_text=_DONE_LEDGER_64_1)
    _stub_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land("pyforge-marshal", "64.1") == 0

    assert _read_finalize_resync_entry(tmp_path, "pyforge-marshal")["payload"]["findings"] == []


def test_finalize_judges_the_landed_key_from_origin_main_not_from_the_promotions_return_value(
    tmp_path: Path, monkeypatch
) -> None:
    """A promotion that RETURNS its key but whose ledger still does not read done (the return value
    says nothing about `origin/main`) is still a failed landing."""
    vcs = _StubVcs(ledger_text=_BACKLOG_LEDGER_64_1)
    _stub_finalize(monkeypatch, tmp_path, vcs, promote=lambda *a, **k: ("64-1-a-landing-s-ledger-promotion",))

    assert finalize_dispatch_land("pyforge-marshal", "64.1") == 1


def test_finalize_names_a_ledger_it_cannot_read(tmp_path: Path, monkeypatch) -> None:
    """AC 6: `origin/main`'s ledger unreadable after the promotion -> `MRS-DISP-051` naming the read failure."""
    _stub_finalize(monkeypatch, tmp_path, _StubVcs(read_raises=True))

    assert finalize_dispatch_land("pyforge-marshal", "64.1") == 1

    [finding] = _read_finalize_resync_entry(tmp_path, "pyforge-marshal")["payload"]["findings"]
    assert finding["code"] == "MRS-DISP-051"
    assert finding["severity"] == "error"
    assert "cannot read" in finding["message"]
    assert "bad object" in finding["message"]


def test_finalize_names_a_fetch_it_cannot_make(tmp_path: Path, monkeypatch) -> None:
    """I/O matrix 'origin/main unreadable: fetch or read fails' -- never a clean `landed`."""
    vcs = _StubVcs(fetch_raises=True)
    _stub_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land("pyforge-marshal", "64.1") == 1

    [finding] = _read_finalize_resync_entry(tmp_path, "pyforge-marshal")["payload"]["findings"]
    assert finding["code"] == "MRS-DISP-051"
    assert "could not read from remote" in finding["message"]
    assert vcs.read_calls == []


@pytest.mark.parametrize(
    ("ledger_text", "needle"),
    [
        (None, "does not exist"),
        ("development_status:\n  epic-64: in-progress\n  64-2-another-story: done\n", "has no row for story 64.1"),
        ("development_status:\n  64-1-a-landing-s-ledger-promotion: review\n", "reads 'review'"),
        ("", "has no row for story 64.1"),
    ],
)
def test_finalize_names_an_absent_ledger_an_absent_row_and_another_status(
    tmp_path: Path, monkeypatch, ledger_text, needle
) -> None:
    _stub_finalize(monkeypatch, tmp_path, _StubVcs(ledger_text=ledger_text))

    assert finalize_dispatch_land("pyforge-marshal", "64.1") == 1

    [finding] = _read_finalize_resync_entry(tmp_path, "pyforge-marshal")["payload"]["findings"]
    assert finding["code"] == "MRS-DISP-051"
    assert needle in finding["message"]


def test_the_64_1_replay_a_publish_timeout_inside_finalize_is_a_failed_landing(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC 4 + 5 end to end, with the REAL `_promote_sprint_ledger`: the publish is killed at the git timeout,
    `origin/main` still reads `backlog`. The promotion journals INTENT then OUTCOME `ok: false`; the resync
    observation carries `MRS-LAND-011` and `MRS-DISP-051`; finalize returns 1."""
    from pyforge.marshal.dispatch_land_finalize import __main__ as mod

    ledger = (
        tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "sprint-status-ledger.yaml"
    )
    ledger.parent.mkdir(parents=True)
    ledger.write_text(_BACKLOG_LEDGER_64_1, encoding="utf-8")

    class _TimingOutVcs(_StubVcs):
        def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message, preflight_skip_reason=None):
            raise VcsCommandError(
                f"git command timed out after 120.0s: git -C {repo_root} push origin abc:refs/heads/main"
            )

    vcs = _TimingOutVcs(ledger_text=_BACKLOG_LEDGER_64_1)
    monkeypatch.setattr(mod, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(mod, "GitVcs", lambda: vcs)
    monkeypatch.setattr(mod, "_scan_promotions", lambda *a, **k: _NoScan())
    monkeypatch.setattr(mod, "_resync_home_branch", lambda *a, **k: True)
    monkeypatch.setattr(mod, "_run_deferred_work_intake", lambda *a, **k: None)

    assert finalize_dispatch_land("pyforge-marshal", "64.1") == 1

    runs_dir = tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "implementation-artifacts" / "runs"
    [run_dir] = list(runs_dir.iterdir())
    entries = [
        json.loads(line) for line in (run_dir / "journal.jsonl").read_text(encoding="utf-8").splitlines() if line
    ]
    ledger_entries = [e for e in entries if e["kind"] == "land-sprint-ledger-promotion"]
    assert [e["phase"] for e in ledger_entries] == ["intent", "outcome"]
    assert ledger_entries[1]["payload"]["ok"] is False
    assert "timed out after 120.0s" in ledger_entries[1]["payload"]["error"]
    [observation] = [e for e in entries if e["kind"] == _FINALIZE_RESYNC_KIND]
    assert [f["code"] for f in observation["payload"]["findings"]] == ["MRS-LAND-011", "MRS-DISP-051"]
    assert "finding MRS-DISP-051" in capsys.readouterr().err


def test_the_resync_observation_carries_every_finding_of_every_severity(tmp_path: Path, monkeypatch) -> None:
    """Not only ERRORs: a WARN the run collected (here, the promotion's) is on the journal even though
    it never changes the exit code."""
    vcs = _StubVcs(ledger_text=_DONE_LEDGER_64_1)
    _stub_finalize(monkeypatch, tmp_path, vcs, promote=_promotion_warns)

    assert finalize_dispatch_land("pyforge-marshal", "64.1") == 0

    [finding] = _read_finalize_resync_entry(tmp_path, "pyforge-marshal")["payload"]["findings"]
    assert (finding["code"], finding["severity"]) == ("MRS-LAND-011", "warn")


# --- Story 79.1 (spec-pyforge-marshal CAP-229/CAP-277/CAP-233/CAP-261b) -------------------------
#
# Every automatic landing on 2026-09-30 promoted the tracked ledger twin and left the story's Tier-3
# feed row at `backlog`, so the next plain `sprint-ledger-sync` refused ("feed would un-finish")
# (DW-OPS-2026-10-01-1); a session that committed its tracked spec itself and left no Tier-3 twin got
# no spec promotion (DW-FU-53-2-4). These tests run finalize against a REAL feed file (and a real
# tracked-spec path) in `tmp_path`; only git is a fake -- and one whose `origin/main` history shows the
# landing's merge subject only AFTER `fetch`, as a real GitHub merge does.

_SLUG_79 = "pyforge-marshal"
_FEED_KEY_79 = "79-1-a-landing-promotes-the-feed-row"
_FEED_HEADER_79 = "generated: 2026-10-01T00:00:00Z\nproject: pyforge-marshal\n"
_FEED_BACKLOG_79 = (
    f"{_FEED_HEADER_79}development_status:\n  epic-79: in-progress\n  {_FEED_KEY_79}: backlog\n"
    "  79-2-another-story: backlog\n"
)
_FEED_DONE_79 = _FEED_BACKLOG_79.replace(f"{_FEED_KEY_79}: backlog", f"{_FEED_KEY_79}: done")
_DONE_LEDGER_79 = (
    f"development_status:\n  epic-79: in-progress\n  {_FEED_KEY_79}: done\n  79-2-another-story: backlog\n"
)
_BACKLOG_LEDGER_79 = _DONE_LEDGER_79.replace(f"{_FEED_KEY_79}: done", f"{_FEED_KEY_79}: backlog")
#: A `dispatch/<slug>/<key>` merge is trusted outright; a station-branch merge needs the spec `done` on origin/main.
_DISPATCH_MERGE_79 = "Merge pull request #1705 from rxm7706/dispatch/pyforge-marshal/79.1"
_STATION_BRANCH_MERGE_79 = "Merge pull request #1706 from rxm7706/marshal/79-1-a-landing-promotes-the-feed-row"
_STATION_BRANCH_MERGE_79_2 = "Merge pull request #1707 from rxm7706/marshal/79-2-another-story"
_SPEC_NAME_79 = "spec-79-1-a-landing-promotes-the-feed-row.md"
_SPEC_REL_79 = f"_bmad-output/projects/{_SLUG_79}/planning-artifacts/specs/{_SPEC_NAME_79}"
_TRACKED_SPEC_79 = (
    "---\ntitle: \"79.1: x\"\nstatus: 'backlog'\n---\n\n## Review Triage Log\n\n- No independent review has run yet.\n"
)
_FINALIZE_MOD_79 = "pyforge.marshal.dispatch_land_finalize.__main__"


def _feed_path_79(root: Path) -> Path:
    return root / "_bmad-output" / "projects" / _SLUG_79 / "implementation-artifacts" / "sprint-status.yaml"


def _write_feed_79(root: Path, text: str = _FEED_BACKLOG_79) -> Path:
    path = _feed_path_79(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_tracked_spec_79(root: Path, text: str = _TRACKED_SPEC_79, name: str = _SPEC_NAME_79) -> Path:
    path = root / "_bmad-output" / "projects" / _SLUG_79 / "planning-artifacts" / "specs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class _Plan79:
    to_promote: tuple = ()


class _PlannedScan:
    """A scan that HAS a plan, with nothing for the Tier-3 promotion to copy -- the shape a session that
    committed its tracked spec itself leaves -- and the merge subjects it read BEFORE finalize's fetch."""

    def __init__(self, subjects: tuple[str, ...] = ()) -> None:
        self.findings: list = []
        self.plan = _Plan79()
        self.combined_subjects = subjects
        self.template = "Merge {slug}/{key} into main"


class _PublishVcs(_StubVcs):
    """`_StubVcs` that answers the tracked-spec read separately from the ledger read, records (or refuses)
    the `commit_paths_onto_remote_tip` publishes, and models `origin/main`'s history as a real merge leaves
    it: BEFORE `fetch` it reads ``('base',)``, AFTER it ``merge_subjects`` on top of ``'base'``."""

    def __init__(
        self,
        *,
        spec_text: str | None = None,
        spec_read_raises: bool = False,
        publish_raises: bool = False,
        merge_subjects: tuple[str, ...] = (_DISPATCH_MERGE_79,),
        history_raises: bool = False,
        fail_fetch_from: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.fail_fetch_from = fail_fetch_from
        self.spec_text = spec_text
        self.spec_read_raises = spec_read_raises
        self.publish_raises = publish_raises
        self.merge_subjects = merge_subjects
        self.history_raises = history_raises
        self.fetched = False
        self.subject_reads: list[tuple[str, bool]] = []
        self.publishes: list[dict] = []

    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        super().fetch(repo_root, remote, ref)
        if self.fail_fetch_from is not None and len(self.fetch_calls) >= self.fail_fetch_from:
            raise VcsCommandError("git fetch origin refs/heads/main failed: could not read from remote")
        self.fetched = True

    def commit_subjects(self, _repo_root: Path, ref: str) -> tuple[str, ...]:
        self.subject_reads.append((ref, self.fetched))
        if self.history_raises and self.fetched:
            raise VcsCommandError(f"git log {ref} --format=%s failed: bad object")
        if ref == ORIGIN_MAIN and self.fetched:
            return (*self.merge_subjects, "base")
        return ("base",)

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str) -> str | None:
        if path.endswith("sprint-status-ledger.yaml"):
            return super().file_text_at_ref(repo_root, ref, path)
        self.read_calls.append((repo_root, ref, path))
        if self.spec_read_raises:
            raise VcsCommandError(f"git show {ref}:{path} failed: bad object")
        return self.spec_text

    def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message, preflight_skip_reason=None):
        if self.publish_raises:
            raise VcsCommandError("git push origin main failed: not a fast-forward")
        self.publishes.append(
            {
                "remote": remote,
                "ref": ref,
                "writes": writes,
                "message": message,
                "preflight_skip_reason": preflight_skip_reason,
            }
        )
        return "deadbeefdeadbeef"


def _stub_planned_finalize(
    monkeypatch, tmp_path: Path, vcs, scan_subjects: tuple[str, ...] = (), *, scan=None, fs=None
) -> None:
    """Finalize with a stubbed scan (a planned one over ``scan_subjects`` unless ``scan`` is given) and the
    ledger promotion stubbed to a converged no-op, so what moves is only what 79.1 adds; the feed, the
    tracked-spec path and the journal are real."""
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.repo_root", lambda: tmp_path)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.GitVcs", lambda: vcs)
    if fs is not None:
        monkeypatch.setattr(f"{_FINALIZE_MOD_79}.LocalFs", lambda: fs)
    monkeypatch.setattr(
        f"{_FINALIZE_MOD_79}._scan_promotions",
        lambda *a, **k: scan if scan is not None else _PlannedScan(scan_subjects),
    )
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._promote_sprint_ledger", lambda *a, **k: ())
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._resync_home_branch", lambda *a, **k: True)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._run_deferred_work_intake", lambda *a, **k: None)


def _stub_real_scan_finalize(monkeypatch, tmp_path: Path, vcs) -> None:
    """The same, but the REAL `_scan_promotions` runs (over ``vcs`` and the empty ``tmp_path`` tree), so the
    subjects the gate joins are the ones the production scan reads -- before the fetch."""
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.repo_root", lambda: tmp_path)
    monkeypatch.setattr("pyforge.marshal.cli.config.repo_root", lambda: tmp_path)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.GitVcs", lambda: vcs)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._promote_sprint_ledger", lambda *a, **k: ())
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._resync_home_branch", lambda *a, **k: True)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._run_deferred_work_intake", lambda *a, **k: None)


def _observation_79(tmp_path: Path) -> dict:
    return _read_finalize_resync_entry(tmp_path, _SLUG_79)["payload"]


def _journaled_findings_79(tmp_path: Path) -> list[dict]:
    return _observation_79(tmp_path)["findings"]


def _promotion_flags_79(tmp_path: Path) -> tuple[bool, bool, bool]:
    payload = _observation_79(tmp_path)
    return payload["landing_corroborated"], payload["feed_row_promoted"], payload["tracked_spec_promoted"]


# -- the Tier-3 feed row (AC 1-3) ----------------------------------------------------------------


def test_finalize_marks_the_landed_stories_tier3_feed_row_done(tmp_path: Path, monkeypatch) -> None:
    """AC 1: the twin reads `done` on origin/main, the feed row reads `backlog` -> the feed row reads `done`,
    every other byte of the feed is as it was, and nothing is left beside it (no temp file)."""
    feed = _write_feed_79(tmp_path)
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79))

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    assert sorted(entry.name for entry in feed.parent.iterdir() if entry.name != "runs") == ["sprint-status.yaml"]
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (True, True, False)


def test_a_plain_sprint_ledger_sync_reports_unchanged_once_the_feed_row_is_promoted(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC 1, second clause, through the sync's own entry point (`scripts/promote_sprint_status.py`, the module
    `marshal land` loads) over the tmp feed and the twin a landing leaves: the sync REFUSES before finalize
    (the incident, "feed would un-finish") and reports `unchanged` after it."""
    from pyforge.marshal.cli.land import _load_promote_sprint_status_module

    sync = _load_promote_sprint_status_module()
    assert sync is not None, "scripts/promote_sprint_status.py must load -- the AC is stated in its terms"
    monkeypatch.setattr(sync, "REPO_ROOT", tmp_path)
    feed = _write_feed_79(tmp_path)
    # The twin `_promote_sprint_ledger` writes: the sync's own render of the pre-landing feed, the landed key
    # advanced to done.
    feed_rel = f"_bmad-output/projects/{_SLUG_79}/implementation-artifacts/sprint-status.yaml"
    rendered = sync.render("marshal", feed_rel, sync._load_generate().parse_sprint_status(feed))
    twin_text, matched = render_ledger_advancements(rendered, frozenset({_FEED_KEY_79}))
    assert matched == {_FEED_KEY_79}
    twin = sync.ledger_path_for(_SLUG_79)
    twin.parent.mkdir(parents=True, exist_ok=True)
    twin.write_text(twin_text, encoding="utf-8")
    assert sync.main(["--project", "marshal"]) == 1
    before = capsys.readouterr().out
    assert "refused 1" in before and f"{_FEED_KEY_79} (done -> backlog)" in before

    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=twin_text))
    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0
    capsys.readouterr()

    assert sync.main(["--project", "marshal"]) == 0
    after = capsys.readouterr().out
    assert "wrote 0, unchanged 1, skipped 0, refused 0" in after
    assert twin.read_text(encoding="utf-8") == twin_text


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("backlog", "done"),
        ("in-progress", "done"),
        ("review", "done"),
        ("ready-for-dev", "done"),
        ("backlog  # waiting", "done  # waiting"),
        ("done", "done"),
        ("blocked", "blocked"),
        ("done  # shipped", "done  # shipped"),
        ("blocked  # waiting on the operator", "blocked  # waiting on the operator"),
    ],
)
def test_finalize_moves_only_a_feed_row_that_is_neither_done_nor_blocked(
    tmp_path: Path, monkeypatch, before: str, after: str
) -> None:
    """AC 1 + AC 2: any row short of `done` becomes `done`; a `done` or `blocked` row -- judged by its status
    TOKEN, so a trailing `# comment` does not hide it -- is left byte for byte, with no finding."""
    feed = _write_feed_79(tmp_path, _FEED_BACKLOG_79.replace(f"{_FEED_KEY_79}: backlog", f"{_FEED_KEY_79}: {before}"))
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79))

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79.replace(
        f"{_FEED_KEY_79}: backlog", f"{_FEED_KEY_79}: {after}"
    )
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (True, before != after, False)


def test_finalize_warns_and_creates_nothing_when_there_is_no_feed_file(tmp_path: Path, monkeypatch) -> None:
    """AC 3: no feed -> an `MRS-DISP-047` WARN naming the path, no file created, the landing still completes."""
    feed = _feed_path_79(tmp_path)
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79))

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert not feed.exists()
    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert str(feed) in finding["message"] and "no Tier-3 sprint feed" in finding["message"]
    assert _promotion_flags_79(tmp_path) == (True, False, False)


def test_finalize_warns_and_adds_no_row_when_the_feed_has_no_row_for_the_key(tmp_path: Path, monkeypatch) -> None:
    """AC 3: a feed with no row for the key -> WARN naming the path, the feed is not touched, no row is created."""
    original = f"{_FEED_HEADER_79}development_status:\n  epic-79: in-progress\n  79-2-another-story: backlog\n"
    feed = _write_feed_79(tmp_path, original)
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79))

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == original
    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert str(feed) in finding["message"] and "no row for story 79.1" in finding["message"]
    assert _promotion_flags_79(tmp_path) == (True, False, False)


@pytest.mark.parametrize("row", [f"  {_FEED_KEY_79} : backlog", f"\t{_FEED_KEY_79}: backlog"])
def test_finalize_warns_about_a_feed_row_the_rewrite_cannot_match(tmp_path: Path, monkeypatch, row: str) -> None:
    """The parser reads a row with a space before its colon, or a tab indent, that the line rewrite cannot
    match: the feed keeps its bytes and the WARN names the path and the row, never a silent skip."""
    original = f"{_FEED_HEADER_79}development_status:\n  epic-79: in-progress\n{row}\n"
    feed = _write_feed_79(tmp_path, original)
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79))

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == original
    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert str(feed) in finding["message"] and _FEED_KEY_79 in finding["message"]
    assert "could not be rewritten" in finding["message"]
    assert _promotion_flags_79(tmp_path) == (True, False, False)


def test_finalize_warns_when_the_key_also_sits_outside_the_development_status_block(
    tmp_path: Path, monkeypatch
) -> None:
    """`render_ledger_advancements` rewrites the FIRST line carrying the key, wherever it is: here a `notes:`
    line, which would take the rewrite and leave the real row at `backlog` with no finding. The rewritten
    text is re-parsed with the sync's own parser and judged -- the feed keeps its bytes, one WARN."""
    original = (
        f"{_FEED_HEADER_79}notes:\n  {_FEED_KEY_79}: see the thread\n"
        f"development_status:\n  epic-79: in-progress\n  {_FEED_KEY_79}: backlog\n"
    )
    feed = _write_feed_79(tmp_path, original)
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79))

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == original
    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert str(feed) in finding["message"] and "outside the development_status block" in finding["message"]
    assert _promotion_flags_79(tmp_path) == (True, False, False)


def test_finalize_warns_when_the_feed_cannot_be_written_and_still_completes(tmp_path: Path, monkeypatch) -> None:
    """An unwritable feed is a WARN naming the path, never a crash: the feed keeps its bytes, exit 0."""

    class _UnwritableFeedFs(LocalFs):
        def write_text_atomic(self, path: Path, content: str) -> None:
            if path.name == "sprint-status.yaml":
                raise FsError(f"cannot write {path}: Permission denied")
            super().write_text_atomic(path, content)

    feed = _write_feed_79(tmp_path)
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79), fs=_UnwritableFeedFs())

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79
    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert str(feed) in finding["message"] and "Permission denied" in finding["message"]
    assert _promotion_flags_79(tmp_path) == (True, False, False)


def test_finalize_warns_when_the_feed_cannot_be_read_and_still_completes(tmp_path: Path, monkeypatch) -> None:
    class _UnreadableFeedFs(LocalFs):
        def read_text(self, path: Path) -> str | None:
            if path.name == "sprint-status.yaml":
                raise FsError(f"cannot read {path}: Is a directory")
            return super().read_text(path)

    _write_feed_79(tmp_path)
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79), fs=_UnreadableFeedFs())

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert "cannot read the Tier-3 sprint feed" in finding["message"]


def test_a_rerun_repairs_a_feed_an_earlier_run_left_behind(tmp_path: Path, monkeypatch) -> None:
    """The gate reads `origin/main`'s ledger, not the promotion's return value (empty for a converged twin as
    well as for a failed publish) -- so a second finalize over an already-`done` twin still fixes the feed,
    and a third finds nothing left to promote."""
    feed = _write_feed_79(tmp_path)
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79))

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0
    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    feed.write_text(_FEED_BACKLOG_79, encoding="utf-8")  # an earlier run left it behind
    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0
    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79


def test_finalize_writes_the_feed_after_the_real_ledger_promotion_not_before(tmp_path: Path, monkeypatch) -> None:
    """End to end with the REAL `_promote_sprint_ledger`: the promotion reads the feed (still `backlog`) and
    publishes the advanced twin; only then does the feed row move to `done`."""
    feed = _write_feed_79(tmp_path)
    twin = tmp_path / "_bmad-output" / "projects" / _SLUG_79 / "planning-artifacts" / "sprint-status-ledger.yaml"
    twin.parent.mkdir(parents=True)
    twin.write_text(_BACKLOG_LEDGER_79, encoding="utf-8")
    feed_when_the_twin_was_published: list[str] = []

    class _OrderedVcs(_PublishVcs):
        def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message, preflight_skip_reason=None):
            feed_when_the_twin_was_published.append(feed.read_text(encoding="utf-8"))
            self.ledger_text = writes[0][1]  # what origin/main now reads
            return super().commit_paths_onto_remote_tip(
                repo_root,
                remote=remote,
                ref=ref,
                writes=writes,
                message=message,
                preflight_skip_reason=preflight_skip_reason,
            )

    vcs = _OrderedVcs(ledger_text=_BACKLOG_LEDGER_79)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.repo_root", lambda: tmp_path)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.GitVcs", lambda: vcs)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._scan_promotions", lambda *a, **k: _PlannedScan())
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._resync_home_branch", lambda *a, **k: True)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._run_deferred_work_intake", lambda *a, **k: None)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed_when_the_twin_was_published == [_FEED_BACKLOG_79]
    assert f"{_FEED_KEY_79}: done" in vcs.ledger_text
    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79


# -- the tracked spec (AC 4) ---------------------------------------------------------------------


def test_finalize_promotes_a_tracked_spec_the_session_committed_itself(tmp_path: Path, monkeypatch) -> None:
    """AC 4: corroborated, the tracked spec reads `status: backlog` on origin/main, no Tier-3 twin exists ->
    the spec reads `done` in the one publish onto origin/main; only the status token moves; the operator
    checkout's own copy is not written (CAP-233)."""
    local_spec = _write_tracked_spec_79(tmp_path)
    _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [publish] = vcs.publishes
    assert (publish["remote"], publish["ref"]) == ("origin", "main")
    assert publish["writes"] == ((_SPEC_REL_79, _TRACKED_SPEC_79.replace("status: 'backlog'", "status: 'done'")),)
    assert "79.1" in publish["message"] and "tracked spec" in publish["message"]
    assert "79.1" in publish["preflight_skip_reason"]
    assert (tmp_path, ORIGIN_MAIN, _SPEC_REL_79) in vcs.read_calls
    assert local_spec.read_text(encoding="utf-8") == _TRACKED_SPEC_79
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (True, True, True)


@pytest.mark.parametrize("status", sorted(PRE_DONE_SPEC_STATUSES))
def test_finalize_promotes_a_tracked_spec_at_every_pre_done_status(tmp_path: Path, monkeypatch, status: str) -> None:
    _write_tracked_spec_79(tmp_path)
    _write_feed_79(tmp_path)
    vcs = _PublishVcs(
        ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79.replace("status: 'backlog'", f"status: '{status}'")
    )
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [publish] = vcs.publishes
    assert publish["writes"] == ((_SPEC_REL_79, _TRACKED_SPEC_79.replace("status: 'backlog'", "status: 'done'")),)
    assert _promotion_flags_79(tmp_path) == (True, True, True)


@pytest.mark.parametrize("status", sorted(TERMINAL_SPEC_STATUSES))
def test_finalize_leaves_a_terminal_tracked_spec_untouched(tmp_path: Path, monkeypatch, status: str) -> None:
    _write_tracked_spec_79(tmp_path)
    _write_feed_79(tmp_path)
    vcs = _PublishVcs(
        ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79.replace("status: 'backlog'", f"status: '{status}'")
    )
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert vcs.publishes == []
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (True, True, False)


def test_finalize_is_silent_when_the_story_has_no_tracked_spec(tmp_path: Path, monkeypatch) -> None:
    """No spec resolves under `root` (and no worktree is given) -> nothing to promote, no finding, no git read for it."""
    _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert vcs.publishes == []
    assert all(path.endswith("sprint-status-ledger.yaml") for _root, _ref, path in vcs.read_calls)
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (True, True, False)


def test_finalize_is_silent_when_neither_the_primary_nor_the_worktree_holds_the_spec(
    tmp_path: Path, monkeypatch
) -> None:
    _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1", worktree=tmp_path / "no-such-worktree") == 0

    assert vcs.publishes == []
    assert _journaled_findings_79(tmp_path) == []


def test_finalize_resolves_the_tracked_spec_through_the_dispatch_worktree(tmp_path: Path, monkeypatch) -> None:
    """The primary's local tree may not hold a spec the merged PR added (the resync runs after) -- the
    worktree's copy names the path, and the read is still `origin/main`'s."""
    primary, worktree = tmp_path / "primary", tmp_path / "worktree"
    primary.mkdir()
    _write_tracked_spec_79(worktree)
    _write_feed_79(primary)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79)
    _stub_planned_finalize(monkeypatch, primary, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1", worktree=worktree) == 0

    [publish] = vcs.publishes
    assert [path for path, _text in publish["writes"]] == [_SPEC_REL_79]
    assert (primary, ORIGIN_MAIN, _SPEC_REL_79) in vcs.read_calls


def test_finalize_warns_when_the_tracked_spec_publish_fails_and_still_completes(tmp_path: Path, monkeypatch) -> None:
    _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79, publish_raises=True)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert _SPEC_REL_79 in finding["message"] and "not a fast-forward" in finding["message"]
    # an independent step: the feed row still moved
    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    assert _promotion_flags_79(tmp_path) == (True, True, False)


@pytest.mark.parametrize(
    ("vcs_kwargs", "needle"),
    [
        ({"spec_read_raises": True}, "cannot read"),
        ({"spec_text": None}, "does not exist at origin/main"),
        ({"spec_text": "---\ntitle: 'x'\nstatus: 'backlog' # a template comment\n---\n"}, "could not be read"),
        ({"spec_text": "no frontmatter at all\n"}, "could not be read"),
        ({"spec_text": "---\nstatus: shipped\n---\n"}, "'shipped' is not one a landing advances"),
    ],
)
def test_finalize_warns_naming_the_path_when_it_cannot_promote_a_tracked_spec(
    tmp_path: Path, monkeypatch, vcs_kwargs: dict, needle: str
) -> None:
    """The spec resolves locally but `origin/main` cannot give a status a landing may advance: a read that
    raises, a spec absent there, a commented or absent status (the reader rejects `status: 'x' # note`) and a
    status that is neither pre-done nor terminal are each an `MRS-DISP-047` WARN naming the path -- nothing is
    published, the landing still exits 0 and the feed row is unaffected."""
    _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, **vcs_kwargs)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert _SPEC_REL_79 in finding["message"] and needle in finding["message"]
    assert finding["path"] == _SPEC_REL_79
    assert vcs.publishes == []
    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    assert _promotion_flags_79(tmp_path) == (True, True, False)


class _Tier3Vcs(_PublishVcs):
    """`_PublishVcs` for a landing whose merge subject local `main` ALREADY holds when the scan reads (so the
    Tier-3 route finds the key durable), recording the executor's local `commit_paths`."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.local_commits: list[tuple[tuple[Path, ...], str]] = []

    def commit_subjects(self, _repo_root: Path, ref: str) -> tuple[str, ...]:
        return (_DISPATCH_MERGE_79, "base")

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: str) -> str:
        self.local_commits.append((tuple(paths), message))
        return "cafebabecafebabe"


def test_a_key_the_tier3_route_promoted_this_run_is_not_promoted_again_as_a_tracked_spec(
    tmp_path: Path, monkeypatch
) -> None:
    """AC 4 is for a session that left NO Tier-3 twin. Here one exists: the REAL `_execute_promotion_plan`
    copies it into the primary's `specs/` and commits it locally, so the tracked-spec path now resolves while
    `origin/main` does not hold the copy yet. That route owns the spec: no "absent at origin/main" WARN, no
    read of the spec at origin/main, no second status-only publish."""
    twin = tmp_path / "_bmad-output" / "projects" / _SLUG_79 / "implementation-artifacts" / _SPEC_NAME_79
    twin.parent.mkdir(parents=True)
    twin.write_text(_TRACKED_SPEC_79.replace("'backlog'", "'done'"), encoding="utf-8")
    feed = _write_feed_79(tmp_path)
    vcs = _Tier3Vcs(ledger_text=_DONE_LEDGER_79, spec_text=None)
    _stub_real_scan_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    copied = tmp_path / _SPEC_REL_79
    assert copied.read_text(encoding="utf-8") == twin.read_text(encoding="utf-8")
    [(targets, _message)] = vcs.local_commits
    assert targets == (copied,)
    assert [path for _root, _ref, path in vcs.read_calls if path == _SPEC_REL_79] == []
    assert vcs.publishes == []
    assert _journaled_findings_79(tmp_path) == []
    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    assert _promotion_flags_79(tmp_path) == (True, True, False)


# -- the gate (AC 5): fed FRESH evidence --------------------------------------------------------


def test_the_gate_opens_on_the_real_scan_because_it_rereads_origin_main_after_the_fetch(
    tmp_path: Path, monkeypatch
) -> None:
    """The defect behind review pass 1: `_scan_promotions` reads its merge subjects BEFORE finalize's first
    fetch, and right after a GitHub merge neither `origin/main` nor local `main` holds the landing's subject.
    With the REAL scan and the REAL `corroborated_merged_story_keys`, over a git fake that shows the merge
    subject only after `fetch`, the feed row and the tracked spec still move -- the gate read the history
    again once the fetch had run."""
    _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79)
    _stub_real_scan_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert vcs.subject_reads == [(ORIGIN_MAIN, False), ("refs/heads/main", False), (ORIGIN_MAIN, True)]
    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    [publish] = vcs.publishes
    assert [path for path, _text in publish["writes"]] == [_SPEC_REL_79]
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (True, True, True)


def test_the_gate_stays_shut_when_the_history_it_reads_never_shows_the_merge(tmp_path: Path, monkeypatch) -> None:
    """The same real scan over a fake whose history never shows the merge subject (before or after the fetch):
    nothing moves, no finding -- the journal says why (`landing_corroborated` false)."""
    local_spec = _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79, merge_subjects=())
    _stub_real_scan_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79
    assert local_spec.read_text(encoding="utf-8") == _TRACKED_SPEC_79
    assert vcs.publishes == []
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (False, False, False)


def test_the_gate_fetches_origin_main_for_itself_instead_of_leaning_on_the_readback(
    tmp_path: Path, monkeypatch
) -> None:
    """The gate must not depend on `_landed_key_not_done_finding` happening to fetch: with that readback
    stubbed out (nothing before the gate fetches), the real scan's pre-fetch evidence alone would not
    corroborate the landing -- and the gate still opens, because it fetched `origin/main` itself and read the
    history after that."""
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79)
    _stub_real_scan_finalize(monkeypatch, tmp_path, vcs)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._landed_key_not_done_finding", lambda *a, **k: None)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert vcs.fetch_calls == [(tmp_path, "origin", "main")]  # the gate's own, and the only one
    assert vcs.subject_reads[-1] == (ORIGIN_MAIN, True)
    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    assert _promotion_flags_79(tmp_path) == (True, True, False)


def test_a_gate_fetch_that_fails_is_a_warn_naming_the_ref_and_nothing_moves(tmp_path: Path, monkeypatch) -> None:
    """The readback's fetch (the first) succeeds and `origin/main` reads `done`; the gate's own fetch (the
    second) fails -> an `MRS-DISP-047` WARN naming the ref, no history read, nothing moves, exit 0."""
    _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79, fail_fetch_from=2)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert len(vcs.fetch_calls) == 2
    assert vcs.subject_reads == []
    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert "cannot fetch" in finding["message"] and ORIGIN_MAIN in finding["message"]
    assert "could not read from remote" in finding["message"]
    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79
    assert vcs.publishes == []
    assert _promotion_flags_79(tmp_path) == (False, False, False)


def test_the_scans_own_subjects_still_count_beside_the_fresh_history(tmp_path: Path, monkeypatch) -> None:
    """The gate JOINS the fresh read with the scan's subjects rather than replacing them: a merge subject only
    the scan holds (here, local `main` already pulled) corroborates the landing too."""
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, merge_subjects=())
    _stub_planned_finalize(monkeypatch, tmp_path, vcs, scan_subjects=(_DISPATCH_MERGE_79,))

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    assert _promotion_flags_79(tmp_path)[0] is True


def test_an_uncorroborated_landing_moves_neither_the_feed_row_nor_the_tracked_spec(tmp_path: Path, monkeypatch) -> None:
    """AC 5, no merge evidence at all."""
    local_spec = _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79, merge_subjects=())
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79
    assert local_spec.read_text(encoding="utf-8") == _TRACKED_SPEC_79
    assert vcs.publishes == []
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (False, False, False)


def test_a_station_branch_merge_with_a_not_done_spec_is_not_a_landing(tmp_path: Path, monkeypatch) -> None:
    """AC 5, the CAP-255 case: a mint/fallout/fix PR merges the story's branch with its spec still at `backlog`
    on origin/main. The same gate the Tier-3 promotion uses refuses it, so nothing moves."""
    _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(
        ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79, merge_subjects=(_STATION_BRANCH_MERGE_79,)
    )
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79
    assert vcs.publishes == []
    assert _promotion_flags_79(tmp_path) == (False, False, False)


def test_a_station_branch_merge_whose_spec_cannot_be_read_is_not_a_landing(tmp_path: Path, monkeypatch) -> None:
    """The spec-status read in the gate fails closed on a git error -- never a crash, never a landing."""
    _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_read_raises=True, merge_subjects=(_STATION_BRANCH_MERGE_79,))
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79
    assert vcs.publishes == []
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (False, False, False)


def test_a_station_branch_merge_with_a_done_spec_is_a_landing_and_only_its_own_key_is_read(
    tmp_path: Path, monkeypatch
) -> None:
    """The positive CAP-255 case: the spec reads `done` on origin/main, so the station-branch merge counts.
    The history also holds ANOTHER story's station-branch merge; the gate reads only the landed key's spec."""
    _write_tracked_spec_79(tmp_path, _TRACKED_SPEC_79.replace("'backlog'", "'done'"))
    _write_tracked_spec_79(tmp_path, _TRACKED_SPEC_79.replace("79.1", "79.2"), "spec-79-2-another-story.md")
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(
        ledger_text=_DONE_LEDGER_79,
        spec_text=_TRACKED_SPEC_79.replace("'backlog'", "'done'"),
        merge_subjects=(_STATION_BRANCH_MERGE_79_2, _STATION_BRANCH_MERGE_79),
    )
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    assert [path for _root, _ref, path in vcs.read_calls if "79-2-another-story.md" in path] == []
    assert vcs.publishes == []  # the spec already reads done: nothing to publish
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (True, True, False)


def test_an_unreadable_origin_main_history_is_a_warn_naming_the_ref_and_nothing_moves(
    tmp_path: Path, monkeypatch
) -> None:
    _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79, history_raises=True)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert "origin/main" in finding["message"] and ORIGIN_MAIN in finding["message"]
    assert "bad object" in finding["message"]
    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79
    assert vcs.publishes == []
    assert _promotion_flags_79(tmp_path) == (False, False, False)


def test_a_scan_with_no_plan_fails_closed_without_a_finding(tmp_path: Path, monkeypatch) -> None:
    """`MRS-DEPLOY-003` (local main unreadable): nothing is corroborated, so nothing moves and 79.1 adds no WARN."""
    _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs, scan=_NoScan())

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79
    assert vcs.publishes == []
    assert vcs.subject_reads == []
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (False, False, False)


def test_nothing_moves_while_origin_mains_ledger_does_not_read_the_key_done(tmp_path: Path, monkeypatch) -> None:
    """The feed and the spec follow a twin that reached `done` on origin/main -- never run ahead of it. A
    corroborated landing whose promotion failed is still `MRS-DISP-051` and exit 1, with the feed as it was."""
    _write_tracked_spec_79(tmp_path)
    feed = _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_BACKLOG_LEDGER_79, spec_text=_TRACKED_SPEC_79)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 1

    assert feed.read_text(encoding="utf-8") == _FEED_BACKLOG_79
    assert vcs.publishes == []
    assert [f["code"] for f in _journaled_findings_79(tmp_path)] == ["MRS-DISP-051"]
    assert _promotion_flags_79(tmp_path) == (False, False, False)
