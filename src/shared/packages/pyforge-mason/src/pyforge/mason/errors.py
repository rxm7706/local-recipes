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

from pyforge.core.errors import PyforgeError

# Two lowercase, hyphen-delimited segments joined by a single colon, e.g.
# "cfe:unresolved" or "ship:credential-missing". Neither segment may be
# empty, start/end with a hyphen, or contain a double hyphen. `\Z` (not `$`)
# anchors strictly to the end of the string -- `$` alone would also accept a
# single trailing newline, letting a malformed identifier through.
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*:[a-z0-9]+(-[a-z0-9]+)*\Z")


class MasonError(PyforgeError):
    """Base class for every anticipated Mason failure.

    Story 14.3, SPEC-pyforge-core CAP-5: re-parented to the shared
    ``PyforgeError`` marker (no ``__init__`` override on either side, so
    this changes nothing observable, including for subclasses like
    ``CfeUnresolvedError``/``CfeTimeoutError`` with their own custom
    ``__init__``/``__reduce__``) -- they re-parent transitively.

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


class RecipeGenerationError(MasonError):
    """`cfe.py::generate_recipe` reported a non-zero exit for `recipe.py::new`
    (FR-7, NFR-14).

    `source` is the CFE subcommand name the caller selected (`pypi`/`github`/
    `cran`/`npm` -- `recipe.py`'s own `--from-*` -> subcommand mapping, spec
    Always boundary), not a filesystem path or a Mason-invented label.
    `cfe_message` is CFE's own failure text, embedded verbatim -- the wrapped
    recipe-generator script's `main()` prints `Error: <e>` to **stdout** on
    failure (its own trailing `except Exception as e: print(f"Error:
    {e}")`), not stderr, so `recipe.py` prefers `CfeResult.stdout` over
    `stderr` when building this argument; this class does no interpretation
    of its own, only carries the string through. (Script filenames are named
    once, in `cfe.py` alone -- AD-3, `tests/meta/test_adapter_sole_caller.py`
    -- so this docstring deliberately never spells the `.py` filename.)

    `__reduce__` mirrors `CfeTimeoutError`'s override immediately below, for
    the identical reason: `MasonError.__init__` sets `self.args =
    (identifier, message)` -- two items, but the WRONG two values for this
    class's own two-argument constructor (`source`, `cfe_message`). Without
    this override, `RecipeGenerationError(*self.args)` would not raise, but
    would silently reconstruct with `self.source` bound to the identifier
    string and `self.cfe_message` bound to the built message, corrupting
    every deepcopy/pickle round-trip instead of failing loudly.
    """

    def __init__(self, source: str, cfe_message: str) -> None:
        self.source = source
        self.cfe_message = cfe_message
        message = f"recipe generation from {source} failed: {cfe_message}"
        super().__init__("recipe:generation-failed", message)

    def __reduce__(self):
        return (self.__class__, (self.source, self.cfe_message))


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

    def __reduce__(self):
        # Mirrors `CfeTimeoutError.__reduce__` (review pass, 2026-08-13):
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = (identifier, message)` --
        # two items, coincidentally the same count this class's own
        # constructor takes, but the WRONG two values (`"engine:absent"` and
        # the built message string, not `name` and `conda_package`).
        # `copy.deepcopy`/`pickle` restore `__dict__` state on top of that
        # reconstruction, so `.name`/`.conda_package`/`.message`/`str(exc)`
        # end up correct anyway -- but `.args` itself, and therefore
        # `repr(exc)`, stays permanently garbled without this override.
        return (self.__class__, (self.name, self.conda_package))


class PackageVersionMismatchError(MasonError):
    """`package.py::build()`'s wheel/sdist build and its `.conda` build
    reported different version numbers for the same project (Story 3.2,
    FR-22, NFR-14).

    Raised only when BOTH `wheel_version` and `conda_version` are known
    (neither engine's build failed to produce a parseable artifact) and
    they actually disagree -- a real packaging inconsistency (a stale
    generated file, a build backend reading a different source of truth
    than `pixi-build-python` did), never raised merely because one side is
    unknown (spec Always boundary: that case is data on `models.
    PackageBuildResult`, not this error). Construction raises `ValueError`
    for an empty `wheel_version`/`conda_version`/`wheel_path`/`conda_path`,
    matching `EngineAbsentError`'s validation rigor: a mismatch error naming
    no version on one side is incoherent.

    `wheel_path`/`conda_path` are the two ALREADY-BUILT artifacts' own
    paths (review pass, 2026-08-13): by the time this error is raised, both
    engine builds already succeeded and left real files on disk, so the
    message names exactly where to find each one -- a bare pair of version
    strings with no path leaves a user with nothing to act on. Both are
    guaranteed non-`None` at `package.py::build()`'s one call site (the
    mismatch branch only runs when both `*_version` fields are non-`None`,
    which only happens when the corresponding `*_path` was also
    successfully discovered).
    """

    def __init__(
        self, wheel_version: str, conda_version: str, wheel_path: str, conda_path: str,
    ) -> None:
        if not isinstance(wheel_version, str) or not wheel_version.strip():
            raise ValueError(
                "PackageVersionMismatchError requires a non-empty `wheel_version`: "
                "a mismatch error naming no wheel version is incoherent"
            )
        if not isinstance(conda_version, str) or not conda_version.strip():
            raise ValueError(
                "PackageVersionMismatchError requires a non-empty `conda_version`: "
                "a mismatch error naming no conda version is incoherent"
            )
        if not isinstance(wheel_path, str) or not wheel_path.strip():
            raise ValueError(
                "PackageVersionMismatchError requires a non-empty `wheel_path`: "
                "a mismatch error with no wheel artifact location is incoherent"
            )
        if not isinstance(conda_path, str) or not conda_path.strip():
            raise ValueError(
                "PackageVersionMismatchError requires a non-empty `conda_path`: "
                "a mismatch error with no conda artifact location is incoherent"
            )
        self.wheel_version = wheel_version
        self.conda_version = conda_version
        self.wheel_path = wheel_path
        self.conda_path = conda_path
        message = (
            f"wheel/sdist build reports version {wheel_version!r} (at {wheel_path!r}) but "
            f"the .conda build reports {conda_version!r} (at {conda_path!r}) -- these must "
            "match (FR-22)"
        )
        super().__init__("package:version-mismatch", message)

    def __reduce__(self):
        # Mirrors `EngineAbsentError.__reduce__` above: `Exception.
        # __reduce__` reconstructs via `cls(*self.args)`, and `MasonError.
        # __init__` sets `self.args = ("package:version-mismatch", <built
        # message>)` -- the wrong two values for this class's own
        # `(wheel_version, conda_version, wheel_path, conda_path)` constructor.
        return (
            self.__class__,
            (self.wheel_version, self.conda_version, self.wheel_path, self.conda_path),
        )


class PackageBuildTimeoutError(MasonError):
    """A `package build` engine invocation (`engines.pep517.build`/
    `engines.pixi.build`) exceeded its mandatory timeout (Story 3.2, FR-15,
    AD-25, NFR-14) -- mirrors `CfeTimeoutError`'s own shape and rationale
    exactly; only the wrapped subprocess boundary differs (an engine
    adapter's own `subprocess.run(timeout=...)` rather than
    `cfe.py::_invoke_captured`/`run_streamed`).

    `subprocess.run`'s own `timeout=` kill-and-reap-before-raising behaviour
    is what guarantees "no orphaned process" here -- this class only names
    the failure; it does not itself do any process cleanup. `engine` is the
    `engines/__init__.py::_KNOWN_ENGINES` display name (`"build"` or
    `"pixi"`), the same name a caller passed to `require_engine` at the top
    of that adapter's own `build()`. `timeout` is the number of seconds that
    elapsed before the child was killed, echoed verbatim into the message.
    Unlike `CfeTimeoutError`'s `--cfe-timeout/MASON_CFE_TIMEOUT` override,
    v1 exposes no per-engine timeout flag (spec Never boundary) -- the
    message says so rather than pointing at a knob that does not exist.
    """

    def __init__(self, engine: str, timeout: float) -> None:
        self.engine = engine
        self.timeout = timeout
        message = (
            f"the {engine!r} engine did not complete its build within {timeout}s "
            "and was killed; this is not a currently configurable v1 knob"
        )
        super().__init__("package:build-timeout", message)

    def __reduce__(self):
        # Mirrors `CfeTimeoutError.__reduce__` (module docstring precedent):
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = ("package:build-timeout",
        # <built message>)` -- the wrong two values for this class's own
        # `(engine, timeout)` constructor.
        return (self.__class__, (self.engine, self.timeout))


class PackageProjectPathError(MasonError):
    """`package.py::build()`'s `project_path` could not be resolved, or an
    engine adapter could not use it as a build directory (Story 3.2, FR-15,
    NFR-14).

    Two distinct raise sites share this one error: (1) `package.py::build()`
    itself, when `Path(project_path).expanduser().resolve()` raises
    `OSError`/`ValueError` for a pathological input (a null byte, an
    unreadable parent directory encountered during symlink resolution) --
    before either engine adapter is ever called; (2) `engines.pep517.build`/
    `engines.pixi.build`, when `project_path` resolves fine but does not
    exist (or is not a directory) by the time the child process starts,
    so `subprocess.run(cwd=project_path)` raises `FileNotFoundError`/
    `NotADirectoryError` (both `OSError` subclasses) BEFORE the wrapped
    tool ever runs. This is NOT the "wrapped tool reports its own failure
    via returncode" case those adapters otherwise treat as data (AD-4): the
    tool never starts, so there is no returncode to report -- the raw
    stdlib exception must not escape past `main()`'s `except MasonError`
    handler either.

    `reason` is `str(exc)` from whichever `OSError`/`ValueError` was caught
    -- the stdlib's own diagnostic text, verbatim (AD-1), never a Mason-side
    re-authoring of it. Construction raises `ValueError` for an empty
    `project_path`/`reason`, matching `EngineAbsentError`'s validation
    rigor: a path error naming no path, or giving no reason, is incoherent.
    """

    def __init__(self, project_path: str, reason: str) -> None:
        if not isinstance(project_path, str) or not project_path.strip():
            raise ValueError(
                "PackageProjectPathError requires a non-empty `project_path`: "
                "a path error naming no path is incoherent"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "PackageProjectPathError requires a non-empty `reason`: "
                "a path error giving no reason is incoherent"
            )
        self.project_path = project_path
        self.reason = reason
        message = f"could not use {project_path!r} as a package build directory: {reason}"
        super().__init__("package:project-path-invalid", message)

    def __reduce__(self):
        # Mirrors `CfeTimeoutError.__reduce__` (module docstring precedent):
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = (
        # "package:project-path-invalid", <built message>)` -- the wrong two
        # values for this class's own `(project_path, reason)` constructor.
        return (self.__class__, (self.project_path, self.reason))
