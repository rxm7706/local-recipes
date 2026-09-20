"""Unit tests for Story 51.4 (spec-pyforge-marshal CAP-252).

A blocked outcome must never land: a deliberate ``status: blocked`` worktree
spec (the 27.3 incident) or a diff that collapses to just the tracked spec
file itself -- narration, not work (the 51.3 incident) -- must stop the
supervisor before verify/land, never trust a session's self-report, and
never invent a second gate/verdict owner. Scoped at the level
``test_dispatch_push.py`` already establishes for sibling CAP-4 helpers:
the pure spec-reading helpers and the land-vs-block gate directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_completion import DispatchGitFacts
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.journal import Phase
from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main
from pyforge.marshal.dispatch_supervisor.__main__ import (
    _journal_dispatch_blocked,
    _land_or_journal_block,
    _spec_land_block_reason,
    _worktree_story_spec,
)

_SLUG = "pyforge-marshal"
_STORY_KEY = "51.4"
_MERGE_SUBJECT_TEMPLATE = "marshal: land {slug} {story_key}"


class FakeFs:
    """Mirrors ``test_dispatch_push.py``'s FakeFs; ``read_text`` reads
    through to the real tree since the tracked-spec resolution helpers glob
    real files on disk, not a fake filesystem."""

    def __init__(self) -> None:
        self.files: dict[Path, str] = {}
        self.appended: list[tuple[Path, str, bool]] = []

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))
        text = self.files.get(path, "")
        if text and not text.endswith("\n"):
            text += "\n"
        self.files[path] = text + line + "\n"

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content

    def read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None


def _git_facts(*, changed_paths: tuple[str, ...] = ()) -> DispatchGitFacts:
    return DispatchGitFacts(
        baseline_head_sha="baseline0001",
        current_head_sha="story0002",
        changed_paths=changed_paths,
        branch_merged=False,
        story_merged_on_main=False,
    )


def _seed_spec(*, repo_root: Path, worktree: Path, slug: str, story_key: str, text: str) -> str:
    """Write the tracked spec at its repo-root path AND its worktree-relocated
    copy (real files on disk -- ``resolve_story_spec_path`` globs the real
    filesystem). Returns the worktree-relative path."""
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


# --------------------------------------------------------------------------
# _worktree_story_spec
# --------------------------------------------------------------------------


def test_worktree_story_spec_resolves_relocated_relative_path_and_text(
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

    resolved_relative, text = _worktree_story_spec(
        fs=fs, repo_root=tmp_path, slug=_SLUG, story_key=_STORY_KEY, worktree=worktree
    )

    assert resolved_relative == relative
    assert text == "---\nstatus: in-progress\n---\n"


def test_worktree_story_spec_no_signal_is_none_none(tmp_path: Path) -> None:
    """No tracked spec at all resolves to (None, None) -- "no signal" is
    never read as "blocked" by any caller."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)

    relative, text = _worktree_story_spec(fs=fs, repo_root=tmp_path, slug=_SLUG, story_key="99.9", worktree=worktree)

    assert relative is None
    assert text is None


# --------------------------------------------------------------------------
# _spec_land_block_reason
# --------------------------------------------------------------------------


def test_spec_land_block_reason_blocks_on_deliberate_status(tmp_path: Path) -> None:
    """The 27.3 incident: a deliberate ``status: blocked`` always blocks,
    regardless of changed-path count."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text='---\nstatus: blocked\nblocking_condition: "an intent gap"\n---\n',
    )

    reason = _spec_land_block_reason(
        fs=fs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=_git_facts(changed_paths=()),
    )

    assert reason == "an intent gap"


def test_spec_land_block_reason_blocks_on_narration_only_diff(tmp_path: Path) -> None:
    """The 51.3 incident: a diff that collapses to just the tracked spec's
    own path blocks even when the spec's own status is not ``blocked``."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    relative = _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text="---\nstatus: in-progress\n---\n",
    )

    reason = _spec_land_block_reason(
        fs=fs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=_git_facts(changed_paths=(relative,)),
    )

    assert reason == "harness produced no changes beyond the tracked spec"


def test_spec_land_block_reason_allows_real_changed_path_progress(
    tmp_path: Path,
) -> None:
    """Regression safety: real work alongside the spec is not narration-only
    and must not block -- an implementation with changed paths lands exactly
    as today."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)
    relative = _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text="---\nstatus: in-progress\n---\n",
    )

    reason = _spec_land_block_reason(
        fs=fs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=_git_facts(changed_paths=(relative, "src/real_change.py")),
    )

    assert reason is None


def test_spec_land_block_reason_no_signal_never_blocks(tmp_path: Path) -> None:
    """An unresolvable spec is "no signal", never "blocked"."""
    fs = FakeFs()
    worktree = _worktree(tmp_path)

    reason = _spec_land_block_reason(
        fs=fs,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key="99.9",
        worktree=worktree,
        git_facts=_git_facts(changed_paths=()),
    )

    assert reason is None


# --------------------------------------------------------------------------
# _journal_dispatch_blocked
# --------------------------------------------------------------------------


def test_journal_dispatch_blocked_writes_intent_and_outcome(tmp_path: Path) -> None:
    fs = FakeFs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    journal_path = run_dir / "journal.jsonl"
    fs.files[journal_path] = ""
    worktree = _worktree(tmp_path)

    counter = _journal_dispatch_blocked(
        fs=fs,
        run_dir=run_dir,
        run_id="run-51-4",
        writer_id="test-writer",
        counter=0,
        story_key=_STORY_KEY,
        worktree=worktree,
        reason="an intent gap was found",
    )

    assert counter == 2
    lines = fs.files[journal_path].splitlines()
    assert len(lines) == 2
    entries = [json.loads(line) for line in lines]
    assert entries[0]["kind"] == dispatch_core.KIND_DISPATCH_BLOCKED
    assert entries[0]["phase"] == Phase.INTENT.value
    assert entries[0]["payload"]["story_key"] == _STORY_KEY
    assert entries[1]["kind"] == dispatch_core.KIND_DISPATCH_BLOCKED
    assert entries[1]["phase"] == Phase.OUTCOME.value
    assert entries[1]["payload"]["reason"] == "an intent gap was found"
    assert entries[1]["payload"]["ok"] is True


# --------------------------------------------------------------------------
# _land_or_journal_block
# --------------------------------------------------------------------------


def test_land_or_journal_block_skips_landing_when_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation-test shape (Story 51.4's own AC): prove the guard is
    load-bearing by making the landing call raise if it is ever reached for
    a blocked spec -- removing the guard would surface here immediately."""

    def _boom(**kwargs: object) -> int:
        raise AssertionError("landing must not be attempted for a blocked spec")

    monkeypatch.setattr(supervisor_main, "_run_and_journal_landing", _boom)

    fs = FakeFs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    journal_path = run_dir / "journal.jsonl"
    fs.files[journal_path] = ""
    worktree = _worktree(tmp_path)
    _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text='---\nstatus: blocked\nblocking_condition: "an intent gap"\n---\n',
    )

    counter = _land_or_journal_block(
        fs=fs,
        vcs=None,
        process=None,
        run_dir=run_dir,
        run_id="run-51-4",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=_git_facts(changed_paths=()),
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        merge_subject_template=_MERGE_SUBJECT_TEMPLATE,
    )

    assert counter == 2
    entries = [json.loads(line) for line in fs.files[journal_path].splitlines()]
    assert entries[0]["kind"] == dispatch_core.KIND_DISPATCH_BLOCKED
    assert entries[1]["payload"]["reason"] == "an intent gap"


def test_land_or_journal_block_lands_through_unchanged_when_not_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An implementation with real changed paths lands exactly as today:
    ``_land_or_journal_block`` delegates straight to
    ``_run_and_journal_landing`` with the same arguments it received."""
    recorded: dict[str, object] = {}

    def _fake_land(**kwargs: object) -> int:
        recorded.update(kwargs)
        return 99

    monkeypatch.setattr(supervisor_main, "_run_and_journal_landing", _fake_land)

    fs = FakeFs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    worktree = _worktree(tmp_path)
    relative = _seed_spec(
        repo_root=tmp_path,
        worktree=worktree,
        slug=_SLUG,
        story_key=_STORY_KEY,
        text="---\nstatus: in-progress\n---\n",
    )
    facts = _git_facts(changed_paths=(relative, "src/real_change.py"))

    counter = _land_or_journal_block(
        fs=fs,
        vcs=None,
        process=None,
        run_dir=run_dir,
        run_id="run-51-4",
        writer_id="test-writer",
        counter=0,
        repo_root=tmp_path,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=facts,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        merge_subject_template=_MERGE_SUBJECT_TEMPLATE,
    )

    assert counter == 99
    assert recorded["story_key"] == _STORY_KEY
    assert recorded["verification_verdict"] == DispatchVerificationVerdict.VERIFIED
    assert recorded["worktree"] == worktree
