"""Meta test -- Story 28.2 (SPEC-marshal-token-economy CAP-2): the
wire-compression CCR store is git-ignored, and the ``.marshal/`` NAMESPACE
around it is not.

Two rules meet in one directory and they want opposite things:

- ``.marshal/wire/`` is the wrapper's reversible CCR store -- a
  multi-megabyte sqlite cache written into a live loop home. It must be
  ignored, for the same two reasons ``.bmad-loop/archive/`` and
  ``claude_hash.txt`` are: ``bmad-loop run`` refuses to start on a dirty
  worktree, and the loop's own ``git add -A`` would otherwise sweep the
  cache into a merge commit.
- ``.marshal/seed-state.yml`` and ``.marshal/plan.json`` belong to the
  Genesis seed subsystem, which handles its own dirty-tree problem by
  EXCLUDING ``.marshal/`` with a git pathspec (``seed/verbs/adopt.py``'s
  ``':!.marshal/'``) rather than ignoring it -- and ``seed-state.yml``'s
  documented remedy for a ``state-invalid`` finding is literally "Restore
  ``.marshal/seed-state.yml`` from version control"
  (``docs/finding-remedy-reference.md``). A blanket ``.marshal/`` rule
  shadows that recovery path.

Story 28.2 first shipped the blanket rule; this test pins the narrowed one
so the namespace cannot be re-shadowed by a later convenience edit. It
asserts effective BEHAVIOR via ``git check-ignore`` rather than a literal
line, mirroring ``test_rendered_policy_untracked.py``'s own reasoning: a
negation pattern later in the ~880-line ``.gitignore`` would pass a literal
check while silently changing the outcome.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

#: The store path the packaged claude profile's ``wrapper.store_relpath``
#: declares, relative to a loop home -- and, one directory deeper, the same
#: store in a loop home that is not itself a worktree root.
_IGNORED = (".marshal/wire/ccr_store.db", "homes/acme/.marshal/wire/ccr_store.db")

#: The seed subsystem's own files in the same namespace, which must stay
#: visible to git.
_NOT_IGNORED = (
    ".marshal/seed-state.yml",
    ".marshal/plan.json",
    "homes/acme/.marshal/seed-state.yml",
)


def _repo_root() -> Path:
    """Walk up until a ``.git`` entry (an ordinary repo's directory, or a
    linked worktree's pointer file) -- never a hardcoded parents index, so
    this keeps working inside a dispatch/bmad-loop run worktree."""
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise AssertionError(f"no .git found walking up from {current}")


def _check_ignore(path: str) -> subprocess.CompletedProcess[str]:
    # `--no-index` so the answer is about the RULES, not about whether the
    # path happens to exist or be tracked in this particular checkout.
    return subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "--", path],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize("path", _IGNORED)
def test_the_ccr_store_is_ignored(path: str) -> None:
    result = _check_ignore(path)
    assert result.returncode == 0, (
        f"{path} must be git-ignored -- the wire-compression store would "
        "otherwise dirty a loop worktree (blocking `bmad-loop run`) and be "
        f"swept into a commit by `git add -A` (rc={result.returncode})"
    )


@pytest.mark.parametrize("path", _NOT_IGNORED)
def test_the_seed_namespace_is_not_shadowed(path: str) -> None:
    result = _check_ignore(path)
    assert result.returncode == 1, (
        f"{path} must NOT be git-ignored: it belongs to the Genesis seed "
        "subsystem, whose `state-invalid` remedy is to restore it from "
        "version control, and whose dirty-tree handling is a git pathspec "
        "exclusion in seed/verbs/adopt.py -- not an ignore rule "
        f"(rc={result.returncode}, matched: {result.stdout.strip()!r})"
    )
