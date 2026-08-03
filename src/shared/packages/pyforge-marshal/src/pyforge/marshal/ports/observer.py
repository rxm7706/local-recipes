"""``SessionObserverPort`` -- AD-9's externally-observable pane/mtime inputs
(Story 3.4), plus the Story 3.5 nudge-delivery seam ``send_text``. A
Protocol definition only (Structural Seed: ``ports/`` declares shapes, never
implementations); implemented solely by ``adapters/observer_mux.py`` (AD-4).

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

``pane_content``/``mtime`` -- both NEVER raise, matching every other
observation-only port in this package (``HarnessPort.binary_present``,
``ProcessPort.is_alive``): a probe that cannot answer degrades to ``None``,
since "the pane/path could not be observed" is itself a legitimate, expected
outcome (a session that has not yet created its multiplexer pane, a usage
file an adapter has not yet written), never a failure this seam needs to
model as an exception.

``pane_content`` is redaction-carrying at the CAPTURE site (AD-34): "Pane-
derived content is redacted at capture, before it enters ``core``, because
``core`` cannot redact (AD-4)." A raw agent-session pane can echo a
credential (an API key printed by a misbehaving tool, a token embedded in a
URL a `git` error surfaced) straight into its own terminal buffer, so the
ADAPTER implementing this method -- never a caller downstream of it -- must
route the captured text through ``core.egress.to_redacted`` before this
method ever returns it. See ``adapters/observer_mux.py``'s own docstring
for the concrete mechanics.

Story 3.5 (idle-strand detection, AD-9/AD-20) adds ``send_text`` -- the
ladder's own nudge-delivery primitive: deliver ``text`` into the named
session's live pane, as if typed and submitted at its prompt. NEVER raises,
matching ``pane_content``/``mtime`` -- ``False`` when no window could be
resolved or delivery otherwise failed (never distinguished further; the
caller's own registered finding names the condition generically, matching
this story's own I/O matrix). Both ``pane_content`` and ``send_text``
resolve their target window LIVE, at call time, never from a cached or
formula-derived id -- see ``adapters/observer_mux.py``'s own docstring for
why.

``core/**`` never calls this Protocol directly (AD-4) -- only
``supervisor/__main__.py`` holds a reference; ``core/supervise.py``
(Story 3.5) consumes the plain, already-redacted ``str | None``/``float |
None`` values this seam produces via ``Sample``, never the port itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class SessionObserverPort(Protocol):
    def pane_content(self, session: str) -> str | None:
        """The named session's live, currently-active window's captured
        text, already redacted (AD-34) -- ``None`` if ``session`` names no
        session this host can find, no window resolves unambiguously
        (``adapters/observer_mux.py``'s own live ``list-windows`` resolution
        finds zero or more than one candidate with no clear active one), or
        the multiplexer backend itself is unavailable. Never raises."""
        ...

    def mtime(self, path: Path) -> float | None:
        """``path``'s last-modified time as a Unix timestamp, or ``None`` if
        ``path`` does not exist or cannot be stat'd. Never raises."""
        ...

    def send_text(self, session: str, text: str) -> bool:
        """Deliver ``text`` into ``session``'s live, currently-active
        window, as if typed and submitted at its prompt (Story 3.5's own
        nudge-delivery primitive). ``True`` iff delivery was attempted
        against a resolved window and the underlying commands succeeded;
        ``False`` for the same degrade conditions ``pane_content`` documents
        (no session, no unambiguous window, an unavailable backend) or any
        delivery failure. Never raises."""
        ...
