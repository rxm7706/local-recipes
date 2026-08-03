"""``MultiplexerObserver`` -- the sole implementation of
``ports.SessionObserverPort`` (Story 3.4, AD-4/AD-9/AD-34): shells out to
``tmux capture-pane -t <session> -p`` for a pane's text, and
``Path.stat().st_mtime`` for a file's modification time. Neither method
raises -- an unavailable pane or an unreadable path is this port's own
documented ``None``, not a failure.

``tmux`` directly, via this module's OWN ``subprocess`` call -- NOT
``adapters/process_posix.py``'s ``ProcessPort.run`` (adapters never import
each other, AD-4; the Code Map is explicit that this module "cannot reuse
process_posix.py"). ``bmad_loop`` itself supports more than one multiplexer
backend (``adapters/harness_bmadloop.py::multiplexer_backend_available``),
but this story wires only the ``tmux`` case -- the packaged default and the
one this repo's own loop homes run under; a second backend is out of this
story's own Surface (Story 3.5's `core/supervise.py` is the first real
CONSUMER of a pane sample, and nothing in this story's own AC asks for
multi-backend support).

**Redaction at capture (AD-34).** ``pane_content`` wraps the raw captured
text as ``{"pane": text}``, redacts it whole via ``core.egress.to_redacted``
(the ONE redacting serializer this package owns -- no second, adapter-local
redaction vocabulary), then ``json.loads``\\s the result's own ``.text``
back out and returns the ``"pane"`` value as a plain ``str``. Round-tripping
through JSON rather than hand-picking a substring out of ``Redacted.text``
keeps this adapter from ever having to re-parse ``to_redacted``'s own
serialization format itself -- the wrapper/unwrap is symmetric, and
``to_redacted`` is already the one place this package trusts to walk a
string for secret shapes (Story 2.6's own closed token-shape vocabulary).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..core.egress import to_redacted

# A capture-pane call reads an already-running terminal's own back-buffer --
# no engine work happens inside tmux itself to wait on. Sized well below the
# supervisor's own 60s tick (see supervisor/__main__.py) so a hung or
# misbehaving tmux binary degrades one sample to None rather than stalling
# an entire tick.
_CAPTURE_PANE_TIMEOUT_S = 5.0


class MultiplexerObserver:
    """``ports.SessionObserverPort``'s sole implementation."""

    def pane_content(self, session: str) -> str | None:
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", session, "-p"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_CAPTURE_PANE_TIMEOUT_S,
            )
        except (OSError, subprocess.TimeoutExpired, ValueError):
            # tmux itself missing, or a hung capture -- indistinguishable
            # from "no such session" at this port's own documented
            # granularity: both degrade to None, never raise. `ValueError`
            # too (review finding): `subprocess.run` raises a plain
            # `ValueError` -- not an `OSError` -- for an embedded NUL byte
            # in an argv element, which would otherwise escape this port's
            # own documented "never raises" contract.
            return None
        if result.returncode != 0:
            # tmux's own "no such session" exit (and every other capture
            # failure) -- the pane simply cannot be observed right now.
            return None
        redacted = to_redacted({"pane": result.stdout})
        return json.loads(redacted.text)["pane"]

    def mtime(self, path: Path) -> float | None:
        try:
            return path.stat().st_mtime
        except (OSError, ValueError):
            # `ValueError` alongside `OSError` (review finding): `Path.stat`
            # raises a plain `ValueError` -- not an `OSError` -- for a path
            # containing an embedded NUL byte, which would otherwise escape
            # this port's own documented "never raises" contract.
            return None
