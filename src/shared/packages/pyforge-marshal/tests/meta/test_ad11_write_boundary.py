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


class _RecordingFs:
    """Fakes ``FsPort`` in full (incl. ``remove_empty_dir``, unreached by
    THIS fixture's fresh-provision scenario but implemented so the guard
    would not crash if a future scenario pre-seeds a stale local Tier-3
    directory) so ``run_init`` can reach every one of its writes
    (tier3_backlink's ``ensure_dir``/symlink repoint, the planning-artifacts
    symlink repoint, marker write), recording each write path."""

    def __init__(self, dirs: set[Path], *, files: set[Path] | None = None) -> None:
        self._dirs = dirs
        # Story 1.7: a distinct membership set from `_dirs` -- run_preflight's
        # seed-file loop probes `exists()` on plain FILE paths (a home
        # destination, a main-checkout source), never `is_dir()`.
        self._files = files if files is not None else set()
        self._texts: dict[Path, str] = {}
        self.write_paths: list[Path] = []

    def is_dir(self, path: Path) -> bool:
        return path in self._dirs

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
        return None

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
        # Story 3.1: not reached by any scenario this module drives today
        # (no CLI wiring exists yet -- see core/journal.py's module
        # docstring), implemented so the guard would not crash if a future
        # scenario reaches it, mirroring ensure_dir's own precedent.
        self.write_paths.append(path)

    def create_dir_exclusive(self, path: Path) -> None:
        # Story 3.1: same precedent as append_line above.
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
    recorded, mirroring ``_RecordingVcs``'s own read/write split."""

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
