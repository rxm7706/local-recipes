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

``pytest`` is needed for skip-on-missing-base-ref (the whole point of this
module), but it is imported INSIDE ``_require_ref`` rather than at module
scope, so this package keeps the empty ``[project.dependencies]`` it declares.
Every consumer is itself a pytest test file, so nothing is added that isn't
already present -- but a module-level import would still make it an undeclared
runtime dependency, which `tests/packaging/test_dependency_completeness.py`
correctly fails on. See the comment at the import for the full reasoning.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path


def _require_ref(root: Path, ref: str) -> None:
    # Imported HERE, not at module scope: `pytest` is the one non-stdlib name
    # this module touches, and it is reachable from exactly this one call. A
    # module-level import would make it a real, undeclared dependency of a
    # package whose `[project.dependencies]` is deliberately empty -- which is
    # precisely what `tests/packaging/test_dependency_completeness.py` fails on
    # (it inspects module-level imports only). Keeping it function-local lets
    # the package stay the stdlib leaf it claims to be while `pytest.skip`
    # still works for every consumer, all of which are pytest test files.
    import pytest

    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
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
    base: str = "origin/main",
    pathspec: str | tuple[str, ...] | None = None,
    require: str | None = None,
) -> str:
    """Raw ``git diff <base> [-- pathspec...]`` text. Skips the calling test
    when the base ref (``require``, defaulting to ``base``) is not resolvable
    in this checkout -- never raises ``CalledProcessError``."""
    _require_ref(root, require or base)
    cmd = ["git", "diff", base, *_pathspec_args(pathspec)]
    return subprocess.check_output(cmd, cwd=root, text=True)


def changed_paths_since(
    root: Path,
    *,
    base: str = "origin/main",
    pathspec: str | tuple[str, ...] | None = None,
    require: str | None = None,
    include_untracked: bool = False,
    always_include: tuple[str, ...] = (),
) -> list[str]:
    """Paths changed since ``base`` under ``pathspec`` (repo-wide if
    ``None``). Skips the calling test (never raises ``CalledProcessError``)
    when the base ref is not resolvable in this checkout."""
    _require_ref(root, require or base)
    named = subprocess.check_output(
        ["git", "diff", "--name-only", base, *_pathspec_args(pathspec)],
        cwd=root,
        text=True,
    )
    changed = {line for line in named.splitlines() if line.strip()}
    if include_untracked:
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", *_pathspec_args(pathspec)],
            cwd=root,
            text=True,
        )
        changed |= {line for line in untracked.splitlines() if line.strip()}
    changed |= set(always_include)
    return sorted(changed)


def existed_at_ref(root: Path, path: str, *, ref: str = "origin/main") -> bool:
    """True if ``path`` was already present in ``ref``'s tree -- i.e. a diff
    against it MODIFIES an existing file rather than ADDING a new one."""
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{path}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


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
    base: str = "origin/main",
    pathspec: str | tuple[str, ...] | None = None,
    no_merges: bool = True,
) -> list[str]:
    """Full commit SHAs on ``base..HEAD`` touching ``pathspec`` (repo-wide if
    ``None``). Skips the calling test when ``base`` is not resolvable."""
    _require_ref(root, base)
    cmd = ["git", "log"]
    if no_merges:
        cmd.append("--no-merges")
    cmd += ["--format=%H", f"{base}..HEAD", *_pathspec_args(pathspec)]
    return subprocess.check_output(cmd, cwd=root, text=True).split()


def commit_subject(root: Path, sha: str) -> str:
    return subprocess.check_output(["git", "log", "-1", "--format=%s", sha], cwd=root, text=True).strip()


def commit_files(root: Path, sha: str) -> list[str]:
    return subprocess.check_output(["git", "show", "--format=", "--name-only", sha], cwd=root, text=True).split()


# `retro:` or `retro(<scope>):` -- see unsanctioned_commits.__doc__.
_RETRO_SUBJECT = re.compile(r"^retro(\([^)]*\))?:")


def unsanctioned_commits(
    root: Path,
    *,
    pathspec: str,
    changelog_path: str,
    base: str = "origin/main",
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
    dirty = subprocess.check_output(["git", "diff", "--name-only", "HEAD", "--", pathspec], cwd=root, text=True).split()
    if dirty:
        bad.append("uncommitted: " + ", ".join(dirty))
    return bad
