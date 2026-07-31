"""Meta test -- AD-11 write-boundary guard for Story 1.4's active surface
(``marshal init``'s loop home). Unlike the AST-scan meta-tests this package
already ships (AD-3/AD-4, AD-7, AD-26), this guard is RUNTIME: it injects
path-recording fake ``VcsPort``/``FsPort`` implementations into
``cli.init.run_init``'s own dependency-injection seam
(``run_init(args, vcs=..., fs=...)``), drives one full ``init`` invocation
against a ``tmp_path``-rooted fake home, and asserts every path either fake
recorded a WRITE to resolves under that home directory -- the architecture's
"Marshal writes only inside the loop home ... " invariant (Epic 1 context,
Technical Decisions), scoped to exactly what this story can write (no
Tier-3 backlink, no promotion target, no host/adapter-facts path -- those
are later stories' surfaces).

Bounds (stated, not aspirational): this exercises the REAL orchestration
logic in ``cli/init.py`` end-to-end (unlike an AST scan, it proves the
RUNTIME write set, not just the absence of a banned import), but the ports
themselves are fakes -- ``tests/unit/test_vcs_git.py``/``test_fs_local.py``
and the real end-to-end ``tests/integration/test_init_worktree.py`` are
what prove the ADAPTERS' own writes land where their fake counterparts
claim. The guarded invariant is therefore: every FS-port write and the
worktree TARGET path land under the home. A real ``git worktree add`` also
writes git-internal bookkeeping OUTSIDE the home (the new branch ref and
``$GIT_DIR/worktrees/<id>`` admin data in the main repo's ``.git``) --
those are git's own writes, not Marshal's, and are deliberately exempt
from the claim (review finding: the earlier docstring implied the real
adapter could satisfy an all-writes-under-home reading, which it cannot).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pyforge.marshal.cli.init import run_init
from pyforge.marshal.core.verdict import EXIT_OK


class _RecordingVcs:
    """Fakes just enough of ``VcsPort`` to let ``run_init`` reach every
    write path, recording the one write (``add_worktree``) it can make."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.write_paths: list[Path] = []

    def repo_common_root(self, start: Path) -> Path:
        return self.repo_root

    def branch_exists(self, repo_root: Path, branch: str) -> bool:
        return False

    def worktree_path_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        return None

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        self.write_paths.append(home)


class _RecordingFs:
    """Fakes just enough of ``FsPort`` to let ``run_init`` reach both of its
    writes (symlink repoint, marker write), recording each write path."""

    def __init__(self, dirs: set[Path]) -> None:
        self._dirs = dirs
        self.write_paths: list[Path] = []

    def is_dir(self, path: Path) -> bool:
        return path in self._dirs

    def read_text(self, path: Path) -> str | None:
        return None

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.write_paths.append(path)

    def read_symlink_target(self, path: Path) -> Path | None:
        return None

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:
        self.write_paths.append(path)


def test_every_observed_write_resolves_under_the_provisioned_home(tmp_path, monkeypatch):
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
    # Non-vacuous: a full successful init writes the worktree (vcs) AND the
    # symlink + marker (fs) -- three writes total. If this drops to zero the
    # guard would trivially pass without checking anything.
    assert vcs.write_paths, "no vcs write was observed -- the guard would be vacuous"
    assert len(fs.write_paths) == 2, "expected exactly the symlink + marker writes"

    home_resolved = home.resolve()
    for path in all_writes:
        resolved = Path(path).resolve()
        assert resolved == home_resolved or home_resolved in resolved.parents, (
            f"write to {path} does not resolve under the provisioned home {home}"
        )
