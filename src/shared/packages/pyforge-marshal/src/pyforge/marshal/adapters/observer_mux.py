"""``MultiplexerObserver`` -- the sole implementation of
``ports.SessionObserverPort`` (Story 3.4/3.5, AD-4/AD-9/AD-34): shells out to
``tmux capture-pane`` for a pane's text, ``tmux send-keys`` to deliver a
nudge, and ``Path.stat().st_mtime`` for a file's modification time. No
method raises -- an unavailable pane, an unresolvable window, or an
unreadable path is this port's own documented ``None``/``False``, not a
failure.

This adapter invokes ``tmux`` via ``pyforge.core.process.PosixProcess``
(Story 14.4, SPEC-pyforge-core CAP-6 -- previously this module's OWN direct
``subprocess`` call; adapters still never import each other, AD-4, but
``pyforge.core`` is the shared leaf every station may depend on, not a
sibling adapter). ``bmad_loop`` itself supports more than one multiplexer
backend (``adapters/harness_bmadloop.py::multiplexer_backend_available``),
but this story wires only the ``tmux`` case -- the packaged default and the
one this repo's own loop homes run under; a second backend is out of this
story's own Surface.

**Why the window target is resolved live, never cached or formula-derived
(Story 3.5).** The tmux SESSION name is a pure formula
(``f"bmad-loop-{harness_run_id}"``, confirmed live against the installed
``bmad_loop`` 0.9.0's own ``runs.py::session_name``), but the WINDOW inside
it is backend-assigned at creation and never persisted anywhere Marshal
could read it back from. ``_resolve_window`` shells out to ``tmux
list-windows -t <session> -F "#{window_id}\\t#{window_active}"`` at call
time and picks the row tmux itself marks ``window_active`` -- a session
always has exactly one active window once it has any (tmux's own per-session
invariant; ``bmad_loop``'s own ``new_window`` never passes ``-d``, so the
newest task window it creates becomes the active one automatically). Zero
rows (no such session) or more than one row claiming active (a query-level
anomaly this port's own contract treats identically to "unresolvable")
degrade to ``None`` -- never raise, and never guess among ambiguous
candidates. Shared by ``pane_content`` and ``send_text``, replacing this
module's own former placeholder ``pane_content -t <session>`` bare-session
target (Story 3.4 left that unresolved -- see that story's own deferred-work
entry).

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

**``send_text`` mirrors upstream's own delivery recipe exactly** (confirmed
live against ``bmad_loop.adapters.tmux_base.BaseTmuxBackend.send_text``):
``send-keys -t <window> -l <text>`` (literal, unescaped paste) followed by a
short settle delay, then a bare ``send-keys -t <window> Enter`` to submit
it -- the same two-call shape upstream itself uses to deliver text into one
of its own managed windows.
"""

from __future__ import annotations

import json

# `subprocess` is imported for this module's own tests' monkeypatch anchor
# (`monkeypatch.setattr(module.subprocess, "run", ...)` -- the same physical
# stdlib module object `PosixProcess.run` itself calls, so patching it here
# still reaches the real launch below) -- the production code never calls
# `subprocess.*` directly (Story 14.4, SPEC-pyforge-core CAP-6).
import subprocess  # noqa: F401
import time
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError

from ..core.egress import to_redacted

# A capture-pane/list-windows call reads an already-running terminal's own
# state -- no engine work happens inside tmux itself to wait on. Sized well
# below the supervisor's own 60s tick (see supervisor/__main__.py) so a hung
# or misbehaving tmux binary degrades one sample to None rather than
# stalling an entire tick.
_CAPTURE_PANE_TIMEOUT_S = 5.0

# Mirrors upstream's own `send_text`'s identical settle delay (confirmed live
# against `bmad_loop.adapters.tmux_base.BaseTmuxBackend.send_text`): lets the
# target CLI ingest the pasted text before the `Enter` that submits it.
_SEND_TEXT_SETTLE_S = 0.3


class MultiplexerObserver:
    """``ports.SessionObserverPort``'s sole implementation."""

    def _resolve_window(self, session: str) -> str | None:
        """The shared live window-target resolver -- see this module's own
        docstring for why this is never cached or formula-derived. Returns
        the sole window tmux itself marks active, or ``None`` for any
        degrade condition (no such session, a hung/missing binary, zero or
        more than one row claiming active). Never raises."""
        try:
            result = PosixProcess().run(
                ["tmux", "list-windows", "-t", f"={session}", "-F", "#{window_id}\t#{window_active}"],
                cwd=Path.cwd(),
                timeout_s=_CAPTURE_PANE_TIMEOUT_S,
            )
        except ProcessError:
            # Story 14.4, SPEC-pyforge-core CAP-6: `PosixProcess.run` folds
            # a missing/hung binary and an embedded NUL byte into ONE
            # `ProcessError` -- this port's own documented `None`, never
            # raise.
            return None
        if result.returncode != 0:
            # tmux's own "no such session" exit (and every other list
            # failure) -- there is nothing to resolve a window against.
            return None
        active_windows: list[str] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            window_id = parts[0] if parts else ""
            window_active = parts[1] if len(parts) > 1 else ""
            if window_id and window_active == "1":
                active_windows.append(window_id)
        if len(active_windows) != 1:
            # Zero (the session vanished between resolving its name and this
            # call) or more than one (a query-level anomaly) -- either way,
            # no clear active window to target. Never guess among ambiguous
            # candidates.
            return None
        return active_windows[0]

    def pane_content(self, session: str) -> str | None:
        window = self._resolve_window(session)
        if window is None:
            return None
        try:
            result = PosixProcess().run(
                ["tmux", "capture-pane", "-t", window, "-p"],
                cwd=Path.cwd(),
                timeout_s=_CAPTURE_PANE_TIMEOUT_S,
            )
        except ProcessError:
            # tmux itself missing, or a hung capture -- indistinguishable
            # from "no such window" at this port's own documented
            # granularity: both degrade to None, never raise. Story 14.4,
            # SPEC-pyforge-core CAP-6: `PosixProcess.run` folds this and an
            # embedded-NUL-byte failure (review finding, Story 3.4) into the
            # SAME `ProcessError`, which would otherwise escape this port's
            # own documented "never raises" contract.
            return None
        if result.returncode != 0:
            # The window died between resolution and this call -- the pane
            # simply cannot be observed right now.
            return None
        try:
            redacted = to_redacted({"pane": result.stdout})
            return json.loads(redacted.text)["pane"]
        except ValueError, LookupError, TypeError:
            # Review finding (Story 3.4): these two lines -- the only ones in
            # this method that TRANSFORM data -- sat outside the try above,
            # so this port's documented "never raises" contract rested
            # entirely on `to_redacted`'s current shape rather than on
            # anything this module enforces. The unwrap assumes
            # `to_redacted` round-trips `{"pane": ...}` as resolvable JSON;
            # any future change that wraps, caps or truncates its output (a
            # size ceiling on captured text being the obvious one) turns
            # that into a `JSONDecodeError`/`KeyError` escaping into
            # `supervisor/__main__.py`'s tick, which catches only
            # `(FsError, ValueError)` -- killing the sidecar with a raw
            # traceback after `supervisor-attach`. An unusable capture is
            # this port's own documented `None`, exactly like an unavailable
            # pane.
            return None

    def send_text(self, session: str, text: str) -> bool:
        window = self._resolve_window(session)
        if window is None:
            return False
        try:
            paste = PosixProcess().run(
                ["tmux", "send-keys", "-t", window, "-l", text],
                cwd=Path.cwd(),
                timeout_s=_CAPTURE_PANE_TIMEOUT_S,
            )
            if paste.returncode != 0:
                return False
            time.sleep(_SEND_TEXT_SETTLE_S)
            submit = PosixProcess().run(
                ["tmux", "send-keys", "-t", window, "Enter"],
                cwd=Path.cwd(),
                timeout_s=_CAPTURE_PANE_TIMEOUT_S,
            )
        except ProcessError:
            # Same CPython/tmux failure classes `pane_content` already
            # guards, all folded into ONE `ProcessError` (Story 14.4,
            # SPEC-pyforge-core CAP-6) -- a hung or missing binary, or an
            # embedded NUL byte in `text`, must degrade to this port's own
            # documented `False`, never raise.
            return False
        # A settle AFTER the submitting Enter, not only before it (review
        # finding). `tmux send-keys` returns as soon as tmux has queued the
        # keys, NOT when the target program has processed them and redrawn.
        # The supervisor re-captures this very pane immediately after this
        # call returns, to rebase its sample history onto the nudge's own
        # echo -- and with no settle here that capture caught the PRE-submit
        # frame (input line still holding the typed text). The post-submit
        # redraw -- input cleared, the message moved into the transcript --
        # then landed in the NEXT tick's capture, 60s later, where it read
        # as fresh session output and re-armed the idle window. That is the
        # nudge -> re-arm -> nudge loop the rebase exists to close, reopened
        # through a timing door: `stop-and-retry` stayed unreachable no
        # matter how wedged the session was.
        #
        # Reusing the same constant as the paste/Enter settle: both are the
        # same "give the target program a moment to catch up" wait, and one
        # tunable is easier to reason about than two.
        time.sleep(_SEND_TEXT_SETTLE_S)
        return submit.returncode == 0

    def mtime(self, path: Path) -> float | None:
        try:
            return path.stat().st_mtime
        except OSError, ValueError:
            # `ValueError` alongside `OSError` (review finding, Story 3.4):
            # `Path.stat` raises a plain `ValueError` -- not an `OSError` --
            # for a path containing an embedded NUL byte, which would
            # otherwise escape this port's own documented "never raises"
            # contract.
            return None
