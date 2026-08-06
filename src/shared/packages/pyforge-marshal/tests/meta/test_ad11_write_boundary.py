"""Meta test -- AD-11 write-boundary guard for Story 1.4/1.5's active
surface (``marshal init``'s loop home, plus Story 1.5's Tier-3 backlink),
extended by Story 1.6 to prove ``marshal homes`` -- a READ-ONLY command by
design -- performs literally ZERO writes, and by Story 1.7 to prove
``marshal preflight``'s writes (seed-file copies into the home, the
machine-scoped acknowledgement file) resolve under one of THREE allowed
targets rather than the original two -- see that test's own docstring for
why a third target is legitimate here (AD-37's fourth write target, not a
loosening of AD-11), and by Story 1.8 to prove ``marshal teardown`` performs
literally ZERO ``FsPort`` writes (mirroring ``marshal homes``'s own
read-only guard) while its one ``VcsPort`` mutation target
(``remove_worktree``'s ``home`` argument) resolves under the provisioned
home *in the provisioned-in-place case this guard constructs* -- when git's
registry names a DIFFERENT path for ``loop/<slug>`` (e.g.
``BMAD_LOOP_HOME_ROOT`` changed since provisioning), the registered path is
the removal target by design, outside any home root (review finding: the
claim as previously worded overstated a universal containment the code
deliberately does not have -- see ``test_init.py``'s
``test_teardown_remove_worktree_uses_the_git_registered_path_not_the_computed_home``).
Unlike the AST-scan meta-tests this package already ships (AD-3/AD-4, AD-7,
AD-26), this guard is RUNTIME: it injects path-recording fake
``VcsPort``/``FsPort`` implementations into ``cli.init.run_init``'s own
dependency-injection seam (``run_init(args, vcs=..., fs=...)``), drives one
full ``init`` invocation against a ``tmp_path``-rooted fake home, and
asserts every path either fake recorded a WRITE to resolves under ONE of
the architecture's two allowed targets for this story's surface (Epic 1
context, Technical Decisions -- "Marshal writes only inside ... the loop
home, the canonical execution-artifact store (via backlink) ..."): the
provisioned home, OR the main checkout's canonical Tier-3 store at
``repo_root/_bmad-output/projects/<slug>/implementation-artifacts`` (no
promotion target, no host/adapter-facts path -- those are later stories'
surfaces).

Bounds (stated, not aspirational): this exercises the REAL orchestration
logic in ``cli/init.py`` end-to-end (unlike an AST scan, it proves the
RUNTIME write set, not just the absence of a banned import), but the ports
themselves are fakes -- ``tests/unit/test_vcs_git.py``/``test_fs_local.py``
and the real end-to-end ``tests/integration/test_init_worktree.py`` are
what prove the ADAPTERS' own writes land where their fake counterparts
claim. The guarded invariant is therefore: every FS-port write and the
worktree TARGET path land under the home OR the canonical Tier-3 store. A
real ``git worktree add`` also writes git-internal bookkeeping OUTSIDE the
home (the new branch ref and ``$GIT_DIR/worktrees/<id>`` admin data in the
main repo's ``.git``) -- those are git's own writes, not Marshal's, and are
deliberately exempt from the claim (review finding: the earlier docstring
implied the real adapter could satisfy an all-writes-under-home reading,
which it cannot). Likewise ``ensure_dir`` is recorded only at its leaf
argument: the real adapter's ``mkdir(parents=True)`` could also create
missing ANCESTORS of the canonical store (above the guarded boundary) --
unreachable today because the in-home project gate guarantees those
ancestors exist, but structurally invisible to this guard if that ever
changes (review finding: the guard's claim is bounded by what the fakes
can observe).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pyforge.marshal.cli.init import run_homes, run_init, run_preflight, run_teardown
from pyforge.marshal.cli.spin import run_spin
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.vcs import WorktreeEntry


class _RecordingVcs:
    """Fakes just enough of ``VcsPort`` to let ``run_init``/``run_homes``/
    ``run_teardown`` reach every write path, recording the writes
    (``add_worktree``, ``remove_worktree``) each can make. ``provisioned_*``
    default to "nothing provisioned" (``run_init``'s own fresh-provision
    scenario); ``run_teardown``'s own test overrides them so a worktree
    genuinely exists to remove."""

    def __init__(
        self,
        repo_root: Path,
        *,
        provisioned_worktree: Path | None = None,
        provisioned_branch_exists: bool = False,
    ) -> None:
        self.repo_root = repo_root
        self.write_paths: list[Path] = []
        self._provisioned_worktree = provisioned_worktree
        self._provisioned_branch_exists = provisioned_branch_exists

    def repo_common_root(self, start: Path) -> Path:
        return self.repo_root

    def branch_exists(self, repo_root: Path, branch: str) -> bool:
        return self._provisioned_branch_exists

    def worktree_path_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        return self._provisioned_worktree

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        self.write_paths.append(home)

    def list_worktrees(self, repo_root: Path) -> tuple[WorktreeEntry, ...]:
        # Story 1.6: a read -- never recorded. One main-checkout entry plus
        # one loop home, so run_homes has a non-trivial home row to gather.
        return (
            WorktreeEntry(path=self.repo_root, branch="main"),
            WorktreeEntry(path=self.repo_root / "loop-homes" / "acme", branch="loop/acme"),
        )

    def has_uncommitted_changes(self, worktree_path: Path) -> bool:
        # Story 1.8: a read -- never recorded. Clean by construction, so
        # run_teardown's own refusal path never blocks this guard's run.
        return False

    def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
        # Story 1.8: a read -- never recorded. Merged by construction, for
        # the same reason as has_uncommitted_changes above.
        return True

    def remove_worktree(self, repo_root: Path, home: Path, *, force: bool = False) -> None:
        # The worktree TARGET path this guard tracks, mirroring
        # add_worktree's own recorded write above.
        self.write_paths.append(home)

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        # NOT recorded: branch deletion is a git-ref-level operation inside
        # $GIT_DIR, outside both allowed targets -- git-internal bookkeeping
        # exempt from this guard's claim for the SAME reason add_worktree's
        # own branch-ref write is (see this class's own docstring precedent
        # and the module docstring's "real git worktree add" paragraph).
        pass

    # Story 4.2: run_teardown's AD-29 check now really calls
    # deploy.unreachable_promotions_for_slug, which reads these three
    # VcsPort methods -- all reads, never recorded, so nothing durable is
    # merged and the "nothing unreachable" world this guard's clean-home
    # scenario describes stays unaffected.
    def commit_subjects(self, repo_root: Path, ref: str) -> tuple[str, ...]:
        return ()

    def commit_paths(self, repo_root: Path, paths: tuple, message: str) -> str:  # pragma: no cover
        return "deadbeef"

    def path_has_uncommitted_changes(self, repo_root: Path, path: Path) -> bool:
        return False


class _RecordingFs:
    """Fakes ``FsPort`` in full (incl. ``remove_empty_dir``, unreached by
    THIS fixture's fresh-provision scenario but implemented so the guard
    would not crash if a future scenario pre-seeds a stale local Tier-3
    directory) so ``run_init`` can reach every one of its writes
    (tier3_backlink's ``ensure_dir``/symlink repoint, the planning-artifacts
    symlink repoint, marker write), recording each write path."""

    def __init__(
        self,
        dirs: set[Path],
        *,
        files: set[Path] | None = None,
        symlinks: dict[Path, Path] | None = None,
    ) -> None:
        self._dirs = dirs
        # Story 1.7: a distinct membership set from `_dirs` -- run_preflight's
        # seed-file loop probes `exists()` on plain FILE paths (a home
        # destination, a main-checkout source), never `is_dir()`.
        self._files = files if files is not None else set()
        # Story 3.3: `run_spin` gates its whole write path on the Tier-3
        # BACKLINK existing (a real symlink), so a scenario driving it must
        # be able to say one does. Defaults to empty -- the "no symlinks at
        # all" world every pre-existing scenario already described.
        self._symlinks = symlinks if symlinks is not None else {}
        self._texts: dict[Path, str] = {}
        self.write_paths: list[Path] = []
        # A READ, recorded separately from write_paths: Story 3.3's guard
        # needs to prove the backlink was CONSULTED, which the write paths
        # alone cannot show (they resolve under the home either way).
        self.symlink_reads: list[Path] = []

    def is_dir(self, path: Path) -> bool:
        # A seeded symlink resolves as a directory: `run_spin`'s backlink
        # gate probes presence with `read_symlink_target` and then
        # DANGLING-ness with `is_dir` (a review finding -- a link whose
        # target was removed passed the presence check and then made
        # `ensure_dir` raise `FileExistsError` under a launch-failure code).
        # A scenario that seeds a backlink is describing a healthy one.
        return path in self._dirs or path in self._symlinks

    def exists(self, path: Path) -> bool:
        # Story 1.6: a read -- never recorded. Nothing exists beyond the
        # seeded dirs, so run_homes's occupancy probes stay False (benign
        # absence) and its clean-run exit stays EXIT_OK. Story 1.7 extends
        # membership to `_files`/`_texts` for the same reason.
        return path in self._dirs or path in self._files or path in self._texts

    def read_text(self, path: Path) -> str | None:
        return self._texts.get(path)

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.write_paths.append(path)

    def read_symlink_target(self, path: Path) -> Path | None:
        self.symlink_reads.append(path)
        return self._symlinks.get(path)

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:
        self.write_paths.append(path)

    def ensure_dir(self, path: Path) -> None:
        self.write_paths.append(path)

    def remove_empty_dir(self, path: Path) -> bool:
        self.write_paths.append(path)
        self._dirs.discard(path)
        return True

    def resolve_path(self, path: Path) -> Path:
        # Story 1.6: a read -- never recorded. This fake carries no
        # symlinks, so "resolves to itself" is the correct/sufficient
        # answer for both the main-checkout-identification comparison and
        # the (absent) Tier-3 backlink comparison run_homes performs.
        return path

    def copy_file(self, src: Path, dst: Path) -> None:
        self.write_paths.append(dst)
        self._files.add(dst)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        # Story 3.1 implemented this speculatively (no CLI wiring existed
        # yet). Story 3.3's `run_spin` is the first scenario that actually
        # reaches it -- see this module's own `test_spin_writes_...` below.
        self.write_paths.append(path)

    def create_dir_exclusive(self, path: Path) -> None:
        # Story 3.1: same precedent as append_line above, likewise first
        # reached by Story 3.3's `run_spin` scenario.
        self.write_paths.append(path)


def test_every_observed_write_resolves_under_the_home_or_canonical_tier3_store(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    slug = "acme"
    repo_root = tmp_path / "repo"
    home = tmp_path / "loop-homes" / slug
    planning_dir = repo_root / "_bmad-output" / "projects" / slug / "planning-artifacts"
    # The home-side twin: the in-home project gate probes the tree the
    # symlink will resolve in, right after the worktree step.
    home_planning_dir = home / "_bmad-output" / "projects" / slug / "planning-artifacts"

    vcs = _RecordingVcs(repo_root)
    fs = _RecordingFs({planning_dir, home_planning_dir})

    args = argparse.Namespace(slug=slug, format="text")
    exit_code = run_init(args, vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK

    all_writes = vcs.write_paths + fs.write_paths
    # Non-vacuous: a full successful init writes the worktree (vcs) AND,
    # from cli/init.py's fs-port calls: tier3_backlink's canonical
    # ensure_dir + local symlink repoint, the planning-artifacts symlink
    # repoint, and the marker write -- four fs writes total. If this drops
    # the guard would trivially pass without checking anything.
    assert vcs.write_paths, "no vcs write was observed -- the guard would be vacuous"
    assert len(fs.write_paths) == 4, (
        "expected exactly tier3_backlink's ensure_dir + symlink repoint, "
        "the planning-artifacts symlink repoint, and the marker write"
    )

    home_resolved = home.resolve()
    # AD-11's second allowed target for this story's surface: the main
    # checkout's canonical Tier-3 store (Story 1.5's backlink destination).
    canonical_tier3_resolved = (
        repo_root / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    ).resolve()
    for path in all_writes:
        resolved = Path(path).resolve()
        under_home = resolved == home_resolved or home_resolved in resolved.parents
        under_canonical_tier3 = (
            resolved == canonical_tier3_resolved
            or canonical_tier3_resolved in resolved.parents
        )
        assert under_home or under_canonical_tier3, (
            f"write to {path} does not resolve under the provisioned home "
            f"{home} or the canonical Tier-3 store {canonical_tier3_resolved}"
        )


def test_homes_produces_zero_recorded_writes(tmp_path):
    """Story 1.6: ``marshal homes`` is read-only by construction -- unlike
    ``run_init`` above, the guarded claim here is not "every write resolves
    under an allowed target" but "there is no write at all", on BOTH
    ``VcsPort`` and ``FsPort``, even for a run that discovers a real home
    and reports it clean."""
    repo_root = tmp_path / "repo"
    vcs = _RecordingVcs(repo_root)
    # The loop home's own directory must exist for this to be "a run that
    # discovers a real home" (per this test's own docstring) rather than
    # tripping run_homes's phantom/prunable-worktree guard (Story 1.6
    # review finding), which would report MRS-HOMES-003 instead of clean.
    fs = _RecordingFs({repo_root / "loop-homes" / "acme"})

    args = argparse.Namespace(format="text")
    exit_code = run_homes(args, vcs=vcs, fs=fs)

    assert exit_code == EXIT_OK
    assert vcs.write_paths == []
    assert fs.write_paths == []


class _RecordingHarness:
    """Fakes ``HarnessPort`` in full, all-converged, so ``run_preflight``
    reaches its two writes (the seed-file copy, the ack-state write) without
    tripping any OTHER finding first. Harness methods are all reads -- never
    recorded, mirroring ``_RecordingVcs``'s own read/write split -- with one
    Story 3.3 exception: ``spin`` is handed a LOG PATH it will write to, so
    that path is recorded (``spin_log_paths``) and guarded like any other
    write target."""

    def __init__(self) -> None:
        self.spin_log_paths: list[Path] = []

    def binary_present(self, binary: str) -> bool:
        return True

    def harness_version(self) -> str | None:
        return "0.9.0"

    def multiplexer_backend_available(self) -> tuple[str, bool]:
        return ("tmux", True)

    def adapter_binary(self, adapter_name: str, project: Path) -> str:
        return "claude"

    def adapter_seed_files(self, adapter_name: str, project: Path) -> tuple[str, ...]:
        return (".mcp.json",)

    def adapter_first_run_note(self, adapter_name: str, project: Path) -> str:
        return "run claude once"

    def story_feed_error(self, project: Path) -> str | None:
        return None

    # --- Story 3.3's three additions ------------------------------------------
    def story_feed_keys(self, project: Path) -> tuple[str, ...]:
        return ("1-1-first-story", "1-2-second-story")

    def spin(
        self,
        project: Path,
        *,
        epic: int | None,
        story: str | None,
        max_count: int | None,
        log_path: Path,
    ):
        from pyforge.marshal.ports.harness import SpinResult

        # A read from this guard's standpoint (it launches a process, it does
        # not write through FsPort) -- but the LOG PATH it is handed is a
        # real write target, so record it for the assertion below.
        self.spin_log_paths.append(log_path)
        return SpinResult(pid=4242, harness_run_id="20260803T101112000Z-abcd1234")


class _RecordingProcess:
    """Fakes ``ProcessPort``'s ``spawn_detached`` for Story 3.4's supervisor
    spawn, on exactly the same principle ``_RecordingHarness.spin`` uses: the
    call itself launches a process (not a write this guard tracks), but the
    LOG PATH it is handed is a real write target -- ``PosixProcess.
    spawn_detached`` ``open(log_path, "wb")``s it, truncating or creating a
    file entirely OUTSIDE ``FsPort`` -- so that path is recorded and guarded
    like any other.

    Injecting this at all is the review finding this class exists for: the
    Story 3.3 scenario below passed no ``process=``, so it drove the REAL
    ``PosixProcess`` and thereby (a) left a genuine non-``FsPort`` write into
    the canonical Tier-3 store completely unguarded -- invisible to
    ``fs.write_paths``, whose count assertion still passed -- and (b) stood
    one ``_RecordingFs`` behaviour change (any fake that actually creates the
    run directory) away from spawning a real detached Python process out of a
    meta-test. This is verbatim the omission class this file's own docstring
    records the Story 3.3 review catching one story earlier."""

    def __init__(self) -> None:
        self.spawn_log_paths: list[Path] = []

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None):  # pragma: no cover
        raise AssertionError("run_spin must never call ProcessPort.run")

    def is_alive(self, pid: int) -> bool:  # pragma: no cover
        raise AssertionError("run_spin must never call ProcessPort.is_alive")

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        self.spawn_log_paths.append(log_path)
        return 5150


def test_preflight_writes_resolve_under_the_home_or_the_ack_state_path(
    tmp_path, monkeypatch
):
    """Story 1.7: ``marshal preflight`` is NOT read-only like ``marshal
    homes`` -- it copies seed files into the home and records first-run
    acknowledgement in a machine-scoped state file OUTSIDE both of
    ``run_init``'s two allowed targets (the home, the canonical Tier-3
    store) -- AD-37's own fourth write target, not a loosening of AD-11: the
    guarded claim here is "every write resolves under the home OR the
    ack-state path", never the canonical Tier-3 store (this command never
    touches it) and never anywhere else."""
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    state_home = tmp_path / "state-home"
    monkeypatch.setenv("MARSHAL_STATE_HOME", str(state_home))

    slug = "acme"
    repo_root = tmp_path / "repo"
    home = tmp_path / "loop-homes" / slug
    # The seed file's SOURCE (main checkout) must exist for the copy to be
    # attempted at all -- copy-when-absent-on-both-sides is a skip, not a
    # write (see cli/init.py's own seed-file loop).
    vcs = _RecordingVcs(repo_root)
    fs = _RecordingFs({home}, files={repo_root / ".mcp.json"})
    harness = _RecordingHarness()

    args = argparse.Namespace(slug=slug, acknowledge="claude", format="text")
    exit_code = run_preflight(args, vcs=vcs, fs=fs, harness=harness)

    assert exit_code == EXIT_OK
    assert vcs.write_paths == []  # run_preflight never touches VcsPort's one write
    all_writes = fs.write_paths
    # Non-vacuous: the seed-file copy (fs) and the ack-state write (fs) --
    # two writes total. If this drops the guard would trivially pass without
    # checking anything.
    assert len(all_writes) == 2, (
        "expected exactly the seed-file copy and the ack-state write"
    )

    home_resolved = home.resolve()
    ack_path_resolved = (state_home / "adapter-acknowledgements.json").resolve()
    for path in all_writes:
        resolved = Path(path).resolve()
        under_home = resolved == home_resolved or home_resolved in resolved.parents
        is_ack_path = resolved == ack_path_resolved
        assert under_home or is_ack_path, (
            f"write to {path} does not resolve under the provisioned home "
            f"{home} or the ack-state path {ack_path_resolved}"
        )


def test_teardown_produces_zero_fs_writes_and_its_one_vcs_write_resolves_under_the_home(
    tmp_path, monkeypatch
):
    """Story 1.8: ``marshal teardown`` is NOT read-only like ``marshal
    homes``, but it makes exactly ONE mutation this guard can observe --
    ``remove_worktree``'s ``home`` target (``delete_branch``'s ref deletion
    is git-internal bookkeeping in ``$GIT_DIR``, exempt from this guard's
    claim for the same reason ``add_worktree``'s own branch-ref write is --
    see ``_RecordingVcs.delete_branch``'s own comment). The guarded claims
    are: zero ``FsPort`` writes at all (cli/init.py's own docstring: this
    command calls no write method and never references the canonical Tier-3
    store), and the one ``VcsPort`` write resolves under the home WHEN the
    registry and the computed home agree -- the provisioned-in-place case
    this test constructs. That containment is deliberately NOT universal
    (review finding: the previous wording overclaimed it): when git
    registers ``loop/<slug>`` at a different path, that registered path is
    the removal target by design -- proven by ``test_init.py``'s own
    moved-home test."""
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    slug = "acme"
    repo_root = tmp_path / "repo"
    home = tmp_path / "loop-homes" / slug

    vcs = _RecordingVcs(repo_root, provisioned_worktree=home, provisioned_branch_exists=True)
    fs = _RecordingFs(set())

    args = argparse.Namespace(slug=slug, force=False, format="text")
    exit_code = run_teardown(args, vcs=vcs, fs=fs)

    assert exit_code == EXIT_OK
    assert fs.write_paths == []
    assert vcs.write_paths, "no vcs write was observed -- the guard would be vacuous"

    home_resolved = home.resolve()
    for path in vcs.write_paths:
        resolved = Path(path).resolve()
        assert resolved == home_resolved or home_resolved in resolved.parents, (
            f"write to {path} does not resolve under the provisioned home {home}"
        )


def test_spin_writes_resolve_under_the_home_and_reach_it_through_the_tier3_backlink(
    tmp_path, monkeypatch
):
    """Story 3.3: ``marshal factory spin`` is the FIRST command in this
    package that writes a journal, and the first scenario this guard drives
    that reaches ``create_dir_exclusive``/``append_line`` at all (both were
    implemented speculatively by Story 3.1).

    Review finding (Blind Hunter): this guard was extended for stories
    1.4/1.5/1.6/1.7/1.8 but NOT for 3.3 -- and the defect the same review
    pass found is exactly the class it exists to catch. ``run_spin`` gated
    only on ``fs.is_dir(home)``, so against a home with NO Tier-3 backlink
    its ``ensure_dir(parents=True)`` fabricated the local
    ``_bmad-output/.../implementation-artifacts/runs/`` tree as real
    directories and journaled into them -- paths that resolve under the home
    (so the containment assertion below alone would have passed) but that do
    NOT reach the canonical store, dying with the next ``marshal teardown``
    (NFR-8). Containment under the home therefore cannot be the whole claim
    here -- it holds either way. The second assertion is what distinguishes
    the two worlds: the backlink must have been READ, which is what makes
    those in-home paths a view of the canonical store rather than a second,
    local copy of it. (The refusal behaviour when the backlink is absent is
    ``test_spin.py``'s own
    ``test_spin_missing_tier3_backlink_refuses_before_any_write``.)

    Extended again for Story 3.4 (follow-up review finding, both reviewers),
    which added a SECOND non-``FsPort`` write target to this same command:
    the supervisor sidecar's own ``supervisor.log``, opened directly by
    ``PosixProcess.spawn_detached``. The identical omission repeated one
    story later -- this scenario passed no ``process=``, so the real adapter
    ran and the new write went entirely unguarded while the count assertion
    above kept passing. See ``_RecordingProcess``'s own docstring."""
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    tier3_local = home / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    tier3_canonical = (
        tmp_path / "repo" / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    )

    fs = _RecordingFs({home}, symlinks={tier3_local: tier3_canonical})
    harness = _RecordingHarness()
    process = _RecordingProcess()

    args = argparse.Namespace(
        slug=slug, epic=None, story=None, max_count=None, foreground=False, format="text"
    )
    exit_code = run_spin(args, fs=fs, harness=harness, process=process)

    assert exit_code == EXIT_OK
    # Non-vacuous: the run directory's parent (ensure_dir), the run directory
    # itself (create_dir_exclusive), and the two journal appends (intent +
    # outcome, both to the same journal.jsonl) -- four recorded writes.
    assert len(fs.write_paths) == 4, f"unexpected write set: {fs.write_paths}"
    assert harness.spin_log_paths, "no spin log path was observed -- the guard would be vacuous"
    # Story 3.4: the supervisor's own log is the SECOND non-FsPort write
    # target this command hands out, and it must be guarded exactly like the
    # harness log above -- without this the guard is blind to it entirely.
    assert process.spawn_log_paths, (
        "no supervisor log path was observed -- run_spin no longer spawns a "
        "supervisor, or stopped routing it through the injected ProcessPort, "
        "and this half of the guard has gone vacuous"
    )

    home_resolved = home.resolve()
    guarded_paths = [*fs.write_paths, *harness.spin_log_paths, *process.spawn_log_paths]
    for path in guarded_paths:
        resolved = Path(path).resolve()
        assert home_resolved in resolved.parents, (
            f"write to {path} does not resolve under the provisioned home {home}"
        )

    # Every one of those paths sits under the local Tier-3 path...
    for path in guarded_paths:
        assert tier3_local in Path(path).parents, (
            f"write to {path} does not pass through the Tier-3 path {tier3_local}"
        )
    # ...and that path was VERIFIED to be a backlink before anything was
    # written, which is the part that makes the line above mean "reaches the
    # canonical store" rather than merely "is inside the home".
    assert fs.symlink_reads == [tier3_local], (
        "run_spin wrote without first confirming the Tier-3 backlink -- "
        f"symlink reads were {fs.symlink_reads}"
    )
