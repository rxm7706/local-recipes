"""The `MasonError` taxonomy root (AD-7, FR-33).

Every anticipated failure Mason raises is a `MasonError` (or, in later
stories, one of its subclasses) carrying a stable, colon-delimited
identifier -- part of the public surface (Consistency Conventions: "Error
identifiers... Identifiers are API -- changing one is a MAJOR bump"), shaped
like `cfe:unresolved` / `ship:credential-missing` / `engine:absent`.

No concrete subclass or raise site is added by this story (see the spec's
Never boundary) -- those belong to the epics that implement CFE resolution,
credentials, and engines. This module pins the taxonomy machinery only.

Per AD-1 (shared shapes, no behaviour), this module holds the exception type
and its validation only -- no formatting beyond `__str__`, no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

# Two lowercase, hyphen-delimited segments joined by a single colon, e.g.
# "cfe:unresolved" or "ship:credential-missing". Neither segment may be
# empty, start/end with a hyphen, or contain a double hyphen. `\Z` (not `$`)
# anchors strictly to the end of the string -- `$` alone would also accept a
# single trailing newline, letting a malformed identifier through.
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*:[a-z0-9]+(-[a-z0-9]+)*\Z")


class MasonError(Exception):
    """Base class for every anticipated Mason failure.

    `identifier` must be a string matching `_IDENTIFIER_PATTERN`, and
    `message` must be a string with non-whitespace content that states what
    failed and what to do next (NFR-14); construction raises `ValueError`
    for either violation, since
    an unvalidated identifier or a message with nothing to say is exactly
    the drift AD-7 and NFR-14 exist to prevent.
    """

    def __init__(self, identifier: str, message: str) -> None:
        if not isinstance(identifier, str) or not _IDENTIFIER_PATTERN.match(identifier):
            raise ValueError(
                f"invalid MasonError identifier {identifier!r}: must be a string "
                f"matching {_IDENTIFIER_PATTERN.pattern!r} (e.g. 'cfe:unresolved')"
            )
        if not isinstance(message, str) or not message.strip():
            raise ValueError(
                "MasonError message must be a non-empty string: it must state "
                "what failed and what to do next (NFR-14)"
            )
        self.identifier = identifier
        self.message = message
        super().__init__(identifier, message)

    def __str__(self) -> str:
        return f"{self.identifier}: {self.message}"


class CfeImportFloorError(MasonError):
    """The selected CFE interpreter is missing part of CFE's import floor
    (FR-3, NFR-14).

    Raised by `cfe.py::ensure_import_floor` when `probe_import_floor`
    reports any gap -- construction raises `ValueError` for an empty
    `missing`, since an import-floor error naming nothing missing is
    exactly the incoherent state this class exists to rule out. `missing`
    holds pip/conda *distribution* names (e.g. `pyyaml`), not import names
    (`yaml`), in `cfe.CFE_IMPORT_FLOOR`'s declared order, so the message
    names exactly what a user would `pip install`/`conda install`; it is
    stored as a `tuple`, not whatever `Sequence` was passed, matching the
    immutable-shape convention every other dataclass in this story follows.
    """

    def __init__(self, missing: Sequence[str], interpreter: str) -> None:
        missing = tuple(missing)
        if not missing:
            raise ValueError(
                "CfeImportFloorError requires a non-empty `missing`: an "
                "import-floor error naming nothing missing is incoherent"
            )
        self.missing = missing
        self.interpreter = interpreter
        message = (
            f"interpreter {interpreter!r} is missing CFE's import floor: "
            f"{', '.join(missing)}"
        )
        super().__init__("cfe:import-floor-missing", message)


class CfeUnresolvedError(MasonError):
    """The CFE root could not be resolved by any step of `resolve.py`'s
    chain (FR-5, D-2, NFR-14).

    Raised by `cfe.py::ensure_cfe_root` when the already-computed
    `ResolvedCfeRoot.step` is `STEP_NOT_FOUND`. Unlike `CfeImportFloorError`,
    there is no per-call variable data to report -- the four steps either
    matched or did not, and nothing about *which* value was tried is
    meaningful once resolution has already failed -- so the constructor
    takes no arguments and the message is a fixed string naming all four
    step names and how to satisfy the first three.
    """

    # `.claude/scripts/conda-forge-expert/` below duplicates `resolve.py`'s
    # `_CFE_MARKER` literal -- the same sanctioned duplication pattern as
    # `_ENV_CFE_ROOT`/`_ENV_CFE_PYTHON` (documented in resolve.py's module
    # docstring): AD-2's dependency-direction rule forbids this leaf module
    # from importing `resolve.py`, so the marker path is spelled out again
    # here rather than imported. Not an oversight.
    _MESSAGE = (
        "the CFE root could not be resolved: none of the three discoverable "
        "resolution steps matched (flag, environment, cwd-walk), leaving the "
        "chain in its not-found terminal state. Set --cfe-root, set the "
        "MASON_CFE_ROOT environment variable, or run mason from within or "
        "below a directory containing .claude/scripts/conda-forge-expert/."
    )

    def __init__(self) -> None:
        super().__init__("cfe:unresolved", self._MESSAGE)

    def __reduce__(self):
        # `Exception.__reduce__` (used by both `copy.deepcopy` and
        # `pickle`) reconstructs via `cls(*self.args)`; `MasonError.__init__`
        # sets `self.args = (identifier, message)` (two items), but this
        # class's constructor takes zero arguments. Without this override,
        # `CfeUnresolvedError(*self.args)` would raise `TypeError` on every
        # deepcopy/pickle round-trip.
        return (self.__class__, ())


class CfeTimeoutError(MasonError):
    """A CFE invocation exceeded its mandatory timeout (FR-4, AD-4, AD-25,
    NFR-14) -- either a CAPTURE-mode one (`cfe.py::_invoke_captured`) or a
    STREAM-mode one (`cfe.py::build_native`/`build_docker`, Story 2.6),
    which translate `run_streamed`'s bare `subprocess.TimeoutExpired` to
    this same typed error themselves (`run_streamed` only re-raises the
    stdlib exception; it does not know about Mason's error taxonomy).

    `subprocess.run`'s own `timeout=` kill-and-reap-before-raising behaviour
    (CAPTURE mode), or `run_streamed`'s equivalent explicit kill-and-reap on
    `BaseException` (STREAM mode), is what guarantees "no orphaned process"
    here (spec Always boundary) -- this class only names the failure; it
    does not itself do any process cleanup. `script` is the `_CFE_SCRIPTS`
    table key (e.g. `"validate_recipe"`, `"build_native"`), not a filesystem
    path -- the same key a caller passed to a named adapter function, so the
    message points at something a user or a future `--cfe-timeout` override
    can act on. `timeout` is the number of seconds that elapsed before the
    child was killed, echoed verbatim into the message so a user can decide
    whether to raise it.
    """

    def __init__(self, script: str, timeout: float) -> None:
        self.script = script
        self.timeout = timeout
        message = (
            f"CFE script {script!r} did not complete within its {timeout}s "
            "timeout and was killed; increase --cfe-timeout/MASON_CFE_TIMEOUT "
            "if this operation is expected to take longer"
        )
        super().__init__("cfe:timeout", message)

    def __reduce__(self):
        # Mirrors `CfeUnresolvedError.__reduce__` above (review pass,
        # 2026-08-11): `Exception.__reduce__` reconstructs via
        # `cls(*self.args)`, and `MasonError.__init__` sets `self.args =
        # (identifier, message)` -- two items, coincidentally the same count
        # this class's own constructor takes, but the WRONG two values
        # (`"cfe:timeout"` and the built message string, not `script` and
        # `timeout`). Without this override, `CfeTimeoutError(*self.args)`
        # would not raise, but would silently reconstruct with
        # `self.script == "cfe:timeout"` and `self.timeout` bound to a
        # message string, corrupting every deepcopy/pickle round-trip
        # instead of failing loudly.
        return (self.__class__, (self.script, self.timeout))


class EngineAbsentError(MasonError):
    """The named engine is not on `PATH` (Story 3.1, NFR-14).

    Raised by `engines/__init__.py::require_engine` when `probe_engine`
    reports `available=False` -- the ONE typed error every future engine
    invocation raises for "not installed" (Design Notes: Stories 3.2's build
    engines, 3.4/3.5's upload engines, and 4.1's lock engine all call
    `require_engine` at the top of their own operation methods rather than
    re-implementing absence handling), never a raw `FileNotFoundError`
    leaking a subprocess implementation detail past `engines/__init__.py`'s
    boundary.

    `name` is the engine's display name -- an `engines/__init__.py::
    _KNOWN_ENGINES` key (e.g. `"pixi"`, or `"build"` for the `build` engine),
    the same name a caller passed to `require_engine`, NOT its `PATH` binary
    name (`build`'s binary is `pyproject-build`; see that module's docstring
    for why). `conda_package` is the conda package name that provisions it
    (e.g. `"python-build"` for the `build` engine -- matching `pixi.toml`'s
    `[package.run-dependencies]` key, not the display name), so the message
    names exactly what a user would `pixi add`/`conda install`. Construction
    raises `ValueError` for an empty `name` or `conda_package`, matching
    `CfeImportFloorError`'s validation rigor: an absence error naming no
    engine, or naming one with no provisioning hint, is exactly the
    incoherent state this class exists to rule out.
    """

    def __init__(self, name: str, conda_package: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "EngineAbsentError requires a non-empty `name`: an absence "
                "error naming no engine is incoherent"
            )
        if not isinstance(conda_package, str) or not conda_package.strip():
            raise ValueError(
                "EngineAbsentError requires a non-empty `conda_package`: an "
                "absence error with no provisioning hint is incoherent"
            )
        self.name = name
        self.conda_package = conda_package
        message = (
            f"engine {name!r} was not found on PATH; provision it via the "
            f"{conda_package!r} conda package (e.g. `pixi add {conda_package}`)"
        )
        super().__init__("engine:absent", message)
