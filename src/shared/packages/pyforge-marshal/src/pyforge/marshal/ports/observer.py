"""``SessionObserverPort`` -- AD-9's externally-observable pane/mtime inputs
(Story 3.4). A Protocol definition only (Structural Seed: ``ports/``
declares shapes, never implementations); implemented solely by
``adapters/observer_mux.py`` (AD-4).

AD-9's own rule: "the supervisor observes from outside and never trusts
self-report ... its inputs are externally observable only: multiplexer pane
content, file modification times, process liveness, and adapter-reported
usage read from files the session wrote. It never asks the session how it
is doing." ``ProcessPort.is_alive`` already covers the liveness leg; this
Protocol covers the other two an agent session cannot fake from the
inside -- a captured terminal pane (the session cannot silently blank it
without producing observably blank output) and a file's own mtime (the
session cannot claim progress without touching a file the filesystem
timestamps independently of anything the session says).

Two methods, ``pane_content``/``mtime`` -- both NEVER raise, matching every
other observation-only port in this package (``HarnessPort.
binary_present``, ``ProcessPort.is_alive``): a probe that cannot answer
degrades to ``None``, since "the pane/path could not be observed" is itself
a legitimate, expected outcome (a session that has not yet created its
multiplexer pane, a usage file an adapter has not yet written), never a
failure this seam needs to model as an exception.

``pane_content`` is redaction-carrying at the CAPTURE site (AD-34): "Pane-
derived content is redacted at capture, before it enters ``core``, because
``core`` cannot redact (AD-4)." A raw agent-session pane can echo a
credential (an API key printed by a misbehaving tool, a token embedded in a
URL a `git` error surfaced) straight into its own terminal buffer, so the
ADAPTER implementing this method -- never a caller downstream of it -- must
route the captured text through ``core.egress.to_redacted`` before this
method ever returns it. See ``adapters/observer_mux.py``'s own docstring
for the concrete mechanics.

``core/**`` never calls this Protocol directly (AD-4) -- only
``supervisor/__main__.py`` holds a reference today; a future
``core/supervise.py`` (Story 3.5) will consume the plain, already-redacted
``str | None`` values this seam produces, never the port itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class SessionObserverPort(Protocol):
    def pane_content(self, session: str) -> str | None:
        """The named multiplexer pane's currently-captured text, already
        redacted (AD-34) -- ``None`` if ``session`` names no pane this host
        can find (the session has not started yet, has already exited and
        been reaped, or the multiplexer backend itself is unavailable).
        Never raises."""
        ...

    def mtime(self, path: Path) -> float | None:
        """``path``'s last-modified time as a Unix timestamp, or ``None`` if
        ``path`` does not exist or cannot be stat'd. Never raises."""
        ...
