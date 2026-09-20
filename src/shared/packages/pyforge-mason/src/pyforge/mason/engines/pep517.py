"""`build` engine adapter (AD-12, Story 3.2): PEP 517 wheel+sdist
construction via `pyproject-build --no-isolation` (FR-15, FR-21).

`name`/`probe()` are module-level, not a class instance: this file itself
is the adapter, satisfying `engines/__init__.py::EngineAdapter`'s shape
structurally (`isinstance(pyforge.mason.engines.pep517, EngineAdapter)`
holds -- a module is an ordinary object with attributes) -- matches this
package's existing function-only style (no class anywhere under
`pyforge.mason` except a frozen dataclass, an `Exception` subclass, or the
`Protocol` itself). `build()` is the adapter's one operation:
`package.py::build()` (Story 3.2) calls this module's `build()` and
`engines.pixi`'s `build()` and composes their two results into one
`models.PackageBuildResult`.

`_BINARY_NAME` duplicates `engines/__init__.py`'s own
`_KNOWN_ENGINES["build"]` entry (`"pyproject-build"`, not `"build"` -- see
that module's docstring for why) -- the same sanctioned small-fact
duplication `resolve.py`/`errors.py`/`recipe.py` already use elsewhere in
this package (e.g. `_ENV_CFE_ROOT`, `_CFE_RECIPES_ROOT_ENV_VAR`) rather than
importing a private name across a module boundary, which no module in this
package does today.

STREAM mode without porting `cfe.run_streamed` (spec Design Notes): only
`stdout` is captured (`PIPE`); `stderr` is inherited (`None`), so the
child's build output streams live to the user's own stderr with zero
buffering (AD-25) and there is no two-pipe deadlock risk `subprocess.run`
would otherwise carry -- its own timeout handling already kills and reaps
the child, so no threaded reader is needed. `stdout` is captured only so a
chatty build tool's own stdout never reaches Mason's stdout, preserving
AD-8's single-JSON-document guarantee under `--format json`; its content is
discarded, never parsed -- which artifacts were produced is read back off
the filesystem instead (below), never scraped from build-tool output text.

Version discovery: after a zero-returncode build, this module globs
`<project_path>/dist/` for `*.whl`/`*.tar.gz` files and parses each
filename with `packaging.utils.parse_wheel_filename`/`parse_sdist_filename`
-- PEP 427/625 filename conventions `packaging` already implements, never
CFE/recipe knowledge. When more than one candidate of either kind is
present (a dirty `dist/` left over from an earlier build), the most
recently modified one is used -- deterministic without parsing build-tool
stdout. A file that fails to parse (`InvalidWheelFilename`/
`InvalidSdistFilename`) is treated as absent rather than raised: this
module's own job is discovery, not validating a build tool's output.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from packaging.utils import (
    InvalidSdistFilename,
    InvalidWheelFilename,
    parse_sdist_filename,
    parse_wheel_filename,
)

from ..errors import PackageBuildTimeoutError, PackageProjectPathError
from . import probe_engine, require_engine

name = "build"
"""`EngineAdapter.name` -- an `engines/__init__.py::_KNOWN_ENGINES` key."""

_BINARY_NAME = "pyproject-build"
"""Duplicates `_KNOWN_ENGINES["build"]` (module docstring)."""

_PEP517_BUILD_TIMEOUT_SECONDS = 600.0
"""Ten minutes: a wheel+sdist build from a clean project is normally a few
seconds, but a project with a heavier build step can run considerably
longer -- generous relative to `cfe.py`'s CAPTURE-mode adapters' 120s
defaults, mirroring `cfe.py::_BUILD_NATIVE_TIMEOUT_SECONDS`'s own "a build
compiles from source" rationale for a similarly generous value."""


def probe() -> str | None:
    """`EngineAdapter.probe()` -- the `build` engine's raw `--version`
    output, or `None` if present but unparseable (never raises; see
    `engines/__init__.py::probe_engine`'s own contract)."""
    return probe_engine(name, _BINARY_NAME).version


@dataclass(frozen=True)
class Pep517BuildResult:
    """One `build()` call's outcome. `returncode` is the child's raw exit
    code -- DATA, never raised (AD-4, mirrors `models.BuildResult`).
    `wheel_path`/`sdist_path` are the discovered artifacts' paths (module
    docstring), or `None` when the build failed (`returncode != 0`, so
    discovery is skipped entirely -- a stale artifact from an earlier
    successful build must never be reported as this call's own output) or
    no matching file was found. `wheel_version` is the wheel filename's own
    parsed version, stringified -- `package.py::build()`'s one point of
    comparison against `engines.pixi`'s own `conda_version` (FR-22); this
    module does not itself compare it against the sdist's own parsed
    version (spec Never boundary: no field on `models.PackageBuildResult`
    carries a separate sdist version). `stdout` is the child's captured
    stdout in full (review pass, 2026-08-13) -- mirrors `models.BuildResult.
    stdout`'s own precedent: a build failure investigated outside a live
    terminal (CI, a captured test run) needs diagnostic text, not a bare
    returncode integer."""

    returncode: int
    wheel_path: str | None
    sdist_path: str | None
    wheel_version: str | None
    stdout: str


def _newest(paths: list[Path]) -> Path | None:
    """Return the most recently modified path in `paths`, or `None` if
    empty -- resolves ambiguity when a dirty `dist/` holds more than one
    matching file (module docstring)."""
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def build(project_path: str, *, timeout: float | None = None) -> Pep517BuildResult:
    """Build `project_path`'s wheel+sdist via `pyproject-build --no-
    isolation` (FR-15, FR-21).

    Raises `EngineAbsentError` (via `require_engine`) before any subprocess
    spawns if the `build` engine is not on `PATH` (spec Always boundary).
    Runs with `cwd=project_path` -- `pyproject-build`'s own `srcdir`
    positional defaults to its process cwd, so no explicit source-directory
    argument is needed once `cwd` is set (mirrors the existing hand-run
    `pyforge-mason-build-dist` pixi task's own invocation shape: `python -m
    build --no-isolation --outdir dist` from that same `cwd` --
    `pyproject-build` IS the `python -m build` frontend's console-script
    entry point, per `engines/__init__.py`'s module docstring). Output lands
    at `<project_path>/dist/` (spec Always boundary, FR-24) -- the same
    directory name that task's own `--outdir dist` (relative to its `cwd`)
    produces.

    `timeout` defaults to `_PEP517_BUILD_TIMEOUT_SECONDS` when `None`,
    mirroring every `cfe.py` adapter's own per-operation-default
    convention. A non-zero return code is DATA on the returned
    `Pep517BuildResult`, never raised (AD-4, spec Always boundary) -- the
    caller decides what a failed build means; this function only reports
    it.

    Raises `PackageBuildTimeoutError` (review pass, 2026-08-13) when the
    child exceeds `timeout` -- `subprocess.run`'s own timeout handling has
    already killed and reaped the child by the time that exception reaches
    here, mirroring `cfe.py::_invoke_captured`'s identical translation.
    Raises `PackageProjectPathError` when `cwd=project_path` itself fails
    (`OSError` -- e.g. `project_path` does not exist or is not a directory):
    this is NOT the "wrapped tool reports its own failure via returncode"
    case above, since the tool never even starts.
    """
    require_engine("build")

    outdir = f"{project_path}/dist"
    resolved_timeout = timeout if timeout is not None else _PEP517_BUILD_TIMEOUT_SECONDS
    argv = [_BINARY_NAME, "--no-isolation", "--outdir", outdir]
    try:
        completed = subprocess.run(
            argv,
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=resolved_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise PackageBuildTimeoutError(engine=name, timeout=resolved_timeout) from None
    except OSError as exc:
        raise PackageProjectPathError(project_path=project_path, reason=str(exc)) from None

    if completed.returncode != 0:
        return Pep517BuildResult(
            returncode=completed.returncode,
            wheel_path=None,
            sdist_path=None,
            wheel_version=None,
            stdout=completed.stdout,
        )

    wheel = _newest(list(Path(outdir).glob("*.whl")))
    sdist = _newest([*Path(outdir).glob("*.tar.gz"), *Path(outdir).glob("*.zip")])

    wheel_version: str | None = None
    if wheel is not None:
        try:
            _, version, _, _ = parse_wheel_filename(wheel.name)
        except InvalidWheelFilename:
            wheel = None
        else:
            wheel_version = str(version)

    if sdist is not None:
        try:
            parse_sdist_filename(sdist.name)
        except InvalidSdistFilename:
            sdist = None

    return Pep517BuildResult(
        returncode=completed.returncode,
        wheel_path=str(wheel) if wheel is not None else None,
        sdist_path=str(sdist) if sdist is not None else None,
        wheel_version=wheel_version,
        stdout=completed.stdout,
    )
