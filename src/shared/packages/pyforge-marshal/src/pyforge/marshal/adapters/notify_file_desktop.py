"""``FileDesktopNotifier`` -- ``ports.NotifyPort``'s sole implementation
(Story 3.7, AD-4/AD-34): a durable file-marker write plus a best-effort
desktop notification, both accepting only an already-redacted
``core.egress.Redacted`` payload.

``notify_file`` delegates ENTIRELY to an injected ``RecordPort`` (default
``adapters/fs_local.py::LocalFs``, the same default DI convention every
other adapter-consuming module in this package applies) -- no new atomic-
write logic, the same "same type guards, same delegation to an existing
atomic-write primitive" precedent ``ports/record.py``'s own docstring
already establishes for the durable-write half of AD-34's egress boundary.

``notify_desktop`` shells out to ``notify-send`` (the packaged default
desktop notifier on every Linux loop home this project targets) via
``pyforge.core.process.PosixProcess`` (Story 14.4, SPEC-pyforge-core CAP-6 --
previously a direct ``subprocess.run`` call, mirroring
``adapters/observer_mux.py``'s own pre-migration convention): catches the
ONE ``ProcessError`` that primitive folds every launch failure into (a
missing binary, a hung process, an embedded-NUL byte) and returns ``bool``,
never raising -- an unavailable notifier degrades to ``False``, the same
"unavailable is this port's own documented answer, never a failure" shape
``MultiplexerObserver``'s methods already establish.
"""

from __future__ import annotations

# `subprocess` is imported for this module's own tests' monkeypatch anchor
# (`monkeypatch.setattr(module.subprocess, "run", ...)` -- the same physical
# stdlib module object `PosixProcess.run` itself calls, so patching it here
# still reaches the real launch below) -- the production code never calls
# `subprocess.*` directly.
import subprocess  # noqa: F401
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError

from ..core.egress import Redacted
from ..ports.record import RecordPort
from .fs_local import LocalFs

# A desktop notification is a fire-and-forget local IPC call to the host's
# own notification daemon -- no engine work to wait on. Sized well below the
# supervisor's own 60s tick (see supervisor/__main__.py's own
# _CAPTURE_PANE_TIMEOUT_S precedent for the identical reasoning) so a hung
# or missing notifier degrades this one best-effort call rather than
# stalling the detach it must never block.
_DESKTOP_NOTIFY_TIMEOUT_S = 5.0
_DESKTOP_NOTIFY_BINARY = "notify-send"
_DESKTOP_NOTIFY_TITLE = "Marshal: escalation detected"


class FileDesktopNotifier:
    """``ports.NotifyPort``'s sole implementation."""

    def __init__(self, record: RecordPort | None = None) -> None:
        self._record: RecordPort = record if record is not None else LocalFs()

    def notify_file(self, path: Path, payload: Redacted) -> None:
        # Delegates entirely to the existing egress-port precedent -- same
        # type guards (`isinstance(path, Path)`, `isinstance(payload,
        # Redacted)`), same atomic-write mechanics, no new logic here at
        # all.
        self._record.write_redacted_atomic(path, payload)

    def notify_desktop(self, payload: Redacted) -> bool:
        if not isinstance(payload, Redacted):
            # The TYPE only, never the value -- mirrors
            # `LocalFs.write_redacted_atomic`'s own contract-violation guard.
            raise TypeError(f"payload must be a Redacted instance, got {type(payload).__name__}")
        try:
            result = PosixProcess().run(
                [_DESKTOP_NOTIFY_BINARY, _DESKTOP_NOTIFY_TITLE, payload.text],
                cwd=Path.cwd(),
                timeout_s=_DESKTOP_NOTIFY_TIMEOUT_S,
            )
        except ProcessError:
            # Story 14.4, SPEC-pyforge-core CAP-6: `PosixProcess.run` folds
            # every launch failure (missing binary, a hung notifier, an
            # embedded NUL byte in the payload text) into one `ProcessError`
            # -- this port's own documented `False`, never raise.
            return False
        return result.returncode == 0
