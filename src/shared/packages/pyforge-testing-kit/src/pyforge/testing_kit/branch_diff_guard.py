"""Shared mechanics for the fleet's whole-branch diff-guard meta-tests
(retro-pyforge-steward-2026-09-04.md action item 11).

Every station grew its own "this story must not touch X" test computing
roughly the same thing -- files or commits changed since a base ref -- and
every copy but one carried the same latent bug: a depth-1 CI checkout has no
`origin/main` until the workflow fetches it, and a bare `git diff origin/main`
raises `CalledProcessError` instead of skipping loudly (retro row 20). The one
call site that got this right first was
`src/platform/tests/test_warden_portal_audit_start_get.py::_platform_python_rels`.

This module centralizes the git mechanics only. Each guard's own POLICY --
which paths, which exemptions, which content check -- stays local to the test
file that owns it; nothing here decides what a violation looks like.

The base defaults to ``refs/remotes/origin/main`` (``ORIGIN_MAIN``), and an
explicit ``origin/<branch>`` is read by its full refname too (marshal Story
62.1, spec-pyforge-marshal CAP-272): git resolves a short name to a local
branch or tag of that name before ``refs/remotes/<name>``, so a stray local
``origin/main`` at HEAD emptied every guard, which then passed having checked
nothing.

Every ``git`` call goes through ``pyforge.core.process.PosixProcess.run``, the
one sanctioned subprocess seam (``spec-pyforge-core`` CAP-6). The kit declares
``pyforge-core`` as a runtime dependency (marshal Story 74.1, the operator
ruling of 2026-09-30 that retired Q-26's stdlib-leaf premise), so this module
no longer opts out of ``pyforge-core``'s subprocess sole-ownership scan.
``PosixProcess.run`` never raises for a non-zero exit; ``_git_out`` restores
the ``CalledProcessError`` the old ``check_output`` calls raised, so a failing
``git`` is still loud.

``pytest`` is needed for skip-on-missing-base-ref (the whole point of this
module), but it is imported INSIDE ``_require_ref`` rather than at module
scope: the kit does not declare it (every consumer is itself a pytest test
file), and a module-level import would make it an undeclared runtime
dependency, which `tests/packaging/test_dependency_completeness.py` correctly
fails on. See the comment at the import for the full reasoning.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessResult

#: The remote's ``main`` by its full refname -- every guard's default base.
ORIGIN_MAIN = "refs/remotes/origin/main"

_PROCESS = PosixProcess()


def _git(root: Path, *args: str) -> ProcessResult:
    """Run ``git <args>`` in ``root``; a non-zero exit is returned, never raised."""
    return _PROCESS.run(["git", *args], cwd=root)


def _git_out(root: Path, *args: str) -> str:
    """``git <args>`` stdout; a non-zero exit raises ``CalledProcessError`` (the old ``check_output`` contract)."""
    result = _git(root, *args)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, ["git", *args], output=result.stdout, stderr=result.stderr
        )
    return result.stdout


def _full(ref: str) -> str:
    """``origin/<branch>`` as ``refs/remotes/origin/<branch>``; any other ref (a full
    ref, ``HEAD``, a sha, a local branch name) unchanged."""
    return f"refs/remotes/{ref}" if ref.startswith("origin/") else ref


def _require_ref(root: Path, ref: str) -> None:
    # Imported HERE, not at module scope: `pytest` is the one name this module
    # touches that the kit does not declare, and it is reachable from exactly
    # this one call. A module-level import would make it a real, undeclared
    # dependency of the package -- which is precisely what
    # `tests/packaging/test_dependency_completeness.py` fails on (it inspects
    # module-level imports only). Keeping it function-local lets `pytest.skip`
    # still work for every consumer, all of which are pytest test files.
    import pytest

    resolved = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if resolved.returncode != 0:
        pytest.skip(f"{ref} is not available in this checkout; the diff guard needs the base ref")


def _pathspec_args(pathspec: str | tuple[str, ...] | None) -> list[str]:
    if pathspec is None:
        return []
    paths = [pathspec] if isinstance(pathspec, str) else list(pathspec)
    return ["--", *paths]


def diff_text_since(
    root: Path,
    *,
    base: str = ORIGIN_MAIN,
    pathspec: str | tuple[str, ...] | None = None,
    require: str | None = None,
) -> str:
    """Raw ``git diff <base> [-- pathspec...]`` text. Skips the calling test
    when the base ref (``require``, defaulting to ``base``) is not resolvable
    in this checkout -- never raises ``CalledProcessError``."""
    base = _full(base)
    _require_ref(root, _full(require) if require else base)
    return _git_out(root, "diff", base, *_pathspec_args(pathspec))


def changed_paths_since(
    root: Path,
    *,
    base: str = ORIGIN_MAIN,
    pathspec: str | tuple[str, ...] | None = None,
    require: str | None = None,
    include_untracked: bool = False,
    always_include: tuple[str, ...] = (),
) -> list[str]:
    """Paths changed since ``base`` under ``pathspec`` (repo-wide if
    ``None``). Skips the calling test (never raises ``CalledProcessError``)
    when the base ref is not resolvable in this checkout."""
    base = _full(base)
    _require_ref(root, _full(require) if require else base)
    named = _git_out(root, "diff", "--name-only", base, *_pathspec_args(pathspec))
    changed = {line for line in named.splitlines() if line.strip()}
    if include_untracked:
        untracked = _git_out(root, "ls-files", "--others", "--exclude-standard", *_pathspec_args(pathspec))
        changed |= {line for line in untracked.splitlines() if line.strip()}
    changed |= set(always_include)
    return sorted(changed)


def existed_at_ref(root: Path, path: str, *, ref: str = ORIGIN_MAIN) -> bool:
    """True if ``path`` was already present in ``ref``'s tree -- i.e. a diff
    against it MODIFIES an existing file rather than ADDING a new one."""
    return _git(root, "cat-file", "-e", f"{_full(ref)}:{path}").returncode == 0


def pyforge_import_offenders(paths: list[str], root: Path) -> list[str]:
    """Which of ``paths`` (repo-relative) contain a top-level ``import
    pyforge`` / ``from pyforge...`` -- ``"rel:lineno"`` entries, never a
    crash on a non-Python or already-deleted path."""
    offenders: list[str] = []
    for rel in paths:
        path = root / rel
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            if "pyforge" in names:
                offenders.append(f"{rel}:{node.lineno}")
    return offenders


def commits_since(
    root: Path,
    *,
    base: str = ORIGIN_MAIN,
    pathspec: str | tuple[str, ...] | None = None,
    no_merges: bool = True,
) -> list[str]:
    """Full commit SHAs on ``base..HEAD`` touching ``pathspec`` (repo-wide if
    ``None``). Skips the calling test when ``base`` is not resolvable."""
    base = _full(base)
    _require_ref(root, base)
    args = ["log"]
    if no_merges:
        args.append("--no-merges")
    args += ["--format=%H", f"{base}..HEAD", *_pathspec_args(pathspec)]
    return _git_out(root, *args).split()


def commit_subject(root: Path, sha: str) -> str:
    return _git_out(root, "log", "-1", "--format=%s", sha).strip()


def commit_files(root: Path, sha: str) -> list[str]:
    return _git_out(root, "show", "--format=", "--name-only", sha).split()


# `retro:` or `retro(<scope>):` -- see unsanctioned_commits.__doc__.
_RETRO_SUBJECT = re.compile(r"^retro(\([^)]*\))?:")


def unsanctioned_commits(
    root: Path,
    *,
    pathspec: str,
    changelog_path: str,
    base: str = ORIGIN_MAIN,
) -> list[str]:
    """Commits on ``base..HEAD`` touching ``pathspec`` that are NOT a
    sanctioned Rule-2 retro (subject starts ``retro:`` or ``retro(<scope>):``
    AND ``changelog_path`` moves in the same commit) -- plus any uncommitted
    dirty paths under ``pathspec``. Mirrors the CFE-surface guard duplicated
    across atlas/marshal/mason/steward (``_unsanctioned_cfe_commits``).

    The optional Conventional-Commits scope is accepted deliberately. This
    matched a bare ``retro:`` only, but the repo's own practice had already
    moved to ``retro(cfe):`` -- v8.87.2, v8.88.0, v8.88.1 and v8.89.0 are all
    on ``main`` in that form. They landed because this guard only ever inspects
    ``base..HEAD``, so a subject it would reject stops being visible the moment
    it merges. Widening to the scoped form costs nothing: the load-bearing half
    of the rule is that ``changelog_path`` moves in the SAME commit, which is
    unchanged. Rejecting the scope instead would have meant rewriting a retro
    commit whose SHA is recorded as ``brief_mirrored_through`` in
    ``spec-conda-forge-expert-rebuild``'s campaign-state and validated by
    ``cfe_rebuild_guard_check``."""
    bad: list[str] = []
    for sha in commits_since(root, base=base, pathspec=pathspec, no_merges=True):
        subject = commit_subject(root, sha)
        files = commit_files(root, sha)
        if not (_RETRO_SUBJECT.match(subject) and changelog_path in files):
            bad.append(f"{sha[:10]} {subject}")
    dirty = _git_out(root, "diff", "--name-only", "HEAD", "--", pathspec).split()
    if dirty:
        bad.append("uncommitted: " + ", ".join(dirty))
    return bad
