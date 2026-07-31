"""Meta test -- AD-11 write-boundary guard for Story 1.4/1.5's active
surface (``marshal init``'s loop home, plus Story 1.5's Tier-3 backlink).
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
    """Fakes ``FsPort`` in full (incl. ``remove_empty_dir``, unreached by
    THIS fixture's fresh-provision scenario but implemented so the guard
    would not crash if a future scenario pre-seeds a stale local Tier-3
    directory) so ``run_init`` can reach every one of its writes
    (tier3_backlink's ``ensure_dir``/symlink repoint, the planning-artifacts
    symlink repoint, marker write), recording each write path."""

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

    def ensure_dir(self, path: Path) -> None:
        self.write_paths.append(path)

    def remove_empty_dir(self, path: Path) -> bool:
        self.write_paths.append(path)
        self._dirs.discard(path)
        return True


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
