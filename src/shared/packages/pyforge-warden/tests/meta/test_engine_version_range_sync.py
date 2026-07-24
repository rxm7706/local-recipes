"""Meta test — the pixi.toml / engines.py version-range sync guard (Story
6.6, the distribution gate).

``pixi.toml``'s ``deptry``/``osv-scanner`` run-dependency pins and
``engines.py``'s ``DEPTRY_VERSION_RANGE``/``OSV_SCANNER_VERSION_RANGE``
``SpecifierSet`` constants must never drift apart — one edited without the
other is exactly the failure mode this guard exists to catch.

The comparison runs BOTH sides through ``packaging.specifiers.SpecifierSet``
before comparing their ``str()`` forms byte-for-byte, rather than comparing
``pixi.toml``'s raw string directly: ``SpecifierSet.__str__`` canonicalizes
specifier ORDER (e.g. ``str(SpecifierSet(">=0.25.1,<0.26"))`` equals
``"<0.26,>=0.25.1"``, per its own docstring — "the ordering of the individual
specifiers within the set may not match the input string"), so a literal
string comparison would fire on the repo's own conventional ``">=X,<Y"`` pin
style even with zero semantic drift. Normalizing both sides through the SAME
machinery keeps the guard sensitive to REAL drift (a different version
bound) while staying silent on cosmetic reordering."""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.specifiers import SpecifierSet

import pyforge.warden
from pyforge.warden.engines import DEPTRY_VERSION_RANGE, OSV_SCANNER_VERSION_RANGE

_PACKAGE_FILE = pyforge.warden.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
# .../src/pyforge/warden/__init__.py -> warden -> pyforge -> src -> package
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
    assert "deptry" in run_deps
    assert "osv-scanner" in run_deps


def test_deptry_range_matches_pixi_toml():
    run_deps = _run_dependencies()
    pixi_range = SpecifierSet(str(run_deps["deptry"]))
    assert str(pixi_range) == str(DEPTRY_VERSION_RANGE), (
        "pixi.toml's deptry run-dependency range and engines.py's "
        "DEPTRY_VERSION_RANGE have drifted apart — edit both together"
    )


def test_osv_scanner_range_matches_pixi_toml():
    run_deps = _run_dependencies()
    pixi_range = SpecifierSet(str(run_deps["osv-scanner"]))
    assert str(pixi_range) == str(OSV_SCANNER_VERSION_RANGE), (
        "pixi.toml's osv-scanner run-dependency range and engines.py's "
        "OSV_SCANNER_VERSION_RANGE have drifted apart — edit both together"
    )


def test_ranges_are_ranges_not_exact_pins():
    """NFR-C1: a range, not an exact pin — engines come from feedstocks."""
    assert len(DEPTRY_VERSION_RANGE) >= 2
    assert len(OSV_SCANNER_VERSION_RANGE) >= 2


def test_evidence_backed_versions_are_in_range():
    """The exact minors this codebase has verified output-schema evidence
    for (deptry 0.25.1, osv-scanner 2.4.0) must be inside their own range —
    a vacuous guard (a range that excludes its own evidence) would be worse
    than no guard at all."""
    from packaging.version import Version

    assert Version("0.25.1") in DEPTRY_VERSION_RANGE
    assert Version("2.4.0") in OSV_SCANNER_VERSION_RANGE


def test_ranges_do_not_widen_to_the_next_untested_minor():
    """NFR-C1's entire point: an untested newer minor must fail loud, not
    silently pass."""
    from packaging.version import Version

    assert Version("0.26.0") not in DEPTRY_VERSION_RANGE
    assert Version("2.5.0") not in OSV_SCANNER_VERSION_RANGE
