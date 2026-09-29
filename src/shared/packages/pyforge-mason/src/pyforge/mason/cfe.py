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
table in this file"), a private CAPTURE-mode invocation helper
(`_invoke_captured`), tolerant JSON-from-stdout extraction (`_extract_json`),
and two public named adapters (`validate_recipe`, `submit_pr`) that each
return the new `CfeResult` (`models.py`). Story 2.7 adds a third named
adapter, `diagnose_failure`, mirroring the same shape exactly against
`failure_analyzer.py`.

Story 2.8 adds two more named adapters, `optimize_recipe` and
`scan_for_vulnerabilities`, against `recipe_optimizer.py`/
`vulnerability_scanner.py` -- otherwise identical in shape to the three
above (CAPTURE mode via `_invoke_captured`, a per-operation default timeout,
`args` passed straight through). Unlike every prior adapter, both of these
wrapped scripts are NOT stdlib-only (`recipe_optimizer.py` needs
`ruamel.yaml`; `vulnerability_scanner.py` needs `requests`+`pyyaml`), so
their own use-case caller (`recipe.py`'s `optimize()`/`scan()`) probes
`probe_import_floor` itself and raises `CfeImportFloorError` before reaching
either adapter, scoped to only the operation-relevant subset of `.missing`
-- this file's two new functions do not gate on the floor themselves,
because their caller has already done so.

Story 2.9 adds a keyword-only `env: Mapping[str, str] | None = None`
parameter to `_invoke_captured` (and threads it through `submit_pr`, the one
adapter that uses it): `recipe.py::submit()` is the one caller in this whole
package that ever passes a non-`None` value, to inject `CFE_RECIPES_ROOT`
into the child's environment so an out-of-tree recipe (Story 2.4) still
resolves under CFE's own `_path_guard.py` confinement (epic-2-context.md
Technical Decisions, correct-course 2026-08-10). It mirrors `run_streamed`'s
already-established `env=` contract exactly -- forwarded to `subprocess.run`
as `env=dict(env) if env is not None else None`, the EXACT expression text
`tests/meta/test_credential_isolation.py`'s `_SANCTIONED_PASS_THROUGH_ENV_
EXPR` names, so that file's Guard 3a allowlist (generalized the same story,
from one sanctioned call site to two) recognizes this call structurally,
the same way it already recognizes `run_streamed`'s own `Popen` call: a
*replacement*, never a merge -- the caller builds the whole dict. Every
other existing caller (`validate_recipe`, `diagnose_failure`,
`optimize_recipe`, `scan_for_vulnerabilities`) passes no `env`, so `None`
reaches `subprocess.run` exactly as before this story and their behavior is
byte-for-byte unchanged.

Story 2.10 adds two more named adapters, `update_recipe` and
`update_recipe_from_github`, against `recipe_updater.py`/`github_updater.py`
-- otherwise identical in shape to `diagnose_failure` above (CAPTURE mode via
`_invoke_captured`, a per-operation default timeout of 120.0s matching the
real MCP server's own `_run_script` default for both, `args` passed straight
through, no `env=` parameter). Neither adapter gates on CFE's import floor
itself, and neither needs a caller-side scoped probe the way `optimize()`/
`scan()` do: reading both wrapped scripts confirms every import-floor-
dependent call is already wrapped in a blanket `try/except (ImportError,
ValueError, FileNotFoundError)` (plus a catch-all `except Exception`) that
degrades a missing dependency to `{"success": false, "error": ...}` JSON
data, never a raw traceback -- the same "already handles it" case
`diagnose_failure`'s own caller (`recipe.py::diagnose()`) established.

Story 2.4 adds a third named adapter, `generate_recipe` (`recipe-generator.py`,
FR-7), following the identical shape -- args passed straight through, a
per-operation default timeout, `CfeResult` returned unchanged. Unlike its two
predecessors, the wrapped script has no `--json` mode, so `json_body` is
always `None` for this one adapter; `recipe.py::new` is the caller that turns
a non-zero `returncode` into a raised, typed error (`RecipeGenerationError`)
-- this file's own AD-4 rule that a non-zero return code is data, never
raised, is unchanged by that: the raise happens one layer up, not here.

`_CFE_SCRIPTS` maps an adapter's own key (e.g. `"validate_recipe"`) to the
script's filename relative to a resolved CFE root's
`.claude/scripts/conda-forge-expert/` -- a caller never passes a script
name or path; it calls the named adapter and the adapter looks up its own
key. This is a local re-declaration of that same subpath `resolve.py`'s
`_CFE_MARKER` and `errors.py`'s `CfeUnresolvedError._MESSAGE` already spell
out -- the sanctioned `_ENV_CFE_ROOT`/`_ENV_CFE_PYTHON`-style duplication
pattern documented in those modules, since AD-2 forbids this file from
importing a private constant out of either of them, and because `cfe.py` is
the one module AD-3's carve-out does not restrict in the first place.

CAPTURE mode (`_invoke_captured`, this story) and STREAM mode
(`run_streamed`, above) are AD-25's two invocation modes, not one
generalized over the other: CAPTURE buffers stdout whole and parses it for
a short, JSON-returning operation; STREAM forwards stderr live and never
parses stdout at all, for an operation expected to run long. `_invoke_
captured` therefore duplicates a small amount of `run_streamed`'s own
timeout-validation logic rather than sharing a helper with it -- the
Consistency Conventions forbid a shared `utils`/`helpers` module, and
`run_streamed` is shipped, reviewed, tested code this story does not touch.
A non-zero return code is data on the returned `CfeResult`, never raised as
an exception (AD-4) -- only timeout expiry raises, as the new, distinct
`CfeTimeoutError`.

Story 2.6 adds the first two STREAM-mode named adapters, `build_native` and
`build_docker` (FR-9), returning `models.BuildResult` rather than
`CfeResult`: a build is expected to run for minutes, so it belongs on
`run_streamed`, not `_invoke_captured`. Both translate `subprocess.
TimeoutExpired` to `CfeTimeoutError` themselves, exactly like
`_invoke_captured` does above -- `run_streamed` itself only re-raises the
bare stdlib exception (its own kill-and-reap already ran before doing so).
`build_native` resolves its script under the standard CFE-root subdirectory
and runs it through `bash` -- a disclosed, isolated exception to this
file's Python-only invocation convention, since it is a bash script, not a
Python one. `build_docker` resolves its script at the CFE root's own top
level instead -- the one `_CFE_SCRIPTS` entry outside the standard
subdirectory -- and runs it under the resolved CFE interpreter like every
other adapter in this file.

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
import json
import math
import re
import subprocess
import sys
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from .errors import CfeImportFloorError, CfeTimeoutError, CfeUnresolvedError
from .models import BuildResult, CfeResult
from .resolve import STEP_NOT_FOUND, ResolvedCfeRoot, detect_native_build_config

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
    except OSError, UnicodeDecodeError, subprocess.TimeoutExpired:
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
            f"run_streamed(argv=...) must be a sequence of arguments, not a bare {type(argv).__name__} -- got {argv!r}"
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
            f"run_streamed(timeout=...) must be a number of seconds, not {type(timeout).__name__} -- got {timeout!r}"
        )
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(f"run_streamed(timeout=...) must be a finite, positive number -- got {timeout!r}")

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
            f"{type(sink).__name__}" + (" (sys.stderr is None -- pass an explicit sink)" if sink is None else "")
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


# --- Story 2.1: CAPTURE-mode invocation (AD-3, AD-4, AD-25) -----------------

_CFE_SCRIPTS: dict[str, str] = {
    "validate_recipe": "validate_recipe.py",
    "submit_pr": "submit_pr.py",
    "generate_recipe": "recipe-generator.py",
    "build_native": "native-build.sh",
    "build_docker": "build-locally.py",
    "diagnose_failure": "failure_analyzer.py",
    "optimize_recipe": "recipe_optimizer.py",
    "scan_for_vulnerabilities": "vulnerability_scanner.py",
    "update_recipe": "recipe_updater.py",
    "update_recipe_from_github": "github_updater.py",
}
"""Every CFE script Mason invokes, declared exactly once (AD-3): adapter key
-> script filename. A named adapter function below (e.g. `validate_recipe`)
looks up its own key here; no caller anywhere passes a script name or path
directly.

Every entry's filename is relative to a resolved CFE root's
`.claude/scripts/conda-forge-expert/`, EXCEPT `build_docker`, the one entry
outside that standard subdirectory -- its script lives at the CFE root's
own top level (spec Always boundary), so `build_docker` below builds that
path itself rather than reusing `_invoke_captured`'s standard-subdirectory
join.

`validate_recipe.py` and `submit_pr.py` were Story 1.9's fixture-stubbed
pair. Story 2.4 adds `generate_recipe` -> `recipe-generator.py` (FR-7),
with a matching fixture stub of its own. Story 2.6 adds `build_native` ->
`native-build.sh` and `build_docker` -> `build-locally.py`, the first two
STREAM-mode entries. Story 2.7 adds `diagnose_failure` ->
`failure_analyzer.py` (OQ-A1's answer for FR-10, resolved by reading the
real script). Story 2.8 adds `optimize_recipe` -> `recipe_optimizer.py` and
`scan_for_vulnerabilities` -> `vulnerability_scanner.py` (OQ-A1's answer for
FR-11/FR-12), each with a matching stub added to the fixture tree in the
same story. Story 2.10 adds `update_recipe` -> `recipe_updater.py` and
`update_recipe_from_github` -> `github_updater.py` (OQ-A1's answer for
FR-14), each with a matching stub added to the fixture tree in the same
story -- resolving the earlier "still open" note this docstring carried for
Stories 2.9-2.10 (2.9 turned out to reuse the existing `submit_pr` entry
rather than add a new one)."""

_JSON_LINE_START_PATTERN = re.compile(r"^[ \t]*[{\[]", re.MULTILINE)
"""Matches the first `{` or `[` that starts a line (optionally indented),
skipping any leading non-JSON progress line CFE's scripts sometimes print
before their JSON body -- ports `_extract_json_from_stdout()`'s matching
strategy from `.claude/tools/conda_forge_server.py` (not imported: AD-3
reserves CFE path/invocation knowledge to this file alone, and that shim
isn't even part of the installed `pyforge.mason` package -- importing it
would give `cfe.py` a second, ungoverned CFE-invocation path besides this
file's own subprocess calls, review pass 2026-08-11: the original comment
here cited AD-15, which governs writes to that surface, not reads)."""


def _extract_json(stdout: str) -> object | None:
    """Tolerantly extract a JSON value from `stdout` (FR-4).

    Tries the whole string first -- the common case, where the child's only
    output is its JSON result. On failure, falls back to a line-anchored
    search for the first `{`/`[` that starts a (possibly indented) line and
    parses from there, tolerating exactly one inherited quirk of CFE's
    scripts: a leading, non-JSON progress line before the real body (e.g.
    `submit_pr`'s fork-sync status line). Unlike the MCP server's own
    version of this extraction, which raises `json.JSONDecodeError` when
    nothing parses, this function returns `None` in every failure case --
    FR-4 says a parsed body is present "when one is present," so its absence
    (no JSON anywhere in `stdout`, or a line-start match whose tail still
    isn't valid JSON) is a normal outcome recorded on `CfeResult.json_body`,
    never an exception this adapter layer must catch.
    """
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass

    match = _JSON_LINE_START_PATTERN.search(stdout)
    if match is None:
        return None

    # match.start() points at the beginning of the match, which INCLUDES any
    # leading spaces/tabs the pattern's `[ \t]*` consumed -- walk past them
    # here so json.loads() below is not handed a leading-whitespace slice.
    start = match.start()
    while start < len(stdout) and stdout[start] in " \t":
        start += 1

    try:
        return json.loads(stdout[start:])
    except json.JSONDecodeError:
        return None


def _invoke_captured(
    script_key: str,
    args: Sequence[str],
    *,
    root: Path,
    interpreter: str,
    timeout: float,
    env: Mapping[str, str] | None = None,
) -> CfeResult:
    """Run `_CFE_SCRIPTS[script_key]` under `interpreter` as a CAPTURE-mode
    subprocess and return a `CfeResult` (AD-3, AD-4, AD-25). Private: every
    public caller is a named adapter function below that supplies its own
    `script_key` -- this function is never called with a caller-supplied
    script name (spec Always boundary).

    `env`, when given, *replaces* the child's environment wholesale --
    mirrors `run_streamed`'s own established `env=` contract exactly (Story
    2.9): passed to `subprocess.run` as `dict(env) if env is not None else
    None`, never merged with the caller's own. `None` (the default) is
    `subprocess.run`'s own "inherit the parent environment" behavior,
    unchanged for every caller that omits this parameter -- `submit_pr` is
    the only adapter below that forwards a caller-supplied `env`; every
    other adapter (`validate_recipe`, `diagnose_failure`, `optimize_recipe`,
    `scan_for_vulnerabilities`) never passes one.

    `args` must not be a bare `str`/`bytes` or `None` -- the same
    `run_streamed`-established guard (review pass, 2026-08-11): passed as
    text, `*args` below would explode it into one-character argv elements
    (`"--json"` becomes `"-"`, `"-"`, `"j"`, `"s"`, ...), silently sending
    the wrapped script a garbled invocation instead of raising a clear
    error naming the mistake.

    `timeout` is validated finite and positive before anything spawns,
    mirroring `run_streamed`'s own guard above: a direct caller (e.g. a
    future use-case that bypasses `cli.py`'s `_parse_finite_float`) may pass
    an invalid value, and `nan`/`inf`/non-positive all describe a timeout
    that either never expires or expires before the child has any chance to
    run.

    `[interpreter, str(script_path), *args]` is run as a list argv, never
    `shell=True` (AD-2/AD-4). `encoding="utf-8", errors="replace"` is pinned
    explicitly rather than a bare `text=True` -- the same rationale
    `run_streamed`'s own docstring documents: a locale-derived default
    silently mangles a valid UTF-8 JSON body under `LC_ALL=C`.
    `stdin=subprocess.DEVNULL` mirrors `run_streamed`'s "never hang on an
    unexpectedly-interactive child" rule. `check=False`: a non-zero return
    code is data on the returned `CfeResult`, never raised (AD-4).

    On `subprocess.TimeoutExpired`, raises `CfeTimeoutError` naming
    `script_key` and `timeout` -- `subprocess.run`'s own timeout handling
    already killed and reaped the child before raising that exception, so
    "no orphaned process" holds without this function doing any cleanup of
    its own. Every other outcome -- including a non-zero exit, or stdout
    with no parseable JSON at all -- returns normally.
    """
    if args is None or isinstance(args, (str, bytes)):
        raise TypeError(
            f"_invoke_captured(args=...) must be a sequence of arguments, not "
            f"{'None' if args is None else type(args).__name__} -- got {args!r}"
        )
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise TypeError(
            f"_invoke_captured(timeout=...) must be a number of seconds, not "
            f"{type(timeout).__name__} -- got {timeout!r}"
        )
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(f"_invoke_captured(timeout=...) must be a finite, positive number -- got {timeout!r}")

    script_path = root / ".claude" / "scripts" / "conda-forge-expert" / _CFE_SCRIPTS[script_key]

    try:
        completed = subprocess.run(
            [interpreter, str(script_path), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
            env=dict(env) if env is not None else None,
        )
    except subprocess.TimeoutExpired:
        # subprocess.run's own timeout handling has already killed and
        # reaped the child by the time this exception reaches here -- this
        # translation adds no cleanup of its own, only a typed, actionable
        # error in place of the raw stdlib exception (spec Always boundary).
        raise CfeTimeoutError(script=script_key, timeout=timeout) from None

    return CfeResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        json_body=_extract_json(completed.stdout),
    )


_VALIDATE_RECIPE_TIMEOUT_SECONDS = 120.0
"""Mirrors the real MCP server's own `validate_recipe` default
(`.claude/tools/conda_forge_server.py::_run_script`'s `timeout: int = 120`
default, which `validate_recipe`'s tool wrapper never overrides)."""

_SUBMIT_PR_TIMEOUT_SECONDS = 300.0
"""Mirrors the real MCP server's own `submit_pr` default
(`.claude/tools/conda_forge_server.py::submit_pr`'s explicit
`timeout=300  # 5 min for clone + push`)."""


def validate_recipe(
    args: Sequence[str],
    *,
    root: Path,
    interpreter: str,
    timeout: float | None = None,
) -> CfeResult:
    """Invoke CFE's `validate_recipe.py` (AD-3's `validate_recipe` adapter,
    FR-1, FR-7, FR-8) and return a `CfeResult`.

    `args` is passed straight through as the script's own CLI arguments --
    this adapter applies no recipe-semantics interpretation of its own
    (AD-1). `timeout` defaults to `_VALIDATE_RECIPE_TIMEOUT_SECONDS` when
    `None`, matching the real MCP server's own per-operation default for
    this operation (see that constant's docstring).
    """
    return _invoke_captured(
        "validate_recipe",
        args,
        root=root,
        interpreter=interpreter,
        timeout=timeout if timeout is not None else _VALIDATE_RECIPE_TIMEOUT_SECONDS,
    )


def submit_pr(
    args: Sequence[str],
    *,
    root: Path,
    interpreter: str,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
) -> CfeResult:
    """Invoke CFE's `submit_pr.py` (AD-3's `submit_pr` adapter, FR-1, FR-13)
    and return a `CfeResult`.

    `args` is passed straight through as the script's own CLI arguments --
    this adapter applies no submission-flow composition of its own (Story
    2.9's two-phase `prepare_pr --prepare-only` / `submit_pr` scope, spec
    Never boundary). `timeout` defaults to `_SUBMIT_PR_TIMEOUT_SECONDS` when
    `None`, matching the real MCP server's own per-operation default for
    this operation (see that constant's docstring) -- longer than
    `validate_recipe`'s, since this operation clones and pushes a git
    branch before opening a pull request.

    `env`, when given, replaces the subprocess's inherited environment
    wholesale (see `_invoke_captured`'s own docstring for the exact
    contract) -- `recipe.py::submit()` is the one caller that supplies it,
    to inject `CFE_RECIPES_ROOT` for an out-of-tree recipe (module
    docstring, Story 2.9); every other caller of this adapter passes none,
    and `_invoke_captured`'s own default (`None` -> inherit unmodified)
    applies.
    """
    return _invoke_captured(
        "submit_pr",
        args,
        root=root,
        interpreter=interpreter,
        timeout=timeout if timeout is not None else _SUBMIT_PR_TIMEOUT_SECONDS,
        env=env,
    )


_DIAGNOSE_FAILURE_TIMEOUT_SECONDS = 120.0
"""Mirrors the real MCP server's own `analyze_build_failure` default
(`.claude/tools/conda_forge_server.py::_run_script`'s `timeout: int = 120`
default, which `analyze_build_failure`'s tool wrapper never overrides)."""


def diagnose_failure(
    args: Sequence[str],
    *,
    root: Path,
    interpreter: str,
    timeout: float | None = None,
) -> CfeResult:
    """Invoke CFE's `failure_analyzer.py` (AD-3's `diagnose_failure` adapter,
    FR-1, FR-10) and return a `CfeResult`.

    `args` is passed straight through as the script's own CLI arguments --
    this adapter applies no failure-log interpretation of its own (AD-1):
    the script's own `{"success": ..., "diagnosis": ..., "all_matches":
    ...}` (or, for no match, `{"success": false, "error": ..., "hint":
    ...}`) JSON body is `CfeResult.json_body` verbatim (spec Always
    boundary). `timeout` defaults to `_DIAGNOSE_FAILURE_TIMEOUT_SECONDS`
    when `None`, matching the real MCP server's own per-operation default
    for this operation (see that constant's docstring) -- the same value as
    `validate_recipe`'s, since both are short, single-pass CAPTURE-mode
    operations.
    """
    return _invoke_captured(
        "diagnose_failure",
        args,
        root=root,
        interpreter=interpreter,
        timeout=timeout if timeout is not None else _DIAGNOSE_FAILURE_TIMEOUT_SECONDS,
    )


_OPTIMIZE_RECIPE_TIMEOUT_SECONDS = 120.0
"""Mirrors the real MCP server's own `optimize_recipe` default
(`.claude/tools/conda_forge_server.py::_run_script`'s `timeout: int = 120`
default, which `optimize_recipe`'s tool wrapper never overrides)."""


def optimize_recipe(
    args: Sequence[str],
    *,
    root: Path,
    interpreter: str,
    timeout: float | None = None,
) -> CfeResult:
    """Invoke CFE's `recipe_optimizer.py` (AD-3's `optimize_recipe` adapter,
    FR-1, FR-11) and return a `CfeResult`.

    `args` is passed straight through as the script's own CLI arguments --
    this adapter applies no check-code filtering of its own (AD-1): the
    script's own `{"success": ..., "suggestions_found": ..., "suggestions":
    [...]}` JSON body is `CfeResult.json_body` verbatim (spec Always
    boundary). Unlike `validate_recipe`/`diagnose_failure`, the real script
    takes no `--json` flag -- it always emits JSON -- so a caller's `args`
    is just `[recipe_path]` (spec Always boundary, mirrors the real MCP
    server's own `optimize_recipe` tool wrapper). `timeout` defaults to
    `_OPTIMIZE_RECIPE_TIMEOUT_SECONDS` when `None`, matching the real MCP
    server's own per-operation default for this operation (see that
    constant's docstring).

    This adapter does NOT itself gate on CFE's import floor -- its caller,
    `recipe.py::optimize`, probes `probe_import_floor` and raises
    `CfeImportFloorError` itself, scoped to just `ruamel.yaml`, before
    reaching this function (module docstring): the wrapped script degrades
    to a lone `OPT-000` suggestion at maximum confidence (1.0), rather than
    crashing, when `ruamel.yaml` is missing from `interpreter`.
    """
    return _invoke_captured(
        "optimize_recipe",
        args,
        root=root,
        interpreter=interpreter,
        timeout=timeout if timeout is not None else _OPTIMIZE_RECIPE_TIMEOUT_SECONDS,
    )


_SCAN_FOR_VULNERABILITIES_TIMEOUT_SECONDS = 120.0
"""Mirrors the real MCP server's own `scan_for_vulnerabilities` default
(`.claude/tools/conda_forge_server.py::_run_script`'s `timeout: int = 120`
default, which `scan_for_vulnerabilities`'s tool wrapper never overrides)."""


def scan_for_vulnerabilities(
    args: Sequence[str],
    *,
    root: Path,
    interpreter: str,
    timeout: float | None = None,
) -> CfeResult:
    """Invoke CFE's `vulnerability_scanner.py` (AD-3's
    `scan_for_vulnerabilities` adapter, FR-1, FR-12) and return a
    `CfeResult`.

    `args` is passed straight through as the script's own CLI arguments --
    this adapter applies no severity policy or threshold filtering of its
    own (AD-1): the script's own `{"success": ..., "scanned": ...,
    "vulnerable_packages": ..., "total_vulnerabilities": ..., "results":
    [...]}` JSON body is `CfeResult.json_body` verbatim (spec Always
    boundary). The real script defaults to human-readable text and needs an
    explicit `--json` flag to emit JSON at all -- so a caller's `args` is
    `["--json", recipe_path]` (spec Always boundary, mirrors the real MCP
    server's own `scan_for_vulnerabilities` tool wrapper). `timeout`
    defaults to `_SCAN_FOR_VULNERABILITIES_TIMEOUT_SECONDS` when `None`,
    matching the real MCP server's own per-operation default for this
    operation (see that constant's docstring).

    This adapter does NOT itself gate on CFE's import floor -- its caller,
    `recipe.py::scan`, probes `probe_import_floor` and raises
    `CfeImportFloorError` itself, scoped to `requests`/`pyyaml`, before
    reaching this function (module docstring): the wrapped script degrades
    when either is missing from `interpreter`, but not identically -- a
    missing `pyyaml` is **false-clean** (`{"success": true, "mode":
    "skipped", "scanned": 0, "unpinned_skipped": [...]}`, no `results` key,
    indistinguishable from a genuinely clean scan), while a missing
    `requests` instead raises inside the script's own API call and -- when no
    local CVE database exists yet at the path `pixi run update-cve-db`
    populates -- is reported honestly (`{"success": false, "error": ...,
    "hint": ...}`). Moot in practice: this adapter's own caller gates on
    `requests` before either path is ever reached, so this distinction never
    surfaces through Mason today; noted here only for an accurate account of
    the wrapped script's own behavior.
    """
    return _invoke_captured(
        "scan_for_vulnerabilities",
        args,
        root=root,
        interpreter=interpreter,
        timeout=timeout if timeout is not None else _SCAN_FOR_VULNERABILITIES_TIMEOUT_SECONDS,
    )


_UPDATE_RECIPE_TIMEOUT_SECONDS = 120.0
"""Mirrors the real MCP server's own `update_recipe` default
(`.claude/tools/conda_forge_server.py::_run_script`'s `timeout: int = 120`
default, which `update_recipe`'s tool wrapper never overrides)."""

_UPDATE_RECIPE_FROM_GITHUB_TIMEOUT_SECONDS = 120.0
"""Mirrors the real MCP server's own `update_recipe_from_github` default
(`.claude/tools/conda_forge_server.py::_run_script`'s `timeout: int = 120`
default, which `update_recipe_from_github`'s tool wrapper never overrides)."""


def update_recipe(
    args: Sequence[str],
    *,
    root: Path,
    interpreter: str,
    timeout: float | None = None,
) -> CfeResult:
    """Invoke CFE's `recipe_updater.py` (AD-3's `update_recipe` adapter,
    FR-14) and return a `CfeResult`.

    `args` is passed straight through as the script's own CLI arguments --
    this adapter applies no upstream-version-check logic of its own (AD-1):
    the script's own JSON body -- `{"success": true, "updated": true,
    "new_version": ..., "message": "Recipe updated successfully."}` on a real
    write, `{"success": true, "updated": true, "dry_run": true, "actions":
    [...], "message": ...}` under `--dry-run`, `{"success": true, "updated":
    false, "message": "Recipe is already up-to-date."}` when nothing changed,
    or `{"success": false, "error": ...}` on failure -- is `CfeResult.
    json_body` verbatim (spec Always boundary). `timeout` defaults to
    `_UPDATE_RECIPE_TIMEOUT_SECONDS` when `None`, matching the real MCP
    server's own per-operation default for this operation (see that
    constant's docstring) -- the same value as `validate_recipe`'s/
    `diagnose_failure`'s, since this is likewise a short, single-pass
    CAPTURE-mode operation.
    """
    return _invoke_captured(
        "update_recipe",
        args,
        root=root,
        interpreter=interpreter,
        timeout=timeout if timeout is not None else _UPDATE_RECIPE_TIMEOUT_SECONDS,
    )


def update_recipe_from_github(
    args: Sequence[str],
    *,
    root: Path,
    interpreter: str,
    timeout: float | None = None,
) -> CfeResult:
    """Invoke CFE's `github_updater.py` (AD-3's `update_recipe_from_github`
    adapter, FR-14) and return a `CfeResult`.

    `args` is passed straight through as the script's own CLI arguments --
    this adapter applies no GitHub-repo-detection or version-comparison logic
    of its own (AD-1): the script's own JSON body -- the same
    success/dry-run/already-current/failure shapes `update_recipe` above
    documents, plus `current_version`/`latest_tag`/`github_url` fields and a
    pre-release-skip shape (`{"success": true, "updated": false, ...,
    "message": "Latest release ... is a pre-release ..."}`) neither the PyPI
    script nor its own callers have -- is `CfeResult.json_body` verbatim
    (spec Always boundary). `timeout` defaults to
    `_UPDATE_RECIPE_FROM_GITHUB_TIMEOUT_SECONDS` when `None`, matching the
    real MCP server's own per-operation default for this operation (see that
    constant's docstring).
    """
    return _invoke_captured(
        "update_recipe_from_github",
        args,
        root=root,
        interpreter=interpreter,
        timeout=timeout if timeout is not None else _UPDATE_RECIPE_FROM_GITHUB_TIMEOUT_SECONDS,
    )


# --- Story 2.6: STREAM-mode build adapters (AD-3, AD-25, FR-9) --------------

_BUILD_NATIVE_TIMEOUT_SECONDS = 3600.0
"""One hour: a native build can compile from source (the whole reason a
build adapter exists, unlike a `validate_recipe`/`submit_pr` metadata-only
operation) -- generously longer than either CAPTURE-mode adapter's timeout
above."""

_BUILD_DOCKER_TIMEOUT_SECONDS = 7200.0
"""Two hours: the Docker/CI-parity path additionally pulls a build image and
runs the same compile the native path performs inside it (per SKILL.md's
own description of `build-locally.py`'s "alma9 sysroot, isolated build
env"), so it is expected to run longer than the native path above; not
benchmarked against a logged run of this specific project's own CI (review
pass -- the prior wording overclaimed "this project's own CI experience")."""


def build_native(
    recipe_path: str,
    *,
    root: Path,
    timeout: float | None = None,
    stderr_sink: TextIO | None = None,
    env: Mapping[str, str] | None = None,
) -> BuildResult:
    """Invoke CFE's native build script (AD-3's `build_native` adapter,
    FR-9, AD-25) and return a `BuildResult`.

    Runs `["bash", str(script_path), recipe_path]` through `run_streamed`
    -- STREAM mode, not CAPTURE: the script's stderr forwards live to
    `stderr_sink` as it is produced (a native build is exactly the
    multi-minute operation AD-25 exists for), and its stdout is captured
    whole and returned unparsed (spec Never boundary: no Mason-side
    interpretation of the script's own output, no scraping a filename out
    of it, no pre-validation of `recipe_path`'s existence). Invoked through
    `bash`, never the resolved CFE interpreter (spec Always boundary) -- it
    is a bash script, not a Python one, the one disclosed exception to this
    file's Python-only invocation convention.

    `config` comes from `resolve.detect_native_build_config()`'s own
    outcome for the CURRENT host -- never a caller-supplied override (spec
    Never boundary: there is no `--platform`/config flag for this mode,
    since the wrapped script has none either, and exposing one would let
    Mason report a directory the script never actually used). `artifact_dir`
    is `build_artifacts/<config>` when a config was detected, else `None` --
    an unrecognized host still runs the script and lets it report its own
    failure via `returncode`, never a Mason-level error.

    `timeout` defaults to `_BUILD_NATIVE_TIMEOUT_SECONDS` when `None`.
    `subprocess.TimeoutExpired` (from `run_streamed`, which re-raises the
    bare stdlib exception -- its own kill-and-reap already ran before doing
    so) is translated here to `CfeTimeoutError`, mirroring `_invoke_
    captured`'s translation (spec Always boundary).

    The script's own `"${@:2}"` passthrough (extra rattler-build flags like
    `--test skip`/`--target-platform`) is a deliberate scope cut, not an
    oversight (review pass): the spec's CLI surface is `recipe_path`/
    `--docker`/`--config` only, and no story task calls for exposing it.
    """
    resolved_timeout = timeout if timeout is not None else _BUILD_NATIVE_TIMEOUT_SECONDS
    script_path = root / ".claude" / "scripts" / "conda-forge-expert" / _CFE_SCRIPTS["build_native"]
    config = detect_native_build_config()

    try:
        returncode, stdout = run_streamed(
            ["bash", str(script_path), recipe_path],
            timeout=resolved_timeout,
            stderr_sink=stderr_sink,
            env=dict(env) if env is not None else None,
        )
    except subprocess.TimeoutExpired:
        raise CfeTimeoutError(script="build_native", timeout=resolved_timeout) from None

    artifact_root = env.get("MASON_FACTORY_ROOT") if env is not None else None
    if artifact_root:
        artifact_dir = f"{artifact_root}/build_artifacts/{config}" if config is not None else None
    else:
        artifact_dir = f"build_artifacts/{config}" if config is not None else None

    return BuildResult(
        mode="native",
        config=config,
        returncode=returncode,
        stdout=stdout,
        artifact_dir=artifact_dir,
    )


def build_docker(
    config: str,
    *,
    root: Path,
    interpreter: str,
    timeout: float | None = None,
    stderr_sink: TextIO | None = None,
    env: Mapping[str, str] | None = None,
) -> BuildResult:
    """Invoke CFE's Docker/CI-parity build script (AD-3's `build_docker`
    adapter, FR-9, AD-25) and return a `BuildResult`.

    Runs `[interpreter, str(script_path), config]` through `run_streamed`,
    the same STREAM-mode shape `build_native` uses above. `script_path`
    resolves at the CFE root's own top level (`root / <script filename>`),
    NOT the standard `.claude/scripts/conda-forge-expert/` subdirectory
    (spec Always boundary) -- the one `_CFE_SCRIPTS` entry outside it.
    `interpreter` is the caller's already-resolved CFE interpreter
    (`resolve.resolve_cfe_interpreter`'s outcome) -- unlike `build_native`,
    this script IS a Python script, so it runs under it like every
    CAPTURE-mode adapter above.

    `config` is the caller-supplied `--config` value, required by `cli.py`'s
    own usage check before this adapter is ever reached: the wrapped script
    prompts interactively (reads stdin) when its own config argument is
    omitted and more than one platform variant is discoverable, which would
    hang against `run_streamed`'s `stdin=subprocess.DEVNULL` (spec Design
    Notes). `artifact_dir` is always `build_artifacts/<config>` here --
    never `None`, since `config` is never `None` on this path. This
    function re-validates that itself (review pass) rather than trusting
    `cli.py`'s gate alone: a blank/`None` `config` raises `ValueError` here,
    before any subprocess spawns, mirroring `_invoke_captured`'s/
    `run_streamed`'s own established "validate this function's own
    arguments defensively" convention above -- `recipe.build()` is a public
    use-case a future direct caller (e.g. `package.py`'s conda-forge ship
    target, AD-11) could reach without going through `cli.py`'s parser at
    all, and a caller-supplied `None` reaching `run_streamed`'s argv list
    unvalidated would otherwise surface as a raw `TypeError` deep inside
    `subprocess.Popen`, not a clean, actionable error. Not validated against
    a fixed platform-name set, though: `build-locally.py` discovers valid
    configs dynamically (`.ci_support/*.yaml`, `verify_config`), so a
    hardcoded allowlist here would duplicate -- and could disagree with --
    that judgment (spec Never boundary); an invalid-but-non-blank `config`
    is still forwarded, and the wrapped script's own non-zero exit plus its
    stdout enumerating valid configs is the real diagnostic.

    `timeout` defaults to `_BUILD_DOCKER_TIMEOUT_SECONDS` when `None`. Same
    `subprocess.TimeoutExpired` -> `CfeTimeoutError` translation as
    `build_native` above.
    """
    if not config or not config.strip():
        raise ValueError(
            "build_docker(config=...) must be a non-blank platform-variant name "
            "(e.g. 'linux64') -- the Docker/CI-parity script has no auto-detection"
        )
    resolved_timeout = timeout if timeout is not None else _BUILD_DOCKER_TIMEOUT_SECONDS
    script_path = root / _CFE_SCRIPTS["build_docker"]

    try:
        returncode, stdout = run_streamed(
            [interpreter, str(script_path), config],
            timeout=resolved_timeout,
            stderr_sink=stderr_sink,
            env=dict(env) if env is not None else None,
        )
    except subprocess.TimeoutExpired:
        raise CfeTimeoutError(script="build_docker", timeout=resolved_timeout) from None

    artifact_root = env.get("MASON_FACTORY_ROOT") if env is not None else None
    if artifact_root:
        artifact_dir = f"{artifact_root}/build_artifacts/{config}"
    else:
        artifact_dir = f"build_artifacts/{config}"

    return BuildResult(
        mode="docker",
        config=config,
        returncode=returncode,
        stdout=stdout,
        artifact_dir=artifact_dir,
    )


_GENERATE_RECIPE_TIMEOUT_SECONDS = 240.0
"""`recipe-generator.py` itself runs a `_run_rattler_generate` subprocess
(CRAN/CPAN/LuaRocks generation) under its own internal 180s timeout
(`recipe-generator.py:2285`); 240s gives that inner call headroom to
complete and still leave room for the surrounding Python (network calls,
license scanning, file writes) before this adapter's own timeout would fire
first and mask the inner one's more specific failure. Proportioned the same
way `_SUBMIT_PR_TIMEOUT_SECONDS` exceeds `_VALIDATE_RECIPE_TIMEOUT_SECONDS`
-- more headroom for an operation with more moving parts -- rather than an
arbitrary round number."""


def generate_recipe(
    args: Sequence[str],
    *,
    root: Path,
    interpreter: str,
    timeout: float | None = None,
) -> CfeResult:
    """Invoke CFE's `recipe-generator.py` (AD-3's `generate_recipe` adapter,
    FR-1, FR-7) and return a `CfeResult`.

    `args` is passed straight through as the script's own CLI arguments --
    `recipe.py::new` builds it as `[source, package, "--output", output]`,
    where `source` is CFE's own subcommand vocabulary (`pypi`/`github`/
    `cran`/`npm`), not a Mason-invented value -- this adapter applies no
    recipe-semantics interpretation of its own (AD-1). `timeout` defaults to
    `_GENERATE_RECIPE_TIMEOUT_SECONDS` when `None`, mirroring `validate_
    recipe`/`submit_pr`'s identical per-operation-default pattern above.
    Unlike those two, the wrapped script has no `--json` output mode, so
    `CfeResult.json_body` is always `None` here (`_extract_json` still runs
    -- it is unconditional in `_invoke_captured` -- but finds nothing to
    parse); callers use `returncode`/`stdout`/`stderr` instead (spec Never
    boundary).
    """
    return _invoke_captured(
        "generate_recipe",
        args,
        root=root,
        interpreter=interpreter,
        timeout=timeout if timeout is not None else _GENERATE_RECIPE_TIMEOUT_SECONDS,
    )
