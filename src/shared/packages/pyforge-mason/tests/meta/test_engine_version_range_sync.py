"""Meta test — the pixi.toml / engines/__init__.py version-range sync guard
(Story 3.1), ported from `pyforge-warden`'s identical guard
(`tests/meta/test_engine_version_range_sync.py` there).

`pixi.toml`'s `pixi`/`twine`/`conda-lock`/`python-build`/`gh` run-dependency
pins and `engines/__init__.py`'s `PIXI_VERSION_RANGE`/`TWINE_VERSION_RANGE`/
`CONDA_LOCK_VERSION_RANGE`/`PYTHON_BUILD_VERSION_RANGE`/`GH_VERSION_RANGE`
`SpecifierSet` constants must never drift apart — one edited without the
other is exactly the failure mode this guard exists to catch. Story 3.7
adds the fifth pair (`gh`/`GH_VERSION_RANGE`), extended with the identical
five assertion shapes the other four already have.

The comparison runs BOTH sides through `packaging.specifiers.SpecifierSet`
before comparing their `str()` forms byte-for-byte, rather than comparing
`pixi.toml`'s raw string directly: `SpecifierSet.__str__` canonicalizes
specifier ORDER (e.g. `str(SpecifierSet(">=0.76.2,<0.77"))` equals
`"<0.77,>=0.76.2"`, per its own docstring — "the ordering of the individual
specifiers within the set may not match the input string"), so a literal
string comparison would fire on the repo's own conventional `">=X,<Y"` pin
style even with zero semantic drift. Normalizing both sides through the SAME
machinery keeps the guard sensitive to REAL drift (a different version
bound) while staying silent on cosmetic reordering."""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version

import pyforge.mason
from pyforge.mason.engines import (
    CONDA_LOCK_VERSION_RANGE,
    GH_VERSION_RANGE,
    PIXI_VERSION_RANGE,
    PYTHON_BUILD_VERSION_RANGE,
    TWINE_VERSION_RANGE,
)

_PACKAGE_FILE = pyforge.mason.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
# .../src/pyforge/mason/__init__.py -> mason -> pyforge -> src -> package
# root (three directories up from __init__.py's own parent), where
# pixi.toml lives.
PACKAGE_ROOT = Path(_PACKAGE_FILE).resolve().parent.parent.parent.parent
PIXI_TOML = PACKAGE_ROOT / "pixi.toml"


def _run_dependencies() -> dict[str, object]:
    with PIXI_TOML.open("rb") as stream:
        data = tomllib.load(stream)
    return data["package"]["run-dependencies"]


def test_pixi_toml_is_found_where_expected():
    assert PIXI_TOML.is_file(), f"pixi.toml not found at {PIXI_TOML}"
    run_deps = _run_dependencies()
    assert "pixi" in run_deps
    assert "twine" in run_deps
    assert "conda-lock" in run_deps
    assert "python-build" in run_deps
    assert "gh" in run_deps


def test_pixi_range_matches_pixi_toml():
    run_deps = _run_dependencies()
    pixi_range = SpecifierSet(str(run_deps["pixi"]))
    assert str(pixi_range) == str(PIXI_VERSION_RANGE), (
        "pixi.toml's pixi run-dependency range and engines/__init__.py's "
        "PIXI_VERSION_RANGE have drifted apart — edit both together"
    )


def test_twine_range_matches_pixi_toml():
    run_deps = _run_dependencies()
    pixi_range = SpecifierSet(str(run_deps["twine"]))
    assert str(pixi_range) == str(TWINE_VERSION_RANGE), (
        "pixi.toml's twine run-dependency range and engines/__init__.py's "
        "TWINE_VERSION_RANGE have drifted apart — edit both together"
    )


def test_conda_lock_range_matches_pixi_toml():
    run_deps = _run_dependencies()
    pixi_range = SpecifierSet(str(run_deps["conda-lock"]))
    assert str(pixi_range) == str(CONDA_LOCK_VERSION_RANGE), (
        "pixi.toml's conda-lock run-dependency range and "
        "engines/__init__.py's CONDA_LOCK_VERSION_RANGE have drifted apart "
        "— edit both together"
    )


def test_python_build_range_matches_pixi_toml():
    run_deps = _run_dependencies()
    pixi_range = SpecifierSet(str(run_deps["python-build"]))
    assert str(pixi_range) == str(PYTHON_BUILD_VERSION_RANGE), (
        "pixi.toml's python-build run-dependency range and "
        "engines/__init__.py's PYTHON_BUILD_VERSION_RANGE have drifted "
        "apart — edit both together"
    )


def test_gh_range_matches_pixi_toml():
    run_deps = _run_dependencies()
    pixi_range = SpecifierSet(str(run_deps["gh"]))
    assert str(pixi_range) == str(GH_VERSION_RANGE), (
        "pixi.toml's gh run-dependency range and engines/__init__.py's "
        "GH_VERSION_RANGE have drifted apart — edit both together"
    )


def test_ranges_are_ranges_not_exact_pins():
    """NFR-C1-style convention (matching pyforge-warden's identical guard):
    a range, not an exact pin — engines come from feedstocks. Since the
    2026-09-20 operator ruling ("never cap without a reason") a range is a
    floor (`>=X.Y.Z`, one specifier) unless a ceiling carries a written
    reason; only `PIXI_VERSION_RANGE` does (an in-env pixi above the
    workspace's `requires-pixi` line would parse a manifest the workspace has
    not tested)."""
    for rng in (
        PIXI_VERSION_RANGE,
        TWINE_VERSION_RANGE,
        CONDA_LOCK_VERSION_RANGE,
        PYTHON_BUILD_VERSION_RANGE,
        GH_VERSION_RANGE,
    ):
        assert len(rng) >= 1
        assert all(spec.operator != "==" for spec in rng), f"exact pin in {rng}"
    assert len(PIXI_VERSION_RANGE) == 2  # the one reasoned window


def test_evidence_backed_versions_are_in_range():
    """The exact versions this codebase has live-verified evidence for (spec
    Always boundary: pixi 0.80.0 — 2026-09-11, build+ship self-hosting
    integration green against it — twine 7.0.0, conda-lock 4.0.2, build
    1.6.0 (the floor the fleet's other features pin; 2026-09-20), gh 2.97.0)
    must be inside their own range — a vacuous guard (a range that excludes
    its own evidence) would be worse than no guard at all."""
    assert Version("0.80.0") in PIXI_VERSION_RANGE
    assert Version("7.0.0") in TWINE_VERSION_RANGE
    assert Version("4.0.2") in CONDA_LOCK_VERSION_RANGE
    assert Version("1.6.0") in PYTHON_BUILD_VERSION_RANGE
    assert Version("2.97.0") in GH_VERSION_RANGE


def test_floors_carry_no_unreasoned_ceiling():
    """Operator ruling 2026-09-20 ("remove unnecessary caps"): the
    `pyforge-foundry-full` union env could not solve while `python-build`
    carried a `<1.6` window against the `>=1.6.0` floors pyforge-ci /
    pyforge-core / pyforge-testing-kit / local-recipes pin. Every engine
    range except pixi's is a bare floor: the next minor is allowed, and a
    breaking engine release is caught by the build+ship integration tests,
    not by a ceiling that also blocks every compatible release."""
    for rng in (TWINE_VERSION_RANGE, CONDA_LOCK_VERSION_RANGE, PYTHON_BUILD_VERSION_RANGE, GH_VERSION_RANGE):
        assert [spec.operator for spec in rng] == [">="], f"unreasoned ceiling in {rng}"
    assert Version("7.1.0") in TWINE_VERSION_RANGE
    assert Version("1.7.0") in PYTHON_BUILD_VERSION_RANGE
    # pixi keeps its reasoned window
    assert Version("0.81.0") not in PIXI_VERSION_RANGE
