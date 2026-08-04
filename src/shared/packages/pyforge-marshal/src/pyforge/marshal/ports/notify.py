"""``NotifyPort`` -- a new AD-34 egress port (Story 3.7, FR-15): the
supervisor's own notification seam for an unresolved escalation. A Protocol
definition only (Structural Seed: ``ports/`` declares shapes, never
implementations); implemented solely by
``adapters/notify_file_desktop.py::FileDesktopNotifier`` (AD-4).

Two methods, both accepting only ``core.egress.Redacted`` -- never a bare
``str`` (``tests/meta/test_ad34_egress_registry_completeness.py`` enforces
this structurally at build time over EVERY parameter, not only the one
semantically carrying "the payload"; see ``notify_desktop``'s own docstring
for why its signature departs from the intent-contract's literal two-
parameter (``title: str``, ``payload: Redacted``) wording for exactly this
reason):

- ``notify_file`` -- writes a durable file marker. Mandatory (the spec's own
  Always bullet): the supervisor always attempts it on an unresolved
  escalation, though its own failure (``FsError``) is tolerated and reported
  as a WARN (``MRS-SUPV-007``) rather than blocking the detach.
- ``notify_desktop`` -- a best-effort desktop notification. Any exception or
  a ``False`` return is swallowed entirely by the caller; a failure here
  never affects the detach outcome.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..core.egress import Redacted


class NotifyPort(Protocol):
    def notify_file(self, path: Path, payload: Redacted) -> None:
        """Write ``payload.text`` to ``path`` (the same guarded
        ``write_text_atomic``-backed write ``RecordPort.write_redacted_atomic``
        itself makes -- no new atomic-write logic). Raises ``FsError`` on
        write failure, identical to ``RecordPort.write_redacted_atomic``;
        the caller decides whether a failure here blocks anything (it does
        not -- see the module docstring)."""
        ...

    def notify_desktop(self, payload: Redacted) -> bool:
        """Best-effort desktop notification carrying ``payload``'s already-
        redacted content -- a short-timeout call to a platform notifier.
        ``True`` iff the notifier reported success; ``False`` for any other
        outcome, including one this method could not even attempt. Never
        raises (best-effort by contract, not merely by the caller's own
        tolerance of it).

        Takes only ``payload`` -- not the intent-contract's literal
        ``(title: str, payload: Redacted)`` pair (a genuine spec inaccuracy;
        see the story's own Spec Change Log): the AD-34 meta-test flags ANY
        bare-``str``-typed parameter on an egress-classified port,
        regardless of which parameter is semantically "the payload", so a
        separate ``title: str`` would fail the very guard the intent-
        contract cites as enforcing this port's shape. This port's own
        implementation (``FileDesktopNotifier.notify_desktop``) uses a
        fixed, non-secret title string and passes only ``payload.text`` as
        the notification body -- so no title text ever needs to travel
        through ``payload`` at all (corrected: an earlier draft of this
        docstring claimed the opposite)."""
        ...
