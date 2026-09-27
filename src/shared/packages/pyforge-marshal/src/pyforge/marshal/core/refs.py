"""Refs by their full refname (Stories 60.1 and 61.1, CAP-270 and CAP-271).

Git resolves a short name through ``refs/<name>``, ``refs/tags/<name>``, ``refs/heads/<name>``,
then ``refs/remotes/<name>``, so a stray local ``origin/main`` would stand in for the remote, and a
tag named ``main`` stands in for the local branch ``main``. Stories 57.1 (``refresh``) and 59.1
(the landing heal) closed the first in one place each; this module is the one place every
git-facing read of the remote, and of one of marshal's own local branches, names it from. Pure:
no I/O.
"""

from __future__ import annotations

ORIGIN = "origin"


def remote_tracking_ref(branch: str, remote: str = ORIGIN) -> str:
    """The full refname of ``remote``'s ``branch``: ``refs/remotes/<remote>/<branch>``."""
    return f"refs/remotes/{remote}/{branch}"


def local_branch_ref(branch: str) -> str:
    """The full refname of the local ``branch``: ``refs/heads/<branch>``. For git's revision
    arguments only -- where git reads a branch *name* (``branch -D``, attaching an existing branch
    to a worktree, ``<branch>@{upstream}``) the bare name is the right one."""
    return f"refs/heads/{branch}"


def display_ref(branch: str, remote: str = ORIGIN) -> str:
    """``<remote>/<branch>`` as people read it -- for messages only, never handed to git."""
    return f"{remote}/{branch}"


#: What marshal means by "the remote's main" wherever git reads it.
ORIGIN_MAIN = remote_tracking_ref("main")
#: The same ref as people read it -- for messages only.
ORIGIN_MAIN_SHORT = display_ref("main")
