"""Single-manifest discovery stub (Story 1.2).

OWNERSHIP DECISION (recorded): full FR1 discovery — multi-manifest
enumeration, deterministic selection policy, and the manifest-kind
vocabulary — is Story 1.9's. This stub locates at most ONE manifest: a
``pyproject.toml`` directly in the scan target. The manifest path is
recorded RELATIVE to the target (report paths are target-relative, a
determinism invariant), and the kind token is ``"pyproject.toml"``.

Stat-error honesty: existence is determined via an EXPLICIT ``stat`` —
``Path.is_file()`` swallows every ``OSError`` (returns ``False``), which
would read a permission-denied target as "no manifest" and green-light a
scan that never looked (a false green). ``FileNotFoundError`` /
``NotADirectoryError`` mean genuinely absent; every other ``OSError``
propagates to the caller (the CLI surfaces it as an ``internal-error``
report, exit via ``exit_code_for(error)``).

This module reads the filesystem (existence check only); no subprocess,
no network.
"""

from __future__ import annotations

import stat
from pathlib import Path

from .models import ScannedManifest

# The 1.2 manifest-kind token (vocabulary owned by Story 1.9).
PYPROJECT_KIND = "pyproject.toml"


def discover(target: Path) -> tuple[ScannedManifest, ...]:
    """Return the resolved scan set for ``target`` — at most one entry.

    Empty tuple when no ``pyproject.toml`` exists directly in ``target``
    (the empty-dir case: nothing existed to scan). A stat failure other
    than absence (e.g. ``PermissionError``) propagates — "could not look"
    must never be reported as "nothing there"."""
    candidate = target / PYPROJECT_KIND
    try:
        result = candidate.stat()
    except (FileNotFoundError, NotADirectoryError):
        return ()
    if not stat.S_ISREG(result.st_mode):
        return ()
    return (ScannedManifest(path=PYPROJECT_KIND, kind=PYPROJECT_KIND),)
