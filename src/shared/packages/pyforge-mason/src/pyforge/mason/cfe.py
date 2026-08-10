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

import functools
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Mapping, Sequence, TextIO

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
converts that into "return with whatever was captured so far" instead of an
indefinite hang -- matching this file's existing `probe_import_floor`
precedent of degrading to a best-effort result rather than raising a new
error type for a rare, hard-to-fully-solve edge case."""


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

    `stderr_sink` defaults to `sys.stderr`, resolved *inside* this function
    body -- never as a `= sys.stderr` default parameter, which would bind
    the module-import-time stream object once and never see a test's
    per-call `capsys`/monkeypatch replacement of `sys.stderr`.

    Two daemon threads run concurrently for the life of the child process:
    one reads `proc.stderr` line by line, writing (and flushing) each line
    to `sink` as it arrives; the other reads `proc.stdout` to completion
    into the string this function returns. They must run concurrently, not
    sequentially -- draining only one pipe at a time risks the child
    blocking on a full OS pipe buffer on the *other* stream while nothing is
    reading it, deadlocking both the child and this function. Both are
    started with `errors="replace"` decoding (via `Popen`'s `text=True`
    pairing below) so a child that emits a byte sequence that isn't valid
    text under the platform's default encoding degrades to replacement
    characters in the affected spot rather than crashing the reader thread
    outright and silently truncating everything after it.

    On any exception escaping `proc.wait()` -- `subprocess.TimeoutExpired`,
    but also e.g. a `KeyboardInterrupt` raised while blocked there -- the
    child is killed and reaped (`proc.kill()` + `proc.wait()`) before the
    exception is re-raised, so no orphaned process survives any exit from
    this function, not only the timeout path. The reader threads are then
    joined with a bounded grace period (`_JOIN_GRACE_SECONDS`) rather than
    unboundedly, since a grandchild process that inherited the pipe file
    descriptors could otherwise keep them open past the direct child's own
    death and hang this function forever.

    Always a list argv, never `shell=True` (AD-2/AD-4).
    """
    if isinstance(argv, (str, bytes)):
        raise TypeError(
            f"run_streamed(argv=...) must be a sequence of arguments, not a bare "
            f"{type(argv).__name__} -- got {argv!r}"
        )

    sink = stderr_sink if stderr_sink is not None else sys.stderr

    proc = subprocess.Popen(
        list(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",  # a child emitting non-decodable bytes degrades text, never crashes a reader thread
        bufsize=1,  # line-buffered: each child stderr line is readable as soon as it is written
        env=dict(env) if env is not None else None,
    )

    captured_stdout: list[str] = []

    def _forward_stderr() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            sink.write(line)
            sink.flush()

    def _capture_stdout() -> None:
        assert proc.stdout is not None
        captured_stdout.append(proc.stdout.read())

    stderr_thread = threading.Thread(target=_forward_stderr, daemon=True)
    stdout_thread = threading.Thread(target=_capture_stdout, daemon=True)
    stderr_thread.start()
    stdout_thread.start()

    try:
        proc.wait(timeout=timeout)
    except BaseException:
        # Not just subprocess.TimeoutExpired: ANY exception here (including
        # a KeyboardInterrupt raised while blocked in proc.wait()) must
        # still kill and reap the child before propagating -- "no orphaned
        # process" is a guarantee for every exit from this function, not
        # only the timeout path.
        proc.kill()
        proc.wait()
        raise
    finally:
        stderr_thread.join(timeout=_JOIN_GRACE_SECONDS)
        stdout_thread.join(timeout=_JOIN_GRACE_SECONDS)

    return proc.returncode, "".join(captured_stdout)
