"""The CFE port -- the sole conda-forge-expert (CFE) caller (AD-3, AD-4).

Story 1.6 seeds this file at minimal scope: only what is needed to answer
"does this interpreter have CFE's import floor?" without leaking a raw
subprocess `ImportError` traceback at the user. `resolve.py::
resolve_cfe_interpreter` picks *which* interpreter to probe (a pure,
in-process decision -- AD-5 forbids process spawns there); this module does
the probing itself, because that requires spawning the candidate
interpreter as a subprocess, which only `cli.py`/`cfe.py`/`engines/*.py` may
do (AD-2, enforced by `tests/meta/test_dependency_direction.py`).

Story 1.7 adds `ensure_cfe_root`, mirroring `ensure_import_floor`'s split
from `probe_import_floor`: it takes the already-computed `ResolvedCfeRoot`
(never re-resolving -- `resolve.py`'s own docstring says a later caller
"never needs to re-resolve") and raises `CfeUnresolvedError` when
`resolved.step == STEP_NOT_FOUND`. It lives here, not in `resolve.py`,
because `resolve.py`'s own docstring and every existing test treat
`resolve_cfe_root` as a function that "never raises" -- raising is `cfe.py`'s
job, matching the Capability -> Architecture map's "CFE seam (FR-1 - FR-6)"
row, which assigns FR-5 to `cfe.py` and `resolve.py` together.

Story 1.10 adds `run_streamed`, AD-25's STREAM-mode subprocess primitive: a
delegated operation expected to exceed a few seconds (`recipe build`,
`package build`) forwards its child's stderr through to the user's own
stderr as it is produced, rather than buffering it to completion, so a
long-running build never appears silently hung. CAPTURE mode -- a short,
JSON-returning operation that buffers stdout for parsing -- already exists
in spirit above, as `probe_import_floor`'s `subprocess.run(capture_output=
True)` call; `run_streamed` is STREAM mode's counterpart, living here (not a
shared `utils`/`helpers` module -- the Consistency Conventions forbid one)
for Story 2.1's CFE adapter to call, and for Epic 3's `engines/*` to mirror
independently rather than import.

Story 2.1 extends this same file with CFE's full script-invocation adapter
table (AD-3: "every CFE script Mason uses is declared once in a module-level
table in this file"), `CfeResult`, and JSON-stdout extraction (AD-4). None of
that exists yet -- this story adds only `CFE_IMPORT_FLOOR`,
`ImportFloorResult`, `probe_import_floor`, `ensure_import_floor`,
`ensure_cfe_root`, and `run_streamed`.

`CFE_IMPORT_FLOOR` maps each floor dependency's pip/conda *distribution*
name to its Python *import* name -- the two differ for `pyyaml` (imports as
`yaml`) and `conda-forge-metadata` (imports as `conda_forge_metadata`), and
that mapping is exact and load-bearing: a probe that used the distribution
name as the import name would report `pyyaml` and `conda-forge-metadata` as
always-missing, even when installed.

`probe_import_floor` invokes the candidate interpreter as
`[interpreter, "-c", script]` -- list argv, never `shell=True` -- with a
mandatory timeout, and is cached for the process lifetime
(`functools.lru_cache`) since the answer cannot change mid-process for a
given interpreter path. The generated probe script wraps every import
attempt in its own try/except (catching `Exception`, not just
`ImportError` -- a corrupted install can fail an import with some other
exception entirely), so a failed import prints a one-line `<name>:missing`
marker rather than a raw traceback and never aborts probing of the modules
after it; `subprocess.run` itself raising `OSError` (interpreter cannot be
spawned at all), `UnicodeDecodeError` (its output isn't decodable text), or
`subprocess.TimeoutExpired` is caught here and folded into "every floor
module is missing" -- an unusable interpreter path is indistinguishable
from a probe that ran and reported total absence, so both resolve to the
same outcome without a second error type.
"""

from __future__ import annotations

import codecs
import functools
import math
import subprocess
import sys
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TextIO

from .errors import CfeImportFloorError, CfeUnresolvedError
from .resolve import ResolvedCfeRoot, STEP_NOT_FOUND

CFE_IMPORT_FLOOR: dict[str, str] = {
    "pyyaml": "yaml",
    "requests": "requests",
    "packaging": "packaging",
    "truststore": "truststore",
    "ruamel.yaml": "ruamel.yaml",
    "conda-forge-metadata": "conda_forge_metadata",
}
"""CFE's minimum import floor: pip/conda distribution name -> Python import
name, in declared order. `missing` in `ImportFloorResult` reports
distribution names, in this same order, never import names (see module
docstring)."""

_PROBE_TIMEOUT_SECONDS = 15.0
"""A private constant, not a configurable knob: `--cfe-timeout`/
`MASON_CFE_TIMEOUT` is Story 1.10's closed v1 knob (AD-13) -- wiring it here
would add a flag half a story early."""


@dataclass(frozen=True)
class ImportFloorResult:
    """The outcome of probing `interpreter` for CFE's import floor.

    `missing` holds the *distribution* names (`CFE_IMPORT_FLOOR` keys) of
    every floor module that failed to import, in `CFE_IMPORT_FLOOR`'s
    declared order -- empty when the whole floor is importable."""

    interpreter: str
    missing: tuple[str, ...]


def _build_probe_script() -> str:
    """Build the `-c` probe script run under the candidate interpreter.

    Every import is wrapped in its own try/except so a failure importing one
    module never produces a raw traceback on its stdout/stderr and never
    aborts the probe of the modules after it -- only a `<import name>:ok` or
    `<import name>:missing` line. The except clause catches `Exception`, not
    just `ImportError`: a corrupted install can fail an import with
    `SyntaxError`, `AttributeError`, or another exception entirely, and any
    of those must still degrade to a `:missing` marker for that one module
    rather than crashing the rest of the probe script. Each import name is
    embedded via `repr()`, not naive string interpolation, so names
    containing dots (`ruamel.yaml`) or underscores (`conda_forge_metadata`)
    round-trip as correct Python string literals regardless of their
    content.
    """
    lines = ["import importlib"]
    for import_name in CFE_IMPORT_FLOOR.values():
        literal = repr(import_name)
        lines.append(
            "try:\n"
            f"    importlib.import_module({literal})\n"
            f"    print({literal} + ':ok')\n"
            "except Exception:\n"
            f"    print({literal} + ':missing')"
        )
    return "\n".join(lines)


@functools.lru_cache(maxsize=None)
def probe_import_floor(interpreter: str) -> ImportFloorResult:
    """Probe `interpreter` for CFE's import floor, cached for the process
    lifetime (keyed on `interpreter`).

    Runs `[interpreter, "-c", <probe script>]` with a mandatory timeout and
    `check=False` -- a non-zero exit is not raised, only stdout is parsed, so
    a crash partway through the script (or a non-zero exit for any other
    reason) still credits whichever modules printed their `:ok` marker
    before the crash and reports the rest missing, rather than discarding
    the whole result. If the interpreter cannot be spawned at all
    (`OSError`), its output cannot be decoded as text (`UnicodeDecodeError`),
    or the probe exceeds `_PROBE_TIMEOUT_SECONDS` (`subprocess.
    TimeoutExpired`), every floor module is reported missing rather than
    letting the exception propagate -- an unusable interpreter path is
    indistinguishable from a probe that ran and found nothing.
    """
    script = _build_probe_script()
    try:
        completed = subprocess.run(
            [interpreter, "-c", script],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, UnicodeDecodeError, subprocess.TimeoutExpired):
        return ImportFloorResult(interpreter=interpreter, missing=tuple(CFE_IMPORT_FLOOR))

    stdout_lines = set(completed.stdout.splitlines())
    missing = tuple(
        distribution
        for distribution, import_name in CFE_IMPORT_FLOOR.items()
        if f"{import_name}:ok" not in stdout_lines
    )
    return ImportFloorResult(interpreter=interpreter, missing=missing)


def ensure_import_floor(interpreter: str) -> None:
    """Raise `CfeImportFloorError` if `interpreter` is missing any part of
    CFE's import floor; otherwise return `None`."""
    result = probe_import_floor(interpreter)
    if result.missing:
        raise CfeImportFloorError(missing=result.missing, interpreter=interpreter)


def ensure_cfe_root(resolved: ResolvedCfeRoot) -> None:
    """Raise `CfeUnresolvedError` if `resolved.step` is `STEP_NOT_FOUND`;
    otherwise return `None`.

    Takes the already-computed `ResolvedCfeRoot` -- never re-resolves by
    calling `resolve_cfe_root` itself (spec Never boundary; mirrors
    `ensure_import_floor`'s split from `probe_import_floor` above).
    """
    if resolved.step == STEP_NOT_FOUND:
        raise CfeUnresolvedError()


_JOIN_GRACE_SECONDS = 5.0
"""Bound on the final reader-thread joins in `run_streamed` (review pass,
2026-08-09). The child is always already dead or reaped by the time these
joins run, so its own two pipes close and the threads exit almost
immediately -- *unless* the child spawned a grandchild that inherited the
pipe file descriptors (common for build tooling that shells out further),
in which case the pipes never see EOF and an unbounded `.join()` would hang
`run_streamed` forever even though the direct child is gone. A bounded join
converts that into a prompt return instead of an indefinite hang -- but each
reader is parked in a blocking read (`proc.stdout.read()`, the stderr
reader's `read1()`), so the timeout cannot interrupt it mid-read: in this
rare scenario `run_streamed` returns with `stdout=""` (not a true partial
capture) while the still-blocked daemon thread(s) keep running in the
background until their pipe eventually closes on its own -- which is also
why that pipe is left open rather than closed on the way out (closing it
would block on the lock the reader holds, waiting for the same EOF this
bound exists to stop waiting for). Matches this
file's existing `probe_import_floor` precedent of degrading to a
best-effort result rather than raising a new error type for a rare,
hard-to-fully-solve edge case -- applied honestly here rather than claimed
as a full partial-capture guarantee."""

_STDERR_CHUNK_BYTES = 65536
"""Upper bound on one stderr read in `run_streamed` (review pass,
2026-08-10, third). Only a cap: `BufferedReader.read1` returns whatever the
one raw read it performs delivered, so a single byte is forwarded the moment
it arrives rather than waiting for this many. Sized to keep the syscall
count low on a build that floods stderr, not to batch output for latency."""


def run_streamed(
    argv: Sequence[str],
    *,
    timeout: float,
    env: Mapping[str, str] | None = None,
    stderr_sink: TextIO | None = None,
) -> tuple[int, str]:
    """Run `argv` as a subprocess, streaming its stderr live and capturing
    its stdout in full -- AD-25's STREAM-mode primitive (FR-49).

    A delegated operation expected to exceed a few seconds forwards its
    child's stderr through to `stderr_sink` as it is produced, never
    buffered to completion, so it never appears silently hung; its stdout is
    still captured whole and returned. This is STREAM mode, not CAPTURE
    mode (AD-25: "streams or is captured, never both") -- unlike
    `subprocess.run(capture_output=True)`, the child's stderr is forwarded
    live and is gone once written; it is never accumulated or returned
    alongside stdout, so a caller wanting the failure text of a STREAM-mode
    operation must supply a `stderr_sink` that itself retains what it is
    given (e.g. a `StringIO`/tee), not rely on this function's return value.

    `argv` must not be a bare `str` -- a classic `Sequence[str]` gotcha:
    passed as text, `list(argv)` below would explode it into one-character
    argv elements, producing a confusing `FileNotFoundError` instead of a
    clear error naming the mistake, so that shape is rejected immediately.
    `argv` must also be non-empty -- `Popen([])` raises an unhelpful
    `IndexError` rather than naming the mistake -- and not `None`, which
    `list(argv)` would report as a bare "'NoneType' object is not iterable"
    naming neither this function nor the parameter (review pass, 2026-08-10,
    third).

    `timeout` must be a finite, positive number: `nan` never compares as
    expired, `inf` never expires at all, and zero/negative values expire
    before the child has any chance to run -- all rejected up front, the
    same way `cli.py`'s `_parse_finite_float` guards `--cfe-timeout` at the
    flag layer, since a caller (e.g. a future `engines/*` mirror) may invoke
    this function directly without going through argparse.

    The child's `stdin` is `subprocess.DEVNULL`: a delegated operation that
    unexpectedly prompts for input must fail fast, not hang indefinitely on
    a stream nothing feeds in a non-interactive context -- the same
    "silently hung" failure mode this function exists to prevent on stderr.

    `stderr_sink` defaults to `sys.stderr`, resolved *inside* this function
    body -- never as a `= sys.stderr` default parameter, which would bind
    the module-import-time stream object once and never see a test's
    per-call `capsys`/monkeypatch replacement of `sys.stderr`. Whatever it
    resolves to must have a callable `write`; a sink that does not (or a
    `sys.stderr` that is `None`, as under `pythonw`/a detached host) is
    rejected up front rather than silently discarding every line the child
    produces, which a caller cannot tell apart from a quiet child (review
    pass, 2026-08-10, third). `flush` remains optional.

    Two daemon threads run concurrently for the life of the child process:
    one reads `proc.stderr` in chunks, writing (and flushing) each chunk to
    `sink` as it arrives; the other reads `proc.stdout` to completion into
    the string this function returns. They must run concurrently, not
    sequentially -- draining only one pipe at a time risks the child
    blocking on a full OS pipe buffer on the *other* stream while nothing is
    reading it, deadlocking both the child and this function. Both decode
    UTF-8 with `errors="replace"` so a child that emits a byte sequence that
    isn't valid UTF-8 degrades to replacement characters in the affected
    spot rather than crashing the reader thread outright and silently
    truncating everything after it. The encoding is pinned, not inherited
    from the locale (review pass, 2026-08-10, third): under `LC_ALL=C` --
    routine in CI containers and `docker run` without `LANG` -- the platform
    default would mangle every non-ASCII byte of an otherwise valid UTF-8
    JSON document into replacement characters that still parse as JSON, so
    Story 2.1's AD-4 extraction would return a quietly wrong answer instead
    of an error.

    stderr is forwarded in chunks, NOT line by line (review pass,
    2026-08-10, third). A line-iterating reader blocks until it sees `\\n`,
    so a child that writes a status line without a terminator and then works
    silently -- a spinner, a progress bar, `Building... ` followed by a
    three-minute compile -- delivers nothing at all until it finally
    terminates that line, which is precisely the "buffered to completion"
    behavior AD-25 forbids and this primitive exists to prevent. Reading the
    binary pipe and decoding incrementally also leaves the child's bytes
    intact: text-mode universal-newline translation rewrote every `\\r` into
    `\\n`, turning a build tool's single in-place progress line into hundreds
    of scrolling ones. Chunk boundaries never split a multi-byte character,
    because the incremental decoder carries the partial sequence over to the
    next chunk.

    For anti-deadlock reasons, a `stderr_sink` that raises (the common real
    case: `mason ... 2>&1 | head -5`, where the downstream reader exits and
    every later write is a `BrokenPipeError`) does NOT stop the reader -- it
    keeps consuming the pipe to EOF and discards what it can no longer
    deliver. Abandoning the pipe on the first sink failure would leave
    nothing draining stderr, so the child would block on its next write once
    the ~64KB pipe buffer filled and then be SIGKILLed when `timeout`
    expired: a healthy process destroyed by a broken *output* destination.
    A `BlockingIOError` is the one write failure that does not mark the sink
    dead (review pass, 2026-08-10, third): it means "busy," not "gone" --
    what a non-blocking `sys.stderr` under tmux or some CI runners raises
    when the downstream pipe is momentarily full -- and latching on it
    silently dropped every remaining line of a sink that would have accepted
    the very next write. That one chunk is still lost (retrying would either
    block or spin), but the sink stays live; the same reasoning the `flush`
    handler below already applied.

    On any exception after the child is spawned -- `subprocess.
    TimeoutExpired` from `proc.wait()`, a `KeyboardInterrupt` raised while
    blocked there, or even a `Thread.start()` failure under thread
    exhaustion -- the *direct* child is killed and reaped (`proc.kill()` +
    `proc.wait()`) before the exception is re-raised, on every exit from
    this function and not only the timeout path. `kill()` signals that one
    process, not its process group: a grandchild it spawned survives, so the
    guarantee is "this function never leaves the process it started
    running," not "no descendant survives."

    Each reader thread is then joined with a bounded grace period
    (`_JOIN_GRACE_SECONDS`) rather than unboundedly, since such a grandchild
    can hold the inherited pipe file descriptors open past the direct
    child's own death and would otherwise hang this function forever. Each
    pipe is closed as soon as its reader joins (`Popen` is not used as a
    context manager, because the reader threads outlive any `with` block),
    so a normal call leaks no file descriptors; a pipe whose reader is still
    blocked when its join expires is deliberately left open, because closing
    it would block on that reader's own lock and undo the bound. The two
    joins are sequential, so this function's own worst-case wall-clock bound
    is `timeout` (or however long `kill()`+`wait()` take) plus up to `2 *
    _JOIN_GRACE_SECONDS` -- a caller with a tight external deadline should
    account for that margin, not just `timeout` alone.

    `env`, when given, *replaces* the child's environment wholesale (it is
    passed straight to `Popen`) rather than merging with the caller's own --
    a partial dict (e.g. only a CFE-specific variable) silently strips
    everything else, including `PATH`, leaving a child that cannot itself
    shell out to anything. A caller wanting the inherited environment plus
    overrides must build that merged mapping itself.

    Always a list argv, never `shell=True` (AD-2/AD-4).
    """
    if argv is None:
        # Checked before list(argv), which would otherwise report a bare
        # "'NoneType' object is not iterable" naming neither this function
        # nor the parameter -- the same treatment `timeout=None` already
        # gets below (review pass, 2026-08-10, third).
        raise TypeError("run_streamed(argv=...) must be a sequence of arguments, not None")
    if isinstance(argv, (str, bytes)):
        raise TypeError(
            f"run_streamed(argv=...) must be a sequence of arguments, not a bare "
            f"{type(argv).__name__} -- got {argv!r}"
        )
    # Materialized once, before the emptiness check and before `Popen`
    # (review pass, 2026-08-10, second): `not argv` is always False for a
    # generator or other non-`Sized` iterable, so an exhausted one slipped
    # past the guard and reached `Popen([])` -- raising the very
    # `IndexError` the guard exists to replace. Materializing first also
    # avoids handing `Popen` a one-shot iterator this function has already
    # consumed.
    args = list(argv)
    if not args:
        raise ValueError("run_streamed(argv=...) must not be empty")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        # Checked before math.isfinite(), which would otherwise raise a bare
        # "must be real number, not NoneType" naming neither this function
        # nor the parameter (review pass, 2026-08-10). `timeout=None` is the
        # likely mistake: it means "wait forever" to subprocess's own API,
        # and this function deliberately has no such mode.
        raise TypeError(
            f"run_streamed(timeout=...) must be a number of seconds, not "
            f"{type(timeout).__name__} -- got {timeout!r}"
        )
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(
            f"run_streamed(timeout=...) must be a finite, positive number -- got {timeout!r}"
        )

    sink = stderr_sink if stderr_sink is not None else sys.stderr
    if not callable(getattr(sink, "write", None)):
        # Checked before Popen, so a bad sink costs no child process (review
        # pass, 2026-08-10, third). Without this, an unwritable sink -- or a
        # `sys.stderr` that is `None`, which is what a `pythonw`/detached
        # host hands us -- silently swallowed every line the child produced:
        # the forwarding thread's own degrade-don't-crash handling turned the
        # `AttributeError` into "sink is dead," indistinguishable to the
        # caller from a child that simply said nothing.
        raise TypeError(
            "run_streamed(stderr_sink=...) must have a callable write(); got "
            f"{type(sink).__name__}"
            + (" (sys.stderr is None -- pass an explicit sink)" if sink is None else "")
        )

    proc = subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        # Pinned, not locale-derived: see the docstring's encoding paragraph.
        # `errors="replace"` keeps a child emitting non-decodable bytes from
        # crashing a reader thread; it degrades that spot instead.
        encoding="utf-8",
        errors="replace",
        # bufsize=1 is documented as "line buffered", but `subprocess` only
        # applies line buffering to a *writable* text stream: these two read
        # pipes come back with `line_buffering=False` either way (review
        # pass, 2026-08-10, second). Neither reader below depends on it --
        # stdout reads to EOF, stderr reads raw chunks -- so do not reach for
        # this parameter to tune streaming latency.
        bufsize=1,
        env=dict(env) if env is not None else None,
    )

    captured_stdout: list[str] = []

    def _forward_stderr() -> None:
        assert proc.stderr is not None
        sink_alive = True
        # Resolved once, and never fatal (review pass, 2026-08-10, second):
        # a sink is a `TextIO`-shaped object, and the docstring above
        # explicitly invites a hand-rolled tee -- one without a `flush`
        # method used to raise `AttributeError` on the first line and latch
        # the sink dead, silently dropping every line after it. A flush that
        # *fails* is likewise not proof the sink is gone (a one-off
        # `BlockingIOError` on a non-blocking stderr recovers); only a failed
        # write latches, and a genuinely broken sink fails its next write
        # anyway.
        sink_flush = getattr(sink, "flush", None)
        try:
            # The raw pipe under the text wrapper, decoded here instead of by
            # the wrapper (review pass, 2026-08-10, third). Two reasons, both
            # in the docstring: `read1` returns as soon as any bytes arrive,
            # where the wrapper's line iterator waits for `\n` and so buffers
            # a terminator-free progress line for as long as the child keeps
            # working; and the wrapper's universal-newline translation
            # rewrites the child's `\r` into `\n`. Only this thread ever
            # reads stderr, and it never touches the text layer, so nothing
            # is stranded between the two.
            raw = proc.stderr.buffer
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            while True:
                chunk = raw.read1(_STDERR_CHUNK_BYTES)
                # final=True on the empty (EOF) read flushes any trailing
                # partial multi-byte sequence as replacement characters.
                text = decoder.decode(chunk, final=not chunk)
                # Even with the sink gone, this loop MUST keep reading to EOF
                # (review pass, 2026-08-10). Abandoning the pipe here is what
                # a naive `except: return` around the whole loop did, and it
                # deadlocked the child: nothing drains stderr, the OS pipe
                # buffer fills (~64KB), the child blocks forever on its next
                # write, and a perfectly healthy process is eventually
                # SIGKILLed by `timeout` -- the exact failure mode this
                # function exists to prevent. Reading and discarding costs
                # nothing and keeps the child running.
                if text and sink_alive:
                    try:
                        sink.write(text)
                    except BlockingIOError:
                        # "Busy," not "gone" (review pass, 2026-08-10,
                        # third): a non-blocking stderr whose downstream pipe
                        # is momentarily full raises this and accepts the
                        # very next write. This chunk is lost -- retrying
                        # would block or spin -- but the sink stays live,
                        # matching the flush handler's existing reasoning.
                        pass
                    except Exception:
                        # A broken/closed stderr_sink -- e.g. `mason ... 2>&1
                        # | head -5`, where the downstream reader exits and
                        # every subsequent write raises BrokenPipeError.
                        # Degrade: whatever reached the sink before the
                        # failure stays there, the rest is discarded, and the
                        # child still runs to completion.
                        sink_alive = False
                    else:
                        if sink_flush is not None:
                            try:
                                sink_flush()
                            except Exception:
                                pass
                if not chunk:
                    break
        except Exception:
            # The pipe itself failed (closed underneath us during a bounded
            # join, for instance). Degrade rather than crashing this daemon
            # thread via Python's default excepthook.
            pass

    def _capture_stdout() -> None:
        assert proc.stdout is not None
        try:
            captured_stdout.append(proc.stdout.read())
        except Exception:
            # Mirrors _forward_stderr's degrade-not-crash handling above. The
            # drain retry is best-effort only, and usually a no-op (review
            # pass, 2026-08-10, second): the states that make `read()` raise
            # -- a closed or broken stream -- make iteration raise
            # immediately too, so this cannot deliver the keep-draining
            # guarantee `_forward_stderr` provides against a live pipe. It is
            # kept for the case where the failure was transient, not claimed
            # as anti-deadlock protection.
            try:
                for _ in proc.stdout:
                    pass
            except Exception:
                pass

    stderr_thread = threading.Thread(target=_forward_stderr, daemon=True)
    stdout_thread = threading.Thread(target=_capture_stdout, daemon=True)

    try:
        stderr_thread.start()
        stdout_thread.start()
        proc.wait(timeout=timeout)
    except BaseException:
        # Not just subprocess.TimeoutExpired: ANY exception on this path
        # (a KeyboardInterrupt raised while blocked in proc.wait(), or a
        # Thread.start() RuntimeError under thread exhaustion -- review
        # pass, 2026-08-10) must still kill and reap the child before
        # propagating. "No orphaned process" is a guarantee for every exit
        # from this function, not only the timeout path.
        proc.kill()
        proc.wait()
        raise
    finally:
        # Popen is not used as a context manager here (the reader threads
        # outlive the `with` block's scope), so its two pipes must be closed
        # explicitly or every call leaks two file descriptors until the GC
        # runs -- surfacing as `ResourceWarning: unclosed file` under
        # `-W error::ResourceWarning` (review pass, 2026-08-10).
        #
        # Each pipe is closed only once ITS OWN reader thread has finished
        # (review pass, 2026-08-10, second): `close()` acquires the
        # `BufferedReader` lock that a still-blocked reader holds for the
        # duration of its read, so closing a pipe out from under a reader
        # that the bounded join just gave up on does not interrupt it -- it
        # blocks the calling thread until that read returns on its own,
        # waiting for exactly the EOF `_JOIN_GRACE_SECONDS` exists to stop
        # waiting for. Closing unconditionally therefore reintroduced an
        # unbounded hang (and swallowed `TimeoutExpired` entirely) in the
        # grandchild-holds-the-pipe case. Leaking one descriptor to the
        # daemon reader in that rare, already-degraded path is strictly
        # better than never returning.
        for thread, stream in ((stderr_thread, proc.stderr), (stdout_thread, proc.stdout)):
            if thread.ident is not None:  # never started -> nothing to join
                thread.join(timeout=_JOIN_GRACE_SECONDS)
            if stream is None or thread.is_alive():
                continue
            try:
                stream.close()
            except Exception:
                pass

    return proc.returncode, "".join(captured_stdout)
