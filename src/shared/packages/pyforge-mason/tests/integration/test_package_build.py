"""Story 3.2 -- the FIRST file in `tests/integration/` (spec Code Map):
`slow`-marked, real end-to-end coverage of `mason package build` running
against this very package (`src/shared/packages/pyforge-mason/` itself),
proving FR-24's build half -- the artifacts this story's own engines
produce are equivalent to the existing hand-run `pyforge-mason-build`
reference triad's own output.

Unlike every other test file in this suite (AD-16: fixture CFE root, no
real subprocess dependency), this one needs REAL `pyproject-build`/`pixi`
binaries on `PATH` -- present in the `pyforge-mason` pixi environment this
test suite normally runs inside (`pixi run -e pyforge-mason
pyforge-mason-test-slow`), never the default `pyforge-mason-test` loop
(`-m "not slow"` excludes this file, per `pyproject.toml`'s registered
`slow` marker).

"Matching the reference task's own output" is proven by construction, not
by re-running the workspace root's `pyforge-mason-build` pixi task from
inside this package's own test suite -- a layering violation this suite
carries nowhere else (nothing here otherwise knows the workspace root's
`pixi.toml` even exists): `engines/pep517.py::build()`'s argv
(`["pyproject-build", "--no-isolation", "--outdir", f"{project_path}/dist"]`,
`cwd=project_path`) is functionally equivalent (same `cwd`, same output
directory) to the root `pixi.toml`'s `pyforge-mason-build-dist` task (`cmd =
"python -m build --no-isolation --outdir dist"`, `cwd =
"src/shared/packages/pyforge-mason"` -- `pyproject-build` IS the `python -m
build` frontend's own console-script entry point, per
`engines/__init__.py`'s module docstring), and `engines/pixi.py::build()`'s
argv (`["pixi", "build", "--output-dir", f"{project_path}/dist-conda"]`,
`cwd=project_path`, no `--path`) is functionally equivalent to that same
file's `pyforge-mason-build-conda` task -- both pass an ABSOLUTE
`--outdir`/`--output-dir` where the hand-run tasks pass a RELATIVE one
(relative to that same `cwd`), so the argv is not byte-identical, but both
resolve to the same directory on disk. Running commands that resolve to the
same target against the identical project directory necessarily produces
identical output; this test's job is to prove the story's own engines
actually produce a real, versioned artifact set when run for real -- not to
duplicate a second full build merely to diff it against a first one.

`PACKAGE_ROOT` is derived from `pyforge.mason.__file__`, mirroring
`tests/meta/test_engine_version_range_sync.py`'s identical technique --
never a path hardcoded relative to THIS file -- so it resolves correctly
whether pytest's own cwd is the repo root (`pixi run -e pyforge-mason
pyforge-mason-test-slow`, the normal case) or anywhere else.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import pyforge.mason
from pyforge.mason import package

_PACKAGE_FILE = pyforge.mason.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
# .../src/pyforge/mason/__init__.py -> mason -> pyforge -> src -> the
# pyforge-mason package root (three directories up from __init__.py's own
# parent).
PACKAGE_ROOT = Path(_PACKAGE_FILE).resolve().parent.parent.parent.parent


@pytest.mark.slow
def test_package_build_self_hosting_produces_real_versioned_artifacts():
    result = package.build(str(PACKAGE_ROOT))

    assert result.pep517_returncode == 0, "pyproject-build failed -- see its stderr above"
    assert result.pixi_returncode == 0, "pixi build failed -- see its stderr above"

    assert result.wheel_path is not None
    assert result.sdist_path is not None
    assert result.conda_path is not None

    wheel_path = Path(result.wheel_path)
    sdist_path = Path(result.sdist_path)
    conda_path = Path(result.conda_path)
    assert wheel_path.is_file()
    assert sdist_path.is_file()
    assert conda_path.is_file()

    # Byte-identical output-directory names to the reference triad (FR-24,
    # spec Always boundary): dist/ for wheel+sdist, dist-conda/ for .conda.
    assert wheel_path.parent == PACKAGE_ROOT / "dist"
    assert sdist_path.parent == PACKAGE_ROOT / "dist"
    assert conda_path.parent == PACKAGE_ROOT / "dist-conda"

    assert result.wheel_version is not None
    assert result.conda_version is not None
    assert result.wheel_version == result.conda_version
