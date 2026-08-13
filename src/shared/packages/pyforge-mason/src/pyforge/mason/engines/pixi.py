"""`pixi` engine adapter (AD-12, Story 3.2): `.conda` package construction
via `pixi build` (FR-15, FR-21).

Mirrors `engines/pep517.py`'s own shape and rationale exactly (module-level
`name`/`probe()`/`build()`, STREAM mode without porting `cfe.run_streamed`,
filesystem-based artifact discovery rather than stdout parsing) -- see that
module's docstring for the shared reasoning; only the wrapped tool, its
argv shape, and its own filename-parsing technique differ.

`_BINARY_NAME` duplicates `engines/__init__.py`'s own
`_KNOWN_ENGINES["pixi"]` entry (`"pixi"`) -- the same sanctioned small-fact
duplication `engines/pep517.py` uses for its own `_BINARY_NAME` (see that
module's docstring).

`.conda` filename version parsing (spec Design Notes): conda's own
package/version/build-string filename fields never contain a literal `-`,
so splitting the stem on the LAST two `-` characters is a safe, general
parse even though this specific project's own name (`pyforge-mason`)
itself contains one:

    stem = conda_path.name.removesuffix(".conda")
    name, version, build_string = stem.rsplit("-", 2)

`packaging.version.Version` is deliberately NOT used to re-parse this
result (unlike `engines/pep517.py`'s wheel/sdist versions): the version
segment is kept as the RAW string the `.conda` filename convention already
encodes, so `package.py::build()`'s FR-22 mismatch comparison sees exactly
what `pixi build` itself named, not a Mason-side reinterpretation of it
(AD-1).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import probe_engine, require_engine
from ..errors import PackageBuildTimeoutError, PackageProjectPathError

name = "pixi"
"""`EngineAdapter.name` -- an `engines/__init__.py::_KNOWN_ENGINES` key."""

_BINARY_NAME = "pixi"
"""Duplicates `_KNOWN_ENGINES["pixi"]` (module docstring)."""

_PIXI_BUILD_TIMEOUT_SECONDS = 600.0
"""Mirrors `engines/pep517.py::_PEP517_BUILD_TIMEOUT_SECONDS` -- same
generous ten-minute allowance for a from-source build; no live evidence yet
that `.conda` construction runs meaningfully longer or shorter than the
wheel/sdist path for this project."""


def probe() -> str | None:
    """`EngineAdapter.probe()` -- mirrors `engines/pep517.py::probe`."""
    return probe_engine(name, _BINARY_NAME).version


@dataclass(frozen=True)
class PixiBuildResult:
    """One `build()` call's outcome -- mirrors `engines.pep517.
    Pep517BuildResult`'s own shape and rationale. `conda_path` is the
    discovered `.conda` artifact's path, or `None` under the same
    "build failed or nothing found" conditions that module documents.
    `conda_version` is the RAW version segment the `.conda` filename
    convention encodes (module docstring) -- never re-parsed through
    `packaging.version.Version`. `stdout` is the child's captured stdout in
    full (review pass, 2026-08-13) -- mirrors `models.BuildResult.stdout`'s
    own precedent: a build failure investigated outside a live terminal (CI,
    a captured test run) needs diagnostic text, not a bare returncode
    integer."""

    returncode: int
    conda_path: str | None
    conda_version: str | None
    stdout: str


def _newest(paths: list[Path]) -> Path | None:
    """Mirrors `engines.pep517._newest` exactly (this module's own
    docstring: filesystem-based discovery, not stdout parsing)."""
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def build(project_path: str, *, timeout: float | None = None) -> PixiBuildResult:
    """Build `project_path`'s `.conda` package via `pixi build` (FR-15,
    FR-21).

    Raises `EngineAbsentError` (via `require_engine`) before any subprocess
    spawns if the `pixi` engine is not on `PATH` (spec Always boundary).
    Runs with `cwd=project_path`, no `--path` flag -- `pixi build` searches
    its own cwd for a supported manifest when `--path` is omitted (verified
    live against the installed `pixi` binary), mirroring the existing
    hand-run `pyforge-mason-build-conda` pixi task's own invocation shape
    (`pixi build --output-dir dist-conda` from that same `cwd`) and this
    story's own Block-If clause: `pixi build` has no `--manifest-path` flag
    (root `pixi.toml`'s own comment), only `--path`, which behaves
    identically to omitting it entirely when `cwd` already IS the target
    directory. Output lands at `<project_path>/dist-conda/` (spec Always
    boundary, FR-24) -- the same directory name that task's own
    `--output-dir dist-conda` (relative to its `cwd`) produces.

    `timeout` defaults to `_PIXI_BUILD_TIMEOUT_SECONDS` when `None`. A
    non-zero return code is DATA on the returned `PixiBuildResult`, never
    raised (AD-4, spec Always boundary).

    Raises `PackageBuildTimeoutError` (review pass, 2026-08-13) when the
    child exceeds `timeout` -- mirrors `engines.pep517.build`'s identical
    translation (see that module's docstring). Raises
    `PackageProjectPathError` when `cwd=project_path` itself fails
    (`OSError` -- e.g. `project_path` does not exist or is not a directory):
    this is NOT the "wrapped tool reports its own failure via returncode"
    case above, since the tool never even starts.
    """
    require_engine("pixi")

    outdir = f"{project_path}/dist-conda"
    resolved_timeout = timeout if timeout is not None else _PIXI_BUILD_TIMEOUT_SECONDS
    argv = [_BINARY_NAME, "build", "--output-dir", outdir]
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
        return PixiBuildResult(
            returncode=completed.returncode,
            conda_path=None,
            conda_version=None,
            stdout=completed.stdout,
        )

    conda_path = _newest(list(Path(outdir).glob("*.conda")))
    conda_version: str | None = None
    if conda_path is not None:
        stem = conda_path.name.removesuffix(".conda")
        parts = stem.rsplit("-", 2)
        if len(parts) == 3 and parts[1]:
            conda_version = parts[1]
        else:
            conda_path = None

    return PixiBuildResult(
        returncode=completed.returncode,
        conda_path=str(conda_path) if conda_path is not None else None,
        conda_version=conda_version,
        stdout=completed.stdout,
    )
