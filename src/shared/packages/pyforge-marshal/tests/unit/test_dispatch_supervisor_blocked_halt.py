"""Unit tests for Story 51.11 (spec-pyforge-marshal CAP-258).

A session that halts ``blocked`` correctly -- code reverted, the tracked
spec flipped to ``status: blocked`` with an Auto Run Result -- but exits
before committing that halt must be classified ``blocked``, not
``stopped_externally``: the supervisor reads the worktree's own tracked
spec before attributing an unexplained exit to an operator stop. Scoped at
the same level ``test_dispatch_supervisor_spec_block.py`` establishes for
the sibling Story 51.4 helpers: the pure classifier and the commit/journal/
promote helpers directly, with a fake git port -- no real subprocess.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_completion import (
    DispatchGitFacts,
)
from pyforge.marshal.core.journal import Phase
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.dispatch_supervisor.__main__ import (
    _attempted_change_patch_paths,
    _blocked_halt_reason,
    _commit_and_journal_blocked_halt,
    _promote_blocked_twin,
)

_SLUG = "pyforge-marshal"
_STORY_KEY = "51.11"
_BASELINE = "c8277c03c117ff4779d54a2ff9d900f519415971"


class FakeFs:
    """Mirrors ``test_dispatch_supervisor_spec_block.py``'s FakeFs -- reads
    through to the real tree since the tracked-spec resolution helpers glob
    real files on disk."""

    def __init__(self, *, raise_fs_error_for: frozenset[Path] = frozenset()) -> None:
        self.files: dict[Path, str] = {}
        self.appended: list[tuple[Path, str, bool]] = []
        self._raise_fs_error_for = raise_fs_error_for

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))
        text = self.files.get(path, "")
        if text and not text.endswith("\n"):
            text += "\n"
        self.files[path] = text + line + "\n"

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content

    def read_text(self, path: Path) -> str | None:
        if path in self._raise_fs_error_for:
            raise FsError(f"cannot read {path} (test double)")
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None


class FakeVcs:
    def __init__(
        self,
        *,
        changed: tuple[str, ...] = (),
        changed_files_raises: bool = False,
        commit_paths_raises: bool = False,
        commit_paths_onto_remote_tip_raises: bool = False,
    ) -> None:
        self.changed = changed
        self.changed_files_raises = changed_files_raises
        self.commit_paths_raises = commit_paths_raises
        self.commit_paths_onto_remote_tip_raises = commit_paths_onto_remote_tip_raises
        self.commit_paths_calls: list[tuple[Path, tuple[Path, ...], str]] = []
        self.isolated_promote_calls: list[tuple] = []

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
        if self.changed_files_raises:
            raise VcsCommandError("git diff failed (test double)")
        return self.changed

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: str) -> str:
        if self.commit_paths_raises:
            raise VcsCommandError("git commit failed (test double)")
        self.commit_paths_calls.append((repo_root, paths, message))
        return "committed-sha"

    def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message):
        self.isolated_promote_calls.append((repo_root, remote, ref, tuple(writes), message))
        if self.commit_paths_onto_remote_tip_raises:
            raise VcsCommandError("git push failed: non-fast-forward (test double)")
        return "isolated-promote-sha"


def _git_facts(*, baseline_head_sha: str = _BASELINE) -> DispatchGitFacts:
    return DispatchGitFacts(
        baseline_head_sha=baseline_head_sha,
        current_head_sha="feature0002",
        changed_paths=(),
        branch_merged=False,
        story_merged_on_main=False,
    )


def _seed_spec(*, repo_root: Path, worktree: Path, slug: str, story_key: str, text: str) -> str:
    specs_dir = dispatch_core.planning_specs_dir(repo_root, slug)
    specs_dir.mkdir(parents=True, exist_ok=True)
    key = story_key.replace(".", "-")
    spec_path = specs_dir / f"spec-{key}.md"
    spec_path.write_text(text, encoding="utf-8")
    relocated = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree)
    relocated.parent.mkdir(parents=True, exist_ok=True)
    relocated.write_text(text, encoding="utf-8")
    return str(relocated.resolve().relative_to(worktree.resolve()))


def _worktree(tmp_path: Path, slug: str = _SLUG) -> Path:
    return tmp_path / ".worktrees" / f"dispatch-{slug}"


_BLOCKED_SPEC_TEXT = (
    "---\n"
    "status: blocked\n"
    f"baseline_revision: '{_BASELINE}'\n"
    'blocking_condition: "an intent gap"\n'
    "---\n\n"
    "## Auto Run Result\n\n"
    "Status: escalated\n"
)


# --------------------------------------------------------------------------
# _blocked_halt_reason (the four I/O matrix rows)
# --------------------------------------------------------------------------


def test_blocked_halt_reason_doctor_26_1_replay(tmp_path: Path) -> None:
    """Row 1: a genuine self-halt -- blocked, ARR, baseline matches."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text=_BLOCKED_SPEC_TEXT,
    )

    reason, stale = _blocked_halt_reason(
        fs=fs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=_git_facts(),
    )

    assert reason == "an intent gap"
    assert stale is False


def test_blocked_halt_reason_operator_kill_no_signal(tmp_path: Path) -> None:
    """Row 2: clean tree, spec ``in-progress`` -- no blocked signal at all."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text="---\nstatus: in-progress\n---\n",
    )

    reason, stale = _blocked_halt_reason(
        fs=fs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=_git_facts(),
    )

    assert reason is None
    assert stale is False


def test_blocked_halt_reason_stale_baseline_mismatch(tmp_path: Path) -> None:
    """Row 4: spec ``blocked`` but the ARR's baseline predates this run --
    never re-attribute a stale blocked spec from an earlier dispatch pass."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text=_BLOCKED_SPEC_TEXT,
    )

    reason, stale = _blocked_halt_reason(
        fs=fs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=_git_facts(baseline_head_sha="some-other-run-baseline"),
    )

    assert reason is None
    assert stale is True


def test_stale_blocked_finding_code_is_registered() -> None:
    """The tick loop's ``elif stale:`` branch constructs a Finding with code
    ``MRS-DISP-046`` (never exercised by ``_blocked_halt_reason`` alone,
    which only returns the ``stale`` flag) -- registration lives in
    findings.py/verdict.py, not in this helper, so this is the one place
    that would have caught the code being unregistered: ``Finding.__post_init__``
    raises ``UnregisteredFindingCodeError`` for any unregistered code."""
    finding = Finding(
        code="MRS-DISP-046",
        severity=Severity.WARN,
        message="stale blocked spec baseline mismatch",
    )
    assert finding.code == "MRS-DISP-046"


def test_blocked_halt_reason_no_signal_when_no_spec(tmp_path: Path) -> None:
    fs = FakeFs()
    worktree = _worktree(tmp_path)

    reason, stale = _blocked_halt_reason(
        fs=fs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key="99.9",
        worktree=worktree,
        git_facts=_git_facts(),
    )

    assert reason is None
    assert stale is False


def test_blocked_halt_reason_no_signal_without_auto_run_result(tmp_path: Path) -> None:
    """A bare ``status: blocked`` with no ARR section is not enough signal
    that the harness itself (rather than a hand edit) produced this halt."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text=f"---\nstatus: blocked\nbaseline_revision: '{_BASELINE}'\n---\n",
    )

    reason, stale = _blocked_halt_reason(
        fs=fs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=_git_facts(),
    )

    assert reason is None
    assert stale is False


# --------------------------------------------------------------------------
# _attempted_change_patch_paths
# --------------------------------------------------------------------------


def test_attempted_change_patch_paths_finds_patch_outside_tier3(tmp_path: Path) -> None:
    worktree = _worktree(tmp_path)
    scratch = worktree / "scratch"
    scratch.mkdir(parents=True)
    patch = scratch / "51-11-attempted-change.patch"
    patch.write_text("diff --git a/x b/x\n", encoding="utf-8")

    found = _attempted_change_patch_paths(worktree)

    assert found == (patch,)


def test_attempted_change_patch_paths_excludes_implementation_artifacts(
    tmp_path: Path,
) -> None:
    """Tier-3 (``implementation-artifacts/``) is the backlinked store that
    already survives worktree teardown on the primary checkout and must
    never be git-tracked -- a patch there is never picked up here."""
    worktree = _worktree(tmp_path)
    tier3 = worktree / "_bmad-output" / "projects" / _SLUG / "implementation-artifacts"
    tier3.mkdir(parents=True)
    (tier3 / "51-11-attempted-change.patch").write_text("diff\n", encoding="utf-8")

    found = _attempted_change_patch_paths(worktree)

    assert found == ()


# --------------------------------------------------------------------------
# _commit_and_journal_blocked_halt
# --------------------------------------------------------------------------


def test_commit_and_journal_blocked_halt_commits_and_journals(tmp_path: Path) -> None:
    fs = FakeFs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    journal_path = run_dir / "journal.jsonl"
    fs.files[journal_path] = ""
    worktree = _worktree(tmp_path)
    worktree.mkdir(parents=True)
    vcs = FakeVcs(changed=("spec-51-11.md",))

    counter, committed = _commit_and_journal_blocked_halt(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id="run-51-11",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        reason="an intent gap",
    )

    assert committed is True
    assert counter == 2
    assert len(vcs.commit_paths_calls) == 1
    entries = [json.loads(line) for line in fs.files[journal_path].splitlines()]
    assert entries[0]["kind"] == dispatch_core.KIND_DISPATCH_BLOCKED
    assert entries[0]["phase"] == Phase.INTENT.value
    assert entries[1]["payload"]["reason"] == "an intent gap"
    assert entries[1]["payload"]["ok"] is True


def test_commit_and_journal_blocked_halt_also_commits_attempted_change_patch(
    tmp_path: Path,
) -> None:
    fs = FakeFs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    fs.files[run_dir / "journal.jsonl"] = ""
    worktree = _worktree(tmp_path)
    scratch = worktree / "scratch"
    scratch.mkdir(parents=True)
    (scratch / "51-11-attempted-change.patch").write_text("diff\n", encoding="utf-8")
    vcs = FakeVcs(changed=("spec-51-11.md",))

    counter, committed = _commit_and_journal_blocked_halt(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id="run-51-11",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        reason="an intent gap",
    )

    assert committed is True
    committed_paths = vcs.commit_paths_calls[0][1]
    assert Path("scratch/51-11-attempted-change.patch") in committed_paths


def test_commit_and_journal_blocked_halt_never_widens_on_commit_failure(
    tmp_path: Path,
) -> None:
    """The classifier must never claim a durable blocked record without one
    -- narrows, never widens (spec Always bullet 1)."""
    fs = FakeFs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    fs.files[run_dir / "journal.jsonl"] = ""
    worktree = _worktree(tmp_path)
    worktree.mkdir(parents=True)
    vcs = FakeVcs(changed=("spec-51-11.md",), commit_paths_raises=True)

    counter, committed = _commit_and_journal_blocked_halt(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id="run-51-11",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        reason="an intent gap",
    )

    assert committed is False
    assert counter == 0
    assert fs.files[run_dir / "journal.jsonl"] == ""


def test_commit_and_journal_blocked_halt_false_when_nothing_changed(
    tmp_path: Path,
) -> None:
    fs = FakeFs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    fs.files[run_dir / "journal.jsonl"] = ""
    worktree = _worktree(tmp_path)
    worktree.mkdir(parents=True)
    vcs = FakeVcs(changed=())

    counter, committed = _commit_and_journal_blocked_halt(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id="run-51-11",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        reason="an intent gap",
    )

    assert committed is False
    assert counter == 0


# --------------------------------------------------------------------------
# _promote_blocked_twin
# --------------------------------------------------------------------------


def test_promote_blocked_twin_pushes_worktree_text_onto_primary(
    tmp_path: Path,
) -> None:
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    relative = _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text="---\nstatus: in-progress\n---\n",
    )
    worktree_spec_path = worktree / relative
    worktree_spec_path.write_text(_BLOCKED_SPEC_TEXT, encoding="utf-8")
    vcs = FakeVcs()

    _promote_blocked_twin(
        fs=fs,
        vcs=vcs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
    )

    assert len(vcs.isolated_promote_calls) == 1
    _repo_root, remote, ref, writes, _message = vcs.isolated_promote_calls[0]
    assert remote == "origin"
    assert ref == "main"
    assert writes[0][1] == _BLOCKED_SPEC_TEXT


def test_promote_blocked_twin_noop_when_already_matching(tmp_path: Path) -> None:
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text=_BLOCKED_SPEC_TEXT,
    )
    vcs = FakeVcs()

    _promote_blocked_twin(
        fs=fs,
        vcs=vcs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
    )

    assert vcs.isolated_promote_calls == []


def test_promote_blocked_twin_never_raises_on_push_failure(tmp_path: Path) -> None:
    """Best-effort: a failed remote promotion must not unwind the
    already-committed blocked verdict (spec: "must not unwind")."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    relative = _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text="---\nstatus: in-progress\n---\n",
    )
    (worktree / relative).write_text(_BLOCKED_SPEC_TEXT, encoding="utf-8")
    vcs = FakeVcs(commit_paths_onto_remote_tip_raises=True)

    _promote_blocked_twin(
        fs=fs,
        vcs=vcs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
    )  # must not raise

    assert len(vcs.isolated_promote_calls) == 1


def test_promote_blocked_twin_noop_when_no_spec_resolves(tmp_path: Path) -> None:
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    vcs = FakeVcs()

    _promote_blocked_twin(
        fs=fs,
        vcs=vcs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key="99.9",
        worktree=worktree,
    )

    assert vcs.isolated_promote_calls == []


def test_promote_blocked_twin_never_raises_on_worktree_read_fs_error(
    tmp_path: Path,
) -> None:
    """Best-effort per its own docstring ("Never raises") -- an FsError
    reading the worktree's own spec (permission denied, corrupt encoding)
    must not escape and unwind the already-committed blocked verdict."""
    worktree = _worktree(tmp_path)
    relative = _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text=_BLOCKED_SPEC_TEXT,
    )
    fs = FakeFs(raise_fs_error_for=frozenset({worktree / relative}))
    vcs = FakeVcs()

    _promote_blocked_twin(
        fs=fs,
        vcs=vcs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
    )  # must not raise

    assert vcs.isolated_promote_calls == []


def test_promote_blocked_twin_never_raises_on_primary_read_fs_error(
    tmp_path: Path,
) -> None:
    """Same guarantee for the primary checkout's tracked twin read."""
    worktree = _worktree(tmp_path)
    _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text=_BLOCKED_SPEC_TEXT,
    )
    specs_dir = dispatch_core.planning_specs_dir(tmp_path, _SLUG)
    primary_spec_path = specs_dir / f"spec-{_STORY_KEY.replace('.', '-')}.md"
    fs = FakeFs(raise_fs_error_for=frozenset({primary_spec_path}))
    vcs = FakeVcs()

    _promote_blocked_twin(
        fs=fs,
        vcs=vcs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
    )  # must not raise

    assert vcs.isolated_promote_calls == []
