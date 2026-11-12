"""Story 116.4 (spec-pyforge-marshal:CAP-305): the package half's tree-read guard.

Steward's derivation (``test_station_tests_trigger_map.py``) reads marshal's tests statically, so it cannot see a
read that happens only at run time: code under test that falls back to the checkout. This guard sees those reads as
they happen. ``tests/conftest.py`` installs it once per process (each xdist worker loads that conftest) and arms it
around the setup, call and teardown of every package-half test, so module fixtures count. A package-half test is
one marked neither ``live_tree`` nor ``slow``, the selection ``-m "not slow and not live_tree"``; a ``live_tree``
test is never armed.

The audit hook returns at once unless the guard is armed and the event is ``open``, ``os.listdir``, ``os.scandir``
or ``glob.glob``. Armed, it records each path under the repository that is not allowed, and the conftest fails the
test naming every recorded path.

* The package is this file's ``parents[2]``. The repository is the nearest ancestor of the package holding ``.git``
  (a file in a worktree), or none, and then the guard is inert: a copy of the package outside any repository runs
  with no guard.
* Allowed under the repository: the package, ``.pixi/``, ``.steward/coverage/``, and the directories of the
  installed ``pyforge.core`` and ``pyforge.testing_kit`` modules. A path outside the repository (a tmp dir) is
  never recorded.
* A directory listing the import system makes (its path finder filling a cache, ``importlib.metadata`` scanning
  ``sys.path``) is not a read: the repository root sits on ``sys.path`` under xdist. The import system's ``open`` is
  still a read, so a package-half test that imports a repository script is caught.
* A relative path is judged against the working directory; ``glob.glob``'s event carries no ``root_dir``, so its
  pattern is judged the same way. ``os.open`` (its ``open`` event carries no mode) of a relative name is not judged:
  the event carries no ``dir_fd`` either, and ``shutil.rmtree`` opens each entry of a tmp tree relative to one.
* A subprocess's reads (a test that runs ``git -C <repo>``) are not seen: steward's static derivation stays the
  guard for those. Nor is an existence check (``os.stat``, ``Path.is_file``), which raises no audit event.
* ``tests/conftest.py`` also starts each armed test off the tree (``_package_half_off_the_tree``), so the code under
  test's two fallbacks, ``pyforge.core``'s flag tree and ``cli/config.py``'s ``repo_root()``, find no checkout.

``tests/_support`` is not a package on ``sys.path``; the conftest and ``tests/meta/test_tree_read_guard.py`` load
this file by path under ``MODULE_NAME``, so one process holds one module and one hook.
"""

from __future__ import annotations

import importlib.metadata
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path

MODULE_NAME = "pyforge_marshal_tests_support_tree_read_guard"
EVENTS = frozenset({"open", "os.listdir", "os.scandir", "glob.glob"})
ALLOWED_REPOSITORY_DIRS = (".pixi", ".steward/coverage")
INSTALLED_MODULES = ("pyforge.core", "pyforge.testing_kit")
HEADER_ARMED = "tree-read guard: armed"
HEADER_INERT = "tree-read guard: inert"

_LISTING_EVENTS = frozenset({"os.listdir", "os.scandir"})
_IMPORT_SYSTEM_FILES = frozenset(
    {"<frozen importlib._bootstrap_external>"}
    | ({os.path.abspath(importlib.metadata.__file__)} if importlib.metadata.__file__ else set())
)


def find_repository(package: Path) -> Path | None:
    """The nearest ancestor of ``package`` holding ``.git`` (a directory, or a file in a worktree), or None."""
    for ancestor in package.parents:
        if (ancestor / ".git").exists():
            return ancestor
    return None


def installed_module_dirs(modules: tuple[str, ...] = INSTALLED_MODULES) -> tuple[Path, ...]:
    """The directories the installed ``modules`` load from; a module that is not installed adds none."""
    found: list[Path] = []
    for name in modules:
        try:
            spec = find_spec(name)
        except ImportError, ValueError:
            continue
        if spec is None:
            continue
        if spec.submodule_search_locations:
            found.extend(Path(location).resolve() for location in spec.submodule_search_locations)
        elif spec.origin:
            found.append(Path(spec.origin).resolve().parent)
    return tuple(found)


def _relative(raw: object) -> bool:
    return isinstance(raw, (str, bytes, os.PathLike)) and not os.path.isabs(os.fspath(raw))


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root + os.sep)


@dataclass
class TreeReadGuard:
    """What one process's guard judges: the package, the repository around it, and what is allowed there."""

    package: Path
    repository: Path | None
    allowed: tuple[Path, ...]
    armed: bool = False
    reads: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def around(cls, guard_file: str | Path, modules: tuple[str, ...] = INSTALLED_MODULES) -> TreeReadGuard:
        """The guard for the package whose ``tests/_support/`` holds ``guard_file``."""
        package = Path(guard_file).resolve().parents[2]
        repository = find_repository(package)
        if repository is None:
            return cls(package=package, repository=None, allowed=())
        allowed = (
            package,
            *(repository / relative for relative in ALLOWED_REPOSITORY_DIRS),
            *installed_module_dirs(modules),
        )
        return cls(package=package, repository=repository, allowed=allowed)

    @property
    def inert(self) -> bool:
        return self.repository is None

    def recorded_path(self, raw: object) -> str | None:
        """The absolute path ``raw`` names when the guard records it: under the repository and not allowed."""
        if self.repository is None or isinstance(raw, int):
            return None
        if raw is None:
            path = os.getcwd()
        elif isinstance(raw, (str, bytes, os.PathLike)):
            path = os.path.abspath(os.fsdecode(os.fspath(raw)))
        else:
            return None
        if not _under(path, str(self.repository)):
            return None
        if any(_under(path, str(root)) for root in self.allowed):
            return None
        return path

    def recorded(self, event: str, args: tuple[object, ...]) -> str | None:
        """The path one audit event names when the guard records it (``recorded_path``), else None."""
        raw = args[0] if args else None
        if event == "open" and len(args) > 1 and args[1] is None and _relative(raw):
            return None
        return self.recorded_path(raw)

    def record(self, event: str, path: str) -> None:
        if (event, path) not in self.reads:
            self.reads.append((event, path))

    @contextmanager
    def window(self) -> Iterator[list[tuple[str, str]]]:
        """Arm the guard for one test phase; yields the reads recorded in it. Inert, it arms nothing."""
        reads: list[tuple[str, str]] = []
        if self.inert:
            yield reads
            return
        self.reads = reads
        self.armed = True
        try:
            yield reads
        finally:
            self.armed = False

    def header(self) -> str:
        if self.repository is None:
            return f"{HEADER_INERT} (no repository around {self.package})"
        return f"{HEADER_ARMED} (package {self.package.relative_to(self.repository).as_posix()})"

    def failure(self, nodeid: str, phase: str, reads: list[tuple[str, str]]) -> str:
        assert self.repository is not None
        lines = [
            f"{HEADER_ARMED}: {nodeid} read {len(reads)} repository path(s) outside "
            f"{self.package.relative_to(self.repository).as_posix()} during {phase}:"
        ]
        for event, path in reads:
            lines.append(f"  {Path(path).relative_to(self.repository).as_posix()} ({event})")
        lines.append(
            "A package-half test reads nothing in the repository outside its package (spec-pyforge-marshal:CAP-305): "
            "move the reading test into a *_live_tree.py sibling marked live_tree, mark a module whose every test "
            "reads the tree, or stop the read."
        )
        return "\n".join(lines)


_ACTIVE: TreeReadGuard | None = None
_HOOKED = False


def _audit(event: str, args: tuple[object, ...]) -> None:
    guard = _ACTIVE
    if guard is None or not guard.armed or event not in EVENTS:
        return
    path = guard.recorded(event, args)
    if path is None:
        return
    if event in _LISTING_EVENTS and sys._getframe(1).f_code.co_filename in _IMPORT_SYSTEM_FILES:
        return
    guard.record(event, path)


def install(guard: TreeReadGuard) -> TreeReadGuard:
    """Make ``guard`` the process's active guard; the audit hook is added once per process."""
    global _ACTIVE, _HOOKED
    _ACTIVE = guard
    if not _HOOKED:
        sys.addaudithook(_audit)
        _HOOKED = True
    return guard


def active() -> TreeReadGuard | None:
    return _ACTIVE


@contextmanager
def activated(guard: TreeReadGuard) -> Iterator[TreeReadGuard]:
    """Make ``guard`` the active one for a block, then restore the one before it (the meta test's seam)."""
    global _ACTIVE
    before = _ACTIVE
    install(guard)
    try:
        yield guard
    finally:
        _ACTIVE = before
