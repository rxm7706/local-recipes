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

Story 2.1 extends this same file with CFE's full script-invocation adapter
table (AD-3: "every CFE script Mason uses is declared once in a module-level
table in this file"), `CfeResult`, and JSON-stdout extraction (AD-4). None of
that exists yet -- this story adds only `CFE_IMPORT_FLOOR`,
`ImportFloorResult`, `probe_import_floor`, `ensure_import_floor`, and
`ensure_cfe_root`.

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
from dataclasses import dataclass

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
