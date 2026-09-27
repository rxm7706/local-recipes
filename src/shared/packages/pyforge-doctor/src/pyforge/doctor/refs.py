"""Refs by their full refname (Story 31.1, spec-pyforge-doctor CAP-85).

Git resolves a short name through ``refs/<n>``, ``refs/tags/<n>``, ``refs/heads/<n>``, then
``refs/remotes/<n>``: a local branch or tag named ``origin/main`` stands in for the remote, and a
tag named ``main`` for the local branch. Every git read a Doctor source makes of a branch names it
from here. Doctor's own module -- Doctor imports no station's internals (marshal keeps the same
rule in its ``core/refs.py``, marshal:CAP-270 / marshal:CAP-271). Pure: no I/O.
"""

from __future__ import annotations

ORIGIN = "origin"


def local_branch_ref(branch: str) -> str:
    """The full refname of the local ``branch``: ``refs/heads/<branch>``."""
    return f"refs/heads/{branch}"


def remote_tracking_ref(branch: str, remote: str = ORIGIN) -> str:
    """The full refname of ``remote``'s ``branch``: ``refs/remotes/<remote>/<branch>``."""
    return f"refs/remotes/{remote}/{branch}"


def display_ref(ref: str) -> str:
    """``ref`` as people read it -- ``main`` / ``origin/main`` for the two full forms above,
    anything else unchanged. For findings and evidence only, never handed to git."""
    for prefix in ("refs/heads/", "refs/remotes/"):
        if ref.startswith(prefix):
            return ref.removeprefix(prefix)
    return ref


#: The local ``main`` wherever a Doctor source reads it.
MAIN = local_branch_ref("main")
#: The remote's ``main`` wherever a Doctor source reads it.
ORIGIN_MAIN = remote_tracking_ref("main")
