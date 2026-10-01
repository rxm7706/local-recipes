"""dispatch_land_finalize must pass CAP-5 ``base=`` into ledger promote."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.core.journal import Phase
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.refs import ORIGIN_MAIN
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
    from pyforge.marshal.core.identity import normalize
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
