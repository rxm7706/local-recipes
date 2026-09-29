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
                "MasonError message must be a non-empty string: it must state what failed and what to do next (NFR-14)"
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
        message = f"interpreter {interpreter!r} is missing CFE's import floor: {', '.join(missing)}"
        super().__init__("cfe:import-floor-missing", message)


class FactoryIslandMissingError(MasonError):
    """The factory island or a named ``factory/recipes/<r>`` target is absent.

    Raised by ``resolve.py::resolve_factory_island`` when a factory-shaped
    recipe path cannot be mapped to ``python-foundry/factory/`` (Story 44.7).
    """

    def __init__(self, detail: str) -> None:
        super().__init__(
            "factory:missing-island",
            detail.strip(),
        )


class CfeUnresolvedError(MasonError):
    """The CFE root could not be resolved by any step of `resolve.py`'s
    chain (FR-5, D-2, NFR-14).

    Raised by `cfe.py::ensure_cfe_root` when the already-computed
    `ResolvedCfeRoot.step` is `STEP_NOT_FOUND`. Also raised directly by
    `package.py::ship_conda_forge` (Story 3.6, D-10) when its own
    `resolve_cfe_root` call finds no root, before `recipe.py::submit()` (and
    therefore `cfe.py::ensure_cfe_root`) is ever reached -- reused rather
    than a third dedicated class, since this message is already
    precondition-generic. Unlike `CfeImportFloorError`, there is no per-call
    variable data to report -- the four steps either matched or did not, and
    nothing about *which* value was tried is meaningful once resolution has
    already failed -- so the constructor takes no arguments and the message
    is a fixed string naming all four step names and how to satisfy the
    first three.
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
                "EngineAbsentError requires a non-empty `name`: an absence error naming no engine is incoherent"
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
        self,
        wheel_version: str,
        conda_version: str,
        wheel_path: str,
        conda_path: str,
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
                "PackageProjectPathError requires a non-empty `project_path`: a path error naming no path is incoherent"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "PackageProjectPathError requires a non-empty `reason`: a path error giving no reason is incoherent"
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


class InvalidShipTargetError(MasonError):
    """A `--ship`/`--to` token failed to parse as one of the four valid
    ship-target forms (Story 3.3, FR-16, FR-19, NFR-14; Story 3.9/FR-50 adds
    the fourth, `pypi-test`).

    Raised by `package.py::parse_ship_targets` for a token that is not
    exactly `"pypi"`, exactly `"pypi-test"`, exactly `"conda-forge"`, or
    `"channel:"` followed by a non-empty name -- the message names the
    offending token verbatim and lists all four valid forms (spec AC1:
    "rejected with the valid set listed"), never inventing a partial match
    or a best guess at what the caller meant. `value` is the ORIGINAL
    stripped token, not the whole comma-separated input string, so a caller
    sees exactly which part of a multi-target value was wrong. Construction
    raises `ValueError` for an empty `value`, matching
    `PackageProjectPathError`'s validation rigor: an invalid-target error
    naming no token is incoherent.
    """

    def __init__(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "InvalidShipTargetError requires a non-empty `value`: an "
                "invalid-target error naming no token is incoherent"
            )
        self.value = value
        message = (
            f"{value!r} is not a valid ship target; valid forms are "
            "'pypi', 'pypi-test', 'conda-forge', 'channel:<name>'"
        )
        super().__init__("ship:invalid-target", message)

    def __reduce__(self):
        # Mirrors `PackageProjectPathError.__reduce__` above:
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = ("ship:invalid-target",
        # <built message>)` -- the wrong value for this class's own
        # `(value,)` constructor.
        return (self.__class__, (self.value,))


class ShipCredentialMissingError(MasonError):
    """`package.py::ship_pypi`'s credential-presence precondition failed:
    `TWINE_USERNAME` and/or `TWINE_PASSWORD` are absent or empty (stripped)
    in the caller's `environ` (Story 3.4, FR-15, FR-20, AD-14, NFR-14).

    Raised as `ship_pypi`'s FIRST action, before `build()` or `engines.
    twine.upload()` are ever called (architecture AD-14: "Credential
    presence is validated before any artifact is built") -- mirrors
    `EngineAbsentError`/`CfeUnresolvedError`'s precedent that a structural
    precondition is RAISED, not returned as data. `missing` names exactly
    which of `TWINE_USERNAME`/`TWINE_PASSWORD` were absent or empty, in the
    order `ship_pypi` checked them -- construction raises `ValueError` for
    an empty `missing` or for any entry that is not a non-empty string,
    matching `CfeImportFloorError`'s validation rigor: a credential-missing
    error naming nothing missing, or naming a malformed entry, is exactly
    the incoherent state this class exists to rule out. `missing` is stored
    as a `tuple`, matching every other `Sequence`-typed field in this
    module.

    The message never names a specific repository (review pass 3, Story
    3.9): `ship_pypi` raises this identically for both a real `pypi` ship
    and a `pypi-test` rehearsal (AD-26's "identical code path"), and the
    message is built BEFORE `ship_pypi` computes which of the two it is --
    "set them before shipping to pypi" was accurate when only `pypi`
    existed (Story 3.4) but became actively misleading for a `pypi-test`
    invocation once Story 3.9 added it; genericizing to "before shipping"
    is correct for both rather than threading a new constructor parameter
    through for a cosmetic distinction.
    """

    def __init__(self, missing: Sequence[str]) -> None:
        missing = tuple(missing)
        if not missing:
            raise ValueError(
                "ShipCredentialMissingError requires a non-empty `missing`: a "
                "credential-missing error naming nothing missing is incoherent"
            )
        if not all(isinstance(item, str) and item.strip() for item in missing):
            raise ValueError(
                "ShipCredentialMissingError requires every `missing` entry to "
                "be a non-empty string: a credential-missing error naming a "
                "malformed entry is incoherent"
            )
        self.missing = missing
        message = (
            f"missing PyPI upload credential(s) in the environment: {', '.join(missing)}; set them before shipping"
        )
        super().__init__("ship:credential-missing", message)

    def __reduce__(self):
        # Mirrors `InvalidShipTargetError.__reduce__` above:
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = (
        # "ship:credential-missing", <built message>)` -- the wrong value
        # for this class's own `(missing,)` constructor.
        return (self.__class__, (self.missing,))


class ShipUploadTimeoutError(MasonError):
    """A `engines.twine.upload()` invocation exceeded its mandatory timeout
    (Story 3.4, FR-20, AD-25, NFR-14) -- mirrors `PackageBuildTimeoutError`'s
    own shape and rationale exactly; only the wrapped subprocess boundary
    differs (`engines.twine.upload`'s own `subprocess.run(timeout=...)`
    rather than an `engines.pep517`/`engines.pixi` build).

    `subprocess.run`'s own `timeout=` kill-and-reap-before-raising behaviour
    is what guarantees "no orphaned process" here -- this class only names
    the failure; it does not itself do any process cleanup. `timeout` is the
    number of seconds that elapsed before the child was killed, echoed
    verbatim into the message. v1 exposes no per-upload timeout override
    (spec Never boundary) -- the message says so rather than pointing at a
    knob that does not exist.
    """

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        message = (
            f"the PyPI upload did not complete within {timeout}s and was "
            "killed; this is not a currently configurable v1 knob"
        )
        super().__init__("ship:upload-timeout", message)

    def __reduce__(self):
        # Mirrors `PackageBuildTimeoutError.__reduce__` above:
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = ("ship:upload-timeout",
        # <built message>)` -- the wrong value for this class's own
        # `(timeout,)` constructor.
        return (self.__class__, (self.timeout,))


class ShipChannelCredentialMissingError(MasonError):
    """`package.py::ship_channel`'s credential-presence precondition failed:
    `PREFIX_API_KEY` is absent or empty (stripped) in the caller's `environ`
    (Story 3.5, FR-16, AD-14, NFR-14).

    A dedicated class, NOT a reuse of `ShipCredentialMissingError` (spec
    Always boundary): that class hardcodes "PyPI" into its message text
    (`"missing PyPI upload credential(s)..."`), which would be a factually
    wrong diagnostic for a channel-upload failure. Raised as `ship_channel`'s
    FIRST action, before `build()` or `engines.pixi.upload()` are ever
    called (architecture AD-14: "Credential presence is validated before any
    artifact is built") -- mirrors `ShipCredentialMissingError`/
    `EngineAbsentError`/`CfeUnresolvedError`'s precedent that a structural
    precondition is RAISED, not returned as data. `missing` names exactly
    which required channel-upload credential(s) were absent or empty, in the
    order `ship_channel` checked them -- construction raises `ValueError` for
    an empty `missing` or for any entry that is not a non-empty string,
    matching `ShipCredentialMissingError`'s validation rigor: a credential-
    missing error naming nothing missing, or naming a malformed entry, is
    exactly the incoherent state this class exists to rule out. `missing` is
    stored as a `tuple`, matching every other `Sequence`-typed field in this
    module.
    """

    def __init__(self, missing: Sequence[str]) -> None:
        missing = tuple(missing)
        if not missing:
            raise ValueError(
                "ShipChannelCredentialMissingError requires a non-empty "
                "`missing`: a credential-missing error naming nothing "
                "missing is incoherent"
            )
        if not all(isinstance(item, str) and item.strip() for item in missing):
            raise ValueError(
                "ShipChannelCredentialMissingError requires every `missing` "
                "entry to be a non-empty string: a credential-missing error "
                "naming a malformed entry is incoherent"
            )
        self.missing = missing
        message = (
            f"missing channel upload credential(s) in the environment: "
            f"{', '.join(missing)}; set them before shipping to a channel"
        )
        super().__init__("ship:channel-credential-missing", message)

    def __reduce__(self):
        # Mirrors `ShipCredentialMissingError.__reduce__` above:
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = (
        # "ship:channel-credential-missing", <built message>)` -- the wrong
        # value for this class's own `(missing,)` constructor.
        return (self.__class__, (self.missing,))


class ShipChannelUploadTimeoutError(MasonError):
    """A `engines.pixi.upload()` invocation exceeded its mandatory timeout
    (Story 3.5, FR-16, AD-25, NFR-14) -- mirrors `ShipUploadTimeoutError`'s
    own shape and rationale exactly; only the wrapped subprocess boundary
    differs (`engines.pixi.upload`'s own `subprocess.run(timeout=...)`
    rather than `engines.twine.upload`'s).

    A dedicated class, NOT a reuse of `ShipUploadTimeoutError` (spec Always
    boundary): that class hardcodes "PyPI" into its message text (`"the
    PyPI upload did not complete..."`), which would be a factually wrong
    diagnostic for a channel-upload timeout.

    `subprocess.run`'s own `timeout=` kill-and-reap-before-raising behaviour
    is what guarantees "no orphaned process" here -- this class only names
    the failure; it does not itself do any process cleanup. `timeout` is the
    number of seconds that elapsed before the child was killed, echoed
    verbatim into the message. v1 exposes no per-upload timeout override
    (spec Never boundary) -- the message says so rather than pointing at a
    knob that does not exist.
    """

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        message = (
            f"the channel upload did not complete within {timeout}s and was "
            "killed; this is not a currently configurable v1 knob"
        )
        super().__init__("ship:channel-upload-timeout", message)

    def __reduce__(self):
        # Mirrors `ShipUploadTimeoutError.__reduce__` above:
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = (
        # "ship:channel-upload-timeout", <built message>)` -- the wrong
        # value for this class's own `(timeout,)` constructor.
        return (self.__class__, (self.timeout,))


class ShipCondaForgeRecipeMissingError(MasonError):
    """`package.py::ship_conda_forge`'s first gate failed: no `recipe_path`
    was given -- `None` or blank (Story 3.6, FR-23, D-10, NFR-14).

    This is `ship_conda_forge`'s own precursor check, not one of D-10's two
    shipping preconditions (those are the CFE root resolving, and the
    recipe's location -- see `ShipCondaForgeRecipeLocationError` below).
    Raised as `ship_conda_forge`'s FIRST action, before the CFE root is
    even resolved -- mirrors `ShipCredentialMissingError`/
    `ShipChannelCredentialMissingError`/`CfeUnresolvedError`'s precedent
    that a structural precondition is RAISED, not returned as data.
    Zero-arg constructor, mirroring `CfeUnresolvedError`'s own shape: there
    is no per-call variable data to report -- a missing recipe path is
    missing regardless of what else was passed -- so the message is a
    fixed string naming `mason recipe new` as the remedy. This is what
    satisfies FR-23's "offers... does not generate silently" requirement:
    this error's own message is the offer; nothing here prompts
    interactively or calls `recipe.new()` itself (spec Never boundary --
    that CLI-level offer is Story 3.9's scope).
    """

    _MESSAGE = (
        "no recipe path was given for the conda-forge ship target; run "
        "`mason recipe new` to generate one, then pass its path"
    )

    def __init__(self) -> None:
        super().__init__("ship:conda-forge-recipe-missing", self._MESSAGE)

    def __reduce__(self):
        # Mirrors `CfeUnresolvedError.__reduce__` above: `Exception.
        # __reduce__` reconstructs via `cls(*self.args)`, but `MasonError.
        # __init__` sets `self.args` to a two-item tuple while this class's
        # constructor takes zero arguments -- without this override,
        # `ShipCondaForgeRecipeMissingError(*self.args)` would raise
        # `TypeError` on every deepcopy/pickle round-trip.
        return (self.__class__, ())


class ShipCondaForgeRecipeLocationError(MasonError):
    """`package.py::ship_conda_forge`'s second D-10 shipping precondition
    failed: the resolved recipe directory does not sit at exactly
    `<cfe-root>/recipes/<name>/` (Story 3.6, FR-23, D-10, NFR-14).

    This is the THIRD and last of `ship_conda_forge`'s gates, checked only
    after `ShipCondaForgeRecipeMissingError`'s precursor and D-10's first
    precondition (the root resolving, `CfeUnresolvedError`) both pass -- so
    when several inputs are wrong at once, this is not the error the user
    sees first.

    D-10 deliberately narrows `recipe.py::submit()`'s own leniency (that
    verb tolerates an out-of-tree recipe via its `CFE_RECIPES_ROOT` env
    override, per its own docstring) for the ship-target boundary alone:
    "Shipping to `conda-forge` works only from a repository where... the
    recipe sits at `<cfe-root>/recipes/<name>/`" (PRD D-10) -- `mason
    recipe submit` stays lenient; `mason package ship --to conda-forge`
    does not. Raised before any CFE subprocess spawns (spec Always
    boundary), mirroring `PackageProjectPathError`'s precedent that a
    structural precondition is RAISED, not returned as data.

    `recipe_path`/`expected_path` are both ALREADY-RESOLVED, absolute
    strings (`ship_conda_forge`'s own `recipe_dir`/`expected_dir`) -- the
    message names both, so a caller sees exactly what was given and
    exactly where D-10 requires it to sit. Construction raises `ValueError`
    for an empty `recipe_path`/`expected_path`, matching
    `PackageProjectPathError`'s validation rigor: a location error naming
    no path on either side is incoherent.
    """

    def __init__(self, recipe_path: str, expected_path: str) -> None:
        if not isinstance(recipe_path, str) or not recipe_path.strip():
            raise ValueError(
                "ShipCondaForgeRecipeLocationError requires a non-empty "
                "`recipe_path`: a location error naming no recipe path is "
                "incoherent"
            )
        if not isinstance(expected_path, str) or not expected_path.strip():
            raise ValueError(
                "ShipCondaForgeRecipeLocationError requires a non-empty "
                "`expected_path`: a location error naming no expected "
                "path is incoherent"
            )
        self.recipe_path = recipe_path
        self.expected_path = expected_path
        message = (
            f"recipe at {recipe_path!r} is not at the required conda-forge "
            f"ship location {expected_path!r}: shipping to conda-forge "
            "requires the recipe to sit at <cfe-root>/recipes/<name>/ (D-10)"
        )
        super().__init__("ship:conda-forge-recipe-location", message)

    def __reduce__(self):
        # Mirrors `PackageProjectPathError.__reduce__` above: `Exception.
        # __reduce__` reconstructs via `cls(*self.args)`, and `MasonError.
        # __init__` sets `self.args = ("ship:conda-forge-recipe-location",
        # <built message>)` -- the wrong two values for this class's own
        # `(recipe_path, expected_path)` constructor.
        return (self.__class__, (self.recipe_path, self.expected_path))


class EnvironmentLockTimeoutError(MasonError):
    """A `engines.condalock.lock()` invocation exceeded its mandatory
    timeout (Story 4.1, FR-29, AD-25, NFR-14) -- mirrors
    `ShipUploadTimeoutError`'s own shape and rationale exactly; only the
    wrapped subprocess boundary differs (`engines.condalock.lock`'s own
    `subprocess.run(timeout=...)` rather than `engines.twine.upload`'s).

    `subprocess.run`'s own `timeout=` kill-and-reap-before-raising behaviour
    is what guarantees "no orphaned process" here -- this class only names
    the failure; it does not itself do any process cleanup. `timeout` is the
    number of seconds that elapsed before the child was killed, echoed
    verbatim into the message. v1 exposes no per-lock timeout override (spec
    Never boundary) -- the message says so rather than pointing at a knob
    that does not exist. Only `condalock.lock()` ever raises this error, so
    -- unlike `PackageBuildTimeoutError`'s `engine` argument -- no second
    constructor argument is needed to disambiguate which engine timed out.
    """

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        message = (
            f"the environment lock did not complete within {timeout}s and was "
            "killed; this is not a currently configurable v1 knob"
        )
        super().__init__("environment:lock-timeout", message)

    def __reduce__(self):
        # Mirrors `ShipUploadTimeoutError.__reduce__` above:
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = (
        # "environment:lock-timeout", <built message>)` -- the wrong value
        # for this class's own `(timeout,)` constructor.
        return (self.__class__, (self.timeout,))


class EnvironmentLockfileMissingError(MasonError):
    """`engines.condalock.check()`'s own lockfile-presence precondition
    failed: the caller's `--lockfile`/`-l` path does not exist on disk, is
    not a regular file (e.g. a directory or a broken symlink -- `os.path.
    isfile()` returns `False` for both), or vanished in the narrow race
    between that check and the temp copy (Story 4.4, FR-25, FR-27, FR-29,
    NFR-14).

    Raised before any subprocess spawns or temp copy is made, or -- for the
    race case -- from `check()`'s own `shutil.copyfile` failure translation
    (spec Always boundary) -- a deliberate departure from `lock()`'s own "no
    Mason-side pre-validation" default, forced by `check()`'s copy-before-
    invoke design (Design Notes): there is no existing file to copy when
    none exists, and conda-lock's own returncode cannot be trusted to
    distinguish "missing" from "stale" (Design Notes: `--check-input-hash`'s
    exit code 4 is dead in installed `conda-lock` 4.0.2). Construction
    raises `TypeError` for a non-`str` `lockfile_path` -- unlike most
    sibling `MasonError` subclasses, an EMPTY string is accepted (review
    pass, 2026-08-15): `argparse`'s `required=True` on `--lockfile` only
    demands the flag be given, not that its value be non-blank, so `mason
    environment check ... --lockfile ""` is a real, reachable CLI input, not
    a caller bug -- rejecting it here with `ValueError` would escape
    `main()`'s `except MasonError` handler and surface a raw traceback
    instead of this class's own clean diagnostic.
    """

    def __init__(self, lockfile_path: str) -> None:
        if not isinstance(lockfile_path, str):
            raise TypeError(
                "EnvironmentLockfileMissingError requires `lockfile_path` to "
                f"be a str, got {type(lockfile_path).__name__}"
            )
        self.lockfile_path = lockfile_path
        # Truthiness, NOT `.strip()` (review pass, 2026-08-15 second): a
        # whitespace-only `--lockfile "   "` IS a path the user supplied, and
        # `.strip()` sent it down the "no path was given" branch below,
        # contradicting what they typed. Only the genuinely empty string --
        # `--lockfile ""`, which argparse's `required=True` still accepts --
        # takes that branch now.
        if lockfile_path:
            message = (
                f"lockfile {lockfile_path!r} does not exist or is not a file; run `mason environment lock` to create it"
            )
        else:
            message = "no --lockfile path was given; run `mason environment lock` to create one, then pass its path"
        super().__init__("environment:lockfile-missing", message)

    def __reduce__(self):
        # Mirrors `PackageProjectPathError.__reduce__` above: `Exception.
        # __reduce__` reconstructs via `cls(*self.args)`, and `MasonError.
        # __init__` sets `self.args = ("environment:lockfile-missing", <built
        # message>)` -- the wrong value for this class's own
        # `(lockfile_path,)` constructor.
        return (self.__class__, (self.lockfile_path,))


class EnvironmentLockfileMalformedError(MasonError):
    """`engines.condalock.check()`'s own lockfile-content precondition
    failed: the temp copy of `lockfile_path` could not be read as a
    conda-lock lockfile after `yaml.safe_load` (Story 4.4, FR-25, FR-27,
    FR-29, NFR-14; review pass, 2026-08-15).

    Raised when the lockfile at `lockfile_path` is not valid YAML, is empty
    (`yaml.safe_load` returns `None`), is not valid UTF-8, or does not carry
    the `metadata.content_hash` shape every conda-lock-produced lockfile has
    (spec `LockMeta.content_hash` is a required field) -- a foreign or
    corrupted file passed as `--lockfile` is not `EngineAbsentError` (the
    engine IS present) nor `EnvironmentLockfileMissingError` (the file DOES
    exist), and reaching it must never surface a raw `KeyError`/`TypeError`/
    `yaml.YAMLError`/`UnicodeDecodeError`/`OSError` past this module's own
    boundary, mirroring `EngineAbsentError`'s own "never leak a subprocess
    implementation detail" precedent for a different failure class.
    `reason` is `str(exc)` from whichever exception was caught -- the
    underlying library's own diagnostic text, verbatim (AD-1), never a
    Mason-side re-authoring of it. Construction raises `ValueError` for an
    empty `lockfile_path`/`reason`, matching `PackageProjectPathError`'s
    validation rigor: a malformed-lockfile error naming no path, or giving
    no reason, is incoherent -- unlike `EnvironmentLockfileMissingError`
    above, an empty `lockfile_path` can never reach this class (`check()`'s
    own `os.path.isfile`/`shutil.copyfile` gates already raise the sibling
    error first for any path that does not resolve to a readable file, so by
    the time this class's own raise site runs, `lockfile_path` is known
    non-empty).
    """

    def __init__(self, lockfile_path: str, reason: str) -> None:
        if not isinstance(lockfile_path, str) or not lockfile_path.strip():
            raise ValueError(
                "EnvironmentLockfileMalformedError requires a non-empty "
                "`lockfile_path`: a malformed-lockfile error naming no path "
                "is incoherent"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "EnvironmentLockfileMalformedError requires a non-empty "
                "`reason`: a malformed-lockfile error giving no reason is "
                "incoherent"
            )
        self.lockfile_path = lockfile_path
        self.reason = reason
        message = (
            f"lockfile {lockfile_path!r} could not be read as a conda-lock lockfile: "
            f"{reason}; run `mason environment lock` to regenerate it"
        )
        super().__init__("environment:lockfile-malformed", message)

    def __reduce__(self):
        # Mirrors `PackageProjectPathError.__reduce__` above: `Exception.
        # __reduce__` reconstructs via `cls(*self.args)`, and `MasonError.
        # __init__` sets `self.args = ("environment:lockfile-malformed",
        # <built message>)` -- the wrong two values for this class's own
        # `(lockfile_path, reason)` constructor.
        return (self.__class__, (self.lockfile_path, self.reason))


class EnvironmentCheckTimeoutError(MasonError):
    """A `engines.condalock.check()` invocation exceeded its mandatory
    timeout (Story 4.4, FR-25, FR-27, FR-29, AD-25, NFR-14) -- mirrors
    `EnvironmentLockTimeoutError`'s own shape and rationale exactly; only the
    wrapped operation differs (`condalock.check`'s own `--check-input-hash`
    re-run against a temporary lockfile copy rather than `condalock.lock`'s
    plain solve).

    A dedicated class, NOT a reuse of `EnvironmentLockTimeoutError` (spec
    Always boundary): that class hardcodes "environment lock" into its
    message text (`"the environment lock did not complete..."`), which would
    be a factually wrong diagnostic for a staleness-check timeout -- mirrors
    `ShipUploadTimeoutError`/`ShipChannelUploadTimeoutError`'s identical
    precedent of one dedicated timeout class per distinct operation even when
    the same binary is wrapped.

    `subprocess.run`'s own `timeout=` kill-and-reap-before-raising behaviour
    is what guarantees "no orphaned process" here -- this class only names
    the failure; it does not itself do any process cleanup. `timeout` is the
    number of seconds that elapsed before the child was killed, echoed
    verbatim into the message. v1 exposes no per-check timeout override (spec
    Never boundary) -- the message says so rather than pointing at a knob
    that does not exist.
    """

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        message = (
            f"the environment check did not complete within {timeout}s and was "
            "killed; this is not a currently configurable v1 knob"
        )
        super().__init__("environment:check-timeout", message)

    def __reduce__(self):
        # Mirrors `EnvironmentLockTimeoutError.__reduce__` above:
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = (
        # "environment:check-timeout", <built message>)` -- the wrong value
        # for this class's own `(timeout,)` constructor.
        return (self.__class__, (self.timeout,))


class EnvironmentManifestsNotFoundError(MasonError):
    """`environment.py::discover_manifests` found none of the four supported
    manifest kinds in `directory` (Story 4.2, FR-25, NFR-14).

    Raised only when every check in `discover_manifests`'s fixed-order scan
    -- `pyproject.toml`, `environment.yml`, `requirements*.txt`, `pixi.toml`
    -- comes up empty. `directory` is `str(directory)` (the searched
    directory, `Path.cwd()` at `cli.py`'s own call site); `filenames` is
    exactly the four literal patterns searched, in that order, so the
    message tells a caller both where discovery looked and what it was
    looking for. Construction raises `ValueError` for an empty `directory`
    or `filenames`, matching `PackageProjectPathError`/
    `ShipCredentialMissingError`'s validation rigor: a not-found error
    naming no directory, or naming nothing it searched for, is incoherent.
    `filenames` is stored as a `tuple`, matching every other `Sequence`-typed
    field in this module. Every `filenames` entry must itself be a non-empty
    string (review pass, 2026-08-15, matching `ShipCredentialMissingError`'s
    identical per-entry check) -- a not-found error naming a blank pattern is
    exactly as incoherent as naming none at all.
    """

    def __init__(self, directory: str, filenames: Sequence[str]) -> None:
        if not isinstance(directory, str) or not directory.strip():
            raise ValueError(
                "EnvironmentManifestsNotFoundError requires a non-empty "
                "`directory`: a not-found error naming no directory is "
                "incoherent"
            )
        filenames = tuple(filenames)
        if not filenames:
            raise ValueError(
                "EnvironmentManifestsNotFoundError requires a non-empty "
                "`filenames`: a not-found error naming nothing it searched "
                "for is incoherent"
            )
        if not all(isinstance(item, str) and item.strip() for item in filenames):
            raise ValueError(
                "EnvironmentManifestsNotFoundError requires every `filenames` "
                "entry to be a non-empty string: a not-found error naming a "
                "malformed entry is incoherent"
            )
        self.directory = directory
        self.filenames = filenames
        message = f"no dependency manifests found in {directory!r}; looked for {', '.join(filenames)}"
        super().__init__("environment:manifests-not-found", message)

    def __reduce__(self):
        # Mirrors `EnvironmentLockfileMalformedError.__reduce__` above:
        # `Exception.__reduce__` reconstructs via `cls(*self.args)`, and
        # `MasonError.__init__` sets `self.args = (
        # "environment:manifests-not-found", <built message>)` -- the wrong
        # two values for this class's own `(directory, filenames)`
        # constructor.
        return (self.__class__, (self.directory, self.filenames))
