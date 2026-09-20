"""dispatch_land_finalize must pass CAP-5 ``base=`` into ledger promote."""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.core.process import ProcessError, ProcessResult
from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.core.journal import Phase
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.dispatch_land_finalize.__main__ import (
    _FINALIZE_RESYNC_KIND,
    _run_deferred_work_intake,
    finalize_dispatch_land,
)


class _StubVcs:
    """Story 51.9: production now calls ``vcs.has_uncommitted_changes(root)``
    directly, before ever reaching a monkeypatched ``_resync_home_branch`` --
    a bare ``object()`` can't take new attributes, so these tests (which
    aren't exercising vcs behavior itself) need this minimal fake instead."""

    def __init__(self, *, dirty: bool = False) -> None:
        self.dirty = dirty

    def has_uncommitted_changes(self, _worktree_path: Path) -> bool:
        return self.dirty


def _read_finalize_resync_entry(tmp_path: Path, slug: str) -> dict:
    """Read back the single ``_FINALIZE_RESYNC_KIND`` journal entry written
    under ``tmp_path``'s real (unstubbed) ``LocalFs`` for this test run."""
    runs_dir = (
        tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs"
    )
    run_dirs = list(runs_dir.iterdir())
    assert len(run_dirs) == 1
    lines = (run_dirs[0] / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines if line]
    matches = [entry for entry in entries if entry["kind"] == _FINALIZE_RESYNC_KIND]
    assert len(matches) == 1
    return matches[0]


def test_finalize_passes_base_main_to_isolated_promote(
    tmp_path: Path, monkeypatch
) -> None:
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


def test_finalize_forwards_worktree_to_scan_promotions(
    tmp_path: Path, monkeypatch
) -> None:
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


def test_finalize_resyncs_the_primary_after_ledger_promotion(
    tmp_path: Path, monkeypatch
) -> None:
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


def test_finalize_skips_resync_on_a_dirty_primary(
    tmp_path: Path, monkeypatch
) -> None:
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

    def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message):
        self.calls.append(
            {"repo_root": repo_root, "remote": remote, "ref": ref, "writes": writes,
             "message": message}
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
    assert _run_deferred_work_intake(process, fs, vcs, tmp_path, "pyforge-steward") is None
    [argv], [cwd] = zip(*process.calls)
    assert argv[-2:] == ["--project", "steward"]
    assert "--fix" in argv
    assert cwd == tmp_path
    assert vcs.calls == []


def test_run_deferred_work_intake_refusal_returns_warn_finding(tmp_path: Path) -> None:
    process = _FakeIntakeProcess(returncode=1, stderr="no resolvable location:")
    fs = LocalFs()
    vcs = _FakeIntakeVcs()
    finding = _run_deferred_work_intake(process, fs, vcs, tmp_path, "pyforge-marshal")
    assert finding is not None
    assert finding.code == "MRS-DISP-047"
    assert finding.severity == Severity.WARN
    assert "marshal" in finding.message
    assert "no resolvable location:" in finding.message
    assert vcs.calls == []


def test_run_deferred_work_intake_process_error_returns_warn_finding(tmp_path: Path) -> None:
    fs = LocalFs()
    vcs = _FakeIntakeVcs()
    finding = _run_deferred_work_intake(
        _RaisingIntakeProcess(), fs, vcs, tmp_path, "pyforge-doctor"
    )
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
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
        / "deferred-work-ledger.md"
    )
    tracked_path.parent.mkdir(parents=True)
    tracked_path.write_text("# Deferred Work Ledger\n\nold entry\n", encoding="utf-8")

    class _WritingProcess:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], Path]] = []

        def run(self, tokens, *, cwd: Path):
            self.calls.append((list(tokens), cwd))
            tracked_path.write_text(
                "# Deferred Work Ledger\n\nold entry\n\nnew entry\n", encoding="utf-8"
            )
            return ProcessResult(returncode=0, stdout="", stderr="")

    process = _WritingProcess()
    fs = LocalFs()
    vcs = _FakeIntakeVcs()
    finding = _run_deferred_work_intake(process, fs, vcs, tmp_path, "pyforge-marshal")
    assert finding is None
    assert len(vcs.calls) == 1
    call = vcs.calls[0]
    assert call["remote"] == "origin"
    assert call["ref"] == "main"
    assert call["writes"] == (
        (
            "_bmad-output/projects/pyforge-marshal/planning-artifacts/"
            "deferred-work-ledger.md",
            "# Deferred Work Ledger\n\nold entry\n\nnew entry\n",
        ),
    )
    # root's own working tree is restored to the pre-`--fix` text.
    assert tracked_path.read_text(encoding="utf-8") == "# Deferred Work Ledger\n\nold entry\n"


def test_run_deferred_work_intake_warns_when_publish_fails(tmp_path: Path) -> None:
    """Story 53.2 review (B5): a failed publish to ``origin/main`` is a
    WARN, never a crash -- and the local working tree is still restored."""
    tracked_path = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
        / "deferred-work-ledger.md"
    )
    tracked_path.parent.mkdir(parents=True)
    tracked_path.write_text("old\n", encoding="utf-8")

    class _WritingProcess:
        def run(self, tokens, *, cwd: Path):
            tracked_path.write_text("new\n", encoding="utf-8")
            return ProcessResult(returncode=0, stdout="", stderr="")

    fs = LocalFs()
    vcs = _FakeIntakeVcs(raises=True)
    finding = _run_deferred_work_intake(
        _WritingProcess(), fs, vcs, tmp_path, "pyforge-marshal"
    )
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

    def _fake_intake(process, fs, vcs, root, project_slug):
        seen["intake_args"] = (root, project_slug)
        return Finding(code="MRS-DISP-047", severity=Severity.ERROR, message="forced for test")

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._run_deferred_work_intake",
        _fake_intake,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 1
    assert seen["intake_args"] == (tmp_path, "pyforge-steward")


def test_finalize_stays_green_when_intake_returns_no_finding(
    tmp_path: Path, monkeypatch
) -> None:
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

    def _fake_intake(process, fs, vcs, root, project_slug):
        seen["called"] = True
        return None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._run_deferred_work_intake",
        _fake_intake,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    assert seen["called"] is True


def test_finalize_journals_the_intake_finding_into_the_resync_payload(
    tmp_path: Path, monkeypatch
) -> None:
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

    def _fake_intake(process, fs, vcs, root, project_slug):
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


def test_finalize_journals_a_null_intake_finding_when_intake_is_clean(
    tmp_path: Path, monkeypatch
) -> None:
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
        lambda process, fs, vcs, root, project_slug: None,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    entry = _read_finalize_resync_entry(tmp_path, "pyforge-steward")
    assert entry["payload"]["deferred_work_intake_finding"] is None
