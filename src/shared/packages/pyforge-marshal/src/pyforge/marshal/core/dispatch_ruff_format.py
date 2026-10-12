"""Story 83.9 / 83.15 / 95.1: ruff on a story's ``.py`` files before verify.

Runs ``ruff check --fix`` (safe fixes only, never ``--unsafe-fixes``) then
``ruff format`` per ruff-config tree, using that tree's ``cwd`` and file-list
invocation, but only on paths the story changed against ``origin/main`` that
exist in the worktree — never whole ``src/`` / ``tests/`` trees.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from pyforge.core.process import ProcessError, ProcessPort

from . import dispatch as dispatch_core
from .commit_vcs import CommittingVcs
from .dispatch_cfe_commit import is_cfe_surface_path
from .egress import to_redacted_text
from .refs import ORIGIN_MAIN


@dataclass(frozen=True)
class DispatchRuffFormatGroupResult:
    """One ruff-config tree's pre-verify pass outcome (Story 95.1)."""

    root: str
    files: tuple[str, ...]
    changed_paths: tuple[str, ...]
    ok: bool
    failed_step: str | None = None
    exit_code: int | None = None


@dataclass(frozen=True)
class DispatchRuffFormatResult:
    """Outcome of the pre-verify format pass."""

    reformatted_paths: tuple[str, ...]
    committed: bool
    groups: tuple[DispatchRuffFormatGroupResult, ...] = field(default=(), compare=False)


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


def _pyproject_ruff_table(pyproject: Path) -> dict[str, object] | None:
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return None
    ruff = tool.get("ruff")
    if not isinstance(ruff, dict):
        return None
    return ruff


def _ruff_group_root(worktree: Path, repo_rel: str) -> Path | None:
    """Nearest ancestor directory (never the worktree root) with a ``[tool.ruff]`` table."""
    worktree = worktree.resolve()
    current = (worktree / repo_rel).parent
    while True:
        if current == worktree:
            return None
        if not current.is_relative_to(worktree):
            return None
        pyproject = current / "pyproject.toml"
        if pyproject.is_file() and _pyproject_ruff_table(pyproject) is not None:
            return current
        current = current.parent


def _story_scoped_ruff_py_paths(worktree: Path, changed_files: tuple[str, ...]) -> tuple[str, ...]:
    selected: list[str] = []
    for path in changed_files:
        if not path.endswith(".py"):
            continue
        if is_cfe_surface_path(path):
            continue
        if not (worktree / path).is_file():
            continue
        if _ruff_group_root(worktree, path) is None:
            continue
        selected.append(path)
    return tuple(sorted(selected))


def _group_by_ruff_root(worktree: Path, repo_paths: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    groups: dict[str, list[str]] = {}
    for path in repo_paths:
        root = _ruff_group_root(worktree, path)
        if root is None:
            continue
        key = root.relative_to(worktree).as_posix()
        groups.setdefault(key, []).append(path)
    return {name: tuple(sorted(paths)) for name, paths in sorted(groups.items())}


def _paths_relative_to_root(repo_paths: tuple[str, ...], root_posix: str) -> tuple[str, ...]:
    prefix = root_posix.rstrip("/") + "/"
    return tuple(path.removeprefix(prefix) for path in repo_paths if path.startswith(prefix))


def _force_exclude_flag(group_root: Path) -> tuple[str, ...]:
    pyproject = group_root / "pyproject.toml"
    table = _pyproject_ruff_table(pyproject)
    if table is None:
        return ()
    if "exclude" in table or "extend-exclude" in table:
        return ("--force-exclude",)
    return ()


def _check_step_ok(returncode: int) -> bool:
    return returncode in (0, 1)


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

    story_py = _story_scoped_ruff_py_paths(worktree, scope_changed)
    if not story_py:
        return DispatchRuffFormatResult((), False)

    story_py_set = frozenset(story_py)
    group_results: list[DispatchRuffFormatGroupResult] = []

    for root_posix, repo_paths in _group_by_ruff_root(worktree, story_py).items():
        group_root = worktree / root_posix
        rel_paths = _paths_relative_to_root(repo_paths, root_posix)
        if not rel_paths:
            continue
        exclude = _force_exclude_flag(group_root)
        group_ok = True
        failed_step: str | None = None
        exit_code: int | None = None

        try:
            check_result = process.run(
                ["ruff", "check", "--fix", *exclude, *rel_paths],
                cwd=group_root,
            )
            if not _check_step_ok(check_result.returncode):
                group_ok = False
                failed_step = "check"
                exit_code = check_result.returncode
        except ProcessError:
            group_ok = False
            failed_step = "check"
            exit_code = None
            group_results.append(
                DispatchRuffFormatGroupResult(
                    root=root_posix,
                    files=repo_paths,
                    changed_paths=(),
                    ok=False,
                    failed_step=failed_step,
                    exit_code=exit_code,
                )
            )
            continue

        if group_ok:
            try:
                format_result = process.run(
                    ["ruff", "format", *exclude, *rel_paths],
                    cwd=group_root,
                )
                if format_result.returncode != 0:
                    group_ok = False
                    failed_step = "format"
                    exit_code = format_result.returncode
            except ProcessError:
                group_ok = False
                failed_step = "format"
                exit_code = None

        try:
            dirty = vcs.changed_files(git_repo, worktree, base="HEAD")
        except Exception:
            dirty = ()

        changed_in_group = tuple(sorted(path for path in dirty if path in frozenset(repo_paths)))
        group_results.append(
            DispatchRuffFormatGroupResult(
                root=root_posix,
                files=repo_paths,
                changed_paths=changed_in_group,
                ok=group_ok,
                failed_step=failed_step,
                exit_code=exit_code,
            )
        )

    try:
        dirty = vcs.changed_files(git_repo, worktree, base="HEAD")
    except Exception:
        return DispatchRuffFormatResult((), False, tuple(group_results))

    to_commit = tuple(sorted(path for path in dirty if path in story_py_set))
    if not to_commit:
        return DispatchRuffFormatResult((), False, tuple(group_results))

    try:
        vcs.commit_paths(
            worktree,
            tuple(Path(path) for path in to_commit),
            to_redacted_text("marshal: ruff check --fix and format story files (Story 83.9, 83.15)"),
        )
    except Exception:
        return DispatchRuffFormatResult((), False, tuple(group_results))

    return DispatchRuffFormatResult(to_commit, True, tuple(group_results))


def dispatch_ruff_format_should_journal(result: DispatchRuffFormatResult) -> bool:
    """True when the supervisor should journal the pre-verify ruff pass (Story 95.1)."""
    if result.reformatted_paths:
        return True
    return any(not group.ok for group in result.groups)


def dispatch_ruff_format_groups_payload(
    groups: tuple[DispatchRuffFormatGroupResult, ...],
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for group in groups:
        entry: dict[str, object] = {
            "root": group.root,
            "files": list(group.files),
            "changed_paths": list(group.changed_paths),
            "ok": group.ok,
        }
        if group.failed_step is not None:
            entry["failed_step"] = group.failed_step
        if group.exit_code is not None:
            entry["exit_code"] = group.exit_code
        out.append(entry)
    return out
