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
scan that never looked (a false green). ``NotADirectoryError`` means
genuinely absent; a ``FileNotFoundError`` is disambiguated before it may
claim absence — a dangling ``pyproject.toml`` symlink (visibly present,
target missing) and a scan target that vanished or was replaced mid-scan
(TOCTOU) both FAIL CLOSED with an ``OSError`` instead of reading as "no
manifest" → exit 0. A ``pyproject.toml`` that exists but is not a regular
file (directory, FIFO, socket) also fails closed: found-but-refused must
never be reported as "nothing existed". Every propagated ``OSError``
surfaces as an ``internal-error`` report in the CLI, exit via
``exit_code_for(error)``.

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
    must never be reported as "nothing there" — and found-but-refused
    states (dangling symlink, non-regular file, vanished/replaced target)
    fail closed the same way."""
    candidate = target / PYPROJECT_KIND
    try:
        result = candidate.stat()
    except NotADirectoryError:
        # ``target`` (or a path component) is a file: <file>/pyproject.toml
        # is genuinely absent, not an error.
        return ()
    except FileNotFoundError as exc:
        if candidate.is_symlink():
            # Visibly present but its target is missing: found-but-refused,
            # never "nothing existed".
            raise OSError(
                f"{PYPROJECT_KIND} in {target} is a dangling symlink; "
                "manifest state undeterminable"
            ) from exc
        try:
            target_result = target.stat()
        except FileNotFoundError:
            raise OSError(
                f"scan target {target} vanished mid-scan; manifest state "
                "undeterminable"
            ) from exc
        if not stat.S_ISDIR(target_result.st_mode):
            raise OSError(
                f"scan target {target} is no longer a directory; manifest "
                "state undeterminable"
            ) from exc
        return ()
    if not stat.S_ISREG(result.st_mode):
        raise OSError(
            f"{PYPROJECT_KIND} in {target} exists but is not a regular "
            f"file (mode {stat.filemode(result.st_mode)!r}); refusing to "
            "read it must never read as absent"
        )
    return (ScannedManifest(path=PYPROJECT_KIND, kind=PYPROJECT_KIND),)
