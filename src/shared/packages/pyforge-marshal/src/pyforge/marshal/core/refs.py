"""Remote-tracking refs by their full refname (Story 60.1, CAP-270).

Git resolves a short name like ``origin/main`` to a local branch or tag of that name before
the remote-tracking ref (``refs/<name>``, ``refs/tags/<name>``, ``refs/heads/<name>``, then
``refs/remotes/<name>``), so a stray local ``origin/main`` would stand in for the remote.
Stories 57.1 (``refresh``) and 59.1 (the landing heal) closed that in one place each; this
module is the one place every git-facing read of the remote names it from. Pure: no I/O.
"""

from __future__ import annotations

ORIGIN = "origin"


def remote_tracking_ref(branch: str, remote: str = ORIGIN) -> str:
    """The full refname of ``remote``'s ``branch``: ``refs/remotes/<remote>/<branch>``."""
    return f"refs/remotes/{remote}/{branch}"


def display_ref(branch: str, remote: str = ORIGIN) -> str:
    """``<remote>/<branch>`` as people read it -- for messages only, never handed to git."""
    return f"{remote}/{branch}"


#: What marshal means by "the remote's main" wherever git reads it.
ORIGIN_MAIN = remote_tracking_ref("main")
#: The same ref as people read it -- for messages only.
ORIGIN_MAIN_SHORT = display_ref("main")
