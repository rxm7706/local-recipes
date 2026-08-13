"""`mason package` -- build and ship distributions to PyPI and conda-forge
(FR-15 - FR-24).

Seeded here, docstring-only, solely to prove AD-6's import-safety invariant
(Story 1.7): `package.py` is CFE-independent except for its future
`conda-forge` ship target, which is permitted to import `cfe` *lazily*
(nested inside a function body) but never at module scope -- a `pypi` ship
must succeed with the CFE root absent. `tests/meta/test_capability_tiers.py`
guards this file for exactly that: no module-level `cfe` import, ever.

Epic 3 supplies the real content: wheel/`.conda`/sdist construction
(`engines/pep517`, `engines/pixi`), the `twine` upload path, and the
`conda-forge` ship target that calls into `recipe.py` through the CFE port
(AD-11).

Story 3.2 adds the first real content, `build()` (FR-15, FR-21, FR-22):
drives Story 3.1's engine protocol through two new adapters,
`engines.pep517` (wheel+sdist via `pyproject-build --no-isolation`) and
`engines.pixi` (`.conda` via `pixi build`), and composes their outcomes
into one `models.PackageBuildResult`. Both adapters are called
UNCONDITIONALLY and IN SEQUENCE -- `pep517.build()` first, then
`pixi.build()` -- never gated behind an upfront joint presence check of
both engines: each adapter's own `require_engine` call inside its own
`build()` function is the ONE presence gate (spec Always boundary, mirrors
`recipe.build()`'s own per-branch gating precedent), so a project missing
only `pixi` from `PATH` still runs the (successful) `build`-engine half
before `EngineAbsentError` propagates from the `pixi` half -- "nothing
built" in the spec's own I/O matrix describes the command's overall
reported outcome (no `PackageBuildResult` is ever returned), not a claim
that the PRESENT engine's own subprocess never ran.

`project_path` is resolved to an absolute string ONCE here
(`Path(project_path).expanduser().resolve()`), before either adapter is
called, and that same resolved string is what both receive and what lands
on `PackageBuildResult.project_path` -- NOT an existence/validity check
(`Path.resolve()` succeeds on a path that does not exist, mirroring
`recipe.py::submit()`'s identical `recipe_dir` resolution -- spec Always
boundary: "No Mason-side existence/validity check on PROJECT_PATH"). This
is necessary, not cosmetic: each adapter's own subprocess runs with
`cwd=project_path` AND separately builds its own `--outdir`/`--output-dir`
argument by interpolating that SAME `project_path` string (spec Design
Notes/Tasks) -- so a relative `project_path` would have the child process
interpret that outdir argument relative to ITS OWN cwd (already `project_
path`), doubling the path (`<caller's cwd>/<project_path>/<project_path>/
dist`). Resolving once, up front, to an absolute string makes both
interpolations agree regardless of what the caller passed.

Zero `cfe` reference anywhere in this file (spec Always boundary,
`tests/meta/test_capability_tiers.py` guards it): `build()` never resolves
a CFE root or interpreter, unlike every `recipe.py` verb.
"""

from __future__ import annotations

from pathlib import Path

from packaging.version import InvalidVersion, Version

from .engines import pep517, pixi
from .errors import PackageProjectPathError, PackageVersionMismatchError
from .models import PackageBuildResult


def _versions_disagree(wheel_version: str, conda_version: str) -> bool:
    """Compare two version strings via `packaging.version.Version`, never
    raw string equality (architecture Consistency Conventions: "Versions
    are strings, compared via `packaging.version`, never string-compared").

    `wheel_version` is already PEP-440-canonicalized (`engines.pep517`'s
    own `parse_wheel_filename`-derived value), but `conda_version` is the
    RAW, unparsed segment out of the `.conda` filename (`engines.pixi`'s own
    deliberate design -- kept raw so FR-22's comparison sees exactly what
    `pixi build` named, AD-1). Comparing a canonicalized string against a
    raw one with `!=` can false-positive on formatting differences that mean
    the same version (e.g. `"1.0.0"` vs `"1.0"`). Falls back to raw string
    comparison only when either side fails to parse as a `Version`
    (`InvalidVersion`) -- conda version strings are not guaranteed to be
    strict PEP 440, so a parse failure must degrade gracefully, never crash
    the comparison itself.
    """
    try:
        return Version(wheel_version) != Version(conda_version)
    except InvalidVersion:
        return wheel_version != conda_version


def build(project_path: str, *, target: str = "library") -> PackageBuildResult:
    """Build `project_path`'s distributable artifacts: wheel+sdist via PEP
    517 (`engines.pep517`) and a `.conda` package via `pixi build`
    (`engines.pixi`) -- FR-15, FR-21.

    `target` is the caller's own `--target` value; `cli.py`'s own
    `choices=("library",)` restricts it before this function is ever
    reached (v1 scope, FR-21) -- this function applies no validation of its
    own, it is only carried through onto the returned result.

    After both adapters return, when BOTH `wheel_version` and `conda_
    version` are non-`None` and they disagree, raises `PackageVersionMismatchError`
    naming both (FR-22) -- before this function returns a result. Either
    value is `None` when its own engine's build failed (`returncode != 0`)
    or produced no artifact this module's own discovery could find; the
    comparison is skipped entirely in that case (spec I/O matrix: "One
    engine's build fails" reports data, never raises).

    See this module's own docstring for why `project_path` is resolved to
    an absolute string before either adapter runs, and why the two adapters
    are called unconditionally in sequence rather than behind an upfront
    joint presence check.

    Raises `PackageProjectPathError` (review pass, 2026-08-13) when
    `project_path` cannot even be resolved -- `Path.resolve()` itself raises
    `OSError`/`ValueError` for a pathological input (a null byte, an
    unreadable parent directory hit during symlink resolution); the
    ORIGINAL caller-supplied `project_path` names the error, since the
    resolved form was never successfully computed.
    """
    try:
        resolved_project_path = str(Path(project_path).expanduser().resolve())
    except (OSError, ValueError) as exc:
        raise PackageProjectPathError(project_path=project_path, reason=str(exc)) from None

    pep517_result = pep517.build(resolved_project_path)
    pixi_result = pixi.build(resolved_project_path)

    if (
        pep517_result.wheel_version is not None
        and pixi_result.conda_version is not None
        and _versions_disagree(pep517_result.wheel_version, pixi_result.conda_version)
    ):
        raise PackageVersionMismatchError(
            wheel_version=pep517_result.wheel_version,
            conda_version=pixi_result.conda_version,
            wheel_path=pep517_result.wheel_path,
            conda_path=pixi_result.conda_path,
        )

    return PackageBuildResult(
        target=target,
        project_path=resolved_project_path,
        wheel_path=pep517_result.wheel_path,
        sdist_path=pep517_result.sdist_path,
        conda_path=pixi_result.conda_path,
        wheel_version=pep517_result.wheel_version,
        conda_version=pixi_result.conda_version,
        pep517_returncode=pep517_result.returncode,
        pixi_returncode=pixi_result.returncode,
        pep517_stdout=pep517_result.stdout,
        pixi_stdout=pixi_result.stdout,
    )
