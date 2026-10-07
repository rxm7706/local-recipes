"""dispatch_land_finalize must pass CAP-5 ``base=`` into ledger promote."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.cli.deploy import _scan_promotions
from pyforge.marshal.core.egress import Redacted
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.journal import Phase
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.promotion import PRE_DONE_SPEC_STATUSES, TERMINAL_SPEC_STATUSES
from pyforge.marshal.core.refs import ORIGIN_MAIN
from pyforge.marshal.core.status import render_ledger_advancements
from pyforge.marshal.dispatch_land_finalize.__main__ import (
    _FINALIZE_RESYNC_KIND,
    _landing_corroboration,
    _promote_tracked_spec,
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
                "remote": remote.value,
                "ref": ref.value,
                "writes": writes,
                "message": message.text,
                "preflight_skip_reason": (preflight_skip_reason.text if preflight_skip_reason is not None else None),
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

    def _fake_intake(process, fs, vcs, root, project_slug, story_key, **_kwargs):
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

    def _fake_intake(process, fs, vcs, root, project_slug, story_key, **_kwargs):
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

    def _fake_intake(process, fs, vcs, root, project_slug, story_key, **_kwargs):
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
        lambda process, fs, vcs, root, project_slug, story_key, **_kwargs: None,
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
_EPICS_REL_79 = f"_bmad-output/projects/{_SLUG_79}/planning-artifacts/epics.md"
_EPICS_79 = "### Story 79.1: x\n\n**Status:** backlog\n\n### Story 79.2: y\n\n**Status:** backlog\n"
# Default fake origin epics: the landed story's section carries no **Status:** line (Story 22.13 no-op).
_DEFAULT_FAKE_EPICS_79 = "### Story 79.1: x\n\nSection without a status line.\n"
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
        epics_text: str | None = _DEFAULT_FAKE_EPICS_79,
        spec_read_raises: bool = False,
        epics_read_raises: bool = False,
        publish_raises: bool = False,
        merge_subjects: tuple[str, ...] = (_DISPATCH_MERGE_79,),
        history_raises: bool = False,
        fail_fetch_from: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.fail_fetch_from = fail_fetch_from
        self.spec_text = spec_text
        self.epics_text = epics_text
        self.spec_read_raises = spec_read_raises
        self.epics_read_raises = epics_read_raises
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
        if path.endswith("planning-artifacts/epics.md") and self.epics_read_raises:
            raise VcsCommandError(f"git show {ref}:{path} failed: bad object")
        if self.spec_read_raises and not path.endswith("planning-artifacts/epics.md"):
            raise VcsCommandError(f"git show {ref}:{path} failed: bad object")
        if path.endswith("planning-artifacts/epics.md"):
            return self.epics_text
        return self.spec_text

    def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message, preflight_skip_reason=None):
        if self.publish_raises:
            raise VcsCommandError("git push origin main failed: not a fast-forward")
        self.publishes.append(
            {
                "remote": remote.value,
                "ref": ref.value,
                "writes": writes,
                "message": message.text,
                "preflight_skip_reason": (preflight_skip_reason.text if preflight_skip_reason is not None else None),
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


def test_finalize_advances_the_development_status_row_when_the_key_also_appears_outside_the_block(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 83.22: ``render_ledger_status_rewrites`` limits itself to ``development_status:``, so a decoy
    ``notes:`` line carrying the same key is untouched and the real row reaches ``done``."""
    original = (
        f"{_FEED_HEADER_79}notes:\n  {_FEED_KEY_79}: see the thread\n"
        f"development_status:\n  epic-79: in-progress\n  {_FEED_KEY_79}: backlog\n"
    )
    feed = _write_feed_79(tmp_path, original)
    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=_DONE_LEDGER_79))

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    updated = feed.read_text(encoding="utf-8")
    assert f"{_FEED_KEY_79}: see the thread" in updated
    assert f"  {_FEED_KEY_79}: done\n" in updated
    assert not _journaled_findings_79(tmp_path)
    assert _promotion_flags_79(tmp_path) == (True, True, False)


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
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79, epics_text=_EPICS_79)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [publish] = vcs.publishes
    assert (publish["remote"], publish["ref"]) == ("origin", "main")
    assert publish["writes"] == (
        (_SPEC_REL_79, _TRACKED_SPEC_79.replace("status: 'backlog'", "status: 'done'")),
        (
            _EPICS_REL_79,
            _EPICS_79.replace("### Story 79.1: x\n\n**Status:** backlog", "### Story 79.1: x\n\n**Status:** done"),
        ),
    )
    assert "79.1" in publish["message"] and "tracked spec" in publish["message"]
    assert "79.1" in publish["preflight_skip_reason"]
    assert (tmp_path, ORIGIN_MAIN, _SPEC_REL_79) in vcs.read_calls
    assert local_spec.read_text(encoding="utf-8") == _TRACKED_SPEC_79
    assert _journaled_findings_79(tmp_path) == []
    assert _promotion_flags_79(tmp_path) == (True, True, True)


def test_finalize_leaves_epics_out_of_the_publish_when_the_story_section_has_no_status_line(
    tmp_path: Path, monkeypatch
) -> None:
    _write_tracked_spec_79(tmp_path)
    _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79, epics_text=_DEFAULT_FAKE_EPICS_79)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [publish] = vcs.publishes
    assert publish["writes"] == ((_SPEC_REL_79, _TRACKED_SPEC_79.replace("status: 'backlog'", "status: 'done'")),)
    assert _journaled_findings_79(tmp_path) == []


def test_finalize_warns_when_epics_is_missing_but_still_publishes_the_spec(tmp_path: Path, monkeypatch) -> None:
    _write_tracked_spec_79(tmp_path)
    _write_feed_79(tmp_path)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=_TRACKED_SPEC_79, epics_text=None)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [publish] = vcs.publishes
    assert publish["writes"] == ((_SPEC_REL_79, _TRACKED_SPEC_79.replace("status: 'backlog'", "status: 'done'")),)
    [finding] = _journaled_findings_79(tmp_path)
    assert finding["code"] == "MRS-DISP-047" and "epics.md" in finding["message"]
    assert _promotion_flags_79(tmp_path) == (True, True, True)


def test_finalize_warns_when_epics_has_no_story_heading(tmp_path: Path, monkeypatch) -> None:
    _write_tracked_spec_79(tmp_path)
    _write_feed_79(tmp_path)
    vcs = _PublishVcs(
        ledger_text=_DONE_LEDGER_79,
        spec_text=_TRACKED_SPEC_79,
        epics_text="### Story 79.2: only other story\n\n**Status:** backlog\n",
    )
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert "no ### Story 79.1:" in finding["message"]


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


@pytest.mark.parametrize("status", ("blocked", "superseded"))
def test_finalize_leaves_a_blocked_or_superseded_tracked_spec_untouched(tmp_path: Path, monkeypatch, status: str) -> None:
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


def test_finalize_publishes_only_epics_when_the_tracked_spec_already_reads_done(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 22.15: spec ``done`` at origin/main, epics **Status:** still backlog -> one epics-only publish."""
    _write_tracked_spec_79(tmp_path)
    _write_feed_79(tmp_path)
    done_spec = _TRACKED_SPEC_79.replace("status: 'backlog'", "status: 'done'")
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=done_spec, epics_text=_EPICS_79)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [publish] = vcs.publishes
    assert publish["writes"] == (
        (
            _EPICS_REL_79,
            _EPICS_79.replace("### Story 79.1: x\n\n**Status:** backlog", "### Story 79.1: x\n\n**Status:** done"),
        ),
    )
    assert "epics status" in publish["message"]
    assert _promotion_flags_79(tmp_path) == (True, True, True)


def test_finalize_leaves_epics_untouched_when_the_tracked_spec_already_reads_done_and_the_line_matches(
    tmp_path: Path, monkeypatch
) -> None:
    _write_tracked_spec_79(tmp_path)
    _write_feed_79(tmp_path)
    done_spec = _TRACKED_SPEC_79.replace("status: 'backlog'", "status: 'done'")
    epics_done = _EPICS_79.replace("**Status:** backlog", "**Status:** done", 1)
    vcs = _PublishVcs(ledger_text=_DONE_LEDGER_79, spec_text=done_spec, epics_text=epics_done)
    _stub_planned_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    assert vcs.publishes == []
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

    # Story 66.1: the follow-up carry reads the same spec and warns about a failed read in its own words;
    # this test is about the promotion's finding.
    [finding] = [f for f in _journaled_findings_79(tmp_path) if "follow-up review" not in f["message"]]
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

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: Redacted) -> str:
        self.local_commits.append((tuple(paths), message.text))
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
    # Story 83.20: the Tier-3 twin is promoted only because its full key is a row of the primary's ledger.
    ledger = tmp_path / "_bmad-output" / "projects" / _SLUG_79 / "planning-artifacts" / "sprint-status-ledger.yaml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(_DONE_LEDGER_79, encoding="utf-8")
    feed = _write_feed_79(tmp_path)
    vcs = _Tier3Vcs(ledger_text=_DONE_LEDGER_79, spec_text=None)
    _stub_real_scan_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    copied = tmp_path / _SPEC_REL_79
    assert copied.read_text(encoding="utf-8") == twin.read_text(encoding="utf-8")
    [(targets, _message)] = vcs.local_commits
    assert targets == (copied,)
    # No tracked-spec publish; Story 66.1's follow-up carry and Story 22.15's epics gate may read the spec
    # at origin/main (absent here) without promoting it.
    spec_reads = [path for _root, _ref, path in vcs.read_calls if path == _SPEC_REL_79]
    assert spec_reads == [_SPEC_REL_79, _SPEC_REL_79]
    assert vcs.publishes == []
    assert _journaled_findings_79(tmp_path) == []
    assert feed.read_text(encoding="utf-8") == _FEED_DONE_79
    assert _promotion_flags_79(tmp_path) == (True, True, False)


def test_finalize_publishes_epics_for_a_tier3_promoted_key_when_the_line_is_still_backlog(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 22.15: Tier-3 owns the spec copy; epics still matches on ``origin/main``."""
    twin = tmp_path / "_bmad-output" / "projects" / _SLUG_79 / "implementation-artifacts" / _SPEC_NAME_79
    twin.parent.mkdir(parents=True)
    twin.write_text(_TRACKED_SPEC_79.replace("'backlog'", "'done'"), encoding="utf-8")
    ledger = tmp_path / "_bmad-output" / "projects" / _SLUG_79 / "planning-artifacts" / "sprint-status-ledger.yaml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(_DONE_LEDGER_79, encoding="utf-8")
    feed = _write_feed_79(tmp_path)
    vcs = _Tier3Vcs(ledger_text=_DONE_LEDGER_79, spec_text=None, epics_text=_EPICS_79)
    _stub_real_scan_finalize(monkeypatch, tmp_path, vcs)

    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0

    [publish] = vcs.publishes
    assert publish["writes"] == (
        (
            _EPICS_REL_79,
            _EPICS_79.replace("### Story 79.1: x\n\n**Status:** backlog", "### Story 79.1: x\n\n**Status:** done"),
        ),
    )
    assert _promotion_flags_79(tmp_path) == (True, True, True)


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
    # The gate itself stays silent; the only finding is Story 66.1's follow-up carry failing the same read.
    [finding] = _journaled_findings_79(tmp_path)
    assert finding["code"] == "MRS-DISP-047" and "follow-up review" in finding["message"]
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


# -- real git: the stale scan, the gate's own fetch, and the spec publish through the real adapter ---------


def _git_79(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout


def _configure_git_79(repo: Path) -> None:
    _git_79(repo, "config", "user.email", "test@example.com")
    _git_79(repo, "config", "user.name", "Test")
    _git_79(repo, "config", "commit.gpgsign", "false")
    _git_79(repo, "config", "core.hooksPath", "/dev/null")  # never the machine's own pre-push hook


def test_against_real_git_a_stale_scan_is_corroborated_after_the_gates_own_fetch_and_the_spec_is_published(
    tmp_path: Path, monkeypatch
) -> None:
    """The stale-scan defect and the spec publish against REAL git, not a model of it: a bare `origin`, the
    primary clone, and a second clone that "merges" the landing (adds the story's tracked spec at
    `status: 'backlog'` under `planning-artifacts/specs/`, with a `dispatch/` merge subject, and pushes) while
    the primary has not fetched. The real scan cannot see the merge; the gate fetches itself and does; the
    publish goes through the real `commit_paths_onto_remote_tip` (so its planning-artifacts-only proof runs
    against the path `story_spec_rel_path` yields) and `origin/main`'s spec reads `done`, the primary's
    working tree and branch untouched."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git_79(origin, "init", "--bare", "-b", "main")
    primary = tmp_path / "primary"
    primary.mkdir()
    _git_79(primary, "init", "-b", "main")
    _configure_git_79(primary)
    (primary / "README.md").write_text("hello\n", encoding="utf-8")
    _git_79(primary, "add", "README.md")
    _git_79(primary, "commit", "-m", "base")
    _git_79(primary, "remote", "add", "origin", str(origin))
    _git_79(primary, "push", "-u", "origin", "main")

    landing = tmp_path / "landing"
    _git_79(tmp_path, "clone", str(origin), str(landing))
    _configure_git_79(landing)
    landed_spec = landing / _SPEC_REL_79
    landed_spec.parent.mkdir(parents=True)
    landed_spec.write_text(_TRACKED_SPEC_79, encoding="utf-8")
    landed_epics = landing / _EPICS_REL_79
    landed_epics.parent.mkdir(parents=True, exist_ok=True)
    landed_epics.write_text(_DEFAULT_FAKE_EPICS_79, encoding="utf-8")
    _git_79(landing, "add", _SPEC_REL_79, _EPICS_REL_79)
    _git_79(landing, "commit", "-m", _DISPATCH_MERGE_79)
    landing_sha = _git_79(landing, "rev-parse", "HEAD").strip()
    _git_79(landing, "push", "origin", "main")

    # The dispatch worktree holds the spec the merged PR added; the primary's own tree does not (yet).
    worktree = tmp_path / "dispatch-worktree"
    (worktree / _SPEC_REL_79).parent.mkdir(parents=True)
    (worktree / _SPEC_REL_79).write_text(_TRACKED_SPEC_79, encoding="utf-8")

    monkeypatch.setattr("pyforge.marshal.cli.config.repo_root", lambda: primary)
    vcs = GitVcs()
    head_before = _git_79(primary, "rev-parse", "HEAD").strip()
    scan = _scan_promotions(primary, _SLUG_79, vcs=vcs, fs=LocalFs())
    assert scan.plan is not None
    assert _DISPATCH_MERGE_79 not in scan.combined_subjects  # the defect: the scan ran before any fetch
    key = normalize("79.1")

    corroborated, finding = _landing_corroboration(vcs, primary, _SLUG_79, key, scan)

    assert (corroborated, finding) == (True, None)
    assert _git_79(primary, "rev-parse", "refs/remotes/origin/main").strip() == landing_sha

    promoted, finding = _promote_tracked_spec(vcs, primary, _SLUG_79, key, worktree)

    assert (promoted, finding) == (True, None)
    assert _git_79(origin, "show", f"main:{_SPEC_REL_79}") == _TRACKED_SPEC_79.replace("'backlog'", "'done'")
    assert _git_79(origin, "rev-parse", "main~1").strip() == landing_sha
    assert _git_79(origin, "diff", "--name-only", "main~1", "main").split() == [_SPEC_REL_79]
    assert _git_79(origin, "log", "-1", "--format=%s", "main").strip() == (
        "marshal: promote story 79.1's tracked spec to done"
    )
    # CAP-233: the operator checkout is untouched -- same HEAD and branch, clean tree, no spec, no leaked worktree.
    assert _git_79(primary, "rev-parse", "HEAD").strip() == head_before
    assert _git_79(primary, "branch", "--show-current").strip() == "main"
    assert _git_79(primary, "status", "--porcelain") == ""
    assert not (primary / _SPEC_REL_79).exists()
    assert _git_79(primary, "worktree", "list", "--porcelain").count("worktree ") == 1


# -- Story 66.1 (spec-pyforge-marshal CAP-275): a recommended follow-up review rides into the ledger --------
#
# The REAL `_run_deferred_work_intake` runs here (a fake process for the script, the real `LocalFs` over a real
# ledger file in `tmp_path`); only git is a fake. `_FrrVcs` serves the deferred-work ledger AT `origin/main`
# -- the text a publish replaces, which is what the row is built on -- apart from the primary's own copy, and
# keeps it current: a published ledger becomes what the next fetch reads.

_FRR_KEY = "51.2"
_FRR_NAME = "spec-51-2-the-landing-record-follows-the-session-s-write-not-the-primary-s-directory.md"
_FRR_SPEC_REL = f"_bmad-output/projects/{_SLUG_79}/planning-artifacts/specs/{_FRR_NAME}"
_FRR_LEDGER_REL = f"_bmad-output/projects/{_SLUG_79}/planning-artifacts/deferred-work-ledger.md"
_FRR_ID = "DW-FRR-51-2"
_FRR_SPEC = (
    "---\ntitle: '51.2: x'\nstatus: 'done'\nreview_loop_iteration: 1\nfollowup_review_recommended: true\n---\n\n"
    "## Auto Run Result\n"
)
#: The hand-filed row for the same story: a `DW-FU-` id, never the dispatch twin's `DW-FRR-`.
_FRR_BASE_LEDGER = "# Deferred Work Ledger\n\n### DW-FU-51-2-1: hand-filed\n\n- source_spec: `x`\n  status: open\n"
#: A row a concurrent finalize published onto origin/main after the primary's copy was last synced.
_FRR_CONCURRENT_ROW = (
    "\n### DW-CONCURRENT-1: published since the primary's copy\n\n- source_spec: `y`\n  status: open\n"
)
_FRR_DONE_TWIN = (
    "development_status:\n  epic-51: in-progress\n  51-2-the-landing-record-follows-the-session-s-write: done\n"
)


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)

    def monotonic(self) -> float:
        return 0.0


class _FrrVcs(_PublishVcs):
    """`_PublishVcs` for story 51.2 (spec `done` and flagged at `origin/main`) that also serves the deferred-work
    ledger at `origin/main` (`origin_ledger`, `None` = absent) and applies a published ledger to it.

    The carry's own fetch is observable: the carry reads the spec at `origin/main` first and fetches second, so
    a fetch after that read is the carry's (`carry_fetched`). `stale_until_carry_fetch` is the ledger the tip
    shows until that fetch has run (a clone that has not yet fetched); `carry_fetch_raises` makes that fetch fail."""

    def __init__(
        self,
        *,
        origin_ledger: str | None = _FRR_BASE_LEDGER,
        origin_ledger_raises: bool = False,
        stale_until_carry_fetch: str | None = None,
        carry_fetch_raises: bool = False,
        **kwargs,
    ) -> None:
        kwargs.setdefault("ledger_text", _FRR_DONE_TWIN)
        kwargs.setdefault("spec_text", _FRR_SPEC)
        super().__init__(**kwargs)
        self.origin_ledger = origin_ledger
        self.origin_ledger_raises = origin_ledger_raises
        self.stale_until_carry_fetch = stale_until_carry_fetch
        self.carry_fetch_raises = carry_fetch_raises
        self.carry_fetched = False
        self.ledger_refs: list[str] = []

    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        if self._carry_started():
            if self.carry_fetch_raises:
                self.fetch_calls.append((repo_root, remote, ref))
                raise VcsCommandError("git fetch origin refs/heads/main failed: could not read from remote")
            self.carry_fetched = True
        super().fetch(repo_root, remote, ref)

    def _carry_started(self) -> bool:
        return any(path == _FRR_SPEC_REL for _root, _ref, path in self.read_calls)

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str) -> str | None:
        if path == _FRR_LEDGER_REL:
            self.ledger_refs.append(ref)
            if self.origin_ledger_raises:
                raise VcsCommandError(f"git show {ref}:{path} failed: bad object")
            if self.stale_until_carry_fetch is not None and not self.carry_fetched:
                return self.stale_until_carry_fetch
            return self.origin_ledger
        return super().file_text_at_ref(repo_root, ref, path)

    def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message, preflight_skip_reason=None):
        sha = super().commit_paths_onto_remote_tip(
            repo_root,
            remote=remote,
            ref=ref,
            writes=writes,
            message=message,
            preflight_skip_reason=preflight_skip_reason,
        )
        for rel, text in writes:
            if rel == _FRR_LEDGER_REL:
                self.origin_ledger = text
        return sha


class _AddingIntakeProcess:
    """The intake script as it runs when it files a row of its own: appends to the primary's ledger file (and, with
    a non-zero ``returncode``, then refuses -- a script that wrote before it failed)."""

    def __init__(self, ledger: Path, *, returncode: int = 0) -> None:
        self.ledger = ledger
        self.returncode = returncode
        self.calls: list[list[str]] = []

    def run(self, tokens, *, cwd: Path):
        self.calls.append(list(tokens))
        self.ledger.write_text(
            self.ledger.read_text(encoding="utf-8") + "\n### DW-INTAKE-1: filed by intake\n", encoding="utf-8"
        )
        return ProcessResult(returncode=self.returncode, stdout="", stderr="intake exploded" if self.returncode else "")


class _LedgerLockedFs(LocalFs):
    """The deferred-work ledger's advisory lock is held by another finalize; every other lock is free."""

    def acquire_advisory_lock(self, path, *, timeout_s):
        if path.name == "deferred-work-ledger.md":
            raise FsError(f"lock held: {path}")
        return super().acquire_advisory_lock(path, timeout_s=timeout_s)


def _frr_ledger_path(root: Path) -> Path:
    return root / _FRR_LEDGER_REL


def _frr_setup(root: Path, ledger: str | None = _FRR_BASE_LEDGER, *, spec: bool = True) -> Path:
    """The primary checkout's own files: the story's tracked spec (so the path resolves locally) and the ledger."""
    if spec:
        _write_tracked_spec_79(root, text=_FRR_SPEC, name=_FRR_NAME)
    path = _frr_ledger_path(root)
    if ledger is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ledger, encoding="utf-8")
    return path


def _frr_finalize(
    monkeypatch,
    root: Path,
    vcs,
    process=None,
    *,
    worktree: Path | None = None,
    fs=None,
    with_clock: bool = True,
    **finalize_kwargs,
) -> int:
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.repo_root", lambda: root)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.GitVcs", lambda: vcs)
    if fs is not None:
        monkeypatch.setattr(f"{_FINALIZE_MOD_79}.LocalFs", lambda: fs)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._scan_promotions", lambda *a, **k: _PlannedScan())
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._promote_sprint_ledger", lambda *a, **k: ())
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._resync_home_branch", lambda *a, **k: True)
    process = process if process is not None else _FakeIntakeProcess(returncode=0)
    clock = _FixedClock() if with_clock else None
    return finalize_dispatch_land(
        _SLUG_79, _FRR_KEY, worktree=worktree, process=process, clock=clock, **finalize_kwargs
    )


def _frr_published_ledger(vcs: _PublishVcs) -> str:
    [publish] = vcs.publishes
    [(path, text)] = publish["writes"]
    assert path == _FRR_LEDGER_REL
    return text


def _frr_promoted_id(root: Path) -> str | None:
    return _observation_79(root)["followup_review_promoted_id"]


def _frr_messages(root: Path) -> list[str]:
    return [finding["message"] for finding in _journaled_findings_79(root)]


def test_finalize_publishes_one_followup_review_row_for_a_flagged_landing(tmp_path: Path, monkeypatch) -> None:
    """AC 1: the landed story's spec on origin/main reads `done` with the flag true and the ledger carries no
    `DW-FRR-51-2` -> exactly one row is published onto origin/main's ledger, the ledger's own rows are untouched,
    the payload names it, and the primary's working copy is back to what it was."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs()

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    published = _frr_published_ledger(vcs)
    assert published.startswith(_FRR_BASE_LEDGER)
    assert published.count(f"### {_FRR_ID}:") == 1
    row = published[len(_FRR_BASE_LEDGER) :]
    assert f"- source_spec: `planning-artifacts/specs/{_FRR_NAME}`" in row
    assert f"  location: {_FRR_SPEC_REL}" in row
    assert "  origin: dispatch-followup-review" in row
    assert "  severity: low" in row
    assert "  status: open" in row
    assert "  promoted: 2026-10-01 — dispatch-land finalize" in row
    [publish] = vcs.publishes
    assert (publish["remote"], publish["ref"]) == ("origin", "main")
    assert _FRR_ID in publish["message"] and _FRR_KEY in publish["preflight_skip_reason"]
    assert vcs.ledger_refs == [ORIGIN_MAIN]
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER
    assert _frr_promoted_id(tmp_path) == _FRR_ID
    assert _journaled_findings_79(tmp_path) == []


def test_a_second_finalize_adds_nothing_even_when_the_primarys_copy_is_still_stale(tmp_path: Path, monkeypatch) -> None:
    """AC 2: the first run published the row onto origin/main; its primary copy is restored to the pre-publish
    text (and no resync has run), so a second finalize sees a primary ledger WITHOUT the row. Idempotency is
    judged on origin/main's ledger, so nothing is added and no second publish is made."""
    vcs = _FrrVcs()
    first_root = tmp_path / "first"
    _frr_setup(first_root)
    assert _frr_finalize(monkeypatch, first_root, vcs) == 0
    published = _frr_published_ledger(vcs)
    assert vcs.origin_ledger == published

    second_root = tmp_path / "second"
    stale = _frr_setup(second_root)
    assert stale.read_text(encoding="utf-8") == _FRR_BASE_LEDGER
    assert _frr_finalize(monkeypatch, second_root, vcs) == 0

    assert len(vcs.publishes) == 1
    assert vcs.origin_ledger.count(f"### {_FRR_ID}:") == 1
    assert _frr_promoted_id(second_root) is None
    assert _journaled_findings_79(second_root) == []
    assert stale.read_text(encoding="utf-8") == _FRR_BASE_LEDGER


@pytest.mark.parametrize(
    "spec_text",
    [
        _FRR_SPEC.replace("followup_review_recommended: true", "followup_review_recommended: false"),
        _FRR_SPEC.replace("followup_review_recommended: true", "followup_review_recommended: no"),
        _FRR_SPEC.replace("followup_review_recommended: true\n", ""),
        _FRR_SPEC.replace("status: 'done'", "status: 'in-review'"),
        _FRR_SPEC.replace("status: 'done'", "status: 'backlog'"),
        None,
    ],
    ids=["flag-false", "flag-no", "flag-absent", "in-review", "backlog", "spec-absent-at-origin-main"],
)
def test_finalize_adds_no_row_unless_the_spec_is_done_and_explicitly_flagged(
    tmp_path: Path, monkeypatch, spec_text: str | None
) -> None:
    """AC 3: a flag `false`/`no`/absent, a status other than `done`, or a spec origin/main does not hold yet adds
    no row, publishes nothing and reports a null id -- silently."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(spec_text=spec_text)

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    assert vcs.publishes == []
    assert vcs.ledger_refs == []
    assert _frr_promoted_id(tmp_path) is None
    assert _journaled_findings_79(tmp_path) == []
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER


def test_finalize_adds_the_row_when_the_ledger_holds_a_longer_sibling_id(tmp_path: Path, monkeypatch) -> None:
    """AC 4: `DW-FRR-51-20` is a different story's row, never a hit for `DW-FRR-51-2`."""
    sibling = _FRR_BASE_LEDGER + "\n### DW-FRR-51-20: Follow-up review still recommended for story 51.20\n"
    _frr_setup(tmp_path, ledger=sibling)
    vcs = _FrrVcs(origin_ledger=sibling)

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    published = _frr_published_ledger(vcs)
    assert published.startswith(sibling)
    assert published.count("### DW-FRR-51-20:") == 1 and published.count(f"### {_FRR_ID}:") == 1
    assert _frr_promoted_id(tmp_path) == _FRR_ID


def test_finalize_publishes_the_intakes_rows_and_the_followup_row_together(tmp_path: Path, monkeypatch) -> None:
    """AC 5: an intake that also adds rows in the same finalize -> ONE publish holds the intake's row and the new
    row, so neither can drop the other; the primary's copy is restored to its pre-intake text; and the commit
    message and the preflight opt-out's reason name BOTH, the reason still naming the story."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs()
    process = _AddingIntakeProcess(ledger)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, process) == 0

    published = _frr_published_ledger(vcs)
    assert "### DW-INTAKE-1: filed by intake" in published
    assert published.count(f"### {_FRR_ID}:") == 1
    assert published.index("### DW-INTAKE-1:") < published.index(f"### {_FRR_ID}:")
    [publish] = vcs.publishes
    assert "intake" in publish["message"] and _FRR_ID in publish["message"]
    assert "intake" in publish["preflight_skip_reason"] and "follow-up review" in publish["preflight_skip_reason"]
    assert _FRR_KEY in publish["preflight_skip_reason"]
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER
    assert _frr_promoted_id(tmp_path) == _FRR_ID
    assert _journaled_findings_79(tmp_path) == []


def test_the_row_is_built_on_origin_mains_ledger_never_the_stale_primary_copy(tmp_path: Path, monkeypatch) -> None:
    """The base-text rule, intake-changed-nothing branch: finalize skipped its resync (a dirty primary) or a
    concurrent finalize published since, so the primary's copy lacks a row origin/main holds. The publish writes
    its text over origin/main's, so the row is appended to ORIGIN/MAIN's ledger -- the concurrent row survives."""
    remote = _FRR_BASE_LEDGER + _FRR_CONCURRENT_ROW
    stale = _frr_setup(tmp_path)
    vcs = _FrrVcs(origin_ledger=remote, dirty=True)

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    published = _frr_published_ledger(vcs)
    assert published.startswith(remote)
    assert "### DW-CONCURRENT-1:" in published and published.count(f"### {_FRR_ID}:") == 1
    assert stale.read_text(encoding="utf-8") == _FRR_BASE_LEDGER
    assert _frr_promoted_id(tmp_path) == _FRR_ID
    assert _journaled_findings_79(tmp_path) == []


def test_the_intakes_text_is_the_base_when_it_changed_a_copy_that_was_the_tip(tmp_path: Path, monkeypatch) -> None:
    """The base-text rule, intake-changed-the-tip's-copy branch: the primary's copy equals origin/main's, so the
    intake's text is a faithful successor of the tip and the row goes onto IT (the intake's row is not lost)."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(origin_ledger=_FRR_BASE_LEDGER)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger)) == 0

    published = _frr_published_ledger(vcs)
    assert published.startswith(_FRR_BASE_LEDGER + "\n### DW-INTAKE-1: filed by intake\n")
    assert published.count(f"### {_FRR_ID}:") == 1


def test_no_row_is_carried_and_the_intakes_publish_stands_when_it_changed_a_copy_that_is_not_the_tip(
    tmp_path: Path, monkeypatch
) -> None:
    """The base-text rule, third branch: the intake changed a primary copy that differs from origin/main's. Two
    texts are never merged, so the row is skipped (a WARN says a re-run carries it) and the intake's own publish
    proceeds exactly as it always has -- the row is the one that waits."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(origin_ledger=_FRR_BASE_LEDGER + _FRR_CONCURRENT_ROW)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger)) == 0

    published = _frr_published_ledger(vcs)
    assert published == _FRR_BASE_LEDGER + "\n### DW-INTAKE-1: filed by intake\n"
    assert _FRR_ID not in published
    [message] = _frr_messages(tmp_path)
    assert _FRR_ID in message and "re-run of finalize carries it" in message and _FRR_LEDGER_REL in message
    assert _frr_promoted_id(tmp_path) is None
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER


def test_a_refused_intake_still_publishes_the_followup_row_and_restores_what_it_half_wrote(
    tmp_path: Path, monkeypatch
) -> None:
    """An intake refusal is its own WARN; the row is still published, built on origin/main's ledger -- and a
    script that wrote the primary's copy before it failed has that copy put back, never carried or left dirty."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs()

    assert _frr_finalize(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger, returncode=1)) == 0

    published = _frr_published_ledger(vcs)
    assert "DW-INTAKE-1" not in published
    assert published.startswith(_FRR_BASE_LEDGER) and published.count(f"### {_FRR_ID}:") == 1
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER
    assert _frr_promoted_id(tmp_path) == _FRR_ID
    [message] = _frr_messages(tmp_path)
    assert "refused (exit 1)" in message


def test_a_refused_intake_with_nothing_to_carry_still_restores_the_half_written_copy(
    tmp_path: Path, monkeypatch
) -> None:
    """No follow-up row at all (the flag is false): a refusing script that wrote first no longer leaves the
    primary's ledger dirty -- the pre-script text is put back and nothing is published."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(spec_text=_FRR_SPEC.replace("recommended: true", "recommended: false"))

    assert _frr_finalize(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger, returncode=1)) == 0

    assert vcs.publishes == []
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER
    [message] = _frr_messages(tmp_path)
    assert "refused (exit 1)" in message


def test_finalize_warns_when_the_followup_publish_fails_and_keeps_its_exit_code(tmp_path: Path, monkeypatch) -> None:
    """AC 6: `commit_paths_onto_remote_tip` raising `VcsCommandError` is an `MRS-DISP-047` WARN naming the
    failure and the row, the payload's id is null (nothing landed), the exit code is the one the landing would
    have had without the flag (0), and the primary's copy is untouched."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(publish_raises=True)

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert "not a fast-forward" in finding["message"] and _FRR_ID in finding["message"]
    assert _frr_promoted_id(tmp_path) is None
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER
    assert vcs.origin_ledger == _FRR_BASE_LEDGER


def test_a_failed_publish_of_the_intakes_rows_and_the_row_names_both(tmp_path: Path, monkeypatch) -> None:
    """When both are published together, the publish-failure WARN names both -- not only the row."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(publish_raises=True)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger)) == 0

    [message] = _frr_messages(tmp_path)
    assert "deferred-work intake" in message and _FRR_ID in message and "not a fast-forward" in message
    assert _frr_promoted_id(tmp_path) is None
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER


def test_a_failed_publish_after_a_refused_intake_reports_both_warns(tmp_path: Path, monkeypatch) -> None:
    """Only the follow-up row is published after a refused intake, so its publish failure is a second WARN
    beside the refusal's, never swallowed by it."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(publish_raises=True)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger, returncode=1)) == 0

    messages = _frr_messages(tmp_path)
    assert len(messages) == 2
    assert any("refused (exit 1)" in message for message in messages)
    assert any("not a fast-forward" in message and _FRR_ID in message for message in messages)
    assert _frr_promoted_id(tmp_path) is None
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER


def test_finalize_warns_and_adds_nothing_when_the_spec_cannot_be_read_at_origin_main(
    tmp_path: Path, monkeypatch
) -> None:
    """The I/O matrix row: a `VcsCommandError` reading the spec at origin/main -> nothing added, an
    `MRS-DISP-047` WARN naming the spec path in the payload, the landing's exit code unchanged."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(spec_read_raises=True)

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert _FRR_SPEC_REL in finding["message"] and "follow-up review" in finding["message"]
    assert finding["path"] == _FRR_SPEC_REL
    assert vcs.publishes == []
    assert _frr_promoted_id(tmp_path) is None
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER


def test_finalize_reads_the_spec_through_the_dispatch_worktree_when_the_primary_does_not_hold_it(
    tmp_path: Path, monkeypatch
) -> None:
    """The primary's tree does not hold a spec the merged PR added until a resync -- only the dispatch worktree
    does. The carry resolves the path through it (as the tracked-spec promotion does) and still reads the spec
    at origin/main; with no worktree and no local spec there is nothing to read and nothing is said."""
    primary = tmp_path / "primary"
    _frr_setup(primary, spec=False)
    worktree = tmp_path / "dispatch-worktree"
    _write_tracked_spec_79(worktree, text=_FRR_SPEC, name=_FRR_NAME)
    vcs = _FrrVcs()

    assert _frr_finalize(monkeypatch, primary, vcs, worktree=worktree) == 0

    published = _frr_published_ledger(vcs)
    assert published.count(f"### {_FRR_ID}:") == 1 and f"  location: {_FRR_SPEC_REL}" in published
    assert (primary, ORIGIN_MAIN, _FRR_SPEC_REL) in vcs.read_calls
    assert _frr_promoted_id(primary) == _FRR_ID

    bare = tmp_path / "bare"
    _frr_setup(bare, spec=False)
    bare_vcs = _FrrVcs()
    assert _frr_finalize(monkeypatch, bare, bare_vcs) == 0
    assert bare_vcs.publishes == []
    assert [path for _root, _ref, path in bare_vcs.read_calls if path == _FRR_SPEC_REL] == []
    assert _journaled_findings_79(bare) == []
    assert _frr_promoted_id(bare) is None


def test_finalize_warns_and_adds_nothing_when_the_ledger_cannot_be_read_at_origin_main(
    tmp_path: Path, monkeypatch
) -> None:
    """The tip's ledger is unreadable: the row is skipped with a WARN naming the ledger path and the cause, and
    the intake's own publish still goes out exactly as it always has."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(origin_ledger_raises=True)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger)) == 0

    published = _frr_published_ledger(vcs)
    assert published == _FRR_BASE_LEDGER + "\n### DW-INTAKE-1: filed by intake\n"
    [message] = _frr_messages(tmp_path)
    assert _FRR_LEDGER_REL in message and "bad object" in message and _FRR_ID in message
    assert _frr_promoted_id(tmp_path) is None


def test_a_primary_with_no_ledger_copy_still_publishes_the_row_and_gains_no_file(tmp_path: Path, monkeypatch) -> None:
    """The primary's tree holds no ledger (nothing checked out there yet) but origin/main does: the row is built
    on origin/main's text and published, and the primary is left with no ledger file it never had."""
    ledger = _frr_setup(tmp_path, ledger=None)
    vcs = _FrrVcs()

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    published = _frr_published_ledger(vcs)
    assert published.startswith(_FRR_BASE_LEDGER) and published.count(f"### {_FRR_ID}:") == 1
    assert not ledger.exists()
    assert _frr_promoted_id(tmp_path) == _FRR_ID
    assert _journaled_findings_79(tmp_path) == []


def test_finalize_never_creates_a_ledger_for_a_followup_row(tmp_path: Path, monkeypatch) -> None:
    """No ledger at origin/main: a WARN naming it, no publish, and nothing created in the primary's tree."""
    ledger = _frr_setup(tmp_path, ledger=None)
    vcs = _FrrVcs(origin_ledger=None)

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert _FRR_LEDGER_REL in finding["message"] and "does not exist" in finding["message"]
    assert vcs.publishes == []
    assert not ledger.exists()
    assert _frr_promoted_id(tmp_path) is None


def test_a_contended_ledger_lock_names_the_row_that_was_not_carried(tmp_path: Path, monkeypatch) -> None:
    """The intake step cannot take its lock, so nothing is published -- and the WARN says which follow-up row
    that cost, beside the intake skip it already reports."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs()

    assert _frr_finalize(monkeypatch, tmp_path, vcs, fs=_LedgerLockedFs()) == 0

    [message] = _frr_messages(tmp_path)
    assert "lock" in message and "intake skipped" in message
    assert _FRR_ID in message and "was not carried" in message
    assert vcs.publishes == []
    assert _frr_promoted_id(tmp_path) is None
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER


def test_the_live_ledger_shape_a_prose_mention_of_the_id_is_not_the_row(tmp_path: Path, monkeypatch) -> None:
    """Review pass 2, on the shape the live marshal ledger has today: the hand-filed `DW-FU-51-2-1` row's
    `verified:` line names `DW-FRR-51-2` in prose. That is not the row, so 51.2 -- the story this feature exists
    for -- is carried; a real `### DW-FRR-51-2:` heading (the second finalize) still is not added again."""
    live = (
        _FRR_BASE_LEDGER
        + "  verified: 2026-09-28 -- carried by `DW-FRR-51-2` once Story 66.1 lands (placeholder: DW-FRR-<story>).\n"
    )
    _frr_setup(tmp_path, ledger=live)
    vcs = _FrrVcs(origin_ledger=live)

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    published = _frr_published_ledger(vcs)
    assert published.startswith(live)
    assert published.count(f"### {_FRR_ID}:") == 1
    assert _frr_promoted_id(tmp_path) == _FRR_ID

    again = tmp_path / "again"
    _frr_setup(again, ledger=live)
    assert _frr_finalize(monkeypatch, again, vcs) == 0
    assert len(vcs.publishes) == 1
    assert _frr_promoted_id(again) is None


@pytest.mark.parametrize(
    "status_line",
    ["status: done  # landed via dispatch", "status: Done", 'status: "done"', "status: done"],
)
def test_finalize_carries_a_done_spec_whose_status_line_the_strict_reader_cannot_parse(
    tmp_path: Path, monkeypatch, status_line: str
) -> None:
    """Review pass 2: the status is read through the harness guard's own reader, so the `done  # note` and
    capitalised shapes are carried, not dropped silently."""
    _frr_setup(tmp_path)
    vcs = _FrrVcs(spec_text=_FRR_SPEC.replace("status: 'done'", status_line))

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    assert _frr_published_ledger(vcs).count(f"### {_FRR_ID}:") == 1
    assert _frr_promoted_id(tmp_path) == _FRR_ID


def test_the_carrys_own_fetch_runs_before_it_reads_the_ledger_at_origin_main(tmp_path: Path, monkeypatch) -> None:
    """Review pass 2: the tip shows a stale ledger until the carry's own `fetch` has run. The row must be built
    on the fetched text, so the row a concurrent finalize published since survives; deleting the fetch, or moving
    it after the read, builds the row on the stale tip and drops that row."""
    fresh = _FRR_BASE_LEDGER + _FRR_CONCURRENT_ROW
    _frr_setup(tmp_path)
    vcs = _FrrVcs(origin_ledger=fresh, stale_until_carry_fetch=_FRR_BASE_LEDGER)

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    assert vcs.carry_fetched
    published = _frr_published_ledger(vcs)
    assert published.startswith(fresh)
    assert "### DW-CONCURRENT-1:" in published and published.count(f"### {_FRR_ID}:") == 1


def test_a_failing_carry_fetch_skips_the_row_with_a_warn_and_the_intakes_publish_stands(
    tmp_path: Path, monkeypatch
) -> None:
    """Review pass 2: the carry's own fetch raising is the "cannot read the ledger" skip -- a WARN naming the
    ledger and the cause, no row, and the intake's own publish goes out as it always has. A carry that swallowed
    the error would publish a row built on an unfetched tip."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(carry_fetch_raises=True)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger)) == 0

    published = _frr_published_ledger(vcs)
    assert published == _FRR_BASE_LEDGER + "\n### DW-INTAKE-1: filed by intake\n"
    [message] = _frr_messages(tmp_path)
    assert _FRR_LEDGER_REL in message and "could not read from remote" in message and _FRR_ID in message
    assert _frr_promoted_id(tmp_path) is None
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER


def test_the_followup_row_depends_on_finalizes_own_carry_call(tmp_path: Path, monkeypatch) -> None:
    """AC 7 (mutation): with the carry call answering nothing -- what removing it from `finalize_dispatch_land`
    leaves -- the 51.2 fixture adds no row, so `test_finalize_publishes_one_followup_review_row_for_a_flagged_landing`
    cannot pass without it. The stub records that finalize called it, once, for this story and worktree, so the
    test cannot pass by never reaching the seam."""
    _frr_setup(tmp_path)
    worktree = tmp_path / "dispatch-worktree"
    worktree.mkdir()
    vcs = _FrrVcs()
    calls: list[tuple[str, str, Path | None]] = []

    def _no_carry(_vcs, _root, project_slug, key, carry_worktree, _clock, _findings):
        calls.append((project_slug, str(key), carry_worktree))

    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._followup_review_carry", _no_carry)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, worktree=worktree) == 0

    assert calls == [(_SLUG_79, _FRR_KEY, worktree)]
    assert vcs.publishes == []
    assert _frr_promoted_id(tmp_path) is None


def test_finalize_dates_the_row_through_its_own_default_clock(tmp_path: Path, monkeypatch) -> None:
    """`main()` passes no clock, so every production flagged landing runs on `finalize_dispatch_land`'s own
    default. With none injected the row is dated by the module's `SystemClock` (swapped here for the fixed one,
    so the date is deterministic); a default that is not wired fails the carry instead of dating the row."""
    _frr_setup(tmp_path)
    vcs = _FrrVcs()
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.SystemClock", _FixedClock)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, with_clock=False) == 0

    assert "  promoted: 2026-10-01 \u2014 dispatch-land finalize" in _frr_published_ledger(vcs)
    assert _frr_promoted_id(tmp_path) == _FRR_ID


def test_against_real_git_the_row_is_published_onto_origin_mains_ledger_while_the_primary_copy_is_stale(
    tmp_path: Path, monkeypatch
) -> None:
    """The base-text rule against REAL git, finalize end to end: a bare `origin`, the primary clone (a dirty tree,
    so no resync) and a second clone that "lands" story 79.1 -- its flagged `done` spec, its `done` ledger twin
    and a ledger row a concurrent finalize published -- while the primary has not fetched. The row is published
    through the real `commit_paths_onto_remote_tip` onto origin/main's ledger text (the concurrent row survives),
    the primary's tracked copy is left stale exactly as it was, and a second finalize adds nothing."""
    ledger_rel = f"_bmad-output/projects/{_SLUG_79}/planning-artifacts/deferred-work-ledger.md"
    twin_rel = f"_bmad-output/projects/{_SLUG_79}/planning-artifacts/sprint-status-ledger.yaml"
    stale = "# Deferred Work Ledger\n\n### DW-FU-1-1: old\n\n- source_spec: `x`\n  status: open\n"
    flagged = _TRACKED_SPEC_79.replace("'backlog'", "'done'").replace(
        "---\n\n", "followup_review_recommended: true\n---\n\n", 1
    )
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git_79(origin, "init", "--bare", "-b", "main")
    primary = tmp_path / "primary"
    primary.mkdir()
    _git_79(primary, "init", "-b", "main")
    _configure_git_79(primary)
    (primary / ledger_rel).parent.mkdir(parents=True)
    (primary / ledger_rel).write_text(stale, encoding="utf-8")
    _git_79(primary, "add", ledger_rel)
    _git_79(primary, "commit", "-m", "base")
    _git_79(primary, "remote", "add", "origin", str(origin))
    _git_79(primary, "push", "-u", "origin", "main")

    landing = tmp_path / "landing"
    _git_79(tmp_path, "clone", str(origin), str(landing))
    _configure_git_79(landing)
    remote_ledger = stale + _FRR_CONCURRENT_ROW
    for rel, text in ((_SPEC_REL_79, flagged), (twin_rel, _DONE_LEDGER_79), (ledger_rel, remote_ledger)):
        (landing / rel).parent.mkdir(parents=True, exist_ok=True)
        (landing / rel).write_text(text, encoding="utf-8")
        _git_79(landing, "add", rel)
    _git_79(landing, "commit", "-m", _DISPATCH_MERGE_79)
    landing_sha = _git_79(landing, "rev-parse", "HEAD").strip()
    _git_79(landing, "push", "origin", "main")

    # The dispatch worktree holds the spec; the primary's tree does not, and its tree is dirty (a Tier-3 feed).
    worktree = tmp_path / "dispatch-worktree"
    _write_tracked_spec_79(worktree, text=flagged)
    _write_feed_79(primary)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.repo_root", lambda: primary)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._scan_promotions", lambda *a, **k: _PlannedScan())
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._promote_sprint_ledger", lambda *a, **k: ())
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._resync_home_branch", lambda *a, **k: True)
    head_before = _git_79(primary, "rev-parse", "HEAD").strip()

    assert (
        finalize_dispatch_land(
            _SLUG_79, "79.1", worktree=worktree, process=_FakeIntakeProcess(returncode=0), clock=_FixedClock()
        )
        == 0
    )

    published = _git_79(origin, "show", f"main:{ledger_rel}")
    assert published.startswith(remote_ledger.rstrip("\n"))
    assert "### DW-CONCURRENT-1:" in published
    assert published.count("### DW-FRR-79-1:") == 1
    assert "  origin: dispatch-followup-review" in published and f"  location: {_SPEC_REL_79}" in published
    assert _git_79(origin, "rev-parse", "main~1").strip() == landing_sha
    assert _git_79(origin, "diff", "--name-only", "main~1", "main").split() == [ledger_rel]
    assert _observation_79(primary)["followup_review_promoted_id"] == "DW-FRR-79-1"
    # CAP-233: the operator checkout's tracked ledger is the stale copy it was, with no leaked publish worktree.
    assert (primary / ledger_rel).read_text(encoding="utf-8") == stale
    assert _git_79(primary, "status", "--porcelain", "--", ledger_rel) == ""
    assert _git_79(primary, "rev-parse", "HEAD").strip() == head_before
    assert _git_79(primary, "worktree", "list", "--porcelain").count("worktree ") == 1

    tip = _git_79(origin, "rev-parse", "main").strip()
    assert (
        finalize_dispatch_land(
            _SLUG_79, "79.1", worktree=worktree, process=_FakeIntakeProcess(returncode=0), clock=_FixedClock()
        )
        == 0
    )
    assert _git_79(origin, "rev-parse", "main").strip() == tip
    assert _git_79(origin, "show", f"main:{ledger_rel}").count("### DW-FRR-79-1:") == 1


# -- Story 73.1 (spec-pyforge-marshal CAP-281): the landed follow-up review run closes the row it served -----
#
# Same fixtures as the carry above. After a follow-up review lands, its spec reads `done` with the flag
# `false` (`bmad-build-auto` step 04), so the carry has nothing to add; the open `DW-FRR-51-2` row the review
# served is rendered closed in the intake step's own locked publish.

_FRR_REVIEWED_SPEC = _FRR_SPEC.replace("followup_review_recommended: true", "followup_review_recommended: false")
_FRR_LANDING = "Merge pyforge-marshal/51-2 into main"
_FRR_CLOSED_LINES = f"  resolved: 2026-10-01 (dispatch-land finalize: {_FRR_LANDING})\n  status: closed\n"


def _frr_open_row_ledger(base: str = _FRR_BASE_LEDGER) -> str:
    """``base`` plus the open ``DW-FRR-51-2`` row exactly as the carry renders it (Story 66.1)."""
    from pyforge.marshal.core import deferred_work

    candidate = deferred_work.followup_review_candidate(_FRR_SPEC, normalize(_FRR_KEY), _FRR_SPEC_REL)
    assert candidate is not None
    return deferred_work.append_ledger_entry(
        base, deferred_work.render_followup_review_entry(candidate, promoted_date="2026-09-28")
    )


def _frr_expected_closed(ledger: str) -> str:
    """``ledger`` with ONLY the ``DW-FRR-51-2`` row's own ``status: open`` line closed (other rows' stay)."""
    head, heading, row = ledger.partition(f"### {_FRR_ID}:")
    assert heading, "the ledger holds no DW-FRR-51-2 row"
    return head + heading + row.replace("  status: open\n", _FRR_CLOSED_LINES, 1)


def _frr_closed_id(root: Path) -> str | None:
    return _observation_79(root)["followup_review_closed_id"]


def _frr_close(monkeypatch, root: Path, vcs, process=None, **kwargs) -> int:
    return _frr_finalize(monkeypatch, root, vcs, process, followup_review_id=_FRR_ID, landing=_FRR_LANDING, **kwargs)


def test_a_landed_follow_up_review_closes_its_row_and_adds_no_new_one(tmp_path: Path, monkeypatch) -> None:
    """AC 8: `DW-FRR-51-2` is published `status: closed` with `resolved:` naming the landing, no new `DW-FRR` row
    is added, the rest of the ledger is byte-identical, and the primary's working copy is back as it was."""
    open_ledger = _frr_open_row_ledger()
    ledger = _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger)

    assert _frr_close(monkeypatch, tmp_path, vcs) == 0

    published = _frr_published_ledger(vcs)
    assert published == _frr_expected_closed(open_ledger)
    assert published.count("### DW-FRR-") == 1
    assert published.startswith(_FRR_BASE_LEDGER)
    [publish] = vcs.publishes
    assert (publish["remote"], publish["ref"]) == ("origin", "main")
    assert publish["message"] == "marshal: close follow-up review row DW-FRR-51-2 for 'marshal'"
    assert _FRR_KEY in publish["preflight_skip_reason"]
    assert ledger.read_text(encoding="utf-8") == open_ledger
    assert _frr_closed_id(tmp_path) == _FRR_ID
    assert _frr_promoted_id(tmp_path) is None
    assert _journaled_findings_79(tmp_path) == []


def test_a_second_finalize_closes_nothing_twice(tmp_path: Path, monkeypatch) -> None:
    open_ledger = _frr_open_row_ledger()
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger)
    first = tmp_path / "first"
    _frr_setup(first, open_ledger)
    assert _frr_close(monkeypatch, first, vcs) == 0
    closed = vcs.origin_ledger
    assert "status: closed" in closed

    second = tmp_path / "second"
    _frr_setup(second, open_ledger)
    assert _frr_close(monkeypatch, second, vcs) == 0

    assert len(vcs.publishes) == 1
    assert vcs.origin_ledger == closed
    assert _frr_closed_id(second) is None
    assert _journaled_findings_79(second) == []


def test_a_follow_up_landing_with_no_row_to_close_publishes_nothing(tmp_path: Path, monkeypatch) -> None:
    """The row is absent at origin/main (a closed or never-carried row reads the same): nothing to close."""
    ledger = _frr_setup(tmp_path)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC)

    assert _frr_close(monkeypatch, tmp_path, vcs) == 0

    assert vcs.publishes == []
    assert _frr_closed_id(tmp_path) is None
    assert _journaled_findings_79(tmp_path) == []
    assert ledger.read_text(encoding="utf-8") == _FRR_BASE_LEDGER


def test_a_normal_landing_closes_no_row_even_when_one_is_open(tmp_path: Path, monkeypatch) -> None:
    """No `--followup-review-id`: an open row for the story stays open, and the payload says null."""
    open_ledger = _frr_open_row_ledger()
    _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger)

    assert _frr_finalize(monkeypatch, tmp_path, vcs) == 0

    assert vcs.publishes == []
    assert vcs.origin_ledger == open_ledger
    assert _frr_closed_id(tmp_path) is None


def test_the_closure_rides_the_same_publish_as_the_intakes_rows(tmp_path: Path, monkeypatch) -> None:
    open_ledger = _frr_open_row_ledger()
    ledger = _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger)

    assert _frr_close(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger)) == 0

    published = _frr_published_ledger(vcs)
    assert published == _frr_expected_closed(open_ledger + "\n### DW-INTAKE-1: filed by intake\n")
    [publish] = vcs.publishes
    assert publish["message"] == (
        "marshal: promote deferred-work intake and close follow-up review row DW-FRR-51-2 for 'marshal'"
    )
    assert ledger.read_text(encoding="utf-8") == open_ledger
    assert _frr_closed_id(tmp_path) == _FRR_ID


def test_the_closure_is_built_on_origin_mains_ledger_not_a_stale_primary_copy(tmp_path: Path, monkeypatch) -> None:
    """The primary's copy lacks a row a concurrent finalize published; the closure is built on the tip's text,
    so that row survives and the primary's stale copy is left exactly as it was."""
    stale = _frr_open_row_ledger()
    tip = stale + _FRR_CONCURRENT_ROW
    ledger = _frr_setup(tmp_path, stale)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=tip)

    assert _frr_close(monkeypatch, tmp_path, vcs) == 0

    published = _frr_published_ledger(vcs)
    assert published == _frr_expected_closed(tip)
    assert "### DW-CONCURRENT-1:" in published
    assert ledger.read_text(encoding="utf-8") == stale


def test_a_failed_closure_publish_is_a_warn_naming_the_row_and_keeps_the_exit_code(tmp_path: Path, monkeypatch) -> None:
    """AC 9: `commit_paths_onto_remote_tip` raising `VcsCommandError` while closing is an `MRS-DISP-047` WARN
    naming the closure and the row; nothing landed, the payload id is null, finalize's exit code is unchanged."""
    open_ledger = _frr_open_row_ledger()
    ledger = _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger, publish_raises=True)

    assert _frr_close(monkeypatch, tmp_path, vcs) == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert "closure of follow-up review row" in finding["message"] and _FRR_ID in finding["message"]
    assert "not a fast-forward" in finding["message"]
    assert _frr_closed_id(tmp_path) is None
    assert vcs.origin_ledger == open_ledger
    assert ledger.read_text(encoding="utf-8") == open_ledger


def test_a_failed_closure_publish_after_a_refused_intake_reports_both_warns(tmp_path: Path, monkeypatch) -> None:
    open_ledger = _frr_open_row_ledger()
    ledger = _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger, publish_raises=True)

    assert _frr_close(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger, returncode=1)) == 0

    messages = _frr_messages(tmp_path)
    assert len(messages) == 2
    assert any("refused (exit 1)" in message for message in messages)
    assert any("not a fast-forward" in message and _FRR_ID in message for message in messages)
    assert _frr_closed_id(tmp_path) is None


def test_a_refused_intake_still_publishes_the_closure(tmp_path: Path, monkeypatch) -> None:
    open_ledger = _frr_open_row_ledger()
    ledger = _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger)

    assert _frr_close(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger, returncode=1)) == 0

    published = _frr_published_ledger(vcs)
    assert "DW-INTAKE-1" not in published and "status: closed" in published
    assert ledger.read_text(encoding="utf-8") == open_ledger
    assert _frr_closed_id(tmp_path) == _FRR_ID
    [message] = _frr_messages(tmp_path)
    assert "refused (exit 1)" in message


def test_an_unreadable_tip_skips_the_closure_with_a_warn_and_the_intakes_publish_stands(
    tmp_path: Path, monkeypatch
) -> None:
    open_ledger = _frr_open_row_ledger()
    ledger = _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger, origin_ledger_raises=True)

    assert _frr_close(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger)) == 0

    assert _frr_published_ledger(vcs) == open_ledger + "\n### DW-INTAKE-1: filed by intake\n"
    [message] = _frr_messages(tmp_path)
    assert _FRR_ID in message and "was not closed" in message and "bad object" in message
    assert _frr_closed_id(tmp_path) is None


def test_a_ledger_absent_at_the_tip_is_never_created_for_a_closure(tmp_path: Path, monkeypatch) -> None:
    ledger = _frr_setup(tmp_path, ledger=None)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=None)

    assert _frr_close(monkeypatch, tmp_path, vcs) == 0

    [finding] = _journaled_findings_79(tmp_path)
    assert (finding["code"], finding["severity"]) == ("MRS-DISP-047", "warn")
    assert "does not exist" in finding["message"] and "was not closed" in finding["message"]
    assert vcs.publishes == []
    assert not ledger.exists()


def test_a_primary_copy_the_intake_changed_that_is_not_the_tips_skips_the_closure(tmp_path: Path, monkeypatch) -> None:
    """The carry's rule: two texts are never merged. The intake changed a copy that differs from the tip's, so
    the closure is skipped (a re-run closes it) and the intake's own publish goes out as it always has."""
    stale = _frr_open_row_ledger()
    ledger = _frr_setup(tmp_path, stale)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=stale + _FRR_CONCURRENT_ROW)

    assert _frr_close(monkeypatch, tmp_path, vcs, _AddingIntakeProcess(ledger)) == 0

    assert _frr_published_ledger(vcs) == stale + "\n### DW-INTAKE-1: filed by intake\n"
    [message] = _frr_messages(tmp_path)
    assert _FRR_ID in message and "was not closed" in message and "a re-run of finalize closes it" in message
    assert _frr_closed_id(tmp_path) is None


def test_a_contended_ledger_lock_names_the_row_that_was_not_closed(tmp_path: Path, monkeypatch) -> None:
    open_ledger = _frr_open_row_ledger()
    _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger)

    assert _frr_close(monkeypatch, tmp_path, vcs, fs=_LedgerLockedFs()) == 0

    [message] = _frr_messages(tmp_path)
    assert "lock" in message and _FRR_ID in message and "was not closed" in message
    assert vcs.publishes == []
    assert _frr_closed_id(tmp_path) is None


def test_a_landed_review_that_left_its_flag_true_carries_nothing_but_closes_its_row(
    tmp_path: Path, monkeypatch
) -> None:
    """A review that (against step 04) left `followup_review_recommended: true`: the carry sees the row's
    heading, so it adds nothing; the closure closes it, so the row is not re-queued."""
    open_ledger = _frr_open_row_ledger()
    _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(origin_ledger=open_ledger)  # the spec at origin/main still reads done + flagged

    assert _frr_close(monkeypatch, tmp_path, vcs) == 0

    published = _frr_published_ledger(vcs)
    assert published == _frr_expected_closed(open_ledger)
    assert published.count("### DW-FRR-") == 1
    assert _frr_closed_id(tmp_path) == _FRR_ID
    assert _frr_promoted_id(tmp_path) is None


def test_a_carry_and_a_closure_in_one_finalize_share_one_publish(tmp_path: Path, monkeypatch) -> None:
    """The row is absent and the spec is still flagged: the carry adds it and, on the same tip-built text, the
    closure closes it -- one publish, no second fetch for the closure."""
    _frr_setup(tmp_path)
    vcs = _FrrVcs()

    assert _frr_close(monkeypatch, tmp_path, vcs) == 0

    published = _frr_published_ledger(vcs)
    assert published.startswith(_FRR_BASE_LEDGER) and published.count("### DW-FRR-") == 1
    assert published.endswith(_FRR_CLOSED_LINES)
    assert len(vcs.publishes) == 1
    assert _frr_promoted_id(tmp_path) == _FRR_ID and _frr_closed_id(tmp_path) == _FRR_ID
    [publish] = vcs.publishes
    assert "carry follow-up review row DW-FRR-51-2" in publish["message"]
    assert "close follow-up review row DW-FRR-51-2" in publish["message"]
    assert "follow-up review carry and follow-up review closure" in publish["preflight_skip_reason"]


def test_a_follow_up_landing_without_a_merge_subject_still_closes_its_row(tmp_path: Path, monkeypatch) -> None:
    open_ledger = _frr_open_row_ledger()
    _frr_setup(tmp_path, open_ledger)
    vcs = _FrrVcs(spec_text=_FRR_REVIEWED_SPEC, origin_ledger=open_ledger)

    assert _frr_finalize(monkeypatch, tmp_path, vcs, followup_review_id=_FRR_ID) == 0

    assert "(dispatch-land finalize: the follow-up review landed)" in _frr_published_ledger(vcs)
    assert _frr_closed_id(tmp_path) == _FRR_ID


def test_main_forwards_the_follow_up_flags_and_only_them(monkeypatch, tmp_path: Path) -> None:
    from pyforge.marshal.dispatch_land_finalize import __main__ as mod

    seen: list[tuple] = []

    def _record(slug, key, worktree, **kwargs):
        seen.append((slug, key, worktree, kwargs))
        return 0

    monkeypatch.setattr(mod, "finalize_dispatch_land", _record)

    assert (
        mod.main(
            [
                "pyforge-marshal",
                "51.2",
                str(tmp_path),
                "--followup-review-id",
                "DW-FRR-51-2",
                "--landing-subject",
                "Merge pyforge-marshal/51-2 into main",
            ]
        )
        == 0
    )
    assert mod.main(["pyforge-marshal", "51.2", str(tmp_path), "--followup-review-id", "DW-FRR-51-2"]) == 0
    assert seen == [
        (
            "pyforge-marshal",
            "51.2",
            tmp_path,
            {"followup_review_id": "DW-FRR-51-2", "landing": "Merge pyforge-marshal/51-2 into main"},
        ),
        ("pyforge-marshal", "51.2", tmp_path, {"followup_review_id": "DW-FRR-51-2", "landing": None}),
    ]


def test_against_real_git_the_closure_is_published_onto_origin_mains_ledger(tmp_path: Path, monkeypatch) -> None:
    """The closure against REAL git, finalize end to end: a bare `origin`, a primary clone with a stale ledger and
    a second clone that lands the follow-up review of story 79.1 (its reviewed `done` spec, `done` twin and a
    ledger holding the open `DW-FRR-79-1` row beside a row a concurrent finalize published). The closure is
    published through the real `commit_paths_onto_remote_tip` onto origin/main's text; a second finalize is a no-op."""
    ledger_rel = f"_bmad-output/projects/{_SLUG_79}/planning-artifacts/deferred-work-ledger.md"
    twin_rel = f"_bmad-output/projects/{_SLUG_79}/planning-artifacts/sprint-status-ledger.yaml"
    stale = "# Deferred Work Ledger\n\n### DW-FU-1-1: old\n\n- source_spec: `x`\n  status: open\n"
    reviewed = _TRACKED_SPEC_79.replace("'backlog'", "'done'").replace(
        "---\n\n", "followup_review_recommended: false\n---\n\n", 1
    )
    from pyforge.marshal.core import deferred_work

    candidate = deferred_work.followup_review_candidate(
        reviewed.replace("recommended: false", "recommended: true"), normalize("79.1"), _SPEC_REL_79
    )
    assert candidate is not None
    open_row = deferred_work.render_followup_review_entry(candidate, promoted_date="2026-09-28")
    remote_ledger = deferred_work.append_ledger_entry(stale + _FRR_CONCURRENT_ROW, open_row)

    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git_79(origin, "init", "--bare", "-b", "main")
    primary = tmp_path / "primary"
    primary.mkdir()
    _git_79(primary, "init", "-b", "main")
    _configure_git_79(primary)
    (primary / ledger_rel).parent.mkdir(parents=True)
    (primary / ledger_rel).write_text(stale, encoding="utf-8")
    _git_79(primary, "add", ledger_rel)
    _git_79(primary, "commit", "-m", "base")
    _git_79(primary, "remote", "add", "origin", str(origin))
    _git_79(primary, "push", "-u", "origin", "main")

    landing = tmp_path / "landing"
    _git_79(tmp_path, "clone", str(origin), str(landing))
    _configure_git_79(landing)
    for rel, text in ((_SPEC_REL_79, reviewed), (twin_rel, _DONE_LEDGER_79), (ledger_rel, remote_ledger)):
        (landing / rel).parent.mkdir(parents=True, exist_ok=True)
        (landing / rel).write_text(text, encoding="utf-8")
        _git_79(landing, "add", rel)
    _git_79(landing, "commit", "-m", _DISPATCH_MERGE_79)
    landing_sha = _git_79(landing, "rev-parse", "HEAD").strip()
    _git_79(landing, "push", "origin", "main")

    worktree = tmp_path / "dispatch-worktree"
    _write_tracked_spec_79(worktree, text=reviewed)
    _write_feed_79(primary)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}.repo_root", lambda: primary)
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._scan_promotions", lambda *a, **k: _PlannedScan())
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._promote_sprint_ledger", lambda *a, **k: ())
    monkeypatch.setattr(f"{_FINALIZE_MOD_79}._resync_home_branch", lambda *a, **k: True)
    head_before = _git_79(primary, "rev-parse", "HEAD").strip()

    def _finalize() -> int:
        return finalize_dispatch_land(
            _SLUG_79,
            "79.1",
            worktree=worktree,
            process=_FakeIntakeProcess(returncode=0),
            clock=_FixedClock(),
            followup_review_id="DW-FRR-79-1",
            landing=_DISPATCH_MERGE_79,
        )

    assert _finalize() == 0

    published = _git_79(origin, "show", f"main:{ledger_rel}")
    assert published.count("### DW-FRR-79-1:") == 1
    # Only the follow-up row's own (last) `status: open` line moved; the concurrent row published since survives.
    head, _, tail = remote_ledger.rpartition("  status: open\n")
    closed_lines = f"  resolved: 2026-10-01 (dispatch-land finalize: {_DISPATCH_MERGE_79})\n  status: closed\n"
    assert published == head + closed_lines + tail
    assert "### DW-CONCURRENT-1:" in published
    assert _git_79(origin, "rev-parse", "main~1").strip() == landing_sha
    assert _git_79(origin, "diff", "--name-only", "main~1", "main").split() == [ledger_rel]
    # The story's key reads `done` in the tracked ledger throughout: the closure never touches it.
    assert _git_79(origin, "show", f"main:{twin_rel}") == _DONE_LEDGER_79
    assert _observation_79(primary)["followup_review_closed_id"] == "DW-FRR-79-1"
    assert (primary / ledger_rel).read_text(encoding="utf-8") == stale
    assert _git_79(primary, "status", "--porcelain", "--", ledger_rel) == ""
    assert _git_79(primary, "rev-parse", "HEAD").strip() == head_before

    tip = _git_79(origin, "rev-parse", "main").strip()
    assert _finalize() == 0
    assert _git_79(origin, "rev-parse", "main").strip() == tip


# -- Story 83.20: the atlas 27.1 finalize of 2026-10-03, replayed against real git ----------------------
#
# That finalize made local-main commit cb80aeac52 "marshal: promote 3 story spec(s) to tracked artifacts":
# three pre-rekey Tier-3 leftovers whose stories had landed under their OLD numbers (bmad-loop merges, August)
# and been promoted, then renamed by the 2026-09-17 rekey to new keys -- so the old numbers still read as
# merged and had no tracked spec under them. The fixture rebuilds that history in a real repository.

_ATLAS = "pyforge-atlas"
_ATLAS_DIR = f"_bmad-output/projects/{_ATLAS}"
_ATLAS_SPECS = f"{_ATLAS_DIR}/planning-artifacts/specs"
_ATLAS_LEDGER = f"{_ATLAS_DIR}/planning-artifacts/sprint-status-ledger.yaml"
_ATLAS_LANDED = "27-1-inventory-exports-refuse-hollow-sets-and-the-quartet-fails-loud"
#: (pre-rekey key, rekeyed key, the OLD number's real bmad-loop landing subject on `main`)
_ATLAS_REKEYED = (
    (
        "13-5-downstream-handoff-to-mason",
        "12-5-downstream-handoff-to-mason-fr-68",
        "Merge bmad-loop/20260809-184330-203b/13-5-downstream-handoff-to-mason into loop/pyforge-atlas (bmad-loop)",
    ),
    (
        "14-4-air-gap-asset-rewriting",
        "13-4-air-gap-asset-rewriting-cap-4",
        "Merge bmad-loop/20260815-112701-4285/14-4-air-gap-asset-rewriting into loop/pyforge-atlas (bmad-loop)",
    ),
    (
        "15-3-kedro-pipeline-surfacing",
        "14-3-kedro-pipeline-surfacing-cap-4",
        "Merge bmad-loop/20260815-112701-4285/15-3-kedro-pipeline-surfacing into loop/pyforge-atlas (bmad-loop)",
    ),
)


def _atlas_spec(old_key: str, body: str = "the landed spec") -> str:
    return f"---\ntitle: '{old_key}'\nstatus: 'done'\n---\n\n{body}\n"


def _atlas_ledger(*keys: str) -> str:
    return "development_status:\n" + "".join(f"  {key}: done\n" for key in keys)


def test_against_real_git_the_atlas_finalize_promotes_no_pre_rekey_tier3_spec(tmp_path: Path, monkeypatch) -> None:
    """AC 3: the three pre-rekey Tier-3 specs (two byte-identical to their rekeyed tracked twins, one older),
    the twins and their ledger rows, and the OLD numbers' bmad-loop landing subjects that make 13.5 / 14.4 /
    15.3 read as merged. The real finalize for 27.1 -- real scan, real promotion executor, real git -- makes
    no commit at all, reports three `MRS-DEPLOY-028` orphan findings, and leaves every Tier-3 file as it was."""
    from pyforge.marshal.core import promotion

    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git_79(origin, "init", "--bare", "-b", "main")
    primary = tmp_path / "primary"
    primary.mkdir()
    _git_79(primary, "init", "-b", "main")
    _configure_git_79(primary)
    (primary / ".gitignore").write_text("_bmad-output/projects/*/implementation-artifacts/\n", encoding="utf-8")
    specs = primary / _ATLAS_SPECS
    specs.mkdir(parents=True)
    # August: each story lands under its OLD number and its spec is promoted under that number.
    for old_key, _new_key, landing in _ATLAS_REKEYED:
        (specs / f"spec-{old_key}.md").write_text(_atlas_spec(old_key), encoding="utf-8")
        _git_79(primary, "add", "-A")
        _git_79(primary, "commit", "-m", landing)
    (primary / _ATLAS_LEDGER).write_text(_atlas_ledger(*(old for old, _new, _s in _ATLAS_REKEYED)), encoding="utf-8")
    _git_79(primary, "add", "-A")
    _git_79(primary, "commit", "-m", "atlas ledger")
    # 2026-09-17: the rekey renames the tracked specs and the ledger rows.
    for old_key, new_key, _landing in _ATLAS_REKEYED:
        _git_79(primary, "mv", f"{_ATLAS_SPECS}/spec-{old_key}.md", f"{_ATLAS_SPECS}/spec-{new_key}.md")
    (primary / _ATLAS_LEDGER).write_text(_atlas_ledger(*(new for _old, new, _s in _ATLAS_REKEYED)), encoding="utf-8")
    _git_79(primary, "add", "-A")
    _git_79(primary, "commit", "-m", "land atlas fold: one chain -- rekey 2026-09-17")
    # 2026-10-03: story 27.1 lands, its tracked spec done and its ledger row done.
    (specs / f"spec-{_ATLAS_LANDED}.md").write_text(_atlas_spec(_ATLAS_LANDED), encoding="utf-8")
    (primary / _ATLAS_LEDGER).write_text(
        _atlas_ledger(*(new for _old, new, _s in _ATLAS_REKEYED), _ATLAS_LANDED), encoding="utf-8"
    )
    _git_79(primary, "add", "-A")
    _git_79(primary, "commit", "-m", "Merge pyforge-atlas/27-1 into main")
    _git_79(primary, "remote", "add", "origin", str(origin))
    _git_79(primary, "push", "-u", "origin", "main")

    # The Tier-3 leftovers: two byte-identical to their rekeyed twins, the third older than its twin.
    tier3 = primary / _ATLAS_DIR / "implementation-artifacts"
    tier3.mkdir(parents=True)
    leftovers: dict[Path, str] = {}
    for index, (old_key, _new_key, _landing) in enumerate(_ATLAS_REKEYED):
        text = _atlas_spec(old_key) if index < 2 else _atlas_spec(old_key, "an older draft")
        leftovers[tier3 / f"spec-{old_key}.md"] = text
        (tier3 / f"spec-{old_key}.md").write_text(text, encoding="utf-8")
    (tier3 / "sprint-status.yaml").write_text(f"development_status:\n  {_ATLAS_LANDED}: done\n", encoding="utf-8")

    # The landing evidence that made the old numbers read as merged -- and no tracked spec under them.
    subjects = tuple(_git_79(primary, "log", "--format=%s", "main").splitlines())
    merged = promotion.merged_story_keys(subjects, "Merge {slug}/{key} into main", _ATLAS)
    assert {normalize("13.5"), normalize("14.4"), normalize("15.3")} <= merged
    assert not any((specs / f"spec-{old}.md").exists() for old, _new, _s in _ATLAS_REKEYED)

    head_before = _git_79(primary, "rev-parse", "HEAD").strip()
    origin_before = _git_79(origin, "rev-parse", "main").strip()
    tracked_before = sorted(path.name for path in specs.iterdir())
    _stub_real_scan_finalize(monkeypatch, primary, GitVcs())

    assert finalize_dispatch_land(_ATLAS, "27.1") == 0

    assert _git_79(primary, "rev-parse", "HEAD").strip() == head_before
    assert _git_79(origin, "rev-parse", "main").strip() == origin_before
    assert "marshal: promote" not in _git_79(primary, "log", "--format=%s", "--all")
    assert _git_79(primary, "status", "--porcelain") == ""
    assert sorted(path.name for path in specs.iterdir()) == tracked_before
    findings = _read_finalize_resync_entry(primary, _ATLAS)["payload"]["findings"]
    orphans = [finding for finding in findings if finding["code"] == "MRS-DEPLOY-028"]
    assert len(orphans) == 3
    for finding, (old_key, _new_key, _landing) in zip(orphans, _ATLAS_REKEYED, strict=True):
        assert finding["severity"] == "warn"
        assert f"spec-{old_key}.md" in finding["message"]
        assert "no ledger row" in finding["message"]
    assert [finding for finding in findings if finding["severity"] == "error"] == []
    for path, text in leftovers.items():
        assert path.read_text(encoding="utf-8") == text
