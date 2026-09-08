"""Conformance test — ``PixiLockExtractor`` vs. py-rattler's ``LockFile``
parse (Story 2.6), the test-side oracle for the pixi.lock format.
``py-rattler`` is a TEST-ONLY dependency (``pixi.toml``'s
``[feature.pyforge-warden.dependencies]`` — never a ``pyforge-warden``
runtime dependency). If it is not importable this suite HARD-FAILS (never
skips) — matches the 1.5 provisioned-engine convention
(``test_osv_engine.py``).

Scope note: only ``PixiLockExtractor`` gets an oracle here — ``py-rattler``
has no ``conda-lock.yml`` parser of its own (that format's rows are always
explicit name/version/manager, needing no basename-parsing oracle).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.warden.discovery import PIXI_LOCK_KIND
from pyforge.warden.extract.lockfiles import PixiLockExtractor
from pyforge.warden.models import Ecosystem, ScannedManifest
from pyforge.warden.routing import DefaultRouter

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "projects"
    / "pixi_lock_basic"
    / "pixi.lock"
)
MANIFEST = ScannedManifest(path="pixi.lock", kind=PIXI_LOCK_KIND)


def _rattler_module():
    try:
        import rattler
    except ImportError:
        pytest.fail(
            "py-rattler is not importable -- it is a test-only oracle "
            "dependency (pixi.toml's [feature.pyforge-warden.dependencies]); "
            "a missing import is a broken environment, not an excused "
            "(skipped) test. Run this suite via "
            "`pixi run -e pyforge-warden pyforge-warden-test`."
        )
    return rattler


@pytest.fixture(autouse=True, scope="module")
def _require_py_rattler() -> None:
    _rattler_module()


def test_pixi_lock_extractor_matches_py_rattler_lockfile():
    rattler = _rattler_module()
    components = PixiLockExtractor(DefaultRouter()).extract(FIXTURE, MANIFEST)
    ours = {
        (component.ecosystem, component.name, component.version)
        for component in components
    }
    assert ours, "the fixture must contribute at least one component"

    lock_file = rattler.LockFile.from_path(FIXTURE)
    env = lock_file.default_environment()
    assert env is not None

    oracle: set[tuple[Ecosystem, str, str | None]] = set()
    for _platform, packages in env.packages_by_platform().items():
        for package in packages:
            if isinstance(package, rattler.PypiLockedPackage):
                oracle.add((Ecosystem.PYPI, package.name, package.version))
            elif isinstance(package, rattler.CondaLockedPackage):
                oracle.add((Ecosystem.CONDA, package.name, str(package.version)))

    assert ours == oracle


def test_url_basename_pitfall_matches_py_rattler_lockfile():
    rattler = _rattler_module()
    pitfall_path = FIXTURE.parent.parent / "pixi_lock_url_basename_pitfall" / "pixi.lock"
    components = PixiLockExtractor(DefaultRouter()).extract(pitfall_path, MANIFEST)
    ours = {(c.ecosystem, c.name, c.version) for c in components}

    lock_file = rattler.LockFile.from_path(pitfall_path)
    env = lock_file.default_environment()
    assert env is not None
    oracle: set[tuple[Ecosystem, str, str | None]] = set()
    for _platform, packages in env.packages_by_platform().items():
        for package in packages:
            if isinstance(package, rattler.CondaLockedPackage):
                oracle.add((Ecosystem.CONDA, package.name, str(package.version)))

    assert ours == oracle
    assert oracle == {(Ecosystem.CONDA, "_openmp_mutex", "4.5")}
