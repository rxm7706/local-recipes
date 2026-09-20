"""Unit tests for Story 22.5 station in-flight guard and overlap advisory."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest
from scope_triangle import point_scope_triangle

from pyforge.marshal.cli.dispatch import (
    cross_station_surface_overlap_advisories,
    gather_dispatch_journal_facts,
    run_dispatch,
    station_in_flight_conflict,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.journal import (
    SCOPE_VIOLATION_ADVISORIES_FIELD,
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    prepare_for_write,
    prepare_for_write_offloading_fields,
    sidecar_texts_for_lines,
)
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.dispatch_supervisor.__main__ import _verification_outcome_verdict
from pyforge.marshal.ports.build_harness import DispatchLaunchResult, HarnessResolution


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
        return path in self.dirs or path.is_dir()

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def create_dir_exclusive(self, path: Path) -> None:
        self.dirs.add(path)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))
        self.files[path] = self.files.get(path, "") + line

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content

    def read_text(self, path: Path) -> str | None:
        if path in self.files:
            return self.files[path]
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None


class FakeVcs:
    def __init__(self, repo_root: Path, *, head_sha: str = "baseline1234") -> None:
        self.repo_root = repo_root
        self.head_sha = head_sha
        self.added: list[tuple[Path, Path, str, str]] = []

    def repo_common_root(self, _cwd: Path) -> Path:
        return self.repo_root

    def branch_exists(self, _repo_root: Path, _branch: str) -> bool:
        return False

    def worktree_path_for_branch(self, _repo_root: Path, _branch: str) -> Path | None:
        return None

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        self.added.append((repo_root, home, branch, base))
        home.mkdir(parents=True, exist_ok=True)

    def worktree_head_sha(self, _worktree: Path) -> str:
        return self.head_sha


class FakeBuildHarness:
    def binary_present(self, preference=(), repo_root=None) -> HarnessResolution:
        chosen = next(iter(preference), "claude")
        return HarnessResolution(profile=chosen, binary_path=f"/usr/bin/{chosen}")

    def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
        return DispatchLaunchResult(
            pid=6060,
            command=("fake-harness",),
            model=kwargs.get("model"),
            budget_env=dict(kwargs.get("budget_env") or {}),
        )


class FakeProcess:
    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive

    def is_alive(self, _pid: int) -> bool:
        return self.alive

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        return 6061


def _seed_live_dispatch_journal(
    tmp_path: Path,
    fs: FakeFs,
    *,
    slug: str,
    run_id: str,
    story_key: str,
    session_pid: int = 42,
) -> Path:
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    journal_path = run_dir / "journal.jsonl"
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-08-23T00:00:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": story_key,
                "worktree_path": str(tmp_path / "wt"),
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-08-23T00:00:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": session_pid},
        )
    ).line
    journal_text = intent + "\n" + outcome + "\n"
    journal_path.write_text(journal_text, encoding="utf-8")
    fs.files[journal_path] = journal_text
    return run_dir


def test_declared_globs_overlap_detects_shared_prefix() -> None:
    assert dispatch_core.declared_globs_overlap("src/pkg/**", "src/pkg/foo.py")
    assert not dispatch_core.declared_globs_overlap("src/a/**", "src/b/**")


def test_serial_mode_still_refuses_unrelated_live_story(tmp_path: Path) -> None:
    """``max_parallel=1`` stays byte-identical: any LIVE story blocks."""
    from pyforge.marshal.cli.dispatch import _compose_policy

    slug = "pyforge-marshal"
    fs = FakeFs()
    _seed_live_dispatch_journal(tmp_path, fs, slug=slug, run_id="run-live", story_key="22.1")

    class LiveVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            return ("src/changed.py",)

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

        def worktree_head_sha(self, worktree_path: Path) -> str:
            return "bbb222"

    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=LiveVcs(tmp_path),
        process=FakeProcess(alive=True),
        repo_root=tmp_path,
        slug=slug,
        story_key="22-5-one-story-in-flight",
        effective_policy=_compose_policy(slug),
    )
    assert conflict is not None
    assert conflict.code == "MRS-DISP-021"


def test_unrelated_live_story_allowed_without_surface_data(
    tmp_path: Path,
) -> None:
    """Story 28.16: unrelated LIVE stories no longer blanket-refuse."""
    from pyforge.marshal.cli.dispatch import _compose_policy

    slug = "pyforge-marshal"
    fs = FakeFs()
    _seed_live_dispatch_journal(tmp_path, fs, slug=slug, run_id="run-live", story_key="22.1")

    class LiveVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            return ("src/changed.py",)

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

        def worktree_head_sha(self, worktree_path: Path) -> str:
            return "bbb222"

    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=LiveVcs(tmp_path),
        process=FakeProcess(alive=False),
        repo_root=tmp_path,
        slug=slug,
        story_key="22-5-one-story-in-flight",
        effective_policy=_compose_policy(slug),
        parallel_dispatch=True,
    )
    assert conflict is None


def test_surface_overlap_refuses_second_dispatch(tmp_path: Path) -> None:
    from pyforge.marshal.cli.dispatch import _compose_policy

    slug = "pyforge-marshal"
    fs = FakeFs()
    specs = tmp_path / "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs"
    specs.mkdir(parents=True)
    live_spec = specs / "spec-22-1-live.md"
    live_spec.write_text(
        '---\nsurface: ["src/shared/packages/pyforge-marshal/**"]\n---\n',
        encoding="utf-8",
    )
    cand_spec = specs / "spec-22-5-candidate.md"
    # AD-27 effective surface is policy ∩ spec (exact glob strings). The
    # candidate must declare a glob that survives intersection with the
    # auto-derived default so overlap is judged on effective surfaces.
    cand_spec.write_text(
        '---\nsurface: ["src/shared/packages/pyforge-marshal/**"]\n---\n',
        encoding="utf-8",
    )
    _seed_live_dispatch_journal(tmp_path, fs, slug=slug, run_id="run-live", story_key="22.1")

    class LiveVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            return ("src/changed.py",)

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

        def worktree_head_sha(self, worktree_path: Path) -> str:
            return "bbb222"

    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=LiveVcs(tmp_path),
        process=FakeProcess(alive=True),
        repo_root=tmp_path,
        slug=slug,
        story_key="22-5-one-story-in-flight",
        effective_policy=_compose_policy(slug),
        candidate_spec_text=cand_spec.read_text(encoding="utf-8"),
        parallel_dispatch=True,
    )
    assert conflict is not None
    assert conflict.code == "MRS-DISP-034"
    assert conflict.overlap_paths


def test_redispatch_allowed_when_session_dead_and_verification_refused(
    tmp_path: Path,
) -> None:
    """Regression (2026-08-29, atlas Story 21.1): a crashed dispatch
    supervisor left ``dispatch_verification_verdict: refused`` +
    ``session_alive: false`` in the journal, but the redispatch-refusal
    check only consulted git.changed_paths (nonzero forever once any real
    edit landed before the crash), so it kept refusing redispatch of the
    SAME story indefinitely. A confirmed-dead process plus an independently
    (non-self-reported) refused verification must now let redispatch
    through instead of reading as still live."""
    from pyforge.marshal.cli.dispatch import _compose_policy

    slug = "pyforge-atlas"
    fs = FakeFs()
    run_dir = _seed_live_dispatch_journal(tmp_path, fs, slug=slug, run_id="run-dead", story_key="21.1")
    journal_path = run_dir / "journal.jsonl"
    verification_intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 2),
            ts="2026-08-29T19:55:44.943Z",
            run_id="run-dead",
            kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
            phase=Phase.INTENT,
            payload={"verdict": "refused"},
        )
    ).line
    verification_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 3),
            ts="2026-08-29T19:55:44.943Z",
            run_id="run-dead",
            kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 2),
            payload={"verdict": "refused", "failed_gate": "MRS-GATE-001"},
        )
    ).line
    with journal_path.open("a", encoding="utf-8") as fh:
        fh.write(verification_intent + "\n" + verification_outcome + "\n")
    fs.files[journal_path] = fs.files[journal_path] + verification_intent + "\n" + verification_outcome + "\n"

    class StaleEvidenceVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            return ("src/shared/packages/pyforge-atlas/tools/bootstrap.py",)

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

        def worktree_head_sha(self, worktree_path: Path) -> str:
            return "aaa111"

    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=StaleEvidenceVcs(tmp_path),
        process=FakeProcess(alive=False),
        repo_root=tmp_path,
        slug=slug,
        story_key="21.1",
        effective_policy=_compose_policy(slug),
    )
    assert conflict is None


def test_cross_station_dispatch_allowed_when_other_station_busy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    busy_slug = "pyforge-marshal"
    free_slug = "pyforge-doctor"
    fs = FakeFs()
    _seed_live_dispatch_journal(tmp_path, fs, slug=busy_slug, run_id="run-busy", story_key="22.1")

    story = "22-5-one-story-in-flight-per-station-stations-in-parallel-overlap-is-loud"
    for slug in (busy_slug, free_slug):
        specs = dispatch_core.planning_specs_dir(tmp_path, slug)
        specs.mkdir(parents=True, exist_ok=True)
        (specs / f"spec-{story}.md").write_text(
            '---\ndifficulty: medium\nsurface: ["src/free/**"]\n---\n',
            encoding="utf-8",
        )
    (tmp_path / "_bmad-output" / "projects" / free_slug).mkdir(parents=True, exist_ok=True)

    class LiveVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            if "marshal" in str(worktree_path):
                return ("src/changed.py",)
            return ()

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

        def worktree_head_sha(self, worktree_path: Path) -> str:
            if "marshal" in str(worktree_path):
                return "bbb222"
            return self.head_sha

    import os

    point_scope_triangle(tmp_path, free_slug)
    os.environ["BMAD_ACTIVE_PROJECT"] = free_slug
    args = argparse.Namespace(slug=free_slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=LiveVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert code == EXIT_OK


def test_overlap_advisory_is_warn_and_dispatch_proceeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    slug_a = "pyforge-marshal"
    slug_b = "pyforge-doctor"
    fs = FakeFs()
    _seed_live_dispatch_journal(
        tmp_path,
        fs,
        slug=slug_a,
        run_id="run-a",
        story_key="22.1",
        session_pid=99,
    )

    in_flight_story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    requested_story = "22-5-one-story-in-flight-per-station-stations-in-parallel-overlap-is-loud"
    shared_surface = 'surface: ["src/shared/**"]'
    for slug, story_name in (
        (slug_a, in_flight_story),
        (slug_b, requested_story),
    ):
        specs = dispatch_core.planning_specs_dir(tmp_path, slug)
        specs.mkdir(parents=True, exist_ok=True)
        (specs / f"spec-{story_name}.md").write_text(
            f"---\ndifficulty: medium\n{shared_surface}\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "_bmad-output" / "projects" / slug).mkdir(parents=True, exist_ok=True)

    class LiveVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            return ()

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

    advisories = cross_station_surface_overlap_advisories(
        fs=fs,
        vcs=LiveVcs(tmp_path),
        process=FakeProcess(alive=True),
        repo_root=tmp_path,
        requested_slug=slug_b,
        requested_story_key=requested_story,
        requested_spec_text=f"---\n{shared_surface}\n---\n",
    )
    assert advisories
    assert advisories[0].code == "MRS-DISP-022"
    assert "LOUD ADVISORY" in advisories[0].message

    import os

    point_scope_triangle(tmp_path, slug_b)
    os.environ["BMAD_ACTIVE_PROJECT"] = slug_b
    args = argparse.Namespace(slug=slug_b, story=requested_story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=LiveVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert code == EXIT_OK


def test_gather_dispatch_journal_facts_round_trips_scope_violation_advisories(
    tmp_path: Path,
) -> None:
    """Story 28.15 (CAP-17) write<->read round trip. ``dispatch_supervisor/
    __main__.py::_run_and_journal_verification`` journals ``warn``-mode
    scope-violation advisories under the ``scope_violation_advisories`` key
    of a ``KIND_DISPATCH_VERIFICATION`` OUTCOME payload;
    ``gather_dispatch_journal_facts`` folds that SAME key back into
    ``DispatchJournalFacts.verification_scope_advisories``. Every existing
    test touching this field either builds the dataclass by hand
    (``test_status.py``, ``test_dispatch_verification.py``) or exercises
    ``check_scope_with_mode`` in isolation -- none drove the real write side
    and the real read side together over an actual journal payload, so a
    key rename or a code-filter drift on either end could regress AC4's
    "visible, never journal-only" promise with every other test still
    green. Mirrors this file's own
    ``test_redispatch_allowed_when_session_dead_and_verification_refused``,
    which hand-writes a ``KIND_DISPATCH_VERIFICATION`` OUTCOME entry the
    same way but never populates ``scope_violation_advisories``."""
    slug = "pyforge-marshal"
    fs = FakeFs()
    run_dir = _seed_live_dispatch_journal(tmp_path, fs, slug=slug, run_id="run-scope", story_key="28.15")
    journal_path = run_dir / "journal.jsonl"
    advisories_payload = [
        {
            "code": "MRS-GATE-012",
            "message": (
                "scope-violation mode is 'warn' for this station -- "
                "changed path 'src/outside/surface.py' is outside the "
                "effective surface (would refuse landing under 'hard'; "
                "landing proceeds)"
            ),
            "path": "src/outside/surface.py",
        },
        {
            "code": "MRS-GATE-013",
            "message": (
                "scope-violation mode is 'warn' for this station -- a "
                "frozen path was touched (would refuse landing under "
                "'hard'; landing proceeds)"
            ),
            "path": None,
        },
    ]
    verification_intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 2),
            ts="2026-08-31T00:00:00.000Z",
            run_id="run-scope",
            kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
            phase=Phase.INTENT,
            payload={"verdict": "verified"},
        )
    ).line
    verification_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 3),
            ts="2026-08-31T00:00:00.000Z",
            run_id="run-scope",
            kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 2),
            payload={
                "verdict": "verified",
                "ok": True,
                "failed_gate": None,
                "failed_message": None,
                "scope_violation_advisories": advisories_payload,
            },
        )
    ).line
    appended = verification_intent + "\n" + verification_outcome + "\n"
    with journal_path.open("a", encoding="utf-8") as fh:
        fh.write(appended)
    fs.files[journal_path] = fs.files[journal_path] + appended

    facts = gather_dispatch_journal_facts(fs, run_dir, "run-scope")

    assert facts.verification_scope_advisories == tuple(advisories_payload)


def test_verification_outcome_verdict_reads_legacy_sidecarred_payload(
    tmp_path: Path,
) -> None:
    """Regression: dispatch supervisor must fold sidecars before reading verdict."""
    slug = "pyforge-marshal"
    fs = FakeFs()
    run_dir = _seed_live_dispatch_journal(tmp_path, fs, slug=slug, run_id="run-sidecar", story_key="28.8")
    journal_path = run_dir / "journal.jsonl"
    payload = {
        "verdict": "verified",
        "ok": True,
        "scope_violation_advisories": [{"code": "MRS-GATE-012", "path": f"extra/{index}.py"} for index in range(500)],
    }
    prepared = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 2),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-sidecar",
            kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 1),
            payload=payload,
        )
    )
    assert prepared.sidecar_relative_path is not None
    assert prepared.sidecar_content is not None
    sidecar_path = run_dir / prepared.sidecar_relative_path
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(prepared.sidecar_content, encoding="utf-8")
    fs.files[sidecar_path] = prepared.sidecar_content
    appended = prepared.line + "\n"
    with journal_path.open("a", encoding="utf-8") as fh:
        fh.write(appended)
    fs.files[journal_path] = fs.files[journal_path] + appended

    text = fs.read_text(journal_path)
    assert text is not None
    sidecars = sidecar_texts_for_lines(
        text.splitlines(),
        read_sidecar=lambda ref: fs.read_text(run_dir / ref),
    )
    folded = fold(text.splitlines(), sidecars=sidecars)

    assert _verification_outcome_verdict(folded, "run-sidecar") == "verified"


def test_gather_dispatch_journal_facts_reads_offloaded_scope_advisories(
    tmp_path: Path,
) -> None:
    slug = "pyforge-marshal"
    fs = FakeFs()
    run_dir = _seed_live_dispatch_journal(tmp_path, fs, slug=slug, run_id="run-offload", story_key="28.15")
    journal_path = run_dir / "journal.jsonl"
    advisories = [{"code": "MRS-GATE-012", "path": f"src/outside/{index}.py"} for index in range(400)]
    prepared = prepare_for_write_offloading_fields(
        build_entry(
            id=JournalEntryId("w", 2),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-offload",
            kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 1),
            payload={
                "verdict": "verified",
                "ok": True,
                SCOPE_VIOLATION_ADVISORIES_FIELD: advisories,
            },
        ),
        offload_fields=frozenset({SCOPE_VIOLATION_ADVISORIES_FIELD}),
    )
    assert prepared.sidecar_relative_path is not None
    assert prepared.sidecar_content is not None
    sidecar_path = run_dir / prepared.sidecar_relative_path
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(prepared.sidecar_content, encoding="utf-8")
    fs.files[sidecar_path] = prepared.sidecar_content
    appended = prepared.line + "\n"
    with journal_path.open("a", encoding="utf-8") as fh:
        fh.write(appended)
    fs.files[journal_path] = fs.files[journal_path] + appended

    facts = gather_dispatch_journal_facts(fs, run_dir, "run-offload")

    assert facts.verification_verdict == "verified"
    assert len(facts.verification_scope_advisories) == 400
