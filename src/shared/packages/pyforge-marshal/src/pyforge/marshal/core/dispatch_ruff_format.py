"""Story 83.9 / 83.15: safe ruff fixes and format on a story's ``.py`` files before verify.

Runs ``ruff check --fix`` (safe fixes only, never ``--unsafe-fixes``) then
``ruff format`` per package, using the same per-package ``cwd`` and file-list
invocation as ``scripts/lint_types.py``, but only on paths the story changed
against ``origin/main`` — never whole ``src/`` / ``tests/`` trees.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyforge.core.process import ProcessError, ProcessPort

from . import dispatch as dispatch_core
from .commit_vcs import CommittingVcs
from .dispatch_cfe_commit import filter_story_py_paths_excluding_cfe, paths_excluding_cfe
from .egress import to_redacted_text
from .refs import ORIGIN_MAIN

_PACKAGES_PREFIX = Path("src/shared/packages")


@dataclass(frozen=True)
class DispatchRuffFormatResult:
    """Outcome of the pre-verify format pass."""

    reformatted_paths: tuple[str, ...]
    committed: bool


def story_scoped_pyforge_py_paths(changed_files: tuple[str, ...]) -> tuple[str, ...]:
    """Repo-relative ``.py`` paths under ``src/shared/packages/pyforge-*/``."""
    selected: list[str] = []
    for path in changed_files:
        if not path.endswith(".py"):
            continue
        parts = Path(path).parts
        if len(parts) < 5:
            continue
        if parts[0:3] != ("src", "shared", "packages"):
            continue
        if not parts[3].startswith("pyforge-"):
            continue
        selected.append(path)
    return tuple(sorted(selected))


def _group_by_package(repo_paths: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    groups: dict[str, list[str]] = {}
    for path in repo_paths:
        pkg = Path(path).parts[3]
        groups.setdefault(pkg, []).append(path)
    return {name: tuple(sorted(paths)) for name, paths in sorted(groups.items())}


def _package_relative_paths(repo_paths: tuple[str, ...], package: str) -> tuple[str, ...]:
    prefix = _PACKAGES_PREFIX / package
    prefix_s = prefix.as_posix() + "/"
    return tuple(path.removeprefix(prefix_s) for path in repo_paths if path.startswith(prefix_s))


def apply_dispatch_ruff_format_before_verify(
    *,
    worktree: Path,
    repo_root: Path,
    vcs: CommittingVcs,
    process: ProcessPort,
) -> DispatchRuffFormatResult:
    """Format story-scoped ``.py`` files in ``worktree`` and commit when needed."""
    git_repo = dispatch_core.canonical_repo_root(repo_root)
    try:
        scope_changed = vcs.changed_files(git_repo, worktree, base=ORIGIN_MAIN)
    except Exception:
        return DispatchRuffFormatResult((), False)

    story_py = filter_story_py_paths_excluding_cfe(story_scoped_pyforge_py_paths(scope_changed))
    if not story_py:
        return DispatchRuffFormatResult((), False)

    story_py_set = frozenset(story_py)
    for package, repo_paths in _group_by_package(story_py).items():
        package_root = worktree / _PACKAGES_PREFIX / package
        if not (package_root / "pyproject.toml").is_file():
            continue
        rel_paths = _package_relative_paths(repo_paths, package)
        if not rel_paths:
            continue
        try:
            process.run(["ruff", "check", "--fix", *rel_paths], cwd=package_root)
        except ProcessError:
            continue
        try:
            result = process.run(["ruff", "format", *rel_paths], cwd=package_root)
        except ProcessError:
            continue
        if result.returncode != 0:
            continue

    try:
        dirty = vcs.changed_files(git_repo, worktree, base="HEAD")
    except Exception:
        return DispatchRuffFormatResult((), False)

    to_commit = tuple(sorted(path for path in dirty if path in story_py_set))
    if not to_commit:
        return DispatchRuffFormatResult((), False)

    commit_paths = paths_excluding_cfe(to_commit)
    if not commit_paths:
        return DispatchRuffFormatResult((), False)

    try:
        vcs.commit_paths(
            worktree,
            commit_paths,
            to_redacted_text("marshal: ruff check --fix and format story files (Story 83.9, 83.15)"),
        )
    except Exception:
        return DispatchRuffFormatResult((), False)

    return DispatchRuffFormatResult(to_commit, True)
