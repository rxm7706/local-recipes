"""The supervisor sidecar's actual entry point (Story 3.4, architecture
spine AD-9/AD-20/AD-25/AD-28/AD-30): ``python -m pyforge.marshal.supervisor
<home> <slug> <run_id> <watched_pid> <log_path>``. ``cli/spin.py`` detach-
spawns exactly this invocation (via ``ProcessPort.spawn_detached``) as the
LAST step of a successful ``marshal factory spin`` -- see that module's own
docstring for why "last", after the ``run-launch`` outcome entry append is
attempted whether or not it itself succeeded.

**Order of operations (``run_supervisor``).** Read the run's own
``journal.jsonl`` ONCE (``FsPort.read_text`` + ``core.journal.fold`` -- no
second read, ever) -> inert-check: if no ``phase: outcome, kind:
"run-launch"`` entry names THIS ``run_id``, exit immediately, code 0, no
write at all (AD-25: the journal is the single source of run truth, so
"was this run really started by Marshal" is a journal question, never a
lock file -- see this story's own Design Notes) -> append one
``observation`` entry (``kind="supervisor-attach"``, payload ``{pid,
watched_pid}``) -> loop while ``ProcessPort.is_alive(watched_pid)``: sleep a
fixed 60s tick (``_TICK_SECONDS`` -- no policy knob exists for this yet,
and inventing one against no real caller would be speculative surface, per
this codebase's own precedent), sample ``ClockPort.now()`` plus
``SessionObserverPort.pane_content``/``mtime`` (gathered to prove the
injection seam Story 3.5's own ``core/supervise.py`` will consume -- NONE
of these samples drive a decision here; see this story's own Design Notes
for why), append one ``observation`` (``kind="supervisor-heartbeat"``,
payload ``{pid, watched_alive: true, sampled_at}``) -> when the watched
process is no longer alive, append one final ``observation``
(``kind="supervisor-detach"``, payload ``{pid, reason:
"watched-process-exited"}``) and exit 0.

Every append here is a ``Phase.OBSERVATION`` entry: no ``intent_id``, no
write-before-act pairing (AD-6 governs irreversible/externally-visible
ACTIONS; this sidecar only ever records what it independently observed),
and every write uses ``fsync=False`` -- matching ``cli/spin.py``'s own
``outcome``-entry convention, since an observation carries no invariant
that a crash between the write and an fsync would silently violate. A
journal append failure (``FsError``) at ANY point -- the attach entry, a
heartbeat, or the final detach -- is fatal to this process: it prints a
diagnostic to its own stderr (already redirected to ``log_path`` by the
parent's ``spawn_detached`` call -- this module never opens ``log_path``
itself) and exits non-zero rather than looping forever against a journal it
cannot durably write to. A dead supervisor with no further heartbeats is
itself a later-detectable condition (AD-9: "a dead supervisor is a reported
condition ... never silence") -- surfacing it as a `status` finding is a
later epic's own FR-36..40 scope, explicitly out of this story's Surface.

**Why the read side never loads sidecars.** ``core.journal.fold`` accepts
an optional ``sidecars`` mapping for large, sidecar-referenced payloads;
this module never supplies one. The ONE fact this read needs -- whether a
``phase: outcome, kind: "run-launch"`` entry exists for this run -- lives
entirely in that entry's ``kind``/``phase``/``run_id`` fields, never in its
payload, and that outcome's own payload (``{pid, harness_run_id}``,
``cli/spin.py``'s own shape) is always small enough to inline. A payload
this small can never be sidecar-referenced under
``core.journal.SIDECAR_THRESHOLD_BYTES``'s own threshold, so loading
sidecars here would read files this check never needs.

**Why this module duplicates, rather than imports, ``cli/spin.py``'s own
``_tier3_path``/``_run_dir``/``_format_entry_ts`` helpers.** This story's
own new import-linter contract forbids ``pyforge.marshal.supervisor`` from
importing ``pyforge.marshal.cli`` AT ALL (AD-9: no control channel back
into the session's own front door, structural) -- so even though these
three helpers are pure, private, and byte-for-byte reusable, importing them
from ``cli/spin.py`` would violate the very contract this story exists to
add. Each is reproduced here verbatim rather than promoted to a shared
module neither story's own Code Map asks for (Simplicity First: match what
each story actually needs, not a speculative third location).

**Why ``pane_content``'s ``session`` argument and ``mtime``'s ``path``
argument are placeholders, not a real resolved multiplexer session or
usage file.** ``bmad_loop`` itself names its own tmux session
``f"bmad-loop-{harness_run_id}"`` (its ``runs.py::session_name``,
confirmed live against the installed 0.9.0 package) -- keyed by the
HARNESS's own self-minted run id, not Marshal's own ``run_id`` this
process's argv carries. Resolving that real name would mean either
importing ``bmad_loop`` directly (forbidden here by AD-3's OWN contract,
which already lists this package in its ``source_modules``) or duplicating
a private naming convention from a package this story's Code Map never
asks it to reach into. Neither is this story's call to make speculatively
-- ``core/supervise.py`` (Story 3.5), the first REAL consumer of a pane
sample, is where that resolution belongs, once a real decision needs a real
value. This tick therefore samples ``pane_content(run_id)`` (Marshal's own,
always-known identifier -- a session name no live tmux session will ever
actually carry, so this always degrades to the documented, non-erroring
``None``) and ``mtime(log_path)`` (the one concrete file this process's own
argv already names -- its OWN redirected log, not the harness's), proving
the seam without inventing an unreviewed cross-package convention. Logged
as a follow-up in ``deferred-work.md``.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

from ..adapters.clock_system import SystemClock
from ..adapters.fs_local import FsError, LocalFs
from ..adapters.observer_mux import MultiplexerObserver
from ..adapters.process_posix import PosixProcess
from ..core.journal import (
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    prepare_for_write,
)
from ..ports.clock import ClockPort
from ..ports.fs import FsPort
from ..ports.observer import SessionObserverPort
from ..ports.process import ProcessPort

# Matches cli/spin.py's own _JOURNAL_FILENAME/_LAUNCH_KIND -- duplicated,
# not imported, per this module's own docstring (the new AD-9 contract
# forbids importing anything from pyforge.marshal.cli at all).
_JOURNAL_FILENAME = "journal.jsonl"
_LAUNCH_KIND = "run-launch"

# No policy knob exists for this yet (this story's own Never clause) -- a
# fixed constant is the only defensible value with no real caller to size a
# knob against.
_TICK_SECONDS = 60.0


def _tier3_path(home: Path, slug: str) -> Path:
    """Duplicates ``cli/spin.py``'s own helper of the same name verbatim --
    see this module's own docstring for why it cannot be imported instead."""
    return home / "_bmad-output" / "projects" / slug / "implementation-artifacts"


def _run_dir(home: Path, slug: str, run_id: str) -> Path:
    """Duplicates ``cli/spin.py``'s own helper of the same name verbatim."""
    return _tier3_path(home, slug) / "runs" / run_id


def _format_entry_ts(moment: datetime) -> str:
    """Duplicates ``cli/spin.py``'s own helper of the same name verbatim --
    ``core.journal.JournalEntry``'s own ``ts`` form:
    ``YYYY-MM-DDTHH:MM:SS.mmmZ``."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def run_supervisor(
    home: Path,
    slug: str,
    run_id: str,
    watched_pid: int,
    log_path: Path,
    *,
    fs: FsPort | None = None,
    process: ProcessPort | None = None,
    clock: ClockPort | None = None,
    observer: SessionObserverPort | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """The sidecar's own testable core -- everything ``__main__``'s own
    ``main()`` does after parsing argv. Every collaborator is DI'd with an
    adapter default (matching ``cli/spin.py``'s own ``fs``/``harness``
    convention), including ``sleep`` -- injecting a no-op callable is how
    this story's own tests exercise a multi-tick heartbeat loop in
    milliseconds rather than minutes (AD-20's own "every supervisor
    behaviour has a test that runs in milliseconds" requirement); a real
    invocation's own bounded-iteration-count safety valve is
    ``ProcessPort.is_alive`` itself eventually reporting ``False``, which a
    test controls directly through a fake ``ProcessPort``."""
    fs = fs if fs is not None else LocalFs()
    process = process if process is not None else PosixProcess()
    clock = clock if clock is not None else SystemClock()
    observer = observer if observer is not None else MultiplexerObserver()

    run_dir = _run_dir(home, slug, run_id)
    journal_path = run_dir / _JOURNAL_FILENAME

    try:
        text = fs.read_text(journal_path)
    except FsError as exc:
        # Cannot even determine whether this run is one Marshal started --
        # the only safe reading of "inert on a run it did not start" is to
        # STAY inert rather than assume ownership this read cannot prove.
        print(f"supervisor: cannot read journal {journal_path}: {exc}", file=sys.stderr)
        return 0

    lines = text.split("\n") if text is not None else []
    fold_result = fold(lines)
    # Widened to accept EITHER phase (review finding, both reviewers):
    # checking ONLY the OUTCOME entry meant that when cli/spin.py's own
    # outcome-journal append itself fails (MRS-SPIN-006 -- a live harness
    # process already exists, but its outcome never made it to disk), this
    # check found nothing and concluded "not started by Marshal", exiting
    # silently inert on a run Marshal genuinely DID start -- a live,
    # unsupervised harness process with no signal anywhere that supervision
    # was lost. AD-6's write-before-act guarantees the INTENT entry lands
    # BEFORE any spawn is even attempted, independent of whatever happens to
    # the LATER outcome write, so an intent entry alone already proves this
    # run was Marshal-started.
    started_by_marshal = any(
        entry.phase in (Phase.INTENT, Phase.OUTCOME) and entry.run_id == run_id
        for entry in fold_result.by_kind(_LAUNCH_KIND)
    )
    if not started_by_marshal:
        # The AC's own "inert on a run it did not start" -- no write at all,
        # not even a failed-attempt record: there is nothing this process
        # may legitimately claim happened against a run it did not launch.
        return 0

    writer_id = f"supervisor-{os.getpid()}"
    pid = os.getpid()
    counter = 0

    def _append(kind: str, payload: Mapping[str, object]) -> None:
        nonlocal counter
        entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(clock.now()),
            run_id=run_id,
            kind=kind,
            phase=Phase.OBSERVATION,
            payload=payload,
        )
        counter += 1
        prepared = prepare_for_write(entry)
        if prepared.sidecar_relative_path is not None:
            fs.write_text_atomic(
                run_dir / prepared.sidecar_relative_path, prepared.sidecar_content
            )
        fs.append_line(journal_path, prepared.line, fsync=False)

    try:
        _append("supervisor-attach", {"pid": pid, "watched_pid": watched_pid})

        # `watched_alive` is carried across iterations rather than
        # re-derived from a second `is_alive` call at the top of the loop
        # (review finding): the PREVIOUS shape checked is_alive() BEFORE
        # sleeping, to decide whether to enter a tick at all, then
        # unconditionally wrote `watched_alive: True` into the heartbeat
        # that followed -- a value that could ONLY ever be True (the loop
        # body cannot run otherwise) and that was already up to
        # `_TICK_SECONDS` stale relative to `sampled_at` by the time it was
        # written. This shape instead takes exactly ONE fresh reading per
        # tick, immediately before sampling `moment` -- the SAME reading
        # both fills the heartbeat's own `watched_alive` field (honest and
        # contemporaneous, never a tautology) and decides whether another
        # tick follows, so a tick that finds the watched process just died
        # still journals ONE truthful `watched_alive: False` heartbeat
        # before the final `supervisor-detach`, rather than a silent jump
        # straight from a string of `True` heartbeats to detach.
        watched_alive = process.is_alive(watched_pid)
        while watched_alive:
            sleep(_TICK_SECONDS)
            moment = clock.now()
            watched_alive = process.is_alive(watched_pid)
            # Sampled to prove the injection seam (AD-20) -- neither value
            # drives any decision in this story; see this module's own
            # docstring for why `run_id`/`log_path` are placeholder
            # arguments rather than a resolved real session/usage file.
            observer.pane_content(run_id)
            observer.mtime(log_path)
            _append(
                "supervisor-heartbeat",
                {
                    "pid": pid,
                    "watched_alive": watched_alive,
                    "sampled_at": _format_entry_ts(moment),
                },
            )

        _append(
            "supervisor-detach",
            {"pid": pid, "reason": "watched-process-exited"},
        )
    except FsError as exc:
        # AD-30's own journal is unwritable -- looping forever against it
        # would spin this process indefinitely with zero further signal.
        # Exit non-zero instead: a dead supervisor with no further
        # heartbeats, alongside a watched pid that is (or later becomes)
        # itself dead, is the later-detectable condition AD-9 promises
        # (surfacing it via `status` is a later epic's own scope).
        print(f"supervisor: cannot append to journal {journal_path}: {exc}", file=sys.stderr)
        return 1

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``sys.argv`` (or an injected ``argv`` for testing) into
    ``run_supervisor``'s five positional arguments and relay its exit code.
    This is the ONLY place this module reads its own command line -- AD-9's
    "reads argv once at start and touches no other externally-writable
    input for its own control flow" is literal here: no further read of
    ``sys.argv``, no ``input()``, no ``sys.stdin`` read, anywhere in this
    package."""
    args = list(sys.argv[1:]) if argv is None else list(argv)
    if len(args) != 5:
        print(
            "usage: python -m pyforge.marshal.supervisor <home> <slug> "
            "<run_id> <watched_pid> <log_path>",
            file=sys.stderr,
        )
        return 1
    home, slug, run_id, watched_pid_text, log_path_text = args
    try:
        watched_pid = int(watched_pid_text)
    except ValueError:
        print(f"supervisor: invalid watched pid {watched_pid_text!r}", file=sys.stderr)
        return 1
    if watched_pid <= 0:
        # POSIX's `kill()` gives 0 and negative pids special, non-"single
        # process" meanings (the caller's own process group, or a named
        # process group) -- review finding: `os.kill(watched_pid, 0)` inside
        # `is_alive` would silently probe one of THOSE instead of raising or
        # returning False, so a corrupted/malformed invocation could make
        # this sidecar believe an unintended target is "alive" forever
        # rather than failing cleanly. `cli/spin.py`'s own caller always
        # passes a real, positive `Popen.pid`, so this can only trigger via
        # a malformed direct invocation -- guarded here regardless, the same
        # "raise/refuse rather than silently misinterpret" discipline every
        # other boundary in this package already applies.
        print(f"supervisor: watched pid must be positive, got {watched_pid}", file=sys.stderr)
        return 1
    return run_supervisor(Path(home), slug, run_id, watched_pid, Path(log_path_text))


if __name__ == "__main__":
    raise SystemExit(main())
