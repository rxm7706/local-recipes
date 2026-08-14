"""Story 3.8 -- the `ship` counterpart to `test_package_build.py`'s Story
3.2 self-hosting proof: `slow`-marked, real end-to-end coverage of
`package.ship(...)` running its dry-run (`confirm=False`) plan against this
very package (`src/shared/packages/pyforge-mason/` itself), proving FR-24/
SM-1's "Mason ships Mason" claim for the mechanism -- short of the real,
credentialed, irreversible publish, which is a separately-tracked operator
action (see this story's own spec Design Notes).

Every existing `ship()`/`ship_pypi` test elsewhere in this suite mocks the
`build`/`pep517`/`pixi` engines; this file does not -- it needs REAL
`pyproject-build`/`pixi` binaries on `PATH`, exactly like `test_package_
build.py`, so it carries the identical `@pytest.mark.slow` marker and runs
only via `pixi run -e pyforge-mason pyforge-mason-test-slow`, never the
default `pyforge-mason-test` loop (`-m "not slow"` excludes this file, per
`pyproject.toml`'s registered `slow` marker).

`confirm=False` means `ship()` never calls a target adapter or a network
tool -- it builds once (real wheel/sdist via `pep517`, real `.conda` via
`pixi build`) and hands the result to `plan_ship`, which only reads already-
built paths and formats a message. Zero credentials are read (the `TWINE_
USERNAME`/`TWINE_PASSWORD` check lives inside `ship_pypi`, reached only when
`confirm=True`), zero network calls are made, zero uploads happen -- this
test's own risk profile matches `test_package_build.py`'s exactly.

Requesting `pypi-test,pypi` exercises `plan_ship`'s two PyPI-shaped
branches, NOT the FR-24/FR-50/AD-26 rehearsal gate itself -- that gating
logic lives entirely in `ship()`'s `confirm=True` branch, never reached by
a dry run. The gate's own behavior is already covered by mocked unit
coverage in `tests/unit/test_package.py`; this file proves the dry-run plan
is real and correct, nothing more.

`build()` runs both engines unconditionally here (neither target is
`conda-forge`), so this test also verifies the `.conda` side explicitly --
`plan_ship`'s own PYPI/PYPI_TEST messages never reference `conda_path`, so
a `pixi build` regression would otherwise be invisible to this test.

`PACKAGE_ROOT` is derived from `pyforge.mason.__file__`, the identical
technique `test_package_build.py` uses -- never a path hardcoded relative to
THIS file -- so it resolves correctly regardless of pytest's own cwd.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import pyforge.mason
from pyforge.mason import package
from pyforge.mason.models import ShipState, ShipTargetResult

_PACKAGE_FILE = pyforge.mason.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
# .../src/pyforge/mason/__init__.py -> mason -> pyforge -> src -> the
# pyforge-mason package root (three directories up from __init__.py's own
# parent).
PACKAGE_ROOT = Path(_PACKAGE_FILE).resolve().parent.parent.parent.parent


@pytest.mark.slow
def test_package_ship_self_hosting_dry_run_names_real_artifacts():
    results = package.ship(
        "pypi-test,pypi",
        confirm=False,
        environ={},
        target="library",
        recipe_path=None,
        cfe_root_arg=None,
        cfe_python_arg=None,
        cfe_timeout_arg=None,
        start_directory=PACKAGE_ROOT,
    )

    assert len(results) == 2
    for result in results:
        assert isinstance(result, ShipTargetResult)
        assert result.state is ShipState.NOT_ATTEMPTED

    pypi_test_result, pypi_result = results
    # Input order preserved -- `parse_ship_targets`'s documented no-reorder
    # rule -- never sorted or grouped by kind.
    assert pypi_test_result.target == "pypi-test"
    assert pypi_result.target == "pypi"

    assert "irreversible" in pypi_result.message
    assert "irreversible" not in pypi_test_result.message

    # Both messages name a real, already-built artifact path -- never
    # `_describe_artifact`'s "no {label} was built" placeholder, which would
    # mean the real `pep517.build()` call above produced nothing.
    for result in (pypi_test_result, pypi_result):
        assert "no wheel was built" not in result.message
        assert "no sdist was built" not in result.message

    assert (PACKAGE_ROOT / "dist").is_dir()
    wheels = list((PACKAGE_ROOT / "dist").glob("*.whl"))
    sdists = list((PACKAGE_ROOT / "dist").glob("*.tar.gz"))
    assert wheels, "no wheel found under dist/ after a real ship dry-run build"
    assert sdists, "no sdist found under dist/ after a real ship dry-run build"

    # `plan_ship`'s PYPI/PYPI_TEST messages never reference `conda_path`, so
    # without this, a real `pixi build` regression reached via `ship()`
    # would be invisible to every assertion above (review pass 1).
    assert (PACKAGE_ROOT / "dist-conda").is_dir()
    condas = list((PACKAGE_ROOT / "dist-conda").glob("*.conda"))
    assert condas, "no .conda package found under dist-conda/ after a real ship dry-run build"
